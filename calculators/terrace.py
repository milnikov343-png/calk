import datetime
import pandas as pd
import re
from streamlit_drawable_canvas import st_canvas
import json
from PIL import Image as PILImage, ImageDraw
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import math
from itertools import combinations_with_replacement


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
    if abs(R) < 0.001:
        row_A = [M] * K
        half = round(M / 2.0, 3)
        if half >= min_cut_length and K > 1:
            row_B = [half] + [M] * (K - 1) + [half]
        else:
            row_B = list(row_A)
        return row_A, row_B

    # ─── СЛУЧАЙ 2: Асимметричная разбежка ───
    if R >= min_cut_length and abs(M - R) >= min_stagger:
        row_A = [M] * K + [R]
        row_B = [R] + [M] * K
        return row_A, row_B

    # ─── СЛУЧАЙ 3: Полная симметрия ───
    valid_rows = []
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


# ─── Генерация смешанных симметричных паттернов ───

def _gen_mixed_patterns(L, board_lengths, min_cut_length=0.3):
    """
    Генерация симметричных паттернов с использованием досок разных длин.
    Возвращает список паттернов, отсортированных по качеству симметрии.
    """
    L = round(L, 3)
    if L <= 0.01:
        return []
    lengths = sorted(set(round(b, 3) for b in board_lengths), reverse=True)
    max_l = max(lengths)

    if L <= max_l:
        return [[round(L, 3)]]

    candidates = []  # (pattern, penalty)
    max_n = min(int(L / min(lengths)) + 1, 6)

    for n in range(1, max_n + 1):
        for combo in combinations_with_replacement(lengths, n):
            middle_sum = round(sum(combo), 3)
            if middle_sum > L + 0.001:
                continue
            remainder = round(L - middle_sum, 3)

            if abs(remainder) < 0.001:
                # Целые доски заполняют ряд полностью — НОЛЬ отходов, минимум резов
                pattern = list(combo)
                is_sym = (pattern == pattern[::-1])
                # Точное заполнение целыми досками — лучший вариант
                # Даже несимметричный [3,4] отлично работает в паре с [4,3]
                penalty = 0.0
                penalty += len(pattern) * 0.001  # минимальный штраф за кол-во кусков
                candidates.append((pattern, penalty))
                # Добавляем реверс для стагера ([3,4] → [4,3])
                if not is_sym:
                    rev = pattern[::-1]
                    candidates.append((rev, penalty))
            else:
                edge = round(remainder / 2.0, 3)
                if edge >= min_cut_length:
                    pattern = [edge] + list(combo) + [edge]
                    # Всегда зеркально-симметричный
                    min_piece = min(pattern)
                    penalty = 0.0
                    if min_piece < max_l * 0.2:
                        penalty += (max_l * 0.2 - min_piece) * 5
                    penalty += len(pattern) * 0.01
                    candidates.append((pattern, penalty))

    candidates.sort(key=lambda x: (x[1], len(x[0])))
    return [c[0] for c in candidates]


def _pick_staggered_pair(candidates, L):
    """
    Из списка кандидатов выбирает пару (row_A, row_B) с максимальной разбежкой стыков.
    """
    if not candidates:
        return [L], [L]
    if len(candidates) == 1:
        return candidates[0], candidates[0]

    def joints_of(row):
        j = set()
        x = 0
        for p in row[:-1]:
            x = round(x + p, 3)
            j.add(x)
        return j

    row_A = candidates[0]
    joints_A = joints_of(row_A)

    best_B = candidates[1] if len(candidates) > 1 else row_A
    best_overlap = len(joints_A)

    for cand in candidates[1:20]:  # проверяем топ-20
        overlap = len(joints_A & joints_of(cand))
        if overlap < best_overlap:
            best_overlap = overlap
            best_B = cand
            if overlap == 0:
                break

    return row_A, best_B


def get_best_symmetric_layout(row_lengths_arr, eff_w, collection_boards,
                               min_cut_length=0.3, min_stagger=0.4,
                               mode='economy'):
    """
    Перебирает все типоразмеры досок в коллекции и выбирает оптимальный.
    mode='economy'   — минимизация общей стоимости (один типоразмер).
    mode='symmetric' — красивая симметричная раскладка (смешанные длины из коллекции).
    """
    best_cost = float('inf')
    best_waste = float('inf')
    best_sym_penalty = float('inf')
    best_layout = None
    best_joints = None
    best_base_board = None

    if mode == 'symmetric':
        # ─── Симметричный режим ───
        # Стратегия: сначала пробуем каждый одиночный типоразмер доски.
        # Если хотя бы один даёт хорошую симметрию (penalty < порога) — берём его.
        # Если все одиночные дают плохую симметрию — используем смешанные длины.

        SYM_THRESHOLD = 5.0  # порог: выше = плохая симметрия, нужно смешивать

        # --- Фаза 1: одиночные доски ---
        single_candidates = []
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
                jx = 0
                for p in current_row[:-1]:
                    jx = round(jx + p, 3)
                    joints.add(jx)

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

            waste_m = sum(round(M - b, 3) for b in bins)
            total_cost = len(bins) * base_board['board_cost']

            sym_penalty = 0.0
            for row in layout_matrix:
                if len(row) < 2:
                    continue
                diff = abs(row[0] - row[-1])
                if diff > 0.01:
                    sym_penalty += diff * 10
                min_piece = min(row)
                if min_piece < M * 0.3:
                    sym_penalty += (M * 0.3 - min_piece) * 5
                sym_penalty += len(row) * 0.01

            single_candidates.append({
                'board': base_board, 'layout': layout_matrix, 'joints': joints,
                'cost': total_cost, 'waste': waste_m, 'penalty': sym_penalty
            })

        # Лучший одиночный вариант (по симметрии, потом по стоимости)
        single_candidates.sort(key=lambda c: (round(c['penalty'], 2), c['cost']))
        best_single = single_candidates[0]

        if best_single['penalty'] <= SYM_THRESHOLD:
            # Хорошая симметрия с одной доской — используем её
            best_layout = best_single['layout']
            best_joints = best_single['joints']
            best_base_board = best_single['board']
            best_cost = best_single['cost']
            best_waste = best_single['waste']
        else:
            # --- Фаза 2: смешанные доски ---
            board_lengths = [b['length_m'] for b in collection_boards]
            boards_by_cpm = sorted(collection_boards, key=lambda b: b['board_cost'] / b['length_m'])

            unique_lengths = {}
            for L in row_lengths_arr:
                L_key = round(L, 3)
                if L_key not in unique_lengths and L_key > 0.01:
                    pats = _gen_mixed_patterns(L_key, board_lengths, min_cut_length)
                    row_A, row_B = _pick_staggered_pair(pats, L_key)
                    unique_lengths[L_key] = (row_A, row_B)

            layout_matrix = []
            joints = set()
            for r, L in enumerate(row_lengths_arr):
                L_key = round(L, 3)
                if L_key <= 0.01:
                    layout_matrix.append([])
                    continue
                row_A, row_B = unique_lengths[L_key]
                current_row = row_A if r % 2 == 0 else row_B
                layout_matrix.append(current_row)
                jx = 0
                for p in current_row[:-1]:
                    jx = round(jx + p, 3)
                    joints.add(jx)

            # Bin-packing с мультиразмерными досками
            flat_pieces = sorted([p for row in layout_matrix for p in row], reverse=True)
            bins = []
            for p in flat_pieces:
                placed = False
                best_idx = -1
                best_rem = float('inf')
                for i, (brd, used) in enumerate(bins):
                    rem = round(brd['length_m'] - used, 3)
                    if rem >= p and rem < best_rem:
                        best_idx = i
                        best_rem = rem
                if best_idx >= 0:
                    brd, used = bins[best_idx]
                    bins[best_idx] = (brd, round(used + p, 3))
                    placed = True
                if not placed:
                    for brd in boards_by_cpm:
                        if brd['length_m'] >= p:
                            bins.append((brd, round(p, 3)))
                            placed = True
                            break
                    if not placed:
                        bins.append((boards_by_cpm[-1], round(p, 3)))

            total_cost = sum(brd['board_cost'] for brd, used in bins)
            waste_m = sum(round(brd['length_m'] - used, 3) for brd, used in bins)

            board_counts = {}
            for brd, used in bins:
                nm = brd['name']
                if nm not in board_counts:
                    board_counts[nm] = {'qty': 0, 'sum': 0, 'board': brd}
                board_counts[nm]['qty'] += 1
                board_counts[nm]['sum'] += brd['board_cost']

            best_base_board = max(collection_boards, key=lambda b: b['length_m'])
            best_layout = layout_matrix
            best_joints = joints
            best_cost = total_cost
            best_waste = waste_m
            best_base_board = dict(best_base_board)
            best_base_board['_mixed_counts'] = board_counts

    else:
        # ─── Эконом режим: один типоразмер, минимизация стоимости ───
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
                jx = 0
                for p in current_row[:-1]:
                    jx = round(jx + p, 3)
                    joints.add(jx)

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

            waste_m = sum(round(M - b, 3) for b in bins)
            total_cost = len(bins) * base_board['board_cost']
            cost_per_m = base_board['board_cost'] / M if M > 0 else 0
            effective_cost = total_cost + waste_m * cost_per_m

            if effective_cost < best_cost:
                best_cost = effective_cost
                best_waste = waste_m
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
    """Scanline: горизонтальные отрезки полигона на высоте y."""
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

# --- Работа с досками произвольной длины (под заказ) ---

def round_up_to_custom(piece_len, custom_boards):
    """Находит минимальную доску из custom_boards, которая >= piece_len."""
    for b in custom_boards:
        if b['length_m'] >= piece_len - 0.001:
            return b
    return custom_boards[-1]

def get_custom_length_layout(row_lengths_arr, eff_w, custom_boards, mode='symmetric'):
    """
    Раскладка для режима "Любая длина под заказ".
    custom_boards — список досок (от 0.5 до 6.0 м) с шагом 0.1 м, отсортированный по длине.
    """
    max_board = custom_boards[-1]
    M = max_board['length_m']
    
    layout_matrix = []
    joints = set()
    board_counts = {}
    total_cost = 0.0
    waste_m = 0.0
    
    for r, L in enumerate(row_lengths_arr):
        if L <= 0.01:
            layout_matrix.append([])
            continue
            
        if mode == 'symmetric':
            if L <= M:
                row_A = [L]
                row_B = [L]
            else:
                import math
                n_A = math.ceil(L / M)
                len_A = round(L / n_A, 3)
                
                row_A = [len_A] * (n_A - 1)
                row_A.append(round(L - sum(row_A), 3))
                
                half_A = round(len_A / 2.0, 3)
                if n_A == 1:
                    row_B = [half_A, round(L - half_A, 3)]
                else:
                    row_B = [half_A] + [len_A] * (n_A - 1)
                    row_B.append(round(L - sum(row_B), 3))
        else:
            # Эконом: бьём на куски по максимальной длине M (обычно 6м) + остаток
            if L <= M:
                row_A = [L]
                row_B = [L]
            else:
                K = int(L // M)
                rem = round(L - K * M, 3)
                row = [M] * K
                if rem > 0.01:
                    row.append(rem)
                row_A = row
                row_B = row
                
        current_row = row_A if r % 2 == 0 else row_B
        layout_matrix.append(current_row)
        
        jx = 0
        for p in current_row[:-1]:
            jx = round(jx + p, 3)
            joints.add(jx)
            
        # Заносим каждый кусок в смету (округляя до доступного типоразмера)
        for p in current_row:
            brd = round_up_to_custom(p, custom_boards)
            nm = brd['name']
            if nm not in board_counts:
                board_counts[nm] = {'qty': 0, 'sum': 0.0, 'board': brd}
            board_counts[nm]['qty'] += 1
            board_counts[nm]['sum'] += brd['board_cost']
            total_cost += brd['board_cost']
            waste_m += round(brd['length_m'] - p, 3)
            
    best_base_board = dict(max_board)
    best_base_board['_mixed_counts'] = board_counts
    
    return layout_matrix, joints, best_base_board

def consolidate_lengths(board_counts, min_qty=10):
    """
    Группирует мелкие партии (< 10 шт) в ближайшие бОльшие длины.
    Возвращает обновлённую смету и словарь истории объединений для менеджера.
    """
    items = list(board_counts.values())
    items.sort(key=lambda x: x['board']['length_m'])
    
    if not any(item['qty'] < min_qty for item in items):
        return board_counts, {}
        
    history = {}
    
    while True:
        items.sort(key=lambda x: x['board']['length_m'])
        target_idx = -1
        for i, item in enumerate(items):
            if 0 < item['qty'] < min_qty:
                target_idx = i
                break
                
        if target_idx == -1:
            break
            
        target_item = items[target_idx]
        
        merge_idx = -1
        for i in range(target_idx + 1, len(items)):
            if items[i]['qty'] > 0:
                merge_idx = i
                break
                
        if merge_idx != -1:
            merge_item = items[merge_idx]
            merge_item['qty'] += target_item['qty']
            merge_item['sum'] = merge_item['qty'] * merge_item['board']['board_cost']
            
            new_name = merge_item['board']['name']
            old_name = target_item['board']['name']
            
            if new_name not in history:
                history[new_name] = [new_name]
            if old_name in history:
                history[new_name].extend(history[old_name])
                del history[old_name]
            else:
                history[new_name].append(old_name)
                
            target_item['qty'] = 0
        else:
            old_qty = target_item['qty']
            target_item['qty'] = min_qty
            target_item['sum'] = min_qty * target_item['board']['board_cost']
            new_name = target_item['board']['name']
            if new_name not in history:
                history[new_name] = [f"{new_name} (дозаказ с {old_qty} до {min_qty} шт)"]
            break
            
    final_counts = {item['board']['name']: item for item in items if item['qty'] > 0}
    clean_history = {k: v for k, v in history.items() if len(v) > 1 or "дозаказ" in v[0]}
            
    return final_counts, clean_history
