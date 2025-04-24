from core import Command
import math
from commands.scaler import DXFScaler
from pathlib import Path


class flanec(Command):
    def __init__(self, *args, **kwargs):
        quest_map = (
            ("Введите поперечное усилие (Q) в кН: ", float),
        )
        self.scaler = DXFScaler(Path(__file__).parent, "test_node_e2.dxf")

        # Добавляем переменные по нормам
        self.min_edge_distance_along = 2.0  # вдоль усилия, в диаметрах болта
        self.min_edge_distance_across = 1.5  # поперек усилия, в диаметрах болта

        self.min_spacing_along = 3.0  # межосевое расстояние вдоль усилия
        self.min_spacing_across = 3.0  # межосевое расстояние поперек усилия (можно 4.0 при необходимости)

        super().__init__(*args, quest_map=quest_map, **kwargs)

    @staticmethod
    def round_to_nearest_higher(value):
        standard_values = [10, 12, 14, 15, 16, 18, 20, 22, 25, 28, 30, 32, 35, 36, 40, 45, 50, 55, 60, 63, 65, 70, 75,
                           80, 85, 90, 95, 100, 105, 110, 120, 125, 130, 140, 150, 160, 170, 180, 190, 200]
        if value in standard_values:
            return value
        for standard in standard_values:
            if standard >= value:
                return standard
        return standard_values[-1]

    def invoke(self, Q: float) -> str:
        height_sup_table = Q / 0.8 + 10
        height_sup_table = max(height_sup_table, 100)
        height_sup_table = self.round_to_nearest_higher(math.ceil(height_sup_table))

        Abn_s = (157, 245, 353, 561, 816, 1120, 1472)
        usage_persents = []
        for Abn in Abn_s:
            numerator = Q / (0.33 * Abn * 1.28 * 2 * 0.9)
            denominator = 1 / (0.45 * Abn)
            usage_persent = (numerator ** 2 + denominator ** 2) ** 0.5
            usage_persents.append(usage_persent)

        valid_usage = [x for x in usage_persents if x < 1.0]
        if not valid_usage:
            return "Не удалось подобрать подходящий болт – все варианты перегружены."
        closest_to_09 = min(valid_usage, key=lambda x: abs(x - 0.9))
        index = usage_persents.index(closest_to_09)

        bolt_size_map = {157: 16, 245: 20, 353: 24, 561: 30, 816: 36, 1120: 42, 1472: 48}
        result_Abn = bolt_size_map[Abn_s[index]]
        usage_percent = round(closest_to_09 * 100)

        # Расчёт толщины фланцевой пластины
        St = Q / (0.5 * result_Abn)
        St = max(St, 16)
        St = self.round_to_nearest_higher(math.ceil(St))

        # Пример расчёта расстояний с учетом диаметра болта
        d = result_Abn  # диаметр болта
        min_edge_along = self.min_edge_distance_along * d
        min_edge_across = self.min_edge_distance_across * d
        min_spacing_along = self.min_spacing_along * d
        min_spacing_across = self.min_spacing_across * d


        t_height_sup_table = 50 if St > 20 else 40
        t_height_sup_table = self.round_to_nearest_higher(t_height_sup_table)

        self.scaler.scale_object("support_plate", height=height_sup_table)
        self.scaler.scale_object("support_plate_height_dimension", height=height_sup_table)
        self.scaler.move_object("support_plate_height_dimension",
                                offset=self.scaler.calculate_offset(
                                    "support_plate", width="?", height=height_sup_table))

        # TODO связь с DXF:
        self.scaler.scale_object("xxx", height=min_edge_along)
        self.scaler.scale_object("xxx", height=min_edge_across)
        self.scaler.scale_object("xxx", height=min_spacing_along)
        self.scaler.scale_object("xxx", height=min_spacing_across)

        self.scaler.save()

        return self.result_temp.format(height_sup_table, t_height_sup_table, result_Abn, usage_percent, St)
