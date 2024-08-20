CONTAINER_NAME = 'postgres'
DB_PORT = 5432
DB_NAME = 'postgres'
DB_USER = 'postgres'
DB_PASSWORD = 'postgres'

MQ_HOST = 'rabbitmq'
MQ_PORT = 5672
CONNECT_URI = f'amqp://guest:guest@{MQ_HOST}:{MQ_PORT}/%2F'
MQ_DELIVERY_MODE = 2  # Persistent mode saves messages on HDD in case of crash
