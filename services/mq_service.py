import asyncio
from databases.mq_handler import RabbitMQHandler
from logger.logger import Logger
from app import settings

service_logger = Logger('mq_service')


class MQService:

    prepared = False

    def __init__(self):
        self.mq_handler = RabbitMQHandler()

    async def prepare_database(self):
        if not self.prepared:
            # Create exchange, queues and store them inside handler
            exchange = await self.mq_handler.create_exchange(settings.MQ_EXCHANGE_NAME)

            msg_queue = await self.mq_handler.create_and_bind_queue(
                exchange_name=settings.MQ_EXCHANGE_NAME,
                queue_name=settings.MQ_MSG_QUEUE_NAME)

            login_queue = await self.mq_handler.create_and_bind_queue(
                exchange_name=settings.MQ_EXCHANGE_NAME,
                queue_name=settings.MQ_LOGIN_QUEUE_NAME)

            await self.mq_handler.store_exchange_and_queues(exchange, msg_queue, login_queue)
            self.prepared = True

    async def establish_db_connection(self):
        await self.prepare_database()
        await self.connect()

    async def put_to_message_queue(self, msg_json: dict):
        await self.mq_handler.send_message(self.mq_handler.exchange,
                                           self.mq_handler.msg_queue,
                                           msg_json)

    async def put_to_login_queue(self, login_json: dict):
        await self.mq_handler.send_message(self.mq_handler.exchange,
                                           self.mq_handler.login_queue,
                                           login_json)

    async def connect(self):
        await self.mq_handler.connect()

    async def close(self):
        await self.mq_handler.close()


if __name__ == '__main__':
    async def main():
        service = MQService()

        await service.connect()
        await service.prepare_database()
        await service.close()

    asyncio.run(main())
