import requests

try:
    resp = requests.post(
        "http://127.0.0.1:11434/api/generate",
        json={"model": "llama3", "prompt": "Тест", "stream": False},
        timeout=30
    )
    print("✅ Успех!")
    print("Ответ:", resp.json()["response"])
except Exception as e:
    print("❌ Ошибка:", e)