# commands/perceptron3d/perceptron_logic.py
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
#from neuralnetwork import SigmoidPerceptron3D

DXF_PATH = "/SUPER_PO/commands/neuralnetwork/input/"

# =============================
# Загрузка данных из DXF (ваша функция без изменений)
# =============================
def load_points_from_dxf(dxf_path: str, layer_name: str = None, use_2d: bool = True):
    try:
        import ezdxf
    except ImportError:
        raise ImportError("Для загрузки DXF требуется ezdxf. Установите: pip install ezdxf")

    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    points = []
    labels = []

    for entity in msp:
        color = getattr(entity.dxf, 'color', 7)
        label = 1 if color == 1 else 0
        entity_type = entity.dxftype()

        if entity_type == 'POINT':
            pt = entity.dxf.location
            points.append([float(pt.x), float(pt.y), float(pt.z)])
            labels.append(label)
        elif use_2d and entity_type == 'LWPOLYLINE':
            for vertex in entity.vertices():
                x, y = float(vertex[0]), float(vertex[1])
                z = 0.0
                points.append([x, y, z])
                labels.append(label)
        elif use_2d and entity_type == 'LINE':
            start = entity.dxf.start
            end = entity.dxf.end
            points.append([float(start.x), float(start.y), 0.0])
            points.append([float(end.x), float(end.y), 0.0])
            labels.extend([label, label])

    if not points:
        raise ValueError(f"В файле {dxf_path} не найдено поддерживаемых сущностей")

    X = np.array(points)
    y_true = np.array(labels)
    return X, y_true

# =============================
# Перцептрон (упрощённая версия)
# =============================
class Perceptron3D:
    def __init__(self, lr=0.01):
        self.weights = np.random.randn(3) * 0.1
        self.bias = np.random.randn() * 0.1
        self.lr = lr

    def predict(self, X):
        return ((X @ self.weights + self.bias) > 0).astype(int)

    def train(self, X, y, epochs=100):
        for _ in range(epochs):
            for i in range(len(X)):
                x_i, y_i = X[i], y[i]
                pred = self.predict(x_i)
                if pred != y_i:
                    error = y_i - pred
                    self.weights += self.lr * error * x_i
                    self.bias += self.lr * error
def run_perceptron_analysis(
    dxf_path: Path, 
    output_dir: Path, 
    activation: str = "step",
    model_class=None  # ← новое
):
    if model_class is None:
        if activation == "step":
            model_class = Perceptron3D
        elif activation == "sigmoid":
            model_class = SigmoidPerceptron3D
        else:
            raise ValueError("Поддерживается только 'step' или 'sigmoid'")
    
    output_dir.mkdir(exist_ok=True)
    
    # 1. Загрузка данных
    X, y = load_points_from_dxf(str(dxf_path), use_2d=True)
    
    # 2. Разделение данных
    stratify = y if len(np.unique(y)) > 1 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=stratify
    )
    
    # 3. Обучение модели
    model = model_class(lr=0.01)  # ← теперь гибко
    model.train(X_train, y_train, epochs=100)
    
    # 4. Оценка
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    # 5. Визуализация (без изменений)
    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(X[y == 0, 0], X[y == 0, 1], X[y == 0, 2], 
               c='blue', label='Класс 0', alpha=0.7, s=30)
    ax.scatter(X[y == 1, 0], X[y == 1, 1], X[y == 1, 2], 
               c='red', label='Класс 1', alpha=0.7, s=30)
    ax.set_title(f'Анализ DXF (точность: {accuracy:.2%})')
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.legend()
    
    # 6. Сохранение
    output_image = output_dir / "graph_visualization_Result_test_points.png"
    plt.savefig(output_image, dpi=150, bbox_inches='tight')
    plt.close()
    
    return output_image
# =============================
# ОСНОВНАЯ ФУНКЦИЯ ДЛЯ БОТА
# =============================
'''
def run_perceptron_analysis(dxf_path: Path, output_dir: Path, activation: str = "step"):
    """
    Анализирует DXF-файл и сохраняет изображение с результатом.
    Возвращает путь к PNG-файлу.
    """
    if activation != "step":
        raise ValueError("Поддерживается только активация 'step'")
    
    output_dir.mkdir(exist_ok=True)
    
    # 1. Загрузка данных
    X, y = load_points_from_dxf(str(dxf_path), use_2d=True)
    
    # 2. Разделение данных
    stratify = y if len(np.unique(y)) > 1 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=stratify
    )
    
    # 3. Обучение модели
    model = Perceptron3D(lr=0.01)
    model.train(X_train, y_train, epochs=100)
    
    # 4. Оценка
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    # 5. Визуализация
    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_subplot(111, projection='3d')
    
    # Все точки из исходного набора
    ax.scatter(X[y == 0, 0], X[y == 0, 1], X[y == 0, 2], 
               c='blue', label='Класс 0', alpha=0.7, s=30)
    ax.scatter(X[y == 1, 0], X[y == 1, 1], X[y == 1, 2], 
               c='red', label='Класс 1', alpha=0.7, s=30)
    
    ax.set_title(f'Анализ DXF (точность на тесте: {accuracy:.2%})')
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.legend()
    
    # 6. Сохранение
    output_image = output_dir / "graph_visualization_Result_test_points.png"
    plt.savefig(output_image, dpi=150, bbox_inches='tight')
    plt.close()
    
    return output_image
    '''