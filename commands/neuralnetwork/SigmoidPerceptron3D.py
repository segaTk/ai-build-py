import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
# commands/perceptron3d/perceptron_logic.py
# Добавьте этот класс ПОСЛЕ существующего Perceptron3D

class SigmoidPerceptron3D:
    def __init__(self, lr=0.01):
        self.weights = np.random.randn(3) * 0.1
        self.bias = np.random.randn() * 0.1
        self.lr = lr

    def _sigmoid(self, z):
        # Защита от переполнения
        z = np.clip(z, -500, 500)
        return 1 / (1 + np.exp(-z))

    def predict(self, X):
        """
        Возвращает бинарные метки (0 или 1), как и оригинальный перцептрон.
        """
        if X.ndim == 1:
            X = X.reshape(1, -1)
        logits = X @ self.weights + self.bias
        probabilities = self._sigmoid(logits)
        return (probabilities >= 0.5).astype(int)

    def train(self, X, y, epochs=100):
        """
        Обучение с использованием сигмоидной активации и градиентного спуска.
        """
        n_samples = X.shape[0]
        y = y.astype(float)  # для вычислений

        for epoch in range(epochs):
            # Прямой проход
            logits = X @ self.weights + self.bias
            predictions = self._sigmoid(logits)

            # Ошибка (бинарная кросс-энтропия производная)
            errors = predictions - y  # shape: (n_samples,)

            # Градиенты
            dw = (X.T @ errors) / n_samples
            db = np.mean(errors)

            # Обновление весов
            self.weights -= self.lr * dw
            self.bias -= self.lr * db