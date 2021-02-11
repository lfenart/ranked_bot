using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace Api.Models
{

    public class Game
    {
        [Key]
        [DatabaseGenerat‌ed(DatabaseGeneratedOp‌​tion.Identity)]
        public long Id { get; set; }
        public Result Result { get; set; }
        public DateTime? DateTime { get; set; }

        [InverseProperty("Game")]
        public ICollection<Player> Players { get; set; }
    }

    public enum Result : byte
    {
        Undecided,
        Team1,
        Team2,
        Draw,
        Cancelled,
    }

}
