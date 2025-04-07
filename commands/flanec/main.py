from core import Command


class flanec(Command):
    def __init__(self, *args, **kwargs):
        quest_map = (
            ("Введите поперечное усилие (Q) в кН: ", float),
        )
        super().__init__(*args, quest_map=quest_map, **kwargs)


    def invoke(self, Q: float) -> str:
        height_sup_table = Q / 8 + 1
        height_sup_table = max(height_sup_table, 10)

        Abn_s = (157, 245, 353, 561, 816, 1120, 1472)
        usage_persents = []
        for Abn in Abn_s:
            numerator = Q / (0.33 * Abn * 1.28 * 2 * 0.9)
            denominator = 1 / (0.45 * Abn)
            usage_persent = (numerator ** 2 + denominator ** 2) ** 0.5
            usage_persents.append(usage_persent)

        valid_usage = [x for x in usage_persents if x < 1.0]
        closest_to_09 = min(valid_usage, key=lambda x: abs(x - 0.9))
        index = usage_persents.index(closest_to_09)

        bolt_size_map = {157: 16, 245: 20, 353: 24, 561: 30, 816: 36, 1120: 42, 1472: 48}
        result_Abn = bolt_size_map[Abn_s[index]]
        x = closest_to_09 * 100
        usage_percent = round(x)

        St = Q / (0.5 * result_Abn)
        St = max(St, 16)  # Не менее 16 мм
        t_height_sup_table = 0
        t_height_sup_table += 50 if St > 20 else 40

        return self.result_temp.format(height_sup_table, t_height_sup_table, result_Abn, usage_percent, St)
