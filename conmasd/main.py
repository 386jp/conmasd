import json
import yaml
import time
import uuid

from logging import getLogger

from .util import GitHubAPI, GHADockerRunnerAPI

from .types import ConmasdConfig, RunnerStatusEnum, ContainerIdentifierOnlyModel, ContainerInfoBase, ContainerInfo
from .types.conmasd_config.github import GitHubAuthenticationByToken, GitHubAuthenticationByApp
from .types.conmasd_config.runner import DockerImageConfigByUrl, DockerImageConfigByComposeFile

from docker.models.resource import Model as DockerContainerModel

from typing import Self

class Conmasd:
    def __init__(self) -> None:
        self.logger = getLogger(__name__)

        self.github_client = GitHubAPI()
        self.docker_client = GHADockerRunnerAPI()

        self.runner_base_img = ""

        self.runners: dict[str, ContainerInfo] = {}
        self.status_cache: dict[str, int] = {}

        self._main_loop_while = True

    def _github_auth(self) -> None:
        credentials = self.config.github.credentials
        if isinstance(credentials, GitHubAuthenticationByToken):
            self.github_client.set_auth_token(credentials.token)
            self.logger.info("GitHub authentication by token is set")
        elif isinstance(credentials, GitHubAuthenticationByApp):
            with open(credentials.pem_dir, 'r') as f:
                pem = f.read()
            self.github_client.set_auth_app(
                app_id=credentials.app_id,
                pem=pem,
                installation_id=credentials.installation_id
            )
            self.logger.info("GitHub authentication by app credential is set")
        else:
            self.logger.error("Unknown GitHub credentials type")
            raise ValueError("Unknown GitHub credentials type")

    def _runner_base_img(self) -> None:
        img = self.config.runner.docker_img
        if isinstance(img, DockerImageConfigByComposeFile):
            with open(img.compose_file, 'r') as f:
                compose = yaml.safe_load(f)
            compose_services = compose['services']
            compose_service_names = list(compose_services.keys())
            if len(compose_service_names) != 1:
                raise ValueError("Compose file must have only one service")
            self.runner_base_img = compose_services[compose_service_names[0]]['image']
            self.logger.info("Docker container image from compose file is set")
        elif isinstance(img, DockerImageConfigByUrl):
            self.runner_base_img = img.url
            self.logger.info("Docker container image from URL is set")
        else:
            self.logger.error("Unknown runner base img data type")
            raise ValueError("Unknown runner base img data type")

    def _config_init(self) -> None:
        self._github_auth()
        self._runner_base_img()
        self.docker_client.connect(self.config.docker.docker_host)

    def set_config(self, config: dict) -> Self:
        self.config = ConmasdConfig.model_validate(config)
        self._config_init()
        self.logger.info("Configuration data is set")
        return self

    def set_config_from_file(self, file_path: str) -> Self:
        with open(file_path, mode="rt", encoding="utf-8") as f:
            data = f.read()
        self.config = ConmasdConfig.model_validate_json(data)
        self._config_init()
        self.logger.info("Configuration file is set")
        return self

    def export_config_to_file(self, file_path: str) -> None:
        with open(file_path, mode="wt", encoding="utf-8") as f:
            f.write(json.dumps(self.config.model_dump()))
        self.logger.info(f"Configuration data is successfully exported to file: {file_path}")

    def _config_check(self) -> None:
        if self.config is None:
            raise ValueError("Config not set")

    def _filter_container_identifier(self) -> dict[str, str]:
        return ContainerIdentifierOnlyModel(
            container_identifier=self.config.runner.container_identifier
        ).model_dump()

    def _webhook(self, body: ContainerInfo) -> None:
        pass

    def _add_container_to_runners(self, container: DockerContainerModel, status: RunnerStatusEnum) -> None:
        container_id = str(container.id)
        container_labels = container.labels # type: ignore
        self.runners[container_id] = ContainerInfo(
            container_identifier=self.config.runner.container_identifier,
            github_runner_id=container_labels[self.docker_client.get_converted_label_key('github_runner_id')],
            github_runner_group_id=container_labels[self.docker_client.get_converted_label_key('github_runner_group_id')],
            container_uuid=container_labels[self.docker_client.get_converted_label_key('container_uuid')],
            docker_container_id=container_id,
            status=status
        )

    def _update_containers_info(self) -> None:
        containers = self.docker_client.get_containers(self.docker_client.get_filter(labels=self._filter_container_identifier()))
        for container in containers:
            container_id = str(container.id)
            if container_id in self.runners.keys():
                container_status = self.docker_client.get_container_status(container, self.runners[container_id].status)
                container_status_old = self.runners[container_id].status
                self.runners[container_id].status = container_status
                if container_status in [RunnerStatusEnum.COMPLETED, RunnerStatusEnum.ERROR]:
                    self._delete_runner(container_id)
                elif container_status != container_status_old:
                    self._webhook(self.runners[container_id])
            else:
                container_status = self.docker_client.get_container_status(container)
                self._add_container_to_runners(container, container_status)

    def _get_in_queue_runners(self) -> int:
        return len([True for runner in self.runners.values() if runner.status in [RunnerStatusEnum.PREPARING, RunnerStatusEnum.IN_QUEUE]])

    def _get_active_runners(self) -> int:
        return len([True for runner in self.runners.values() if runner.status in [RunnerStatusEnum.PREPARING, RunnerStatusEnum.IN_QUEUE, RunnerStatusEnum.RUNNING]])

    def _get_required_additional_runners(self) -> int:
        required_num_runners = self.config.runner.min_pool - self._get_in_queue_runners()
        if self.config.runner.max_runners is not None:
            return min(required_num_runners, self.config.runner.max_runners - self._get_active_runners())
        return required_num_runners

    def _create_runner(self) -> None:
        container_uuid = uuid.uuid4()
        runner = self.github_client.create_jit_runner(
            self.config.github.entity,
            self.config.github.place,
            f"{self.config.github.runner_name_prefix}{container_uuid}",
            self.config.github.labels,
            self.config.github.runner_group_id
        )
        github_runner_id = str(runner['runner']['id'])
        github_runner_jit_token = runner['encoded_jit_config']
        container_info = ContainerInfoBase(
            container_identifier=self.config.runner.container_identifier,
            github_runner_id=github_runner_id,
            github_runner_group_id=self.config.github.runner_group_id,
            container_uuid=str(container_uuid),
        )
        try:
            docker_container = self.docker_client.create_container(
                f"{self.config.docker.container_prefix}{container_uuid}",
                self.runner_base_img,
                f"./run.sh --jitconfig {github_runner_jit_token}",
                container_info.model_dump()
            )
            if docker_container is None:
                raise ValueError("Failed to create container")
        except Exception as e:
            self.github_client.delete_runner(self.config.github.entity, self.config.github.place, github_runner_id)
            raise e
        else:
            docker_container_id = str(docker_container.id)
            self._add_container_to_runners(docker_container, RunnerStatusEnum.PREPARING)
            self._webhook(
                ContainerInfo(
                    **container_info.model_dump(),
                    docker_container_id=docker_container_id,
                    status=RunnerStatusEnum.PREPARING
                )
            )
        self.logger.info(f"[Container created] GitHub Runner ID: {container_info.github_runner_id} Container UUID: {container_info.container_uuid} Container ID: {docker_container_id}")

    def _delete_runner(self, container_id: str, force: bool = False) -> None:
        container_info = self.runners[container_id]
        self._webhook(container_info)
        parsed_container_filter = self.docker_client.get_filter(
            labels=ContainerInfoBase(**container_info.model_dump()).model_dump()
        )
        if force:
            self.docker_client.dangerously_kill_containers(parsed_container_filter)
        self.docker_client.prune_containers(parsed_container_filter)
        try:
            self.github_client.delete_runner(self.config.github.entity, self.config.github.place, container_info.github_runner_id)
        except:
            pass
        self.runners.pop(container_id)
        self.logger.info(f"[Container deleted] GitHub Runner ID: {container_info.github_runner_id} Container UUID: {container_info.container_uuid} Container ID: {container_id}")

    def exit(self, signal, frame):
        self.logger.info("Signal received, deleting all runners...")
        self._main_loop_while = False
        [self._delete_runner(k, True) for k in list(self.runners.keys())]
        exit(0)

    def run(self) -> None:
        self._config_check()
        while self._main_loop_while:
            try:
                self._update_containers_info()
                status = {
                    "runners_total": len(self.runners),
                    "runners_in_queue": self._get_in_queue_runners(),
                    "runners_active": self._get_active_runners(),
                    "runners_required": self._get_required_additional_runners()
                }
                if self.status_cache != status:
                    self.logger.info(f"[Runner info] Number of total runners: {status['runners_total']} Currently in-queue runners: {status['runners_in_queue']} Currently active runners (including in-queue runners): {status['runners_active']} Required additional runners: {status['runners_required']}")
                [self._create_runner() for _ in range(status['runners_required'])]
                self.status_cache = status.copy()
            except Exception as e:
                self.logger.error(e)
            time.sleep(self.config.runner.polling_interval_sec)
