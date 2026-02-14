# commands/perceptron3d/main.py
from pathlib import Path
from core import Command
from .perceptron_logic import run_perceptron_analysis  # ← Импортируем новую функцию

class Perceptron(Command):
    def __init__(self, *args, **kwargs):
        quest_map = (
            ("Путь к DXF-файлу (или 'default' для input/test_points.dxf): ", str),
        )
        super().__init__(*args, quest_map=quest_map, **kwargs)

    def invoke(self, dxf_path_input: str) -> str:
        try:
            dxf_path = Path(dxf_path_input.strip())

            if not dxf_path.exists():
                return f"❌ Файл не найден: {dxf_path}"

            # Запускаем полный анализ
            output_image = run_perceptron_analysis(
                dxf_path=dxf_path,
                output_dir=Path("output"),
                activation="step"  # только step поддерживается
            )
            return str(output_image)

        except Exception as e:
            return f"❌ Ошибка: {str(e)}"