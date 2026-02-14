from pathlib import Path
from commands.scaler import DXFScaler
import time

# Путь к папке, где лежит test_pdf.py
script_dir = Path(__file__).parent

# DXF-файл в той же папке
dxf_path = script_dir / "test_node_e2.dxf"

print("1. Загружаем DXF...")
scaler = DXFScaler(script_dir, dxf_path.name)

print(f"   Сущностей в modelspace: {len(scaler.msp)}")

print("2. Сохраняем output.dxf...")
scaler.save()

print("3. Запускаем экспорт в PDF...")
start_time = time.time()

try:
    scaler.export_to_pdf("test_output.pdf", dpi=150)
    print("✅ Успех!")
except Exception as e:
    print(f"❌ Ошибка: {e}")

print(f"Затрачено времени: {time.time() - start_time:.1f} сек")