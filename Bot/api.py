import requests
from typing import Optional, List
from game import Game


class Api:
    def __init__(self, url: str):
        self.url = url

    def get_games(self, player_id: int = None) -> List[Game]:
        url = f"{self.url}/games"
        payload = {}
        if player_id:
            payload["player"] = player_id
        r = requests.get(url, payload)
        return list(map(Game.from_dict, r.json()))

    def get_game_by_id(self, game_id: int) -> Optional[Game]:
        r = requests.get(f"{self.url}/games/{game_id}")
        if r.status_code == 200:
            return Game.from_dict(r.json())
        else:
            return None

    def get_last_game(self) -> Optional[Game]:
        r = requests.get(f"{self.url}/games/last")
        if r.status_code == 200:
            return Game.from_dict(r.json())
        else:
            return None

    def create_game(self, game: Game) -> None:
        requests.post(f"{self.url}/games", json=game.to_dict())

    def update_game(self, game: Game) -> None:
        requests.put(f"{self.url}/games/{game.id}", json=game.to_dict())
