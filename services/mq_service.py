import asyncio
from databases.mq_handler import RabbitMQHandler
from logger.logger import Logger
from app import settings

service_logger = Logger('mq_service')


class MQService:
    prepared = False

    def __init__(self):
        self.mq_handler = RabbitMQHandler()

    async def connect(self):
        await self.mq_handler.connect()

    async def prepare_database(self):
        if not self.prepared:
            service_logger.info('Create exchange and queues.')

            # Create exchange, queues and store them inside handler
            exchange = await self.mq_handler.create_exchange(settings.MQ_EXCHANGE_NAME)

            msg_queue, _ = await self.mq_handler.create_and_bind_queue(
                exchange_name=settings.MQ_EXCHANGE_NAME,
                queue_name=settings.MQ_MSG_QUEUE_NAME)

            login_queue, _ = await self.mq_handler.create_and_bind_queue(
                exchange_name=settings.MQ_EXCHANGE_NAME,
                queue_name=settings.MQ_LOGIN_QUEUE_NAME)

            await self.mq_handler.store_exchange_and_queues(exchange, msg_queue, login_queue)
            self.prepared = True
            service_logger.info('Exchange and queues created.')

    async def establish_db_connection(self):
        service_logger.info('Establish connection and prepare RabbitMQ.')
        await self.connect()
        await self.prepare_database()

    async def put_to_message_queue(self, msg_json: dict):
        service_logger.debug(f'Put message to queue: {msg_json}')
        await self.mq_handler.publish_message_msg_queue(body=msg_json)

    async def put_to_login_queue(self, login_json: dict):
        service_logger.debug(f'Put login message to queue: {login_json}')
        await self.mq_handler.publish_message_login_queue(body=login_json)

    async def close(self):
        await self.mq_handler.close()


if __name__ == '__main__':
    async def main():
        service = MQService()

        await service.connect()
        await service.prepare_database()
        await service.close()


    asyncio.run(main())
