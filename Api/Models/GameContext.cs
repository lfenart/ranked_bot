using Microsoft.EntityFrameworkCore;

namespace Api.Models
{
    public class GameContext : DbContext
    {

        public DbSet<Game> Games { get; set; }
        public DbSet<Player> Players { get; set; }

        public GameContext(DbContextOptions<GameContext> options)
            : base(options)
        {
        }

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            modelBuilder.Entity<Player>().HasKey(x => new { x.GameId, x.Id });
            modelBuilder.Entity<Player>()
                .HasOne(x => x.Game)
                .WithMany(x => x.Players)
                .OnDelete(DeleteBehavior.Cascade);
        }

        protected override void OnConfiguring(DbContextOptionsBuilder optionsBuilder)
        {
            optionsBuilder.UseSqlite("Filename=games.db;");
        }
    }
}
