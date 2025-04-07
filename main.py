import asyncio

from core import commands_manager
from commands import get_question_map

from telebot.async_telebot import AsyncTeleBot


bot = AsyncTeleBot("7449592029:AAGgRpF_8SYd8zI-Fn0Ru9dFaALUxIaSD-4")
user_states = {}


def search_and_install_commands():
    commands = commands_manager.find_new_commands()
    for command_data in commands:
        commands_manager.register_command(*command_data)


search_and_install_commands()


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
            data_type = current_user_state["question"][1]
            current_user_state["args"].append(data_type(message.text))

            try:
                await bot.send_message(message.from_user.id, next(current_user_state["gen"])[0])
            except StopIteration:
                result = handler.invoke(*current_user_state["args"])
                await bot.send_message(message.from_user.id, result)
                clean_state(message.from_user.id)
        else:
            await bot.send_message(message.from_user.id, "Не знаю таких команд")


if __name__ == "__main__":
    try:
        asyncio.run(bot.polling(none_stop=True, interval=0))
    except Exception as e:
        print(e)
