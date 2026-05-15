import datetime
import pandas as pd
# Force redeploy for Streamlit Cloud
import re
from streamlit_drawable_canvas import st_canvas
import json
from PIL import Image as PILImage, ImageDraw
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import math
def get_row_patterns(length, M, min_cut_length=0.3, min_stagger=0.4):
    """
    Генерирует два чередующихся паттерна раскладки досок.
    length — длина ряда (м), M — длина целой доски (м).
    Возвращает (row_A, row_B) — два списка длин кусков.
    """
    length = round(length, 3)
    
    if length <= 0.01:
        return [], []

    # Одна доска или меньше — резать нечего
    if length <= M:
        return [round(length, 3)], [round(length, 3)]

    K = int(length // M)       # сколько целых досок помещается
    R = round(length - K * M, 3)  # остаток

    # ─── СЛУЧАЙ 1: Длина делится ровно (остаток = 0) ───
    # Пример: 9м / 3м → [3, 3, 3] и [1.5, 3, 3, 1.5]
    if abs(R) < 0.001:
        row_A = [M] * K
        half = round(M / 2.0, 3)
        if half >= min_cut_length and K > 1:
            row_B = [half] + [M] * (K - 1) + [half]
        else:
            # Половина доски слишком коротка — без разбежки
            row_B = list(row_A)
        return row_A, row_B

    # ─── СЛУЧАЙ 2: Асимметричная разбежка (например, 4-4-2 и 2-4-4) ───
    # Применяем только если остаток допустим И визуальная разбежка швов (M - R) достаточно большая
    if R >= min_cut_length and abs(M - R) >= min_stagger:
        row_A = [M] * K + [R]       # целые доски + остаток справа
        row_B = [R] + [M] * K       # остаток слева + целые доски
        return row_A, row_B

    # ─── СЛУЧАЙ 3: Полная симметрия (огрызок или слишком мелкая разбежка) ───
    # Если мы попали сюда, значит асимметричный вариант даст либо огрызок (R < 1),
    # либо некрасивый мелкий шов (например, разбежка всего 30 см).
    # Решение: ищем симметричные ряды с равномерной подрезкой краев.
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
        # Искусственно сдвигаем доски для второго ряда, чтобы была разбежка
        shift = round(min(M - e, e - 1.0, M / 4.0), 3)
        if shift >= 0.2:
            row_B = [round(e + shift, 3)] + [M] * (len(row_A) - 2) + [round(e - shift, 3)]
        else:
            row_B = list(row_A)
        return row_A, row_B

    return [length], [length]


def get_1d_symmetric_pieces(L, M, min_cut_length=0.3, min_stagger=0.4):
    """Нарезка торцевой доски с сохранением ритма"""
    if L <= 0.01: return []
    row_A, _ = get_row_patterns(L, M, min_cut_length, min_stagger)
    return row_A


def get_best_symmetric_layout(row_lengths_arr, eff_w, collection_boards, min_cut_length=0.3, min_stagger=0.4):
    """
    Перебирает все типоразмеры досок в коллекции и выбирает тот,
    который даёт минимальную стоимость (= минимальную обрезь).
    """
    best_cost = float('inf')
    best_layout = None
    best_joints = None
    best_base_board = None

    for base_board in collection_boards:
        M = base_board['length_m']

        layout_matrix = []
        joints = set()
        for r, L in enumerate(row_lengths_arr):
            if L <= 0.01:
                layout_matrix.append([])
                continue
            row_A, row_B = get_row_patterns(L, M, min_cut_length, min_stagger)
            current_row = row_A if r % 2 == 0 else row_B
            layout_matrix.append(current_row)
            # Собираем координаты стыков для парных лаг
            jx = 0
            for p in current_row[:-1]:
                jx = round(jx + p, 3)
                joints.add(jx)

        # Оптимизация нарезки: bin-packing (First Fit Decreasing)
        # Обрезки от одного ряда используются в другом для экономии
        flat_pieces = sorted([p for row in layout_matrix for p in row], reverse=True)
        bins = []
        for p in flat_pieces:
            placed = False
            bins.sort(key=lambda b: M - b)
            for i in range(len(bins)):
                if round(M - bins[i], 3) >= p:
                    bins[i] = round(bins[i] + p, 3)
                    placed = True
                    break
            if not placed:
                bins.append(p)

        total_cost = len(bins) * base_board['board_cost']
        # Штраф за отходы: добавляем стоимость выброшенного материала
        # (цена за метр × суммарные отходы), чтобы раскладка без отходов
        # была приоритетнее, даже если кол-во досок одинаковое по цене
        waste_m = sum(round(M - b, 3) for b in bins)
        cost_per_m = base_board['board_cost'] / M if M > 0 else 0
        total_cost += waste_m * cost_per_m  # реальная стоимость отходов

        if total_cost < best_cost:
            best_cost = total_cost
            best_layout = layout_matrix
            best_joints = joints
            best_base_board = base_board

    return best_layout, best_joints, best_base_board

def optimize_waste(pieces_list, allowed_board):
    pieces_list = sorted(pieces_list, reverse=True)
    bins = []
    for p in pieces_list:
        placed = False
        bins.sort(key=lambda b: allowed_board['length_m'] - b['used'])
        for b in bins:
            if round(allowed_board['length_m'] - b['used'], 2) >= p:
                b['used'] = round(b['used'] + p, 2)
                placed = True
                break
        if not placed:
            bins.append({"board": allowed_board, "used": p})
            
    qty = len(bins)
    sum_cost = qty * allowed_board['board_cost']
    return {allowed_board['name']: {"qty": qty, "sum": sum_cost, "unit": allowed_board['unit']}}

def get_shifted_edge(matrix, is_front_or_left, offset_start, offset_end):
    if not matrix: return []
    row_to_copy = matrix[1] if len(matrix) > 1 and is_front_or_left else matrix[-2] if len(matrix) > 1 else matrix[0]
    p = list(row_to_copy)
    if not p: return []
    if len(p) == 1: p[0] = round(p[0] + offset_start + offset_end, 2)
    else: p[0] = round(p[0] + offset_start, 2); p[-1] = round(p[-1] + offset_end, 2)
    return p

# --- Отрисовка торцевой доски под 45 градусов ---
def draw_edge(ax, pieces, side, L, W, ew, flags):
    cur = 0
    for p in pieces:
        xs = cur; xe = cur + p
        if side == 'front':
            pts = [[xs, 0], [xe, 0], [xe, ew], [xs, ew]]
            if xs == 0 and flags['L']: pts[3][0] = ew
            if round(xe,2) >= round(L,2) and flags['R']: pts[2][0] = L - ew
        elif side == 'back':
            pts = [[xs, W], [xe, W], [xe, W - ew], [xs, W - ew]]
            if xs == 0 and flags['L']: pts[3][0] = ew
            if round(xe,2) >= round(L,2) and flags['R']: pts[2][0] = L - ew
        elif side == 'left':
            pts = [[0, xs], [0, xe], [ew, xe], [ew, xs]]
            if xs == 0 and flags['F']: pts[3][1] = ew
            if round(xe,2) >= round(W,2) and flags['B']: pts[2][1] = W - ew
        elif side == 'right':
            pts = [[L, xs], [L, xe], [L - ew, xe], [L - ew, xs]]
            if xs == 0 and flags['F']: pts[3][1] = ew
            if round(xe,2) >= round(W,2) and flags['B']: pts[2][1] = W - ew
            
        ax.add_patch(patches.Polygon(pts, color='#5d4037', ec='black', lw=1.2))
        cur += p

# --- Геометрия для нестандартных полигонов ---
def point_in_polygon(x, y, vertices):
    """Ray-casting: проверка попадания точки внутрь полигона."""
    n = len(vertices)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = vertices[i]
        xj, yj = vertices[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside

def polygon_row_segments(vertices, y):
    """Scanline: горизонтальные отрезки полигона на высоте y. Возвращает [(x_start, x_end), ...]."""
    intersections = []
    n = len(vertices)
    for i in range(n):
        x1, y1 = vertices[i]
        x2, y2 = vertices[(i + 1) % n]
        if y1 == y2:
            continue
        if min(y1, y2) <= y < max(y1, y2):
            t = (y - y1) / (y2 - y1)
            x = x1 + t * (x2 - x1)
            intersections.append(round(x, 4))
    intersections.sort()
    segments = []
    for i in range(0, len(intersections) - 1, 2):
        if intersections[i + 1] - intersections[i] > 0.001:
            segments.append((intersections[i], intersections[i + 1]))
    return segments

