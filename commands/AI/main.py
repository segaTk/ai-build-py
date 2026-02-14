import requests
from core import Command

class AI(Command):
    def __init__(self, *args, **kwargs):
        quest_map = (("Ask question: ", str),)
        super().__init__(*args, quest_map=quest_map, **kwargs)

    def invoke(self, x: str) -> str:
        if not x.strip():
            return "❌ Пустой запрос."
        if len(x) > 500:
            return "❌ Запрос слишком длинный (макс. 500 символов)."

        url = "http://127.0.0.1:11434/api/generate"
        payload = {
            "model": "phi3:mini",  # ← быстрее и надёжнее
            "prompt": x,
            "stream": False,
            "options": {
                "num_predict": 512  # ← ограничить длину ответа
            }
        }

        try:
            print(f"\n📤 Отправляю в Ollama...")
            response = requests.post(url, json=payload, timeout=60)  # можно вернуть 60 сек
            response.raise_for_status()
            result = response.json().get("response", "").strip()
            return f"AI: {result}"
        except requests.exceptions.Timeout:
            return "❌ Ollama не ответила за 60 секунд. Попробуйте короткий запрос."
        except Exception as e:
            return f"❌ Ошибка: {type(e).__name__}"