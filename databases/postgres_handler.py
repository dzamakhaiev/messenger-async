import sys
import typing
import asyncio
import asyncpg
from databases import settings
from logger.logger import Logger

postgres_logger = Logger('postgres_handler')


class PostgresHandler:

    def __init__(self):
        self.connection = None

    async def connect(self):
        try:
            self.connection = await asyncpg.connect(
                database=settings.DB_NAME, user=settings.DB_USER,
                port=settings.DB_PORT, host=settings.DB_HOST,
                password=settings.DB_PASSWORD)

        except (asyncpg.ConnectionFailureError, ConnectionRefusedError) as e:
            postgres_logger.error(e)
            sys.exit(1)

    async def execute_query(self, query, args=None, many=False):
        if args is None:
            args = []

        postgres_logger.debug(f'Execute query: {query}\n'
                              f'with args: {args}\n'
                              f'many: {many}')

        try:
            if many:
                await self.connection.executemany(query, args)
            else:
                await self.connection.execute(query, *args)
            postgres_logger.debug('Query executed.')

        except asyncpg.exceptions.UniqueViolationError as e:
            postgres_logger.error(e)

    async def execute_fetch(self, query, args=None, fetch_all=False):
        if args is None:
            args = []

        postgres_logger.debug(f'Execute query: {query}\n'
                              f'with args: {args}\n'
                              f'fetch all: {fetch_all}')

        if fetch_all:
            result = await self.connection.fetch(query, *args)
            postgres_logger.debug('Query executed.')
            return result

        else:
            result = await self.connection.fetchrow(query, *args)
            postgres_logger.debug('Query executed.')
            return result

    async def create_users_table(self):
        await self.execute_query('''
            CREATE TABLE IF NOT EXISTS users
            (id SERIAL PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            phone_number TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL)
            ''')

    async def create_messages_table(self):
        await self.execute_query('''
            CREATE TABLE IF NOT EXISTS messages
            (id SERIAL PRIMARY KEY,
            user_sender_id INTEGER NOT NULL,
            user_receiver_id INTEGER NOT NULL,
            sender_username TEXT NOT NULL,
            message TEXT NOT NULL,
            send_date TEXT NOT NULL,
            FOREIGN KEY (user_sender_id) REFERENCES users (id),
            FOREIGN KEY (user_receiver_id) REFERENCES users (id))
            ''')

    async def create_address_table(self):
        await self.execute_query('''
            CREATE TABLE IF NOT EXISTS address
            (user_address TEXT NOT NULL UNIQUE,
            last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
            ''')

    async def create_user_address_table(self):
        await self.execute_query('''
            CREATE TABLE IF NOT EXISTS user_address
            (user_id INTEGER NOT NULL,
            user_address TEXT NOT NULL,
            PRIMARY KEY (user_id, user_address),
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (user_address) REFERENCES address (user_address))
            ''')

    async def create_tokens_table(self):
        await self.execute_query('''
            CREATE TABLE IF NOT EXISTS tokens
            (user_id INTEGER NOT NULL UNIQUE,
            token TEXT NOT NULL,            
            FOREIGN KEY (user_id) REFERENCES users (id))
            ''')

    async def create_public_keys_table(self):
        await self.execute_query('''
            CREATE TABLE IF NOT EXISTS public_keys
            (user_id INTEGER NOT NULL UNIQUE,
            public_key TEXT NOT NULL,
            create_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
            FOREIGN KEY (user_id) REFERENCES users (id))
            ''')

    async def create_all_tables(self):
        await self.create_users_table()
        await self.create_tokens_table()
        await self.create_address_table()
        await self.create_messages_table()
        await self.create_public_keys_table()
        await self.create_user_address_table()

    async def get_user(self, user_id: int = None, username: str = None) -> asyncpg.Record | None:
        if user_id:
            result = await self.execute_fetch(
                'SELECT * FROM users WHERE id = $1', (user_id,))
        elif username:
            result = await self.execute_fetch(
                'SELECT * FROM users WHERE username = $1', (username,))
        else:
            return

        return result

    async def get_user_address(self, user_id: int) -> typing.List[asyncpg.Record] | None:
        result = await self.execute_fetch(
            'SELECT user_address FROM user_address WHERE user_id = $1', (user_id,), fetch_all=True)
        return result

    async def get_user_messages(self, receiver_id: int) -> typing.List[asyncpg.Record]:
        result = await self.execute_fetch(
            'SELECT * FROM messages WHERE user_receiver_id = $1', (receiver_id,), fetch_all=True)
        return result

    async def get_user_token(self, user_id: int) -> asyncpg.Record | None:
        result = await self.execute_fetch(
            'SELECT token FROM tokens WHERE user_id = $1', (user_id,))
        return result

    async def get_user_public_key(self, user_id: int) -> asyncpg.Record | None:
        result = await self.execute_fetch(
            'SELECT public_key FROM public_keys WHERE user_id = $1', (user_id,))
        return result

    async def insert_user(self, username: str, phone_number: str, password: str = 'qwerty'):
        await self.execute_query(
            'INSERT INTO users (username, phone_number, password) VALUES ($1, $2, $3)',
            (username, phone_number, password))

    async def insert_address(self, user_address):
        await self.execute_query(
            'INSERT INTO address (user_address) VALUES ($1)', (user_address,))

    async def insert_user_address(self, user_id: int, user_address: str):
        await self.execute_query(
                'INSERT INTO user_address (user_id, user_address) VALUES ($1, $2)',
                (user_id, user_address))

    async def insert_user_token(self, user_id: int, token: str):
        await self.execute_query(
                'INSERT INTO tokens (user_id, token) VALUES ($1, $2)',
                (user_id, token))

    async def insert_user_public_key(self, user_id: int, public_key: str):
        await self.execute_query(
                'INSERT INTO public_keys (user_id, public_key) VALUES ($1, $2)',
                (user_id, public_key))

    async def insert_message(self, sender_id: int, receiver_id: int, sender_username: str,
                             message: str, send_date: str):
        await self.execute_query(
            'INSERT INTO messages '
            '(user_sender_id, user_receiver_id, sender_username, message, send_date) '
            'VALUES ($1, $2, $3, $4, $5)',
            (sender_id, receiver_id, sender_username, message, send_date))

    async def insert_messages(self, messages):
        await self.execute_query(
            'INSERT INTO messages ('
            'user_sender_id, user_receiver_id, sender_username, message, receive_date) '
            'VALUES ($1, $2, $3, $4)', args=messages, many=True)

    async def delete_messages(self, message_ids: str):
        await self.execute_query('DELETE FROM messages WHERE id IN ($1)', (message_ids,))

    async def delete_user_messages(self, receiver_id: int):
        await self.execute_query('DELETE FROM messages WHERE user_receiver_id = $1',
                                 (receiver_id,))

    async def delete_user(self, user_id: int = None, username=None):
        if user_id:
            await self.execute_query('DELETE FROM users WHERE id = $1', (user_id,))
        elif username:
            await self.execute_query('DELETE FROM users WHERE username = $1', (username,))
        else:
            raise NotImplemented

    async def delete_user_token(self, user_id: int):
        await self.execute_query('DELETE FROM tokens WHERE user_id = $1', (user_id,))

    async def delete_user_public_key(self, user_id: int):
        await self.execute_query('DELETE FROM public_keys WHERE user_id = $1', (user_id,))

    async def delete_user_address(self, user_id: int):
        await self.execute_query('DELETE FROM user_address WHERE user_id = $1', (user_id,))

    async def close(self):
        if self.connection:
            await self.connection.close()


if __name__ == '__main__':

    async def main():
        postgres_handler = PostgresHandler()
        try:
            await postgres_handler.connect()
            await postgres_handler.create_all_tables()
            await postgres_handler.insert_user('username', '1234567890', 'qwerty')
            user = await postgres_handler.get_user(username='username')
            print(user)

        finally:
            await postgres_handler.close()


    asyncio.run(main())
