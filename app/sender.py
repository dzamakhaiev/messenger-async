import os
import sys
import json
import asyncio
from aio_pika.abc import AbstractIncomingMessage

current_file = os.path.realpath(__file__)
current_dir = os.path.dirname(current_file)
repo_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(0, repo_dir)


from services.db_service import DBService
from services.mq_service import MQService
from services.sender_service import SenderService
from logger.logger import Logger


sender_logger = Logger('sender')
db_service = DBService()
mq_service = MQService()
sender_service = SenderService()


async def process_user_message(message: AbstractIncomingMessage):
    async with message.process():
        body = message.body.decode()
        message_json = json.loads(body)
        sender_logger.debug(f'Processing user message: {message_json}')

        address_list = message_json.get('address_list')
        msg_json = message_json.get('msg_json')
        msg_sent = await sender_service.send_message_by_list(address_list, msg_json)

        if not msg_sent:
            await db_service.store_message_to_db(msg_json)


async def process_user_login(message: AbstractIncomingMessage):
    async with message.process():
        body = message.body.decode()
        login_json = json.loads(body)
        sender_logger.debug(f'Processing user login: {login_json}')

        user_id = login_json.get('user_id')
        user_address = login_json.get('user_address')
        messages = await db_service.get_messages(user_id=user_id)
        address_list = await db_service.get_user_address(user_id=user_id)

        if user_address not in address_list:
            address_list.append(user_address)
        await sender_service.send_messages_by_list(address_list=address_list, messages=messages)


async def main():
    sender_logger.info('Start async RabbitMQ consumer.')
    await db_service.establish_db_connection()
    await mq_service.establish_db_connection()

    await mq_service.mq_handler.msg_queue.consume(process_user_message)
    await mq_service.mq_handler.login_queue.consume(process_user_login)

    while True:
        try:
            sender_logger.info('Start infinite loop.')
            await db_service.connect_to_databases()
            await mq_service.connect()
            await asyncio.Future()

        except Exception as e:
            sender_logger.error(e)

        finally:
            sender_logger.info('Databases connections are closed in loop.')
            await mq_service.close()
            await db_service.close_all_connections()


if __name__ == '__main__':
    exit_code = 0

    try:
        sender_logger.info('Sender is starting its work.')
        asyncio.run(main())

    except KeyboardInterrupt:
        sender_logger.info('Sender is stopped.')
        sys.exit(exit_code)

    except Exception as e:
        sender_logger.error(e)
        exit_code = 1

    finally:
        sys.exit(exit_code)
