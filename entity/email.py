import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

SMTP_CONFIG = {
    "hostname": os.getenv("SMTP_HOST"),
    "port": int(os.getenv("SMTP_PORT", 587)),
    "username": os.getenv("SMTP_USER"),
    "password": os.getenv("SMTP_PASSWORD"),
}

async def send_subscription_email(user_id: int, username: str | None = None):
    """Отправляет email админу о новой подписке"""
    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = "✅ Новая подписка в Telegram-боте"
        message["From"] = SMTP_CONFIG["username"]
        message["To"] = os.getenv("ADMIN_EMAIL")

        text = f"""Новый пользователь активировал подписку!

ID: {user_id}
Username: @{username if username else 'не указан'}
Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        html = f"""
        <html>
          <body>
            <h2>✅ Новая подписка</h2>
            <p><b>ID:</b> {user_id}</p>
            <p><b>Username:</b> {'@' + username if username else '<i>не указан</i>'}</p>
            <p><b>Время:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
          </body>
        </html>
        """

        message.attach(MIMEText(text, "plain"))
        message.attach(MIMEText(html, "html"))

        await aiosmtplib.send(
            message,
            hostname=SMTP_CONFIG["hostname"],
            port=SMTP_CONFIG["port"],
            start_tls=True,
            username=SMTP_CONFIG["username"],
            password=SMTP_CONFIG["password"],
        )
        print(f"📧 Email отправлен админу о подписке пользователя {user_id}")
    except Exception as e:
        print(f"❌ Ошибка отправки email: {e}")