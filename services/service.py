"""
This module contains class Srvice that provide logical layer
between listener, sender services and databases, broker handlers.
"""
import asyncio
import hashlib
import socket
from urllib.parse import urlparse

from httpx import AsyncClient
from httpx import TimeoutException, ConnectError


from models.users_models import User, UserDB
from databases.mq_handler import RabbitMQHandler
from databases.postgres_handler import PostgresHandler
from databases.sqlite_handler import SQLiteHandler
from logger.logger import Logger
from app import settings

LOCAL_IP = socket.gethostbyname(socket.gethostname())
service_logger = Logger('service')


class Service:

    def __init__(self,
                 hdd_db_handler: PostgresHandler = PostgresHandler(),
                 ram_db_handler: SQLiteHandler = SQLiteHandler(),
                 mq_handler: RabbitMQHandler = RabbitMQHandler()):

        self.hdd_db_handler = hdd_db_handler
        self.ram_db_handler = ram_db_handler
        self.mq_handler = mq_handler

    async def connect_to_databases(self):
        await self.ram_db_handler.connect()
        await self.hdd_db_handler.connect()
        await self.mq_handler.connect()

    async def prepare_databases_data(self):
        await self.ram_db_handler.create_all_tables()
        await self.hdd_db_handler.create_all_tables()

        # Create exchange, queues and store them
        exchange = await self.mq_handler.create_exchange(settings.MQ_EXCHANGE_NAME)

        msg_queue = await self.mq_handler.create_and_bind_queue(
            exchange_name=settings.MQ_EXCHANGE_NAME, queue_name=settings.MQ_MSG_QUEUE_NAME)
        login_queue = await self.mq_handler.create_and_bind_queue(
            exchange_name=settings.MQ_EXCHANGE_NAME, queue_name=settings.MQ_LOGIN_QUEUE_NAME)

        await self.mq_handler.store_exchange_and_queues(exchange, msg_queue, login_queue)

    @staticmethod
    def check_url(url: str):
        parsed_url = urlparse(url)
        if parsed_url.hostname == LOCAL_IP or parsed_url.hostname == '127.0.0.1':
            url = url.replace(parsed_url.hostname, 'localhost')

        return url

    @staticmethod
    def convert_tuple_to_user(user_tuple: tuple):
        user_id, username = user_tuple
        user = UserDB(id=user_id, username=username, phone_number='', password='')
        return user

    @staticmethod
    def convert_record_to_user(user_record):
        user = UserDB(id=user_record.get('id'),
                      username=user_record.get('username'),
                      phone_number=user_record.get('phone_number'),
                      password=user_record.get('password'))
        return user

    @staticmethod
    def convert_public_key(public_key_db) -> str:
        if isinstance(public_key_db, tuple):
            return public_key_db[0]
        else:
            return public_key_db.get('public_key')

    @staticmethod
    def convert_token(token_db) -> str:
        if isinstance(token_db, tuple):
            return token_db[0]
        else:
            return token_db.get('public_key')

    async def send_message(self, url, msg_json):
        try:
            url = self.check_url(url)
            async with AsyncClient() as client:
                response = await client.post(url, json=msg_json, timeout=5)
                return response

        except (ConnectError, TimeoutException) as e:
            return

    async def send_message_by_list(self, address_list, msg_json):
        message_received = False

        for user_address in address_list:
            try:
                response = await self.send_message(user_address, msg_json)
                if response and response.status_code == 200:
                    message_received = True

            except (ConnectError, TimeoutException) as e:
                pass

        if not message_received:
            await self.store_message_to_db(msg_json)
        return message_received

    async def send_messages_by_list(self, address_list, messages):
        messages_to_delete = []

        for message in messages:
            msg_id, sender_id, receiver_id, sender_username, msg, msg_date = message
            msg_json = {'message': msg, 'sender_id': sender_id, 'sender_username': sender_username,
                        'receiver_id': receiver_id, 'send_date': msg_date.strftime(settings.DATETIME_FORMAT)}
            msg_received = await self.send_message_by_list(address_list, msg_json)

            if msg_received:
                messages_to_delete.append(msg_id)

        messages_to_delete = ','.join([str(msg) for msg in messages_to_delete])
        if messages_to_delete:
            await self.hdd_db_handler.delete_messages(messages_to_delete)

    async def create_user(self, user: User):
        password = hashlib.sha256(str(user.password).encode()).hexdigest()
        await self.hdd_db_handler.insert_user(user.username, user.phone_number, password)

        user_record = await self.hdd_db_handler.get_user(username=user.username)
        service_logger.debug(f'User from DB: {user_record}')
        user_db = self.convert_record_to_user(user_record)

        await self.ram_db_handler.insert_username(user_db.id, user_db.username)
        return user_db.id

    async def store_message_to_db(self, msg_json):
        await self.hdd_db_handler.insert_message(msg_json.get('sender_id'),
                                                 msg_json.get('receiver_id'),
                                                 msg_json.get('sender_username'),
                                                 msg_json.get('message'))

    async def store_user_address(self, user_id, user_address):
        service_logger.info('Store user user addresses in HDD and RAM DBs.')
        await self.hdd_db_handler.insert_address(user_address)
        await self.ram_db_handler.insert_user_address(user_id, user_address)
        await self.hdd_db_handler.insert_user_address(user_id, user_address)

    async def store_user_token(self, user_id, token):
        service_logger.info('Store user token.')
        service_logger.debug(token)
        await self.hdd_db_handler.insert_user_token(user_id, token)
        await self.ram_db_handler.insert_user_token(user_id, token)

    async def store_user_public_key(self, user_id, public_key):
        service_logger.info('Store user public key.')
        service_logger.debug(public_key)
        await self.hdd_db_handler.insert_user_public_key(user_id, public_key)
        await self.ram_db_handler.insert_user_public_key(user_id, public_key)

    async def put_message_in_queue(self, address_list, msg_json):
        service_logger.info(f'Put message in {settings.MQ_MSG_QUEUE_NAME} queue.')
        queue_json = {'address_list': address_list, 'msg_json': msg_json}

        await self.mq_handler.send_message(exchange=self.mq_handler.exchange,
                                           queue=self.mq_handler.msg_queue,
                                           body=queue_json)

    async def put_login_in_queue(self, user_id, user_address):
        service_logger.info(f'Put message in {settings.MQ_LOGIN_QUEUE_NAME} queue.')
        queue_json = {'user_id': user_id, 'user_address': user_address}
        await self.mq_handler.send_message(exchange=self.mq_handler.exchange,
                                           queue=self.mq_handler.login_queue,
                                           body=queue_json)

    async def get_user(self, user_id: int = None, username: str = None) -> User | None:
        service_logger.info(f'Get user by "{user_id}" or "{username}".')
        if user_id:

            # Check RAM DB first with user_id
            user_tuple = await self.ram_db_handler.get_user(user_id=user_id)
            if user_tuple:
                service_logger.debug(f'User found in RAM by user_id "{user_id}".')
                user_db = self.convert_tuple_to_user(user_tuple)
                return user_db

            else:
                # Check HDD DB with user_id
                user_record = await self.hdd_db_handler.get_user(user_id=user_id)
                if user_record:
                    service_logger.debug(f'User found in HDD by user_id "{user_id}".')
                    user_db = self.convert_record_to_user(user_record)
                    return user_db

            # If user not found
            service_logger.error(f'User not found by user_id "{user_id}".')
            return None

        elif username:
            # Check RAM DB first with username
            user_tuple = await self.ram_db_handler.get_user(username=username)
            if user_tuple:
                service_logger.debug(f'User found in RAM by username "{username}".')
                user_db = self.convert_tuple_to_user(user_tuple)
                return user_db

            else:
                # Check HDD DB with username
                user_record = await self.hdd_db_handler.get_user(username=username)
                if user_record:
                    service_logger.debug(f'User found in HDD by username "{username}".')
                    user_db = self.convert_record_to_user(user_record)
                    return user_db

            # If user not found
            service_logger.error(f'User not found by username "{username}".')
            return None

    async def get_user_address(self, user_id: int):
        service_logger.info(f'Get user address for user id "{user_id}".')
        address_list = await self.ram_db_handler.get_user_address(user_id)
        if not address_list:
            address_list = await self.hdd_db_handler.get_user_address(user_id)

        service_logger.debug(f'Address list: {address_list}')
        return address_list

    async def get_user_token(self, user_id: int):
        service_logger.info(f'Get user token for user id "{user_id}".')
        token = await self.ram_db_handler.get_user_token(user_id)

        if not token:
            token = await self.hdd_db_handler.get_user_token(user_id)

        service_logger.debug(f'User token: "{token}"')
        return token

    async def get_user_public_key(self, user_id: int):
        service_logger.info(f'Get public key for user_id "{user_id}".')

        public_key = await self.ram_db_handler.get_user_public_key(user_id)
        if public_key is None:
            public_key = await self.hdd_db_handler.get_user_public_key(user_id)

        if public_key:
            service_logger.debug('User public key found.')
            public_key = self.convert_public_key(public_key)
            await self.ram_db_handler.insert_user_public_key(user_id, public_key)
            return public_key

        else:
            service_logger.error('User public key not found.')
            return None

    async def get_messages(self, user_id: int):
        service_logger.info(f'Get messages for user id "{user_id}" from DB.')
        messages = await self.hdd_db_handler.get_user_messages(user_id)
        service_logger.debug(f'Messages: {messages}')
        return messages

    async def check_password(self, username, password: str):
        service_logger.info(f'Check "{username}" password.')
        user_record = await self.hdd_db_handler.get_user(username=username)
        user = self.convert_record_to_user(user_record)
        exp_hashed_password = user.password

        if exp_hashed_password:
            service_logger.debug(f'"{username}" has password in database.')
            act_hashed_password = hashlib.sha256(password.encode()).hexdigest()
            return exp_hashed_password == act_hashed_password

        else:
            service_logger.error(f'"{username}" has no password in database.')
            return False

    async def check_user_token(self, user_id: int, token: str):
        service_logger.info(f'Check user token for user_id "{user_id}".')
        exp_token = await self.ram_db_handler.get_user_token(user_id)

        if exp_token is None:
            exp_token = await self.hdd_db_handler.get_user_token(user_id)
            if exp_token:
                await self.ram_db_handler.insert_user_token(user_id, token)

        if exp_token:
            exp_token = self.convert_token(exp_token)
            service_logger.debug('User token found.')
            return token == exp_token

        else:
            service_logger.error('User token not found.')
            return False

    async def delete_user(self, user_id: int):
        service_logger.info(f'Delete user id "{user_id}".')
        user = await self.get_user(user_id=user_id)

        if user:
            await self.delete_user_token(user_id)
            await self.delete_user_public_key(user_id)

            await self.hdd_db_handler.delete_user_messages(user_id)
            await self.ram_db_handler.delete_user_address(user_id)
            await self.hdd_db_handler.delete_user_address(user_id)
            await self.ram_db_handler.delete_user(user_id=user_id)
            await self.hdd_db_handler.delete_user(user_id=user_id)

            service_logger.info(f'User "{user_id}" deleted.')
            return True

        service_logger.error(f'User "{user_id}" not found.')
        return False

    async def delete_user_token(self, user_id: int):
        service_logger.info(f'Check user token for user_id "{user_id}".')
        await self.hdd_db_handler.delete_user_token(user_id)
        await self.ram_db_handler.delete_user_token(user_id)

    async def delete_user_public_key(self, user_id: int):
        service_logger.info(f'Check user public key for user_id "{user_id}".')
        await self.hdd_db_handler.delete_user_public_key(user_id)
        await self.ram_db_handler.delete_user_public_key(user_id)

    async def close_all_connections(self):
        await self.ram_db_handler.close()
        await self.hdd_db_handler.close()
        await self.mq_handler.close()


if __name__ == '__main__':
    async def main():
        service = Service(ram_db_handler=SQLiteHandler(),
                          hdd_db_handler=PostgresHandler(),
                          mq_handler=RabbitMQHandler())

        await service.connect_to_databases()
        await service.prepare_databases_data()

        await service.close_all_connections()


    asyncio.run(main())
