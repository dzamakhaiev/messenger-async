import sys
from fastapi import FastAPI, status
from uvicorn import run
from app import routes
from app import settings


app = FastAPI()


@app.post(path=routes.MESSAGES, status_code=status.HTTP_200_OK)
async def receive_message():
    return


@app.head(path=routes.MESSAGES_HEALTH, status_code=status.HTTP_200_OK)
async def health():
    return


if __name__ == '__main__':

    try:
        run(app=app, host=settings.HOST, port=settings.PORT)
    except KeyboardInterrupt:
        sys.exit(0)
