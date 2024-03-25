import enum

class DockerContainerStatusEnum(str, enum.Enum):
    RESTARTING = "restarting"
    RUNNING = "running"
    PAUSED = "paused"
    EXITED = "exited"
