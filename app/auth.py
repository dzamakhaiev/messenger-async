import sys
from pydantic import ValidationError
from fastapi import FastAPI, Request, HTTPException, APIRouter, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from uvicorn import run
from app import routes
from app import settings
from models.auth_models import UserLogin
from services.db_service import DBService
from services.mq_service import MQService
from services.auth_service import AuthService
from logger.logger import Logger

auth_logger = Logger('auth_endpoint')
app = FastAPI()
security = HTTPBearer()

login_router = APIRouter(tags=['auth'])
logout_router = APIRouter(tags=['auth'])
auth_health_router = APIRouter(tags=['auth'])

db_service = DBService()
mq_service = MQService()
auth_service = AuthService()


@app.on_event('startup')
async def prepare_databases():
    await db_service.establish_db_connection()
    await mq_service.establish_db_connection()


@app.on_event('shutdown')
async def shutdown_db():
    await db_service.close_all_connections()
    await mq_service.close()


@login_router.post(path=routes.LOGIN, status_code=status.HTTP_200_OK)
@app.post(path=routes.LOGIN, status_code=status.HTTP_200_OK)
async def login(request: Request):
    auth_logger.info('User log in.')

    try:
        request_json = await request.json()
        auth_logger.debug(f'Request body: {request_json}')
        user = UserLogin(**request_json)
        act_hashed_password = auth_service.hash_password(user.password)

    except ValidationError as e:
        auth_logger.error(f'Login validation caused error: {e}')
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=settings.VALIDATION_ERROR)

    auth_logger.debug(f'Get user from database: {user.username}')
    db_user = await db_service.get_user(username=user.username)

    # If user found in database, compare encrypted passwords
    if db_user is None:
        auth_logger.error(f'Username mot found: {user.username}')
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail=settings.INCORRECT_CREDS)

    elif db_user and (act_hashed_password == db_user.password):

        auth_logger.debug('Passwords are matching.')
        token = auth_service.create_token(username=user.username, user_id=db_user.id)
        auth_logger.info('User logged in.')

        # Store user data to RAN and HDD databases
        await db_service.store_user_address(user_id=db_user.id, user_address=user.user_address)
        await db_service.store_user_public_key(user_id=db_user.id, public_key=user.public_key)
        await db_service.store_user_token(user_id=db_user.id, token=token)
        await mq_service.put_to_login_queue({'user_id': db_user.id, 'user_address': user.user_address})

        return {'msg': settings.LOGIN_SUCCESSFUL, 'user_id': db_user.id, 'token': token}

    else:
        auth_logger.error(f'Passwords are not matching:'
                          f'\n{act_hashed_password}\n{db_user.password}')
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail=settings.INCORRECT_CREDS)


@logout_router.post(path=routes.LOGOUT, status_code=status.HTTP_200_OK)
@app.post(path=routes.LOGOUT, status_code=status.HTTP_200_OK)
async def logout(request: Request, token: HTTPAuthorizationCredentials = Depends(security)):
    auth_logger.info('User log out.')
    user_id, token_username, _ = auth_service.check_token(token.credentials)

    try:
        request_json = await request.json()
        auth_logger.debug(f'Request body: {request_json}')
        username = request_json['username']

    except KeyError as e:
        auth_logger.error(f'Logout validation caused error: {e}')
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=settings.VALIDATION_ERROR)

    if token_username == username:
        await db_service.delete_user_token(user_id=user_id)
        auth_logger.info('User logged out.')
        return {'msg': settings.LOGOUT_SUCCESSFUL, 'username': username}

    else:
        auth_logger.error(f'Username from token mismatches username from request.')
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=settings.VALIDATION_ERROR)


@auth_health_router.head(path=routes.AUTH_HEALTH, status_code=status.HTTP_200_OK)
@app.head(path=routes.AUTH_HEALTH, status_code=status.HTTP_200_OK)
async def health():
    return


if __name__ == '__main__':
    exit_code = 0

    try:
        auth_logger.info('"Auth" endpoint is started.')
        run(app=app, host=settings.HOST, port=settings.PORT)

    except KeyboardInterrupt:
        auth_logger.info('"Auth" endpoint is stopped.')

    except Exception as e:
        auth_logger.error(e)
        exit_code = 1

    finally:
        sys.exit(exit_code)
