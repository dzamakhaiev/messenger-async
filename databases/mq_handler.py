"""
This is a async handler for RabbitMQ instance in docker container.
"""
import json
import asyncio
import sys

import aio_pika
from aio_pika import Exchange, Queue, Message, AMQPException
from databases import settings
from utils import docker_handler
from logger.logger import Logger


mq_logger = Logger('mq_handler')


class RabbitMQHandler:

    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = None
        self.msg_queue = None
        self.login_queue = None

        docker = docker_handler.docker_is_running()
        container = docker_handler.container_is_running(settings.MQ_CONTAINER_NAME)
        if not docker or not container:
            mq_logger.error('Docker or container is not running.')
            sys.exit(1)

    async def connect(self):
        mq_logger.info('Connect to RabbitMQ.')
        try:
            self.connection = await aio_pika.connect_robust(settings.CONNECT_URI)
            self.channel = await self.connection.channel()

        except AMQPException as e:
            mq_logger.error(e)
            sys.exit(1)

    async def store_exchange_and_queues(self, exchange: Exchange, msg_queue: Queue, login_queue: Queue):
        self.exchange = exchange
        self.msg_queue = msg_queue
        self.login_queue = login_queue

    async def create_exchange(self, exchange_name='TestExchange') -> Exchange:
        mq_logger.info('Create exchange in RabbitMQ.')
        mq_logger.debug(f'Exchange name: {exchange_name}')
        exchange = await self.channel.declare_exchange(exchange_name, durable=True)
        return exchange

    async def create_and_bind_queue(
            self, queue_name='TestQueue', exchange_name='TestExchange'):
        mq_logger.info('Create and bind queue in RabbitMQ.')
        mq_logger.debug(f'Queue name: {queue_name}')
        mq_logger.debug(f'Exchange name: {exchange_name}')

        queue = await self.channel.declare_queue(queue_name, durable=True)
        bind = await queue.bind(exchange_name)
        return queue, bind

    @staticmethod
    async def send_message(exchange: Exchange, queue: Queue, body: (str, dict)):
        """
        """
        mq_logger.info(f'Publish message in "{queue.name}" queue.')
        mq_logger.debug(f'Message: {body}')

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
            mq_logger.info('Close connection with RabbitMQ.')
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
