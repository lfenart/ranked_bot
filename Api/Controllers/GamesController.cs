using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Api.Models;

namespace Api.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class GamesController : ControllerBase
    {
        private readonly GameContext _context;

        public GamesController(GameContext context)
        {
            _context = context;
        }

        // GET: api/Games?player=5
        [HttpGet]
        public async Task<ActionResult<IEnumerable<Game>>> GetGames(long? player)
        {
            if (player == null)
            {
                return await _context
                    .Games
                    .Include(x => x.Players)
                    .ToListAsync();
            }
            return await _context
                .Players
                .Where(x => x.Id == player)
                .Include(x => x.Game)
                .Include(x => x.Game.Players)
                .Select(x => x.Game)
                .ToListAsync();
        }

        // GET: api/Games/5
        [HttpGet("{id}")]
        public async Task<ActionResult<Game>> GetGame(long id)
        {
            var game = await _context.Games.FindAsync(id);
            if (game == null)
            {
                return NotFound();
            }
            _context.Entry(game).Collection(x => x.Players).Load();
            return game;
        }

        // GET: api/Games/last
        [HttpGet("last")]
        public async Task<ActionResult<Game>> GetLastGame()
        {
            var game = await _context.Games.OrderBy(x => x.Id).LastAsync();
            if (game == null)
            {
                return NotFound();
            }
            _context.Entry(game).Collection(x => x.Players).Load();
            return game;
        }

        // PUT: api/Games/5
        [HttpPut("{id}")]
        public async Task<IActionResult> PutGame(long id, Game game)
        {
            if (id != game.Id)
            {
                return BadRequest();
            }

            _context.Entry(game).State = EntityState.Modified;
            _context.Players.RemoveRange(_context.Players.Where(x => x.GameId == id));

            try
            {
                await _context.SaveChangesAsync();
            }
            catch (DbUpdateConcurrencyException)
            {
                if (!GameExists(id))
                {
                    return NotFound();
                }
                else
                {
                    throw;
                }
            }
            if (game.Players != null)
            {
                foreach (var player in game.Players)
                {
                    _context.Players.Add(player);
                }
            }
            await _context.SaveChangesAsync();

            return NoContent();
        }

        // POST: api/Games
        [HttpPost]
        public async Task<ActionResult<Game>> PostGame(Game game)
        {
            if (game.DateTime == null)
            {
                DateTime now = DateTime.UtcNow;
                game.DateTime = new DateTime(
                    now.Ticks - (now.Ticks % TimeSpan.TicksPerSecond),
                    now.Kind
                );
            }
            _context.Games.Add(game);
            if (game.Players != null)
            {
                foreach (var player in game.Players)
                {
                    _context.Players.Add(player);
                }
            }
            await _context.SaveChangesAsync();
            return CreatedAtAction(nameof(GetGame), new { id = game.Id }, game);
        }

        // DELETE: api/Games/5
        [HttpDelete("{id}")]
        public async Task<IActionResult> DeleteGame(long id)
        {
            var game = await _context.Games.FindAsync(id);
            if (game == null)
            {
                return NotFound();
            }

            _context.Games.Remove(game);
            await _context.SaveChangesAsync();

            return NoContent();
        }

        private bool GameExists(long id)
        {
            return _context.Games.Any(x => x.Id == id);
        }
    }
}
