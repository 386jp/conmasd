from pydantic import BaseModel, ConfigDict

from . import GitHubConfig, DockerConfig, RunnerConfig

from typing import Optional

class ConmasdConfigVersion(BaseModel):
    config_version: str = "0.1.0"

class ConmasdConfig(ConmasdConfigVersion):
    model_config = ConfigDict(strict=True)

    github: GitHubConfig
    docker: DockerConfig = DockerConfig()
    runner: RunnerConfig = RunnerConfig()
