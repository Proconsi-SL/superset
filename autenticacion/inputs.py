from pydantic import BaseModel


class BaseRequest(BaseModel):
    username: str
    password: str

class GuestTokenRequest(BaseRequest):
    dashboard_id: str

class LoginRequest(BaseRequest):
    provider: str
    refresh: bool
