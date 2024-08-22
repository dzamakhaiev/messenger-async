import sys
import json
import asyncio
from aio_pika.abc import AbstractIncomingMessage
from services.db_service import DBService
from services.mq_service import MQService
from services.sender_service import SenderService
from logger.logger import Logger


messages_logger = Logger('sender')
db_service = DBService()
mq_service = MQService()
sender_service = SenderService()


async def process_user_message(message: AbstractIncomingMessage):
    async with message.process():
        body = message.body.decode()
        message_json = json.loads(body)
        messages_logger.debug(f'Processing user message: {message_json}')

        address_list = message_json.get('address_list')
        msg_json = message_json.get('msg_json')
        msg_sent = await sender_service.send_message_by_list(address_list, msg_json)

        if not msg_sent:
            await db_service.store_message_to_db(msg_json)


async def process_user_login(message: AbstractIncomingMessage):
    async with message.process():
        body = message.body.decode()
        login_json = json.loads(body)
        messages_logger.debug(f'Processing user login: {login_json}')

        user_id = login_json.get('user_id')
        user_address = login_json.get('user_address')
        messages = await db_service.get_messages(user_id=user_id)
        address_list = await db_service.get_user_address(user_id=user_id)

        if user_address not in address_list:
            address_list.append(user_address)
        await sender_service.send_messages_by_list(address_list=address_list, messages=messages)


async def main():
    await db_service.establish_db_connection()
    await mq_service.establish_db_connection()

    await mq_service.mq_handler.msg_queue.consume(process_user_message)
    await mq_service.mq_handler.login_queue.consume(process_user_login)

    try:
        await asyncio.Future()
    finally:
        await mq_service.close()
        await db_service.close_all_connections()


if __name__ == '__main__':

    try:
        messages_logger.info('Sender is starting its work.')
        asyncio.run(main())

    except KeyboardInterrupt:
        messages_logger.info('Sender is stopped.')
        sys.exit(0)
