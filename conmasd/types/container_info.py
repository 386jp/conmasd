from pydantic import BaseModel

from . import RunnerStatusEnum

class ContainerIdentifierOnlyModel(BaseModel):
    container_identifier: str

class ContainerInfoBase(ContainerIdentifierOnlyModel):
    github_runner_id: str
    github_runner_group_id: str

    container_uuid: str

class ContainerInfo(ContainerInfoBase):
    docker_container_id: str

    status: RunnerStatusEnum
