from pydantic import BaseModel

from .. import GHEntityEnum

from typing import Optional, Union

class GitHubAuthenticationByToken(BaseModel):
    token: str

class GitHubAuthenticationByApp(BaseModel):
    app_id: str
    pem_dir: str
    installation_id: str

class GitHubConfig(BaseModel):
    credentials: Union[GitHubAuthenticationByToken, GitHubAuthenticationByApp]
    entity: GHEntityEnum
    place: str
    labels: list[str] = ["self-hosted"]
    runner_group_id: str = "1"
    runner_name_prefix: str = "conmasd-runner-"
