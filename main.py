import asyncio
import os

from core import commands_manager
from commands import get_question_map
from pathlib import Path

from telebot.async_telebot import AsyncTeleBot
from telebot.types import BotCommand

from entity.users import save_user, save_subscription, has_subscription
from entity.email import send_subscription_email


BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT2_TOKEN = os.getenv("BOT2_TOKEN")


bot = AsyncTeleBot(BOT_TOKEN)
user_states = {}

bot2 = AsyncTeleBot(BOT2_TOKEN)


def search_and_install_commands():
    commands = commands_manager.find_new_commands()
    for command_data in commands:
        commands_manager.register_command(*command_data)


search_and_install_commands()

async def setup_bot_commands():
    """Регистрирует команды в меню Telegram"""
    search_and_install_commands()
    bot_commands = [
        BotCommand("start", "Запустить бота"),
        BotCommand("list", "Список команд"),
        BotCommand("stop", "Остановить текущую команду"),
        BotCommand("buy", "Купить подписку"),
    ]
    # Добавляем все зарегистрированные команды (например, AI, sum и т.д.)
    for command_name in commands_manager.commands.keys():
        cmd_obj = commands_manager.commands[command_name]
        bot_commands.append(BotCommand(command_name, cmd_obj.alias))
        print(f"🔹 Добавлена команда: /{command_name} — {cmd_obj.alias}")
    
    await bot.set_my_commands(bot_commands)
    print(f"Всего команд зарегистрировано: {len(bot_commands)}")


@bot.message_handler(commands=["buy"])
async def buy_subscription(message):
    user_id = message.from_user.id
    username = message.from_user.username
    
    print(f"Пользователь {user_id} (@{username}) купил подписку!")
    
    # Активируем подписку
    save_subscription(user_id)
    
    try:
        await send_subscription_email(user_id, username)
    except Exception as e:
        print(f"📧 Ошибка email: {e}")
        
    #Уведомляем второго бота
    try:
        await bot2.send_message(
            user_id,
            "🎉 Поздравляем! Вам предоставлен полный доступ к AI-функциям.",
            parse_mode="HTML"
        )
        print(f"✅ Второй бот уведомил пользователя {user_id}")
    except Exception as e:
        error_text = str(e)
        if "403" in error_text and "blocked" in error_text:
            print(f"ℹ️ Пользователь {user_id} заблокировал второго бота. Пропускаем уведомление.")
        else:
            print(f"❌ Ошибка отправки от второго бота: {e}")
            
    await bot.send_message(user_id, "✅ Подписка активирована! Теперь вы можете использовать все функции.")   


@bot2.message_handler(commands=["start"])
async def start2(message):
    if has_subscription(message.from_user.id):
        await bot2.send_message(message.from_user.id, "Добро пожаловать! У вас полный доступ.")
    else:
        await bot2.send_message(message.from_user.id, "Купите подписку в основном боте (/buy).")


async def notify_second_bot(user_id: int):
    """Уведомляет второго бота о покупке"""
    try:
        # Отправляем сообщение пользователю ОТ ВТОРОГО БОТА
        await bot2.send_message(
            user_id,
            "🎉 Поздравляем! Вам предоставлен полный доступ к AI-функциям.",
            parse_mode="HTML"
        )
        print(f"✅ Второй бот уведомил пользователя {user_id}")
    except Exception as e:
        print(f"❌ Ошибка отправки от второго бота: {e}")


@bot.message_handler(commands=["start"])
async def start_handler(message):
    # 👤 Извлекаем данные пользователя
    user = message.from_user
    user_data = {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "language_code": user.language_code,
        "is_premium": bool(user.is_premium)
    }

    # 💾 Сохраняем в БД
    try:
        save_user(user_data)
        print(f"✅ Пользователь {user.id} сохранён в БД")
    except Exception as e:
        print(f"❌ Ошибка сохранения в БД: {e}")

    # 🧠 Инициализация состояния
    user_states[user.id] = {"handler": None, "question": None, "args": [], "gen": None}
    
    # 📤 Отправляем приветствие
    await bot.send_message(
        user.id,
        "👋 Добро пожаловать!\n"
        "Используйте /list для просмотра команд."
    )
    await print_commands_list(message)

@bot.message_handler(commands=["check_commands"])
async def check_commands(message):
    # Передаём None для scope и language_code
    commands = await bot.get_my_commands(scope=None, language_code=None)
    if commands:
        text = "📋 Текущие команды:\n" + "\n".join(
            f"/{c.command} — {c.description}" for c in commands
        )
    else:
        text = "📋 Нет зарегистрированных команд."
    await bot.send_message(message.from_user.id, text)
    
def clean_state(user_id):
    user_states[user_id] = {"handler": None, "question": None, "args": [], "gen": None}


async def print_commands_list(message, extra_message: str | None = None):
    search_and_install_commands()
    commands_list = []

    if extra_message:
        commands_list.append(extra_message)
    commands_list.append("Доступные команды:")

    for i, command_data in enumerate(commands_manager.commands.items()):
        command_name, command_obj = command_data
        commands_list.append(f"{i + 1}). /{command_name} - {command_obj.alias}")

    commands_list.append(f"{len(commands_list)}). /stop - Остановить выполнение команды")
    await bot.send_message(message.from_user.id, "\n".join(commands_list))


@bot.message_handler(commands=["list"])
async def list_commands(message):
    await print_commands_list(message)


@bot.message_handler(commands=["stop"])
async def stop_command(message):
    clean_state(message.from_user.id)
    await bot.send_message(message.from_user.id, "Выполнение команды остановлено")


@bot.message_handler(commands=["start"])
async def start_handler(message):
    user_states[message.from_user.id] = {"handler": None, "question": None, "args": [], "gen": None}
    await setup_bot_commands()
    await bot.send_message(message.from_user.id, "Добро пожаловать!")
    await print_commands_list(message)


@bot.message_handler(func=lambda message: message.from_user.id in user_states)
async def answer_and_commands_handler(message):
    if message.text.startswith("/"):
        command_name = message.text[1:]
        handler = commands_manager.get_command(command_name)

        if not handler:
            await bot.send_message(
                message.from_user.id, f'Команды {command_name} - не существует. Для просмотра списка команд введите "/list"'
            )

        search_and_install_commands()

        current_user_state = user_states[message.from_user.id]
        current_user_state["handler"] = handler
        current_user_state["gen"] = get_question_map(handler.quest_map)
        current_user_state["question"] = next(current_user_state["gen"])
        await bot.send_message(message.from_user.id, current_user_state["question"][0])
    else:
        current_user_state = user_states[message.from_user.id]
        handler = current_user_state.get("handler")

        if handler:
            # 🔚 Возможность выйти
            if message.text.strip().lower() in ("exit", "quit", "/stop"):
                clean_state(message.from_user.id)
                await bot.send_message(message.from_user.id, "Вы вышли из режима AI.")
                return
            
            data_type = current_user_state["question"][1]
            current_user_state["args"].append(data_type(message.text))

            try:
                #new
                current_user_state["question"] = next(current_user_state["gen"])
                # Если есть следующий вопрос — задаём его
                await bot.send_message(message.from_user.id, next(current_user_state["gen"])[0])
            except StopIteration:
                result = handler.invoke(*current_user_state["args"])
                
                # Проверяем, является ли результат путём к файлу
                result_path = Path(result)
                
                # Отладка: проверим существование файла
                print(f"[DEBUG] Проверка файла: {result_path}")
                print(f"[DEBUG] Существует: {result_path.exists()}")
                print(f"[DEBUG] Это файл: {result_path.is_file()}")
                print(f"[DEBUG] Расширение: {result_path.suffix.lower()}")
                
                if result_path.exists() and result_path.is_file():
                    suffix = result_path.suffix.lower()
                    with open(result_path, "rb") as file:
                        if suffix in ('.png', '.jpg', '.jpeg'):
                            # Отправляем как изображение
                            await bot.send_photo(message.from_user.id, file, caption="📊 Результат анализа")
                        elif suffix in ('.xlsx', '.xls'):
                            # Отправляем как документ
                            await bot.send_document(message.from_user.id, file, caption="📄 Excel файл")
                        else:
                            # Неизвестный тип - отправляем как документ
                            await bot.send_document(message.from_user.id, file)
                else:
                    # Файл не существует - отправляем как текст
                    await bot.send_message(message.from_user.id, result)
                 # 🔚 Для команд с одним вопросом — ВЫХОД из режима    
                clean_state(message.from_user.id)
                '''
                # 🔁 Перезапуск цикла
                current_user_state["args"] = []
                current_user_state["gen"] = get_question_map(handler.quest_map)
                current_user_state["question"] = next(current_user_state["gen"])
        
                await bot.send_message(message.from_user.id, current_user_state["question"][0])
                '''
        else:
            await bot.send_message(message.from_user.id, "Не знаю таких команд")

if __name__ == "__main__":
    async def main():
        # 🚀 Регистрируем команды при запуске
        await setup_bot_commands()
        print("✅ Команды успешно зарегистрированы в Telegram")
        
        # 📡 Запускаем polling
        await asyncio.gather(
            bot.polling(none_stop=True, interval=0)
        )
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")

    '''
    try:
        asyncio.run(bot.polling(none_stop=True, interval=0))
    except Exception as e:
        print(e)
'''