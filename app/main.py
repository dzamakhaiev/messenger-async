import sys
from asyncio import new_event_loop
from fastapi import FastAPI
from uvicorn import run
from app import messages
from app import users
from app import auth
from app import settings
from logger.logger import Logger


main_logger = Logger('main_endpoint')
app = FastAPI()

app.include_router(router=users.router)
app.include_router(router=messages.router)
app.include_router(router=auth.login_router)
app.include_router(router=auth.logout_router)
app.include_router(router=auth.auth_health_router)


@app.on_event('startup')
async def prepare_databases():
    await messages.db_service.establish_db_connection()
    await messages.mq_service.establish_db_connection()
    await users.db_service.establish_db_connection()
    await auth.db_service.establish_db_connection()
    await auth.mq_service.establish_db_connection()


@app.on_event('shutdown')
async def shutdown_db():
    await messages.db_service.close_all_connections()
    await messages.mq_service.close()
    await users.db_service.close_all_connections()
    await auth.db_service.close_all_connections()
    await auth.mq_service.close()


if __name__ == '__main__':
    exit_code = 0

    try:
        main_logger.info('"Main" endpoint is started.')
        run(app=app, host=settings.HOST, port=settings.PORT)

    except KeyboardInterrupt:
        main_logger.info('"Main" endpoint is stopped.')

    except Exception as e:
        main_logger.error(e)
        exit_code = 1

    finally:
        sys.exit(exit_code)
