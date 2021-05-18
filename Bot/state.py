from api import Api
from game import Game, Result
from player import Player, env
from typing import Optional
import trueskill


class State:
    def __init__(self, config: dict):
        self.api = Api(config["api"])
        self.channels = config["channels"]
        self.roles = config["roles"]
        self.ranks = config["ranks"]
        self.players = {}
        self.queue = set()
        self.team_size = 4
        self.frozen = False
        self.leaderboard = []

    def update_players(self) -> None:
        games = self.api.get_games()
        players = {}
        for game in games:
            update_ratings(players, game)
        self.players = players

    def add_queue(self, player_id: int) -> None:
        if player_id in self.queue:
            raise KeyError
        self.queue.add(player_id)

    def remove_queue(self, player_id: int) -> None:
        self.queue.remove(player_id)

    def get_player(self, player_id: int) -> Optional[Player]:
        return self.players.get(player_id)

    def get_rank(self, rating) -> str:
        for rank in self.ranks:
            if rating < rank["limit"]:
                return rank


def update_ratings(players: dict, game: Game) -> None:
    if game.score == Result.TEAM1:
        ranks = [0, 1]
    elif game.score == Result.TEAM2:
        ranks = [1, 0]
    elif game.score == Result.DRAW:
        ranks = [0, 0]
    else:
        return
    for player_id in game.team1:
        if not player_id in players:
            players[player_id] = Player()
        if game.score == Result.TEAM1:
            players[player_id].wins += 1
        elif game.score == Result.TEAM2:
            players[player_id].losses += 1
        elif game.score == Result.DRAW:
            players[player_id].draws += 1
    for player_id in game.team2:
        if not player_id in players:
            players[player_id] = Player()
        if game.score == Result.TEAM1:
            players[player_id].losses += 1
        elif game.score == Result.TEAM2:
            players[player_id].wins += 1
        elif game.score == Result.DRAW:
            players[player_id].draws += 1

    def get_rating(x): return players[x].rating
    team1_ratings = list(map(get_rating, game.team1))
    team2_ratings = list(map(get_rating, game.team2))
    team1_ratings, team2_ratings = env.rate(
        [team1_ratings, team2_ratings], ranks=ranks)
    for i, player in enumerate(game.team1):
        players[player].rating = team1_ratings[i]
    for i, player in enumerate(game.team2):
        players[player].rating = team2_ratings[i]
    for player in game.team1 + game.team2:
        players[player].add_rating(game.id)
