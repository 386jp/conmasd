from pydantic import BaseModel

from typing import Optional, Union

class DockerImageConfigByComposeFile(BaseModel):
    compose_file: str = "./gha-baseimg-compose.yml"

class DockerImageConfigByUrl(BaseModel):
    url: str = "ghcr.io/actions/actions-runner:latest"

class RunnerConfig(BaseModel):
    docker_img: Union[DockerImageConfigByComposeFile, DockerImageConfigByUrl] = DockerImageConfigByUrl()
    container_identifier: str = "conmasd-default"
    min_pool: int = 1
    max_runners: Optional[int] = None
    polling_interval_sec: int = 1
    delete_container_after_run: bool = True
