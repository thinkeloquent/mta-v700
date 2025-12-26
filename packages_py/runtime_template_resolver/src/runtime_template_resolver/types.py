from enum import Enum

class MissingStrategy(Enum):
    KEEP = 'KEEP'
    EMPTY = 'EMPTY'
    ERROR = 'ERROR'
    DEFAULT = 'DEFAULT'
