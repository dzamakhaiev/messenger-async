import sys
from asyncio import new_event_loop
from fastapi import FastAPI, Request, HTTPException, APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError
from uvicorn import run
from app import routes
from app import settings
from models.users_models import User
from services.db_service import DBService
from services.auth_service import AuthService
from logger.logger import Logger


users_logger = Logger('users_endpoint')
app = FastAPI()
router = APIRouter(prefix=routes.USERS, tags=['users'])

security = HTTPBearer()
db_service = DBService()
auth_service = AuthService()


@app.on_event('startup')
async def prepare_databases():
    await db_service.establish_db_connection()


@app.on_event('shutdown')
async def shutdown_db():
    await db_service.close_all_connections()


@router.post(path='/', status_code=status.HTTP_201_CREATED)
@app.post(path=routes.USERS, status_code=status.HTTP_201_CREATED)
async def create_user(request: Request):
    users_logger.info('Create user.')

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

    # Encrypt user password and store user in database
    user.password = auth_service.hash_password(user.password)
    user_id = await db_service.create_user(user)
    users_logger.info(f'User "{user.username}" created with id {user_id}')
    return {'user_id': user_id}


@router.get(path='/', status_code=status.HTTP_200_OK)
@app.get(path=routes.USERS, status_code=status.HTTP_200_OK)
async def get_user(request: Request, token: HTTPAuthorizationCredentials = Depends(security)):
    users_logger.info('Get user.')
    user_id, token_username, _ = auth_service.check_token(token.credentials)

    if username := request.query_params.get('username'):

        if user_db := await db_service.get_user(username=username):
            public_key = await db_service.get_user_public_key(user_db.id)
            users_logger.info('User found.')
            return {'user_id': user_db.id, 'public_key': public_key}

        else:
            users_logger.error(f'User "{username}" not found.')
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=settings.USER_NOT_FOUND)
    else:
        users_logger.error('"username" field is missing in get request.')
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=settings.VALIDATION_ERROR)


@router.put(path='/', status_code=status.HTTP_200_OK)
@app.put(path=routes.USERS, status_code=status.HTTP_200_OK)
async def update_user():
    return {}


@router.delete(path='/', status_code=status.HTTP_200_OK)
@app.delete(path=routes.USERS, status_code=status.HTTP_200_OK)
async def delete_user(request: Request):
    users_logger.info('Delete user.')
    request_json = await request.json()

    if user_id := request_json.get('user_id'):
        user_id = int(user_id)
        await db_service.delete_user(user_id=user_id)
        users_logger.info(settings.USER_DELETED)
        return {'details': settings.USER_DELETED}

    else:
        users_logger.error('"user_id" field is missing in put request.')
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=settings.VALIDATION_ERROR)


@router.head(path='/', status_code=status.HTTP_200_OK)
@app.head(path=routes.USERS_HEALTH, status_code=status.HTTP_200_OK)
async def health():
    return


if __name__ == '__main__':
    exit_code = 0

    try:
        users_logger.info('"Users" endpoint is started.')
        run(app=app, host=settings.HOST, port=settings.PORT)

    except KeyboardInterrupt:
        users_logger.info('"Users" endpoint is stopped.')

    except Exception as e:
        users_logger.error(e)
        exit_code = 1

    finally:
        sys.exit(exit_code)
