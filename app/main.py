import sys
from asyncio import new_event_loop
from fastapi import FastAPI
from uvicorn import run
from app import users
from app import auth
from app import settings
from services.db_service import DBService
from logger.logger import Logger


main_logger = Logger('main_endpoint')
app = FastAPI()
app.include_router(router=users.router)
app.include_router(router=auth.router)
db_service = DBService()


if __name__ == '__main__':

    try:
        main_logger.info('"Main" endpoint is started.')
        run(app=app, host=settings.HOST, port=settings.PORT)

    except KeyboardInterrupt:
        loop = new_event_loop()
        loop.run_until_complete(db_service.close_all_connections())
        main_logger.info('"Main" endpoint is stopped.')
        sys.exit(0)
