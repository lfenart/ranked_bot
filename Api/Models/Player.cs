using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

using System.Text.Json.Serialization;

namespace Api.Models
{

    public class Player
    {
        [Required]
        public long? Id { get; set; }
        public byte Team { get; set; }

        [JsonIgnore]
        [ForeignKey("Game")]
        public long GameId { get; set; }
        [JsonIgnore]
        public Game Game { get; set; }
    }

}
