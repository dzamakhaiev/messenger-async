"""
This module contains class Srvice that provide logical layer
between listener, sender services and databases handlers.
"""
import asyncio
from typing import List
from models.users_models import User, UserDB
from databases.postgres_handler import PostgresHandler
from databases.sqlite_handler import SQLiteHandler
from logger.logger import Logger


service_logger = Logger('db_service')


class DBService:

    prepared = False

    def __init__(self):
        self.hdd_db_handler = PostgresHandler()
        self.ram_db_handler = SQLiteHandler()
        service_logger.info('DB service is initialized.')

    async def connect_to_databases(self):
        if not self.prepared:
            await self.ram_db_handler.connect()
            await self.hdd_db_handler.connect()
            self.prepared = True
            service_logger.info('Connections to databases are established.')

    async def prepare_databases_data(self):
        await self.ram_db_handler.create_all_tables()
        await self.hdd_db_handler.create_all_tables()
        service_logger.info('Databases are prepared to work.')

    async def establish_db_connection(self):
        await self.connect_to_databases()
        await self.prepare_databases_data()

    @staticmethod
    def convert_tuple_to_user(user_tuple: tuple) -> UserDB:
        service_logger.debug(f'Convert user tuple to UserDB object: {user_tuple}')
        user_id, username = user_tuple
        user = UserDB(id=user_id, username=username, phone_number='', password='')
        return user

    @staticmethod
    def convert_record_to_user(user_record) -> UserDB:
        service_logger.debug(f'Convert user record to UserDB object: {user_record}')
        user = UserDB(id=user_record.get('id'),
                      username=user_record.get('username'),
                      phone_number=user_record.get('phone_number'),
                      password=user_record.get('password'))
        return user

    @staticmethod
    def convert_public_key(public_key_db) -> str:
        service_logger.debug(f'Convert database public key to string: {public_key_db}')
        if isinstance(public_key_db, tuple):
            return public_key_db[0]
        else:
            return public_key_db.get('public_key')

    @staticmethod
    def convert_token(token_db) -> str:
        service_logger.debug(f'Convert database token to string: {token_db}')
        if isinstance(token_db, tuple):
            return token_db[0]
        else:
            return token_db.get('token')

    async def create_user(self, user: User):
        service_logger.info('Create new user in databases.')
        service_logger.debug(user)
        await self.hdd_db_handler.insert_user(user.username, user.phone_number, user.password)

        user_record = await self.hdd_db_handler.get_user(username=user.username)
        service_logger.debug(f'User from DB: {user_record}')
        user_db = self.convert_record_to_user(user_record)

        await self.ram_db_handler.insert_username(user_db.id, user_db.username)
        service_logger.info('New user is created.')
        return user_db.id

    async def store_message_to_db(self, msg_json):
        service_logger.info('Store message in database.')
        service_logger.debug(msg_json)
        await self.hdd_db_handler.insert_message(msg_json.get('sender_id'),
                                                 msg_json.get('receiver_id'),
                                                 msg_json.get('sender_username'),
                                                 msg_json.get('message'))

    async def store_user_address(self, user_id, user_address):
        service_logger.info('Store user user addresses in HDD and RAM DBs.')
        service_logger.debug(f'User user: {user_address}')
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

    async def get_user(self, user_id: int = None, username: str = None) -> UserDB | None:
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

    async def get_user_address(self, user_id: int) -> List:
        service_logger.info(f'Get user address for user id "{user_id}".')
        address_list = await self.ram_db_handler.get_user_address(user_id)
        service_logger.debug(f'Address list from RAM database: {address_list}')

        if not address_list:
            address_list = await self.hdd_db_handler.get_user_address(user_id)
            service_logger.debug(f'Address list from HDD database: {address_list}')

        if address_list:
            return address_list
        return []

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


if __name__ == '__main__':
    async def main():
        service = DBService()

        await service.connect_to_databases()
        await service.prepare_databases_data()
        await service.close_all_connections()

    asyncio.run(main())
