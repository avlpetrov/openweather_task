FROM python:3.9.0-alpine

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

EXPOSE 8000
WORKDIR /openweather_task

COPY poetry.lock pyproject.toml ./

RUN apk add --no-cache --virtual .build-deps gcc musl-dev libffi-dev libressl-dev alpine-sdk postgresql-dev libpq python3-dev py3-psycopg2 \
     && curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python - \
     && source $HOME/.poetry/env \
     && poetry config virtualenvs.create false \
     && poetry install --no-dev

COPY . ./

CMD gunicorn -b 0.0.0.0:8000 \
    openweather_task.main:app \
    -w 8 -k uvicorn.workers.UvicornWorker
