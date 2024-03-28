# conmasd

GitHub Action Self-hosted Runner Operator for Docker

## Usage

### Using Python file

Use `set_config()` to set config data, including credentials for GitHub App authentication, and execute with `run()` command.

```python
from conmasd import Conmasd

client = Conmasd()
client.set_config({
    "github": {
        "credentials": {
            "app_id": "YOUR_APP_ID_INT",
            "pem_dir": "/data/cert.pem",
            "installation_id": "YOUR_INSTALLATION_ID_INT"
        },
        "entity": "orgs",
        "place": "github",
    }
})

client.run()
```

### Using Docker Compose

Pass `docker.sock`, config file, and some other files required for creating runner to conmasd container.

`386jp/conmasd` image automatically reads `/data/config.json`. However, if you want to change config file path, pass file path to `CONFIG_FILE` environment variable.

```yaml
services:
  conmasd:
    image: 386jp/conmasd:latest
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./config.json:/data/config.json
      - ./cert.pem:/data/cert.pem
      - ./gha-baseimg-compose.yml:/data/gha-baseimg-compose.yml
```

If you gracefully shutdown your conmasd container, it automatically removes all the runners currently running.
