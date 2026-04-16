def get_row_patterns(length, M):
    length = round(length, 3)
    MIN_CUT_LENGTH = 1.0
    MIN_STAGGER = 1.0  # Минимальная разбежка швов (визуальная красота)

    if length <= 0.01: return [], []
    if length <= M: return [length], [length]

    K = int(length // M)
    R = round(length - K * M, 3)

    # СЛУЧАЙ 1: Делится ровно (без остатка)
    if abs(R) < 0.001:
        row_A = [M] * K
        half = round(M / 2.0, 3)
        if half >= MIN_CUT_LENGTH and K > 1:
            row_B = [half] + [M] * (K - 1) + [half]
        else:
            row_B = list(row_A)
        return row_A, row_B

    # СЛУЧАЙ 2: Асимметричная разбежка (например, 4-4-2 и 2-4-4)
    # Применяем только если остаток хороший И визуальная разбежка швов (M - R) достаточно большая
    if R >= MIN_CUT_LENGTH and abs(M - R) >= MIN_STAGGER:
        row_A = [M] * K + [R]
        row_B = [R] + [M] * K
        return row_A, row_B

    # СЛУЧАЙ 3: Полная симметрия (если остаток слишком мал или разбежка невидима)
    valid_rows = []
    # Ищем все возможные симметричные ряды, от максимального кол-ва целых досок к минимальному
    for k in range(K, -1, -1):
        rem = round(length - k * M, 3)
        e = round(rem / 2.0, 3)
        if 1.0 <= e <= M:
            valid_rows.append([e] + [M] * k + [e])

    if len(valid_rows) >= 2:
        return valid_rows[0], valid_rows[1]
    elif len(valid_rows) == 1:
        row_A = valid_rows[0]
        e = row_A[0]
        # Сдвигаем чтобы получить второй искусственный ряд
        shift = round(min(M - e, e - 1.0, M / 4.0), 3)
        if shift >= 0.2:
            row_B = [round(e + shift, 3)] + [M] * (len(row_A) - 2) + [round(e - shift, 3)]
        else:
            row_B = list(row_A)
        return row_A, row_B

    return [length], [length]

tests = [
    (9.0, 3.0),
    (10.0, 4.0),
    (8.71, 3.0),
    (8.5, 4.0)
]
for L, M in tests:
    print(f"{L}/{M}: {get_row_patterns(L, M)}")
