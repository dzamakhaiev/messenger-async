"""
That module contains data model classes to validate and deserialize data from requests.
"""
from typing import Optional
from pydantic import BaseModel


class User(BaseModel):
    username: str
    phone_number: str
    password: str


class UserDB(User):
    id: Optional[int]
