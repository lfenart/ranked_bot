import trueskill


class Player:
    def __init__(self, rating=trueskill.Rating()):
        self.rating = rating
        self.wins = 0
        self.losses = 0
        self.draws = 0
        self.history = []

    def conservative_rating(self):
        return 100 * self.rating.mu - 200 * self.rating.sigma

    def add_rating(self, game_id: int) -> None:
        self.history.append((game_id, self.conservative_rating()))

    def rating_change(self, game_id):
        previous_ratings = list(
            filter(lambda x: x[0] <= game_id, self.history))[-2:]
        return previous_ratings[1][1] - previous_ratings[0][1]
