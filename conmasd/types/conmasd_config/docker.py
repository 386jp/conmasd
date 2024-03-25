from pydantic import BaseModel

from typing import Optional

class DockerConfig(BaseModel):
    docker_host: Optional[str] = None
    container_prefix: str = "conmasd-runner-"
