import trueskill

env = trueskill.TrueSkill(mu=2500, sigma=2500/3,
                          beta=2500/6, tau=25, draw_probability=0.085)
DEFAULT_RATING = env.create_rating()


class Player:
    def __init__(self, rating=DEFAULT_RATING):
        self.rating = rating
        self.wins = 0
        self.losses = 0
        self.draws = 0
        self.history = []

    def conservative_rating(self):
        return self.rating.mu - 2 * self.rating.sigma

    def add_rating(self, game_id: int) -> None:
        self.history.append((game_id, self.conservative_rating()))

    def rating_change(self, game_id):
        previous_ratings = list(
            filter(lambda x: x[0] <= game_id, self.history))[-2:]
        if len(previous_ratings) < 2:
            return previous_ratings[0][1] - Player().conservative_rating()
        return previous_ratings[1][1] - previous_ratings[0][1]
