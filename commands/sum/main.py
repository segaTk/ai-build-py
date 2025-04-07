from core import Command


class SumOfTwo(Command):
    def __init__(self, *args, **kwargs):
        quest_map = (
            ("Введите чило a: ", float),
            ("Введите чило b: ", float),
        )
        super().__init__(*args, quest_map=quest_map, **kwargs)

    def invoke(self, a: int, b: int) -> str:
        return self.result_temp.format(a + b)
