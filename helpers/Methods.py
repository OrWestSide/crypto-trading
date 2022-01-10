from enum import Enum, auto


class Methods(Enum):
    GET = 'GET'
    POST = 'POST'
    DELETE = 'DELETE'

    @classmethod
    def all(cls) -> list:
        return [cls.GET, cls.POST, cls.DELETE]
