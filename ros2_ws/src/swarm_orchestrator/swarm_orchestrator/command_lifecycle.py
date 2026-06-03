from enum import Enum


class CommandState(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
