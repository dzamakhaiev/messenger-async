import sys
from asyncio import new_event_loop
from fastapi import FastAPI, Request, HTTPException, status
from pydantic import ValidationError
from uvicorn import run
from app import routes
from app import settings
from models.users_models import User
from services.db_service import DBService
from logger.logger import Logger


users_logger = Logger('users_endpoint')
app = FastAPI()
db_service = DBService()


async def establish_db_connection():
    users_logger.debug('Connecting to databases.')
    await db_service.connect_to_databases()
    await db_service.prepare_databases_data()
    users_logger.debug('Connection is established.')


async def close_db_async_connection():
    users_logger.debug('Closing async connections with databases.')
    await db_service.close_all_connections()
    users_logger.debug('Connections are closed.')


@app.post(path=routes.USERS, status_code=status.HTTP_201_CREATED)
async def create_user(request: Request):
    users_logger.info('Create user.')
    await establish_db_connection()

    try:
        request_json = await request.json()
        users_logger.debug(f'Request body: {request_json}')
        user = User(**request_json)

    except ValidationError as e:
        users_logger.error(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=settings.VALIDATION_ERROR)

    users_logger.debug(f'Check username in database: {user.username}')
    db_user = await db_service.get_user(username=user.username)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=settings.USER_EXISTS_ERROR)

    user_id = await db_service.create_user(user)
    users_logger.info(f'User "{user.username}" created with id {user_id}')
    return {'user_id': user_id}


@app.get(path=routes.USERS, status_code=status.HTTP_200_OK)
async def get_user():
    return {}


@app.put(path=routes.USERS, status_code=status.HTTP_200_OK)
async def update_user():
    return {}


@app.delete(path=routes.USERS, status_code=status.HTTP_200_OK)
async def create_user():
    return


@app.head(path=routes.USERS_HEALTH, status_code=status.HTTP_200_OK)
async def health():
    return


if __name__ == '__main__':

    try:
        run(app=app, host=settings.HOST, port=settings.PORT)
        users_logger.info('"Users" endpoint is started.')

    except KeyboardInterrupt:
        loop = new_event_loop()
        loop.run_until_complete(close_db_async_connection())
        users_logger.info('"Users" endpoint is stopped.')
        sys.exit(0)
