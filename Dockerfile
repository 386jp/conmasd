FROM python:3.11.8

RUN pip install conmasd==0.1.3

COPY ./docker-entrypoint.sh ./

ENV CONFIG_FILE="/data/config.json"

ENTRYPOINT ["bash", "docker-entrypoint.sh"]
