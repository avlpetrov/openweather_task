import uuid
from time import sleep

import docker as dockerlib
import pytest
from alembic import command
from alembic.config import Config
from databases import Database

POSTGRES_DOCKER_IMAGE = "postgres:13"
EXPOSED_PORT = 5432
POSTGRES_TEST_SERVER_URI = (
    f"postgresql://postgres:postgres@localhost:{EXPOSED_PORT}/postgres"
)


@pytest.fixture(scope="session")
def docker() -> dockerlib.APIClient:
    return dockerlib.APIClient(version="auto")


@pytest.fixture(scope="session", autouse=True)
def postgres_server(docker: dockerlib.APIClient):
    docker.pull(POSTGRES_DOCKER_IMAGE)
    container = docker.create_container(
        image=POSTGRES_DOCKER_IMAGE,
        name=f"test-postgres-{uuid.uuid4()}",
        detach=True,
        environment={"POSTGRES_PASSWORD": "postgres"},
        host_config=docker.create_host_config(port_bindings={5432: EXPOSED_PORT}),
    )
    docker.start(container=container["Id"])
    sleep(2)  # Wait for postgres readiness

    try:
        run_migrations()
        yield
    finally:
        docker.kill(container["Id"])
        docker.remove_container(container["Id"])


@pytest.fixture
async def database():
    db = Database(POSTGRES_TEST_SERVER_URI)
    await db.connect()
    yield db
    await db.disconnect()


def run_migrations() -> None:
    alembic_cfg = Config("./alembic.ini")
    command.upgrade(alembic_cfg, "head")
