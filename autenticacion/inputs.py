from pydantic import BaseModel

"""
Módulo para definir las posibles peticiones de autenticación a la API de Superset.
"""
class BaseRequest(BaseModel):
    username: str
    password: str

class GuestTokenRequest(BaseRequest):
    dashboard_id: str

class LoginRequest(BaseRequest):
    provider: str
    refresh: bool
