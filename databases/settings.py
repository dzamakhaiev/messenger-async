import os
INSIDE_DOCKER = int(os.environ.get('RUN_INSIDE_DOCKER', 0))

MQ_CONTAINER_NAME = 'rabbitmq'
PG_CONTAINER_NAME = 'postgres'

DB_HOST = 'postgres' if INSIDE_DOCKER else 'localhost'
DB_PORT = 5432
DB_NAME = 'postgres'
DB_USER = 'postgres'
DB_PASSWORD = 'postgres'
DB_TIME_ROUND = 4

MQ_HOST = 'rabbitmq' if INSIDE_DOCKER else 'localhost'
MQ_PORT = 5672
CONNECT_URI = f'amqp://guest:guest@{MQ_HOST}:{MQ_PORT}/%2F'
MQ_DELIVERY_MODE = 2  # Persistent mode saves messages on HDD in case of crash
