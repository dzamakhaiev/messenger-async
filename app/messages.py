import sys
from fastapi import FastAPI, Request, HTTPException, APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError
from uvicorn import run
from app import routes
from app import settings
from models.messages_models import Message
from services.db_service import DBService
from services.mq_service import MQService
from services.auth_service import AuthService
from logger.logger import Logger


messages_logger = Logger('messages_endpoint')
app = FastAPI()
router = APIRouter(tags=['messages'])
security = HTTPBearer()

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


@router.post(path=routes.MESSAGES, status_code=status.HTTP_200_OK)
@app.post(path=routes.MESSAGES, status_code=status.HTTP_200_OK)
async def process_message(request: Request, token: HTTPAuthorizationCredentials = Depends(security)):
    messages_logger.info('Process message.')
    token_user_id, token_username, _ = auth_service.check_token(token.credentials)

    try:
        request_json = await request.json()
        messages_logger.debug(f'Request body: {request_json}')
        msg = Message(**request_json)

    except ValidationError as e:
        messages_logger.error(f'Message validation caused error: {e}')
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=settings.VALIDATION_ERROR)

    sender_db = await db_service.get_user(user_id=msg.sender_id)
    receiver_db = await db_service.get_user(user_id=msg.receiver_id)

    if sender_db is None or receiver_db is None:
        messages_logger.error('"sender_id" of "receiver_id" not found in database.')
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=settings.VALIDATION_ERROR)

    elif token_user_id != sender_db.id or token_username != msg.sender_username:
        messages_logger.error('Token user data is mismatching database user data.')
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail=settings.INVALID_TOKEN)

    else:
        messages_logger.info(f'Send message to "{msg.receiver_id}" user id.')
        address_list = await db_service.get_user_address(user_id=msg.receiver_id)
        await mq_service.put_to_message_queue({'address_list': address_list, 'msg_json': request_json})
        messages_logger.debug(f'Message was published to RabbitMQ.')
        return {'details': 'Message processed.'}


@router.post(path=routes.HEALTH, status_code=status.HTTP_200_OK)
@app.head(path=routes.MESSAGES_HEALTH, status_code=status.HTTP_200_OK)
async def health():
    return


if __name__ == '__main__':
    exit_code = 0

    try:
        messages_logger.info('"Messages" endpoint is started.')
        run(app=app, host=settings.HOST, port=settings.PORT)

    except KeyboardInterrupt:
        messages_logger.info('"Messages" endpoint is stopped.')

    except Exception as e:
        messages_logger.error(e)
        exit_code = 1

    finally:
        sys.exit(exit_code)
