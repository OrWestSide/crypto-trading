from enum import Enum


class Strategies(Enum):
    technical = "Technical"
    breakout = "Breakout"

    @classmethod
    def all(cls) -> list:
        return [cls.technical, cls.breakout]

    @classmethod
    def values(cls) -> list:
        return [cls.technical.value, cls.breakout.value]
