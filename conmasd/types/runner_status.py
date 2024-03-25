import enum

class RunnerStatusEnum(str, enum.Enum):
    PREPARING = "preparing"
    IN_QUEUE = "in_queue"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    DELETED = "deleted"
