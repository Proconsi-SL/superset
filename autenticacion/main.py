from fastapi import FastAPI, HTTPException, Query
from functions import get_guest_token
from inputs import GuestTokenRequest

app = FastAPI()

@app.get("/guest_token")
async def guest_token(request: GuestTokenRequest):
    try:
        result = await get_guest_token(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
