from enum import Enum


class Result(Enum):
    UNDECIDED = 0
    TEAM1 = 1
    TEAM2 = 2
    DRAW = 3
    CANCELLED = 4


class Game:
    def __init__(self, team1, team2, id=None, score=Result.UNDECIDED, date=None):
        self.team1 = team1
        self.team2 = team2
        self.id = id
        self.score = score
        self.date = date

    def to_dict(self) -> dict:
        players = []
        for player in self.team1:
            players.append({"id": player, "team": 1})
        for player in self.team2:
            players.append({"id": player, "team": 2})
        d = {"players": players, "result": self.score.value}
        if self.id:
            d["id"] = self.id
        if self.date:
            d["dateTime"] = self.date
        return d

    @staticmethod
    def from_dict(d):
        players = d["players"]
        team1 = list(map(lambda x: x["id"], filter(
            lambda x: x["team"] == 1, players)))
        team2 = list(map(lambda x: x["id"], filter(
            lambda x: x["team"] == 2, players)))
        return Game(team1, team2, d.get("id"), Result(d["result"]), d.get("dateTime"))
