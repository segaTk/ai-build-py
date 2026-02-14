from sqlalchemy import create_engine, select, String, DateTime, func
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Mapped, mapped_column
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
# Читаем параметры подключения из переменных окружения (рекомендуется для безопасности)
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")

print(f"DB_USER: {DB_USER}")
print(f"DB_HOST: {DB_HOST}")
print(f"DB_NAME: {DB_NAME}")

# Формируем URL для PostgreSQL
# Формат: postgresql://user:password@host:port/dbname
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Создаём движок SQLAlchemy
# Для PostgreSQL рекомендуется использовать psycopg2
engine = create_engine(
    DATABASE_URL,
    echo=False,  # установите True для отладки SQL-запросов
    pool_pre_ping=True,  # проверяет соединение перед использованием
)

# Фабрика сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class ChatRequests(Base):
    __tablename__ = "chat_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    ip_address: Mapped[str] = mapped_column(String, index=True)
    prompt: Mapped[str] = mapped_column(String)
    response: Mapped[str] = mapped_column(String)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )


def get_user_requests(ip_address: str) -> list[ChatRequests]:
    with SessionLocal() as db_session:
        query = select(ChatRequests).where(ChatRequests.ip_address == ip_address)
        result = db_session.execute(query)
        return result.scalars().all()


def add_request_data(ip_address: str, prompt: str, response: str) -> None:
    with SessionLocal() as db_session:
        new_request = ChatRequests(
            ip_address=ip_address,
            prompt=prompt,
            response=response,
        )
        db_session.add(new_request)
        db_session.commit()