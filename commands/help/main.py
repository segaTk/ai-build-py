from core import Command, commands_manager


class Help(Command):
    def __init__(self, *args, **kwargs):
        quest_map = (
            ("Введите название команды: ", str),
        )
        super().__init__(*args, quest_map=quest_map, **kwargs)

    def invoke(self, command_name: str) -> str:
        command = commands_manager.get_command(command_name)
        return self.result_temp.format(command.doc)
