from abc import ABC
from importlib import import_module
from types import ModuleType

from exceptions import NotFoundError
from settings import COMMANDS_ENDPOINT_FILENAME, COMMANDS_PATH, COMMANDS_PATTERN, COMMANDS_PROPS_FILENAME
from yaml import safe_load


class Singleton(type):
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "instance"):
            cls.instance = super(Singleton, cls).__new__(cls, *args, **kwargs)
        return cls.instance


class CommandsManager(metaclass=Singleton):
    def __init__(self):
        self.commands: dict[str, "Command"] = {}
        self.existing_modules: dict[str, ModuleType] = {}

    def get_command(self, command_name: str) -> "Command":
        command = self.commands.get(command_name)
        if command:
            return command
        raise NotFoundError(f'Команды "{command_name}" - не существует')

    def register_command(self, command: "Command", module: ModuleType):
        self.commands[command.name] = command
        self.existing_modules[module.__name__] = module

    def find_new_commands(self) -> list[tuple["Command", ModuleType]]:
        commands: list["Command"] = []
        for command_dir in COMMANDS_PATH.glob(COMMANDS_PATTERN):
            if command_dir.is_dir():
                endpoint_file_path = command_dir / COMMANDS_ENDPOINT_FILENAME
                props_file_path = command_dir / COMMANDS_PROPS_FILENAME

                if endpoint_file_path.exists() and props_file_path.exists():
                    with open(props_file_path, "r", encoding="utf-8") as file:
                        command_props: dict[str, str] = safe_load(file)

                    module: ModuleType = import_module(
                        f"{COMMANDS_PATH.name}.{command_dir.name}.{COMMANDS_ENDPOINT_FILENAME[:-3]}"
                    )
                    command: "Command" = getattr(module, command_props["class_name"])
                    command = command(
                        name=command_props["name"],
                        alias=command_props["alias"],
                        result_temp=command_props.get("result_temp", ""),
                        doc=command_props["doc"],
                    )
                    commands.append((command, module))
        return commands


commands_manager = CommandsManager()


class Command(ABC):
    def __init__(
        self,
        name: str,
        alias: str,
        quest_map: tuple[str, type] | None = None,
        result_temp: str = "",
        doc: str = "",
    ):
        self.name = name
        self.alias = alias
        self.quest_map = quest_map if quest_map else ()
        self.result_temp = result_temp
        self.__doc__ = doc

    @property
    def doc(self):
        return self.__doc__

    def invoke(self, *args, **kwargs):
        raise NotImplementedError()
