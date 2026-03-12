from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str
    admin: dict

class TokenData(BaseModel):
    admin_id: Optional[int] = None
    