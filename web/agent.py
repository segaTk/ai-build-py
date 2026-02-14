from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

# --- Загрузка документов ---
from langchain_community.document_loaders import DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_postgres.vectorstores import PGVector
from langchain_ollama import OllamaEmbeddings

import os
from dotenv import load_dotenv

load_dotenv()
# Читаем параметры подключения из переменных окружения (рекомендуется для безопасности)
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")


# Формируем URL для PostgreSQL
# Формат: postgresql://user:password@host:port/dbname
CONNECTION_STRING = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Путь к данным
DATA_PATH = "./data"

COLLECTION_NAME = "doc_chunks"

# Эмбеддинги
embeddings = OllamaEmbeddings(model="llama3")

# Векторное хранилище в PostgreSQL
vectorstore = PGVector(
    embeddings=embeddings,
    collection_name=COLLECTION_NAME,
    connection=CONNECTION_STRING,
    pre_delete_collection=False  # False = не удалять при перезапуске
)

# Загружаем документы, только если коллекция пуста
from sqlalchemy import text
with vectorstore._engine.connect() as conn:
    exists = conn.execute(
        text("SELECT 1 FROM langchain_pg_collection WHERE name = :name"),
        {"name": COLLECTION_NAME}
    ).fetchone()

if not exists:
    print("Загружаем документы в PostgreSQL...")
    loader = DirectoryLoader(DATA_PATH, show_progress=True)
    docs = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    splits = text_splitter.split_documents(docs)
    vectorstore.add_documents(splits)
else:
    print("Документы уже в PostgreSQL")

retriever = vectorstore.as_retriever()

# --- Инструменты ---
@tool
def document_search(query: str) -> str:
    results = retriever.invoke(query)
    return "\n\n".join([doc.page_content for doc in results])

@tool
def calculator(expression: str) -> float:
    try:
        return eval(expression)
    except Exception as e:
        return f"Ошибка: {e}"

# --- Агент ---
model = ChatOllama(model="phi3:mini", temperature=0)
agent = create_react_agent(model, tools=[document_search, calculator])

# --- Тест ---
def print_stream(stream):
    for chunk in stream:
        message = chunk["messages"][-1]
        if hasattr(message, "pretty_print"):
            message.pretty_print()
        else:
            print(message)

print_stream(agent.stream(
    {"messages": [("human", "Что такое требования?")]},
    stream_mode="values"
))