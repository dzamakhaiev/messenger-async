import sys
from fastapi import FastAPI, status
from uvicorn import run
from app import routes
from app import settings


app = FastAPI()


@app.post(path=routes.USERS, status_code=status.HTTP_201_CREATED)
async def create_user():
    return {}


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
    except KeyboardInterrupt:
        sys.exit(0)
