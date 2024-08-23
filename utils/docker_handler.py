import docker
from docker.errors import NotFound, DockerException
from logger.logger import Logger


docker_logger = Logger('docker_handler')


def docker_is_running():
    try:
        docker_handler = docker.from_env()
        return docker_handler.ping()
    except DockerException as e:
        docker_logger.error(f'Cannot connect with Docker: {e}')
        return False


def container_is_running(container_name: str):
    if docker_is_running():

        docker_handler = docker.from_env()
        try:
            docker_logger.info(f'Container "{container_name}" is running.')
            docker_handler.containers.get(container_name)
            return True

        except NotFound:
            docker_logger.info(f'Container "{container_name}" is not running.')
            return False

    return False
