import docker
from ...util.dict2liststr import dict2liststr
from typing import Self, Optional, Union
from docker.models.resource import Model as DockerContainerModel

from ...types import RunnerStatusEnum, DockerContainerStatusEnum

class GHADockerRunnerAPI:
    def __init__(self) -> None:
        self.client_url = None

        self._labels_key_prefix = "jp.386.conmasd."

    def connect(self, url: Optional[str] = None) -> Self:
        if url:
            self.client = docker.DockerClient(base_url=url)
        else:
            self.client = docker.from_env()
        if self.client.ping() == False:
            raise Exception("Failed to connect to Docker")
        return self

    def _get_converted_labels(self, labels: dict[str, str]) -> dict[str, str]:
        return {self.get_converted_label_key(k): v for k, v in labels.items()}

    def get_converted_label_key(self, key: str) -> str:
        return f"{self._labels_key_prefix}{key}"

    def get_filter(self, exit_code: Optional[int] = None, status: Optional[DockerContainerStatusEnum] = None, labels: Optional[dict[str, str]] = None, name: Optional[str] = None) -> dict[str, Union[int, str, list]]:
        filters = {}
        if exit_code:
            filters["exited"] = exit_code
        if status:
            filters["status"] = status.value
        if labels:
            filters["label"] = dict2liststr(self._get_converted_labels(labels))
        if name:
            filters["name"] = name
        return filters

    def get_containers(self, filters: dict[str, Union[int, str, list]] = {}) -> list[DockerContainerModel]:
        return self.client.containers.list(all=True, filters=filters)

    def create_container(self, name: str, image: str, command: str, labels: dict[str, str] = {}) -> DockerContainerModel:
        container = self.client.containers.run(image, name=name, command=command, detach=True, labels=self._get_converted_labels(labels))
        return container # type: ignore

    def prune_containers(self, filters: dict[str, Union[int, str, list]] = {}):
        self.client.containers.prune(filters=filters)

    def dangerously_kill_containers(self, filters: dict[str, Union[int, str, list]] = {}):
        containers = self.get_containers(filters)
        for container in containers:
            container.kill() # type: ignore

    def _get_container_ready_for_job(self, container: DockerContainerModel) -> bool:
        return container.logs().find(b"Listening for Jobs") != -1 # type: ignore

    def _get_container_gets_job(self, container: DockerContainerModel) -> bool:
        return container.logs().find(b"Running job: ") != -1 # type: ignore

    def get_container_status(self, container: DockerContainerModel, old_status: Optional[RunnerStatusEnum] = None) -> RunnerStatusEnum:
        if container.status == 'exited': # type: ignore
            if container.attrs['State']['ExitCode'] == 0: # type: ignore
                return RunnerStatusEnum.COMPLETED
            else:
                return RunnerStatusEnum.ERROR
        elif container.status == 'running': # type: ignore
            # ログを全部見るのはだるいので、前回のrunner statusがRUNNING、かつ現在もcontainer statusがrunningだったら、既にrunnerがjobを捌いているはずなので、RUNNINGとする
            if old_status == RunnerStatusEnum.RUNNING:
                return RunnerStatusEnum.RUNNING
            elif self._get_container_gets_job(container): # type: ignore
                return RunnerStatusEnum.RUNNING
            elif self._get_container_ready_for_job(container): # type: ignore
                return RunnerStatusEnum.IN_QUEUE
            else:
                return RunnerStatusEnum.PREPARING
        return RunnerStatusEnum.ERROR
