from core import Command
import  math


class flanec(Command):
    def __init__(self, *args, **kwargs):
        quest_map = (
            ("Введите поперечное усилие (Q) в кН: ", float),
        )
        super().__init__(*args, quest_map=quest_map, **kwargs)

    @staticmethod
    def round_to_nearest_higher(value):
        standard_values = [40, 45, 50, 55, 60, 63, 65, 70, 75, 80, 85, 90, 95,
                           100, 105, 110, 120, 125, 130, 140, 150, 160, 170, 180, 190, 200]

        # Если значение уже есть в списке, возвращаем его
        if value in standard_values:
            return value

        # Находим первое стандартное значение, которое больше или равно нашему значению
        for standard in standard_values:
            if standard >= value:
                return standard

        # Если значение больше всех стандартных, возвращаем максимальное
        return standard_values[-1]

    def invoke(self, Q: float) -> str:
        # Округляем высоту опорного столика
        height_sup_table = Q / 8 + 1
        height_sup_table = max(height_sup_table, 10)
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

        St = Q / (0.5 * result_Abn)
        St = max(St, 16)  # Не менее 16 мм
        # Округляем толщину фланцевой пластины
        St = self.round_to_nearest_higher(math.ceil(St))

        t_height_sup_table = 50 if St > 20 else 40
        # Округляем толщину опорного столика
        t_height_sup_table = self.round_to_nearest_higher(t_height_sup_table)

        return self.result_temp.format(height_sup_table, t_height_sup_table, result_Abn, usage_percent, St)