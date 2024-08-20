"""
That module contains data model class to validate and deserialize data from requests.
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class Message(BaseModel):
    id: Optional[int]
    sender_id: int
    receiver_id: int
    sender_username: str
    message: str
    send_date: datetime
