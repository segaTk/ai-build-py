import logging
from contextlib import asynccontextmanager
import requests
import json
from router import router 
from fastapi import Response

from fastapi import FastAPI, Body, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from users_web import Base, engine, get_user_requests, add_request_data

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created (if not exist)")
    yield

app = FastAPI(
    title="ST",
    lifespan=lifespan,
)


app.include_router(router)

# === CORS ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ai-build.space"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === ЛОГГИРОВАНИЕ ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("main")

# === КОНСТАНТЫ ===
OLLAMA_API_URL = "http://127.0.0.1:11434/api/generate"
MODEL_NAME = "phi3"
user_authenticated = ""

# /auth/me
@app.get("/auth/me")
async def get_user(request: Request):
    email = request.cookies.get("user_email")
    if email:
        return {"user": email}
    raise HTTPException(status_code=401, detail="Not authenticated")
    

@app.post("/auth/logout")
async def logout(response: Response):
    print("✅ Вызывается /auth/logout")
    response.delete_cookie(
        key="user_email",
        path="/"
    )
    return {"message": "Logged out"}

@app.get("/test")
def test():
    return {"message": "Server is running"}


def get_answer_from_ollama(prompt: str, model: str = MODEL_NAME) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    try:
        logger.debug(f"Sending prompt to Ollama: {prompt[:50]}...")
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        answer = result.get("response", "").strip()
        logger.info(f"Received answer from Ollama (len={len(answer)} chars)")
        return answer
    except requests.exceptions.Timeout:
        logger.error("Ollama request timed out")
        raise HTTPException(status_code=504, detail="Ollama не отвечает (таймаут)")
    except requests.exceptions.ConnectionError:
        logger.error("Failed to connect to Ollama")
        raise HTTPException(status_code=500, detail="Не удаётся подключиться к Ollama")
    except requests.exceptions.HTTPError as e:
        logger.error(f"Ollama returned HTTP error: {e.response.status_code} – {e.response.text}")
        raise HTTPException(status_code=502, detail="Ollama вернул ошибку")
    except (KeyError, json.JSONDecodeError) as e:
        logger.error(f"Invalid JSON from Ollama: {e}")
        raise HTTPException(status_code=502, detail="Некорректный ответ от Ollama")
    except Exception as e:
        logger.exception("Unexpected error in get_answer_from_ollama")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


# === ОБРАБОТКА ОШИБОК ВАЛИДАЦИИ ===
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error from {request.client.host}: {exc}")
    return JSONResponse(
        status_code=422,
        content={"detail": "Некорректный запрос: ожидалось тело { 'prompt': '...' }"}
    )


@app.get("/requests")
def get_my_requests(request: Request):
    user_ip = request.client.host
    logger.info(f"Fetching history for IP: {user_ip}")
    try:
        user_requests = get_user_requests(ip_address=user_ip)
        logger.info(f"Returning {len(user_requests)} records for {user_ip}")
        return jsonable_encoder(user_requests)
    except Exception as e:
        logger.exception("Error in get_my_requests")
        raise HTTPException(status_code=500, detail="Ошибка при загрузке истории")


@app.post("/requests")
def send_prompt(
    request: Request,
    prompt: str = Body(embed=True),
):
    user_ip = request.client.host
    logger.info(f"Received prompt from {user_ip}: '{prompt[:60]}...'")

    try:
        answer = get_answer_from_ollama(prompt)
    except HTTPException:
        raise  # уже обработано
    except Exception as e:
        logger.exception("Unexpected error during Ollama call")
        raise HTTPException(status_code=500, detail="Неожиданная ошибка при генерации ответа")

    try:
        add_request_data(ip_address=user_ip, prompt=prompt, response=answer)
        logger.info(f"Saved request/response for {user_ip}")
    except Exception as e:
        logger.exception("Failed to save to DB")
        # Не прерываем ответ, но логируем

    return {"answer": answer}

app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # ← принимает запросы с любого IP
        port=8000,
        reload=True
    )