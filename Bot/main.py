import discord
import itertools
import math
import os
import requests
import time
import toml
import trueskill
from discord.ext import commands
from dotenv import load_dotenv
import matplotlib.pyplot as plt

from state import State
from api import Api
from game import Game, Result
from player import Player, env

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='?', intents=intents)


async def check_organiser(ctx):
    try:
        return len(set(map(lambda x: x.id, ctx.author.roles)).intersection(state.roles["organiser"])) > 0
    except:
        return False


async def check_spam(ctx):
    try:
        return ctx.channel.id in state.channels["spam"]
    except:
        return False


async def check_lobby(ctx):
    try:
        return ctx.channel.id in state.channels["lobby"]
    except:
        return False


async def check_dm(ctx):
    return isinstance(ctx.channel, discord.channel.DMChannel)


async def check_organiser_lobby(ctx):
    return await check_lobby(ctx) and await check_organiser(ctx)


async def check_organiser_spam(ctx):
    return await check_spam(ctx) and await check_organiser(ctx)


def is_ranked(user: discord.Member):
    return len(set(map(lambda x: x.id, user.roles)).intersection(state.roles["ranked"])) > 0


@bot.event
async def on_ready():
    await update_leaderboard()


async def update_leaderboard():
    for message in state.leaderboard:
        try:
            await message.delete()
        except discord.errors.NotFound:
            pass
    messages = []
    for channel_id in state.channels["leaderboard"]:
        channel = bot.get_channel(channel_id)
        players = list(
            filter(lambda x: x[0] and is_ranked(x[0]), map(lambda x: (channel.guild.get_member(x), state.get_player(x) or Player()), state.players.keys())))
        players = sorted(players, key=lambda x: -x[1].conservative_rating())
        pages = math.ceil(len(players) / 20)
        for page in range(pages):
            start = 20 * page
            description = ""
            for (i, player) in enumerate(players[start:start+20], start + 1):
                name = player[0].mention
                conservative_rating = player[1].conservative_rating()
                mu = 100 * player[1].rating.mu
                sigma = 200 * player[1].rating.sigma
                description += "{}: {} - **{:.0f}** ({:.0f} ± {:.0f})\n".format(
                    i, name, conservative_rating, mu, sigma)
            embed = discord.Embed(
                title=f"Leaderboard ({page + 1}/{pages})", description=description)
            message = await channel.send(embed=embed)
            print(message)
            messages.append(message)
    state.leaderboard = messages


def balance(queue, estimates=None):
    size = len(queue) // 2
    best_score = 0
    best_teams = None
    for team1 in itertools.combinations(queue[1:], size - 1):
        team1 = queue[:1] + list(team1)
        team2 = [x for x in queue if x not in team1]
        def get_player(x): return state.get_player(x) or Player()
        if estimates is None:
            def get_rating(x): return get_player(x).rating
        else:
            def get_rating(x): return trueskill.Rating(
                mu=estimates[x], sigma=get_player(x).sigma) if x in estimates else get_player(x).rating

        team1_rating = list(map(get_rating, team1))
        team2_rating = list(map(get_rating, team2))
        score = env.quality([team1_rating, team2_rating])
        if score > best_score:
            best_score = score
            best_teams = (team1, team2)
    return best_teams, best_score


async def start_game(ctx):
    queue = list(state.queue)
    state.queue = set()
    (team1, team2), quality = balance(queue)
    state.api.create_game(Game(team1, team2))
    mentions = ""
    description = "Quality: {:.0f}\n".format(100 * quality)
    description += "\nTeam 1:\n"
    for player_id in team1:
        member = ctx.guild.get_member(player_id)
        name = member.mention
        description += f"{name}\n"
        mentions += "{} ".format(name)
    description += "\nTeam 2:\n"
    for player_id in team2:
        member = ctx.guild.get_member(player_id)
        name = member.mention
        description += f"{name}\n"
        mentions += "{} ".format(name)
    id = state.api.get_last_game().id
    title = "Game #{} started".format(id)
    embed = discord.Embed(title=title, description=description)
    message = await ctx.send(mentions, embed=embed)
    if quality < 0.8:
        organiser_role = next(
            x for x in ctx.guild.roles if x.id == state.roles["organiser"][0])
        await ctx.send("{}, the previous game has a low quality and the teams may be unbalanced. Please check if swaps are needed.".format(organiser_role.mention))
    for player_id in team1:
        try:
            member = ctx.guild.get_member(player_id)
            await member.send("Game started: {}".format(message.jump_url))
        except:
            pass
    for player_id in team2:
        try:
            member = ctx.guild.get_member(player_id)
            await member.send("Game started: {}".format(message.jump_url))
        except:
            pass


@bot.command()
@commands.check(check_organiser_lobby)
async def rebalance(ctx, *args):
    game = api.get_last_game()
    if not game:
        return
    estimates = {}
    while args:
        try:
            player, rating, *args = args
        except:
            await ctx.send("Wrong number of arguments.")
            return
        player_id = int(player)
        if player_id not in game.team1 + game.team2:
            player = ctx.guild.get_member(player_id)
            message = "{} is not in the game.".format(player.mention)
            await ctx.send(message)
            return
        rating = int(rating)
        if rating < 0 or rating > 5000:
            await ctx.send("Rating should be between 0 and 5000.")
            return
        estimates[int(player[3:-1])] = rating
    (team1, team2), quality = balance(game.team1 + game.team2, estimates)
    game.team1 = team1
    game.team2 = team2
    api.update_game(game)
    title = "Game #{}".format(game.id)
    description = "Quality: {:.0f}\n".format(100 * quality)
    description += "\nTeam 1:\n"
    for player_id in team1:
        member = ctx.guild.get_member(player_id)
        name = member.mention
        description += f"{name}\n"
    description += "\nTeam 2:\n"
    for player_id in team2:
        member = ctx.guild.get_member(player_id)
        name = member.mention
        description += f"{name}\n"
    embed = discord.Embed(title=title, description=description)
    await ctx.send(embed=embed)


async def add_player(ctx, player: discord.User):
    name = player.mention
    try:
        state.add_queue(player.id)
    except KeyError:
        await ctx.send(f"{name} is already in the queue.")
        return
    title = "[{}/{}] {} joined the queue.".format(
        len(state.queue), 2 * state.team_size, name)
    embed = discord.Embed(description=title)
    await ctx.send(embed=embed)
    if len(state.queue) == 2 * state.team_size:
        await start_game(ctx)


@bot.command(aliases=['j'])
@commands.check(check_lobby)
async def join(ctx):
    if state.frozen:
        await ctx.send("The queue is frozen.")
        return
    await add_player(ctx, ctx.author)


@bot.command()
@commands.check(check_organiser_lobby)
async def forcejoin(ctx, user: discord.User):
    await add_player(ctx, user)


async def remove_player(ctx, player: discord.User):
    name = player.mention
    try:
        state.remove_queue(player.id)
    except KeyError:
        await ctx.send(f"{name} is not in the queue.")
        return
    description = "[{}/{}] {} left the queue.".format(
        len(state.queue), 2 * state.team_size, name)
    embed = discord.Embed(description=description)
    await ctx.send(embed=embed)
    if len(state.queue) == 2 * state.team_size:
        await start_game(ctx)


@bot.command(aliases=['l'])
@commands.check(check_lobby)
async def leave(ctx):
    if state.frozen:
        await ctx.send("The queue is frozen.")
        return
    await remove_player(ctx, ctx.author)


@bot.command()
@commands.check(check_organiser_lobby)
async def forceremove(ctx, user: discord.User):
    await remove_player(ctx, user)


@bot.command()
@commands.check(check_organiser_lobby)
async def players(ctx, n: int):
    if n < 1:
        await ctx.send("First argument must be greater than 1.")
        return
    state.team_size = n
    await ctx.send(f"Players per team set to {n}.")
    if len(state.queue) == 2 * state.team_size:
        await start_game(ctx)


@bot.command(aliases=['g'])
@commands.check(check_organiser_lobby)
async def score(ctx, id: int, team: str):
    game = state.api.get_game_by_id(id)
    if not game:
        await ctx.send("This game does not exist.")
        return
    if team == '1':
        result = Result.TEAM1
    elif team == '2':
        result = Result.TEAM2
    elif team == 'draw':
        result = Result.DRAW
    else:
        await ctx.send("Score must be 1, 2 or draw.")
        return
    game.score = result
    state.api.update_game(game)
    state.update_players()
    await update_leaderboard()
    await _gameinfo(ctx, game)


@bot.command(aliases=['cancel'])
@commands.check(check_organiser_lobby)
async def cancelgame(ctx, id: int):
    game = state.api.get_game_by_id(id)
    if not game:
        await ctx.send("This game does not exist.")
        return
    game.score = Result.CANCELLED
    state.api.update_game(game)
    state.update_players()
    await update_leaderboard()
    await ctx.send("Game cancelled.")


@bot.command(aliases=['lb'])
@commands.check(check_organiser_spam)
async def leaderboard(ctx, page=1):
    players = list(
        filter(lambda x: x[0] and is_ranked(x[0]), map(lambda x: (ctx.guild.get_member(x), state.get_player(x) or Player()), state.players.keys())))
    players = sorted(players, key=lambda x: -x[1].conservative_rating())
    pages = math.ceil(len(players) / 20)
    if page > pages:
        return
    start = 20 * (page - 1)
    description = ""
    for (i, player) in enumerate(players[start:start+20], start + 1):
        name = player[0].mention
        conservative_rating = player[1].conservative_rating()
        mu = player[1].rating.mu
        sigma = 2 * player[1].rating.sigma
        description += "{}: {} - **{:.0f}** ({:.0f} ± {:.0f})\n".format(
            i, name, conservative_rating, mu, sigma)
    embed = discord.Embed(
        title=f"Leaderboard ({page}/{pages})", description=description)
    await ctx.send(embed=embed)


@bot.command()
@commands.check(check_organiser_spam)
async def lball(ctx, page=1):
    players = list(
        filter(lambda x: x[0], map(lambda x: (ctx.guild.get_member(x), state.get_player(x) or Player()), state.players.keys())))
    players = sorted(players, key=lambda x: -x[1].conservative_rating())
    pages = math.ceil(len(players) / 20)
    if page > pages:
        return
    start = 20 * (page - 1)
    description = ""
    for (i, player) in enumerate(players[start:start+20], start + 1):
        name = player[0].mention
        conservative_rating = player[1].conservative_rating()
        mu = player[1].rating.mu
        sigma = 2 * player[1].rating.sigma
        description += "{}: {} - **{:.0f}** ({:.0f} ± {:.0f})\n".format(
            i, name, conservative_rating, mu, sigma)
    embed = discord.Embed(
        title=f"Leaderboard ({page}/{pages})", description=description)
    await ctx.send(embed=embed)


@bot.command(aliases=['q'])
@commands.check(check_lobby)
async def queue(ctx):
    last_game = state.api.get_last_game()
    if last_game:
        id = last_game.id + 1
    else:
        id = 1
    title = "Game #{} [{}/{}]".format(id, len(state.queue),
                                      2 * state.team_size)
    description = ""
    for player_id in state.queue:
        name = ctx.guild.get_member(player_id).mention
        description += "{}\n".format(name)
    embed = discord.Embed(title=title, description=description)
    await ctx.send(embed=embed)


async def _gameinfo(ctx, game: Game):
    title = f"Game #{game.id}"
    winner = "undecided"
    if game.score == Result.TEAM1:
        winner = "team 1"
    elif game.score == Result.TEAM2:
        winner = "team 2"
    elif game.score == Result.DRAW:
        winner = "draw"
    elif game.score == Result.CANCELLED:
        winner = "cancelled"
    description = "{}\n\nWinner: {}\n\nTeam 1:\n".format(
        game.date.replace('T', ' '), winner)
    if game.score == Result.UNDECIDED or game.score == Result.CANCELLED:
        for player_id in game.team1:
            description += "<@{}>\n".format(player_id)
        description += "\nTeam2:\n"
        for player_id in game.team2:
            description += "<@{}>\n".format(player_id)
    else:
        for player_id in game.team1:
            player = state.get_player(player_id)
            rating_change = player.rating_change(game.id)
            sign = "+"
            if rating_change < 0:
                sign = "-"
                rating_change = -rating_change
            description += "<@{}> {}{:.0f}\n".format(
                player_id, sign, rating_change)
        description += "\nTeam 2:\n"
        for player_id in game.team2:
            player = state.get_player(player_id)
            rating_change = player.rating_change(game.id)
            sign = "+"
            if rating_change < 0:
                sign = "-"
                rating_change = -rating_change
            description += "<@{}> {}{:.0f}\n".format(
                player_id, sign, rating_change)
    embed = discord.Embed(title=title, description=description)
    await ctx.send(embed=embed)


@bot.command()
@commands.check_any(commands.check(check_spam), commands.check(check_lobby))
async def lastgame(ctx):
    game = state.api.get_last_game()
    if not game:
        await ctx.send("No game was played.")
        return
    await _gameinfo(ctx, game)


@bot.command()
@commands.check_any(commands.check(check_spam), commands.check(check_lobby))
async def gameinfo(ctx, id: int):
    game = state.api.get_game_by_id(id)
    if not game:
        await ctx.send("This game does not exist.")
        return
    await _gameinfo(ctx, game)


async def _info(ctx, user: discord.User):
    player = (state.get_player(user.id) or Player())
    rating = player.rating
    conservative_rating = player.conservative_rating()
    mu = rating.mu
    sigma = 2 * rating.sigma
    title = "{}'s stats".format(user.display_name)
    description = "Rating: {:.0f} ({:.0f} ± {:.0f})\n".format(
        conservative_rating, mu, sigma)
    rank = state.get_rank(conservative_rating)
    try:
        role_id = rank["id"]
        print(role_id)
        role = ctx.guild.get_role(role_id)
        print(role)
        description += f"Rank: {role.mention}\n"
    except:
        description += f"Rank: {rank['name']}\n"
    description += f"Wins: {player.wins}\n"
    description += f"Losses: {player.losses}\n"
    description += f"Draws: {player.draws}\n"
    description += "Games: {}\n".format(player.wins +
                                        player.losses + player.draws)
    embed = discord.Embed(title=title, description=description)
    await ctx.send(embed=embed)


@bot.command()
@commands.check_any(commands.check(check_spam), commands.check(check_dm))
async def info(ctx):
    await _info(ctx, ctx.author)


@bot.command()
@commands.check_any(commands.check(check_organiser_spam), commands.check(check_organiser_lobby))
async def forceinfo(ctx, user: discord.User):
    await _info(ctx, user)


async def _history(ctx, user, limit: str):
    try:
        games = int(limit) + 1
        if games < 2:
            raise Exception
    except:
        if limit == "all":
            games = None
        else:
            await ctx.send("Limit should be a positive integer or \"all\"")
            return
    player = state.get_player(user.id)
    if player is None:
        await ctx.send("{} has not played yet.".format(user.mention))
        return
    ys = list(map(lambda x: x[1], player.history))
    ys = [Player().conservative_rating()] + ys
    xs = [i for i in range(len(ys))]
    if games is not None and len(ys) > games:
        ys = ys[-games:]
        xs = xs[-games:]
    ymin = min(ys)
    ymax = max(ys)
    dy = 0.05 * (ymax - ymin)
    ymin -= dy
    ymax += dy
    plt.clf()
    alpha = 0.3
    rating_min = 0
    for rank in state.ranks:
        rating_max = rank["limit"]
        plt.axhspan(rating_min, rating_max, alpha=alpha, color=rank["color"])
        rating_min = rating_max
    plt.xticks(xs[::round(len(xs)/15)])
    plt.ylim([ymin, ymax])
    plt.grid()
    plt.plot(xs, ys, "black")
    plt.title(f"{user.display_name}'s rating history")
    plt.xlabel('game #')
    plt.ylabel('rating')
    plt.savefig(fname='plot')
    await ctx.send(file=discord.File('plot.png'))
    os.remove('plot.png')


@bot.command()
@commands.check_any(commands.check(check_spam), commands.check(check_dm))
async def history(ctx, limit: str = "20"):
    await _history(ctx, ctx.author, limit)


@bot.command()
@commands.check_any(commands.check(check_organiser_spam), commands.check(check_organiser_lobby))
async def forcehistory(ctx, user: discord.User, limit: str = "20"):
    await _history(ctx, user, limit)


@bot.command()
@commands.check_any(commands.check(check_spam), commands.check(check_organiser_lobby), commands.check(check_dm))
async def gamelist(ctx, user: discord.User = None):
    if user:
        title = "{}'s last games".format(user.display_name)
        last_games = state.api.get_games(user.id)[-20:][::-1]
        description = ""
        for game in last_games:
            result = "undecided"
            if game.score == Result.TEAM1:
                if user.id in game.team1:
                    result = "win"
                else:
                    result = "loss"
            elif game.score == Result.TEAM2:
                if user.id in game.team2:
                    result = "win"
                else:
                    result = "loss"
            elif game.score == Result.DRAW:
                result = "draw"
            elif game.score == Result.CANCELLED:
                result = "cancelled"
            if game.score != Result.UNDECIDED and game.score != Result.CANCELLED:
                rating_change = state.get_player(
                    user.id).rating_change(game.id)
                sign = "+"
                if rating_change < 0:
                    sign = "-"
                    rating_change = -rating_change
                description += "Game #{}: {} ({}{:.0f})\n".format(game.id,
                                                                  result, sign, rating_change)
            else:
                description += "Game #{}: {}\n".format(game.id, result)
    else:
        title = "Last games"
        last_games = state.api.get_games()[-20:][::-1]
        description = ""
        for game in last_games:
            result = "undecided"
            if game.score == Result.TEAM1:
                result = "team 1"
            elif game.score == Result.TEAM2:
                result = "team 2"
            elif game.score == Result.DRAW:
                result = "draw"
            elif game.score == Result.CANCELLED:
                result = "cancelled"
            description += "Game #{}: {}\n".format(game.id, result)
    embed = discord.Embed(title=title, description=description)
    await ctx.send(embed=embed)


@bot.command()
@commands.check_any(commands.check(check_spam), commands.check(check_lobby), commands.check(check_dm))
async def stats(ctx):
    games = state.api.get_games()
    total_games = len(games)
    cancelled = 0
    undecided = 0
    for game in games:
        if game.score == Result.CANCELLED:
            cancelled += 1
        elif game.score == Result.UNDECIDED:
            undecided += 1
    title = "Stats"
    description = "Total games: {}\n".format(total_games)
    description += "Games played: {}\n".format(
        total_games - cancelled - undecided)
    description += "Cancelled games: {}\n".format(cancelled)
    description += "Undecided games: {}\n".format(undecided)
    embed = discord.Embed(title=title, description=description)
    await ctx.send(embed=embed)


@bot.command()
@commands.check(check_organiser_lobby)
async def swap(ctx, user1: discord.User, user2: discord.User):
    game = state.api.get_last_game()
    if not game:
        return
    if user1.id in game.team1:
        if user2.id in game.team1:
            await ctx.send("These players are on the same team.")
            return
        elif user2.id in game.team2:
            game.team1 = [x if x != user1.id else user2.id for x in game.team1]
            game.team2 = [x if x != user2.id else user1.id for x in game.team2]
        else:
            game.team1 = [x if x != user1.id else user2.id for x in game.team1]
    elif user1.id in game.team2:
        if user2.id in game.team2:
            await ctx.send("These players are on the same team.")
            return
        elif user2.id in game.team1:
            game.team1 = [x if x != user2.id else user1.id for x in game.team1]
            game.team2 = [x if x != user1.id else user2.id for x in game.team2]
        else:
            game.team2 = [x if x != user1.id else user2.id for x in game.team2]
    else:
        await ctx.send("{} is not playing.".format(user1.mention))
        return
    state.api.update_game(game)
    await ctx.send("Players swapped.")
    if game.score in [Result.TEAM1, Result.TEAM2, Result.DRAW]:
        state.update_players()
        await update_leaderboard()


@bot.command(aliases=['clear', 'clearq'])
@commands.check(check_organiser_lobby)
async def clearqueue(ctx):
    state.queue = set()
    await ctx.send("Queue cleared.")


@bot.command()
@commands.check(check_organiser_lobby)
async def freeze(ctx):
    state.frozen = True
    await ctx.send("Queue frozen.")


@bot.command()
@commands.check(check_organiser_lobby)
async def unfreeze(ctx):
    state.frozen = False
    await ctx.send("Queue unfrozen.")

load_dotenv()
config = toml.load("config.toml")
api = Api("http://localhost:5000/api")
state = State(config)
state.update_players()
bot.run(os.getenv('DISCORD_TOKEN'))
