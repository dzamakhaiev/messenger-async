import typing
import asyncio
import aiosqlite
from logger.logger import Logger


sqlite_logger = Logger('sqlite_handler')


class SQLiteHandler:

    def __init__(self):
        self.connection = None
        self.cursor = None

    async def connect(self):
        self.connection = await aiosqlite.connect(':memory:')
        self.cursor = await self.connection.cursor()

    async def execute_query(self, query, args, fetch_all=False):
        sqlite_logger.debug(f'Execute query: {query}\n'
                            f'with args: {args}\n'
                            f'fetch all: {fetch_all}')

        try:
            result = await self.cursor.execute(query, args)
            sqlite_logger.debug('Query executed.')

            if result.rowcount and fetch_all:
                return await result.fetchall()
            else:
                return await result.fetchone()

        except aiosqlite.DatabaseError as e:
            sqlite_logger.error(e)
            await self.connection.rollback()

    async def execute_query_with_commit(self, query, args=None, many=False):
        if args is None:
            args = []

        sqlite_logger.debug(f'Execute query: {query}\n'
                            f'with args: {args}\n'
                            f'many: {many}')

        try:
            if many:
                await self.cursor.executemany(query, args)
            else:
                await self.cursor.execute(query, args)

            sqlite_logger.debug('Query executed.')
            await self.connection.commit()

        except aiosqlite.DatabaseError as e:
            sqlite_logger.error(e)
            await self.connection.rollback()

    async def create_usernames_table(self):
        await self.execute_query_with_commit('''
                    CREATE TABLE IF NOT EXISTS usernames
                    (user_id INTEGER UNIQUE,
                    username TEXT NOT NULL UNIQUE)
                    ''')

    async def create_user_address_table(self):
        await self.execute_query_with_commit('''
            CREATE TABLE IF NOT EXISTS user_address
            (user_id INTEGER NOT NULL,
            user_address TEXT NOT NULL,
            PRIMARY KEY (user_id, user_address))
            ''')

    async def create_tokens_table(self):
        await self.execute_query_with_commit('''
                    CREATE TABLE IF NOT EXISTS tokens
                    (user_id INTEGER UNIQUE,
                    token TEXT NOT NULL)
                    ''')

    async def create_public_keys_table(self):
        await self.execute_query_with_commit('''
                    CREATE TABLE IF NOT EXISTS public_keys
                    (user_id INTEGER UNIQUE,
                    public_key TEXT NOT NULL,
                    create_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
                    ''')

    async def create_all_tables(self):
        await self.create_tokens_table()
        await self.create_usernames_table()
        await self.create_public_keys_table()
        await self.create_user_address_table()

    async def insert_user_address(self, user_id: int, user_address: str):
        await self.execute_query_with_commit(
            'INSERT OR IGNORE INTO user_address (user_id, user_address) VALUES (?, ?)',
            (user_id, user_address))

    async def insert_username(self, user_id: int, username: str):
        await self.execute_query_with_commit(
            'INSERT OR IGNORE INTO usernames (user_id, username) VALUES (?, ?)',
            (user_id, username))

    async def insert_user_token(self, user_id: int, token: str):
        await self.execute_query_with_commit(
            'INSERT OR IGNORE INTO tokens (user_id, token) VALUES (?, ?)',
            (user_id, token))

    async def insert_user_public_key(self, user_id: int, public_key: str):
        await self.execute_query_with_commit(
            'INSERT OR IGNORE INTO public_keys (user_id, public_key) VALUES (?, ?)',
            (user_id, public_key))

    async def get_user(self, user_id: int = None, username: str = None):
        if user_id:
            result = await self.execute_query(
                'SELECT * FROM usernames WHERE user_id = ?', (user_id,))

        elif username:
            result = await self.execute_query(
                'SELECT * FROM usernames WHERE username = ?', (username,))
        else:
            return

        return result

    async def get_user_address(self, user_id: int) -> typing.List[typing.Tuple]:
        result = await self.execute_query(
            'SELECT user_address FROM user_address WHERE user_id = ?', (user_id,), fetch_all=True)
        return result

    async def get_user_token(self, user_id: int):
        result = await self.execute_query(
            'SELECT token FROM tokens WHERE user_id = ?', (user_id,))
        return result

    async def get_user_public_key(self, user_id: int):
        result = await self.execute_query(
            'SELECT public_key FROM public_keys WHERE user_id = ?', (user_id,))
        return result

    async def delete_user(self, user_id: int = None, username: str = None):
        if user_id:
            await self.execute_query_with_commit(
                'DELETE FROM usernames WHERE user_id = ?', (user_id,))
        elif username:
            await self.execute_query_with_commit(
                'DELETE FROM usernames WHERE username = ?', (username,))
        else:
            raise NotImplementedError

    async def delete_user_address(self, user_id: int):
        await self.execute_query_with_commit(
            'DELETE FROM user_address WHERE user_id = ?', (user_id,))

    async def delete_user_token(self, user_id: int):
        await self.execute_query_with_commit(
            'DELETE FROM tokens WHERE user_id = ?', (user_id,))

    async def delete_user_public_key(self, user_id: int):
        await self.execute_query_with_commit(
            'DELETE FROM public_keys WHERE user_id = ?', (user_id,))

    async def close(self):
        if self.connection and self.cursor:
            await self.cursor.close()
            await self.connection.close()


if __name__ == "__main__":
    async def main():
        sqlite_handler = SQLiteHandler()
        await sqlite_handler.connect()
        await sqlite_handler.create_all_tables()

        await sqlite_handler.insert_username(1, 'username')
        user = await sqlite_handler.get_user(1)
        print(user)
        await sqlite_handler.delete_user(user_id=1)
        await sqlite_handler.close()

    asyncio.run(main())
