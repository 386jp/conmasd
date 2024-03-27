import datetime
import requests
from jwt import JWT, jwk_from_pem

from ...types import GHEntityEnum

class GitHubAPI:
    def __init__(self) -> None:
        pass

    def _get_app_auth_jwt(self, app_id: str, pem: bytes, algorithm: str = "RS256") -> str:
        utc_now = datetime.datetime.now()
        payload = {
            'typ': 'JWT',
            'alg': algorithm,
            'iat': int(utc_now.strftime('%s')),
            'exp': int((utc_now + datetime.timedelta(seconds=30)).strftime('%s')),
            'iss': app_id,
        }
        return JWT().encode(payload, jwk_from_pem(pem), alg=algorithm)

    def _get_app_auth_installed_access_token(self, installation_id: str) -> str:
        url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            'Authorization': f'Bearer {self.app_auth_token}',
        }
        return requests.post(url, headers=headers).json()["token"]

    def set_auth_app(self, app_id: str, pem: bytes, installation_id: str) -> None:
        self.app_auth_token = self._get_app_auth_jwt(app_id, pem)
        self.access_token = self._get_app_auth_installed_access_token(installation_id)

    def set_auth_token(self, token: str) -> None:
        self.access_token = token

    def _get_request_headers(self) -> dict:
        return {
            'Authorization': f'Bearer {self.access_token}',
        }

    def create_jit_runner(self, place_type: GHEntityEnum, place: str, runner_name: str, labels: list[str] = ["self-hosted"], runner_group_id: str = "1") -> dict:
        url = f"https://api.github.com/{place_type.value}/{place}/actions/runners/generate-jitconfig"
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            **self._get_request_headers()
        }
        data = {
            "name": runner_name,
            "runner_group_id": int(runner_group_id),
            "labels": labels,
        }
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()

    def delete_runner(self, place_type: GHEntityEnum, place: str, runner_id: str):
        url = f"https://api.github.com/{place_type.value}/{place}/actions/runners/{runner_id}"
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            **self._get_request_headers()
        }
        response = requests.delete(url, headers=headers)
        response.raise_for_status()
        return response
