from typing import Annotated
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import RedirectResponse
import aiohttp
import jwt
from state_storage import state_storage
from oauth_google import generate_google_oauth_redirect_uri
from config import settings
from fastapi import Response

router = APIRouter(prefix="/auth")

@router.get("/google/url")
def get_google_oauth_redirect_uri():
    uri = generate_google_oauth_redirect_uri()
    return RedirectResponse(url=uri, status_code=302)

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(
        key="user_email",
        path="/"
    )
    return {"message": "Logged out"}

@router.get("/google/callback")
async def handle_code(
    response: Response,
    code: str = Query(...),
    state: str = Query(...),

):
    if state not in state_storage:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    print("Стейт корректный")

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url="https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.OAUTH_GOOGLE_CLIENT_ID,
                "client_secret": settings.OAUTH_GOOGLE_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "redirect_uri": "http://localhost:8000/auth/google/callback",
                "code": code,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ) as token_response:
            res = await token_response.json()
            if "error" in res:
                raise HTTPException(status_code=400, detail=res.get("error_description", res["error"]))

            id_token = res["id_token"]
            #access_token = res["access_token"]

            user_data = jwt.decode(id_token, algorithms=["RS256"], options={"verify_signature": False})

    # Устанавливаем куку с email пользователя (для простоты)
    response.set_cookie(
        key="user_email",
        value=user_data["email"],
        httponly=False,
        secure=False,
        samesite="lax",
        max_age=3600 * 24 * 7,
        path="/"
    )
    print("✅ Установлена кука user_email =", user_data["email"])

    # Перенаправляем на главную страницу фронтенда (или оставляем как есть)
    response.status_code = 302
    response.headers["Location"] = "/"
    return response