"""
This is a async handler for RabbitMQ instance in docker container.
"""
import json
import asyncio
import aio_pika
from aio_pika import Exchange, Queue, Message
from databases import settings


class RabbitMQHandler:

    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = None
        self.msg_queue = None
        self.login_queue = None

    async def connect(self):
        self.connection = await aio_pika.connect_robust(settings.CONNECT_URI)
        self.channel = await self.connection.channel()

    async def store_exchange_and_queues(self, exchange: Exchange, msg_queue: Queue, login_queue: Queue):
        self.exchange = exchange
        self.msg_queue = msg_queue
        self.login_queue = login_queue

    async def create_exchange(self, exchange_name='TestExchange') -> Exchange:
        exchange = await self.channel.declare_exchange(exchange_name, durable=True)
        return exchange

    async def create_and_bind_queue(
            self, queue_name='TestQueue', exchange_name='TestExchange'):
        queue = await self.channel.declare_queue(queue_name, durable=True)
        bind = await queue.bind(exchange_name)
        return queue, bind

    @staticmethod
    async def send_message(exchange: Exchange, queue: Queue, body: (str, dict)):
        """
        """

        if isinstance(body, dict):
            body = json.dumps(body)
        message = Message(body=body.encode(), delivery_mode=settings.MQ_DELIVERY_MODE)
        await exchange.publish(routing_key=queue.name, message=message)

    @staticmethod
    async def receive_message(queue: Queue):
        message = await queue.get()
        await message.ack()
        body = message.body.decode()
        return body

    async def close(self):
        if self.connection:
            await self.connection.close()


if __name__ == '__main__':

    async def main():
        rabbitmq_handler = RabbitMQHandler()
        await rabbitmq_handler.connect()
        exchange = await rabbitmq_handler.create_exchange()
        queue, bind = await rabbitmq_handler.create_and_bind_queue()

        await rabbitmq_handler.send_message(exchange=exchange, queue=queue, body='test')
        body = await rabbitmq_handler.receive_message(queue=queue)
        print(body)

        await rabbitmq_handler.close()

    asyncio.run(main())
