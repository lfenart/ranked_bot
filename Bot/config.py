import toml

class Config:
    def __init__(self, file):
        self.config = toml.load(file)
