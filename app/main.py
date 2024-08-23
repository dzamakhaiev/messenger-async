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
        messages.loop.run_until_complete(messages.db_service.close_all_connections())
        messages.loop.run_until_complete(messages.mq_service.close())
        users.loop.run_until_complete(users.db_service.close_all_connections())
        auth.loop.run_until_complete(auth.db_service.close_all_connections())
        auth.loop.run_until_complete(auth.mq_service.close())

        sys.exit(exit_code)
