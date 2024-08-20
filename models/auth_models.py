"""
That module contains data model classes to validate and deserialize data from requests.
"""
from datetime import datetime
from pydantic import BaseModel


class UserLogin(BaseModel):
    username: str
    password: str
    user_address: str
    public_key: str


class UserAddress(BaseModel):
    id: int
    user_id: int
    user_address: str
    last_used: datetime
