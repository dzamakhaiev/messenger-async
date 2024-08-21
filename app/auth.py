import sys
from asyncio import new_event_loop
from pydantic import ValidationError
from fastapi import FastAPI, Request, HTTPException, APIRouter, status
from uvicorn import run
from app import routes
from app import settings
from models.users_models import User
from models.auth_models import UserLogin
from services.db_service import DBService
from services.auth_service import AuthService
from logger.logger import Logger


auth_logger = Logger('auth_endpoint')
app = FastAPI()
router = APIRouter(prefix=routes.LOGIN, tags=['auth'])
db_service = DBService()
auth_service = AuthService()


@router.post(path='/', status_code=status.HTTP_200_OK)
@app.post(path=routes.LOGIN, status_code=status.HTTP_200_OK)
async def login(request: Request):
    auth_logger.info('Create user.')
    await db_service.establish_db_connection()

    try:
        request_json = await request.json()
        auth_logger.debug(f'Request body: {request_json}')
        user = UserLogin(**request_json)

    except ValidationError as e:
        auth_logger.error(f'Login validation caused error: {e}')
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=settings.VALIDATION_ERROR)

    auth_logger.debug(f'Get user from database: {user.username}')
    db_user = await db_service.get_user(username=user.username)
    exp_hashed_password = db_user.password
    act_hashed_password = auth_service.hash_password(user.password)

    if act_hashed_password == exp_hashed_password:
        return {'msg': settings.LOGIN_SUCCESSFUL, 'user_id': db_user.id, 'token': 'token'}


@router.post(path='/', status_code=status.HTTP_200_OK)
@app.post(path=routes.LOGOUT, status_code=status.HTTP_200_OK)
async def logout():
    return


@router.head(path='/', status_code=status.HTTP_200_OK)
@app.head(path=routes.AUTH_HEALTH, status_code=status.HTTP_200_OK)
async def health():
    return


if __name__ == '__main__':

    try:
        auth_logger.info('"Auth" endpoint is started.')
        run(app=app, host=settings.HOST, port=settings.PORT)

    except KeyboardInterrupt:
        loop = new_event_loop()
        loop.run_until_complete(db_service.close_all_connections())
        auth_logger.info('"Auth" endpoint is stopped.')
        sys.exit(0)
