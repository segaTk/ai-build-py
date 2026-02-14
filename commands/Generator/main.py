# commands/generator/main.py
from pathlib import Path
from openpyxl import Workbook
from core import Command

class Generator(Command):
    def __init__(self, *args, **kwargs):
        quest_map = (
            ("Введите число a: ", float),
            ("Введите число b: ", float),
        )
        super().__init__(*args, quest_map=quest_map, **kwargs)

    def invoke(self, a: float, b: float) -> str:
        # Создаём пустой Excel-файл
        wb = Workbook()
        ws = wb.active
        ws.title = "Данные"

        # Опционально: можно записать a и b
        ws["A1"] = "a"
        ws["B1"] = a
        ws["A2"] = "b"
        ws["B2"] = b
        ws["A3"] = "Разность"
        ws["B3"] = a - b

        # Сохраняем во временную папку
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        file_path = output_dir / "result.xlsx"
        wb.save(file_path)

        # Возвращаем путь к файлу как строку
        return str(file_path)