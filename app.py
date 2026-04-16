import streamlit as st
import math
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import io
from fpdf import FPDF
import datetime
import pandas as pd
import re

# --- 1. ЗАГРУЗКА БАЗЫ ИЗ GOOGLE ТАБЛИЦ ---
@st.cache_data(ttl=300)
def load_google_sheet():
    SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRgxTJ2JPrhh_da9pEBWMoKU3iT5x0DZkzKmKrOKcJBbAos8XmYJDzJyHKvcTtAfPrcpMKDzHW4AWG6/pub?gid=0&single=true&output=csv"
    
    boards = {}
    pipes_joist = {"Труба 60х40х2": 219, "Труба 60х40х3": 290}
    pipes_frame = {"Труба 80х80х2": 403, "Труба 80х80х3": 475}

    try:
        df = pd.read_csv(SHEET_URL)
        for index, row in df.iterrows():
            brand = str(row['Бренд']).strip()
            raw_name = str(row['Наименование']).strip()
            price = float(row['Цена'])
            unit = str(row['Единица']).strip()
            width = int(row['Ширина (мм)'])
            length_m = float(row['Длина (м)'])

            base_name = re.sub(r'\d{4}[хx*]\d{2,3}[хx*]\d{2,3}', '', raw_name, flags=re.IGNORECASE)
            base_name = re.sub(r'\s*\d+(\.\d+)?\s*м\b', '', base_name, flags=re.IGNORECASE).replace('  ', ' ').strip()
            
            if brand not in boards: boards[brand] = {}
            if base_name not in boards[brand]: boards[brand][base_name] = []
            
            board_cost = price if unit.lower() == 'шт' else price * length_m

            boards[brand][base_name].append({
                "name": raw_name,
                "length_m": length_m,
                "price": price,
                "unit": unit,
                "width_mm": width,
                "board_cost": board_cost
            })
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")
    return boards, pipes_joist, pipes_frame

PARSED_BOARDS, PIPES_JOIST, PIPES_FRAME = load_google_sheet()

METAL_MARGIN = 1.15
GAP_MM = 5
JOIST_STEP_M = 0.4
PILE_STEP_M = 2.0

# --- 2. ИДЕАЛЬНАЯ МАТЕМАТИКА ПРЯМОУГОЛЬНОЙ ТЕРРАСЫ ---
def fill_segment(L, M, min_allowed, step):
    if L <= 0.01: return []
    pieces = []
    rem = L
    while rem > M + 0.01:
        pieces.append(M)
        rem = round(rem - M, 2)
    if rem > 0.01:
        pieces.append(round(rem, 2))
    
    if len(pieces) > 1 and pieces[-1] < min_allowed:
        deficit = math.ceil((min_allowed - pieces[-1]) / step) * step
        if pieces[-2] - deficit >= min_allowed:
            pieces[-2] = round(pieces[-2] - deficit, 2)
            pieces[-1] = round(pieces[-1] + deficit, 2)
        else:
            combined = pieces[-2] + pieces[-1]
            half = math.floor((combined / 2) / step) * step
            if half <= 0: half = step
            pieces[-2] = round(half, 2)
            pieces[-1] = round(combined - half, 2)
    return pieces

def get_1d_symmetric_pieces(L, M, min_allowed, step):
    if L <= 0.01: return []
    eff_M = math.floor(M / step) * step
    if eff_M <= 0: eff_M = M
    if L <= eff_M: return [round(L, 2)]
    
    cx = math.floor((L / 2) / step) * step
    left = fill_segment(cx, eff_M, min_allowed, step)
    right = fill_segment(round(L - cx, 2), eff_M, min_allowed, step)
    return [round(x, 2) for x in left[::-1] + right]

def get_row_patterns(length, M, min_allowed):
    if length <= M: return [round(length, 2)], [round(length, 2)]
    
    # Ряд А (Шов по центру)
    half = length / 2.0
    num = int(half // M)
    edge = half - num * M
    h_a = ([edge] if edge > 0.01 else []) + [M] * num
    if len(h_a) > 1 and h_a[0] < min_allowed:
        comb = h_a[0] + h_a[1]; h_a[0] = comb / 2.0; h_a[1] = comb / 2.0
    row_A = h_a + h_a[::-1]
    
    # Ряд Б (Целая доска по центру)
    half_rem = (length - M) / 2.0
    if half_rem <= 0.01:
        row_B = [round(length/2.0, 2), round(length/2.0, 2)]
    else:
        num = int(half_rem // M)
        edge = half_rem - num * M
        h_b = ([edge] if edge > 0.01 else []) + [M] * num
        if len(h_b) > 1 and h_b[0] < min_allowed:
            comb = h_b[0] + h_b[1]; h_b[0] = comb / 2.0; h_b[1] = comb / 2.0
        elif len(h_b) == 1 and h_b[0] < min_allowed:
            if length / 3.0 <= M:
                return [round(x, 2) for x in row_A], [round(length/3.0, 2)] * 3
        row_B = h_b + [M] + h_b[::-1]
        
    return [round(x, 2) for x in row_A], [round(x, 2) for x in row_B]

def get_best_symmetric_layout(target_len, target_width, eff_w, collection_boards):
    rows_count = math.ceil(target_width / eff_w)
    best_cost = float('inf')
    best_layout = None
    best_joints = None
    best_base_board = None

    for base_board in collection_boards:
        M = base_board['length_m']
        min_allowed = max(0.8, M / 3.0)
        
        row_A, row_B = get_row_patterns(target_len, M, min_allowed)

        layout_matrix = []
        joints = set()
        for r in range(rows_count):
            current_row = row_A if r % 2 == 0 else row_B
            layout_matrix.append(current_row)
            jx = 0
            for p in current_row[:-1]:
                jx = round(jx + p, 2)
                joints.add(jx)

        flat_pieces = sorted([p for row in layout_matrix for p in row], reverse=True)
        bins = []
        for p in flat_pieces:
            placed = False
            bins.sort(key=lambda b: M - b)
            for i in range(len(bins)):
                if round(M - bins[i], 2) >= p:
                    bins[i] = round(bins[i] + p, 2)
                    placed = True
                    break
            if not placed:
                bins.append(p)
                
        total_cost = len(bins) * base_board['board_cost']

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

# --- 3. ИНТЕРФЕЙС И ВЫБОР ФОРМЫ ---
st.set_page_config(page_title="Дача 2000 | Умный Калькулятор", layout="wide")
st.title("🏗️ Профессиональный проект террасы")

col_h1, col_h2 = st.columns([8, 2])
with col_h2:
    if st.button("🔄 Обновить прайс", use_container_width=True):
        st.cache_data.clear(); st.rerun()

st.sidebar.header("1. Форма террасы")
shape_type = st.sidebar.selectbox("Выберите конфигурацию:", [
    "⬜ Прямоугольная (Стандарт)", 
    "📐 Г-образная (Угловая)", 
    "🔲 П-образная (С вырезом)", 
    "⏺️ Округлая (Овал / Круг)",
    "✏️ Свой контур (По координатам)"
])

st.sidebar.header("2. Параметры объекта")
client_name = st.sidebar.text_input("ФИО Клиента:", "Иван Иванович")

if shape_type == "⬜ Прямоугольная (Стандарт)":
    length = st.sidebar.number_input("Длина фасада (X), м:", 1.0, 50.0, 9.0)
    width = st.sidebar.number_input("Глубина (Y), м:", 1.0, 50.0, 4.0)

elif shape_type == "📐 Г-образная (Угловая)":
    st.sidebar.caption("Задайте общие габариты и размер выреза:")
    col1, col2 = st.sidebar.columns(2)
    length = col1.number_input("Общая длина X, м:", 1.0, 50.0, 6.0)
    width = col2.number_input("Общая глубина Y, м:", 1.0, 50.0, 5.0)
    cut_x = col1.number_input("Вырез X, м:", 0.1, float(length-0.1), 3.0)
    cut_y = col2.number_input("Вырез Y, м:", 0.1, float(width-0.1), 2.0)

elif shape_type == "🔲 П-образная (С вырезом)":
    st.sidebar.caption("Задайте общие габариты и центральный вырез:")
    length = st.sidebar.number_input("Общая длина X, м:", 1.0, 50.0, 8.0)
    width = st.sidebar.number_input("Общая глубина Y, м:", 1.0, 50.0, 5.0)
    col1, col2 = st.sidebar.columns(2)
    cut_w = col1.number_input("Ширина выреза X, м:", 0.1, float(length-0.2), 3.0)
    cut_d = col2.number_input("Глубина выреза Y, м:", 0.1, float(width-0.1), 2.0)

elif shape_type == "⏺️ Округлая (Овал / Круг)":
    st.sidebar.caption("Задайте габариты овала (для круга X и Y равны):")
    length = st.sidebar.number_input("Общая длина (Диаметр X), м:", 1.0, 50.0, 6.0)
    width = st.sidebar.number_input("Общая глубина (Диаметр Y), м:", 1.0, 50.0, 4.0)

elif shape_type == "✏️ Свой контур (По координатам)":
    st.sidebar.caption("Таблица точек полигона (в метрах):")
    df_coords = pd.DataFrame([{"X (м)": 0.0, "Y (м)": 0.0}, {"X (м)": 0.0, "Y (м)": 4.0}, {"X (м)": 6.0, "Y (м)": 4.0}, {"X (м)": 6.0, "Y (м)": 0.0}])
    edited_df = st.sidebar.data_editor(df_coords, num_rows="dynamic", use_container_width=True)
    length = 5.0
    width = 5.0

base_type = st.sidebar.radio("Основание:", ["Грунт (Сваи)", "Бетон"])

# --- БАССЕЙН ---
st.sidebar.header("3. Бассейн")
has_pool = st.sidebar.checkbox("Встроенный бассейн (вырез в террасе)", value=False)
if has_pool:
    pool_shape = st.sidebar.radio("Форма бассейна:", ["⬜ Прямоугольный", "⏺️ Круглый", "⬭ Овальный"])
    
    col1, col2 = st.sidebar.columns(2)
    if pool_shape in ["⬜ Прямоугольный", "⬭ Овальный"]:
        pool_l = col1.number_input("Длина басс. X, м:", 0.5, 20.0, 4.0)
        pool_w = col2.number_input("Ширина басс. Y, м:", 0.5, 20.0, 2.5)
    else:
        pool_d = st.sidebar.number_input("Диаметр бассейна, м:", 0.5, 20.0, 3.0)
    
    st.sidebar.caption("Отступы от левого нижнего угла террасы (0,0):")
    col3, col4 = st.sidebar.columns(2)
    pool_offset_x = col3.number_input("Смещение X, м:", 0.0, 50.0, 1.0)
    pool_offset_y = col4.number_input("Смещение Y, м:", 0.0, 50.0, 1.0)


st.sidebar.header("4. Выбор коллекции")
brand_choice = st.sidebar.selectbox("Бренд:", list(PARSED_BOARDS.keys()))
if PARSED_BOARDS[brand_choice]:
    collection_name = st.sidebar.selectbox("Коллекция:", list(PARSED_BOARDS[brand_choice].keys()))
    collection_boards = PARSED_BOARDS[brand_choice][collection_name]
    eff_w = (collection_boards[0]["width_mm"] + GAP_MM) / 1000
else:
    st.stop()

direction_choice = st.sidebar.radio("Направление укладки основной доски:", ["Вдоль фасада (по длине X)", "Поперек фасада (по глубине Y)"])

st.sidebar.header("5. Окантовка (Торцевая доска)")
use_frame = st.sidebar.checkbox("Сделать окантовку по периметру (Picture Frame)", value=True)
edge_front = True; edge_back = True; edge_left = True; edge_right = True
if not use_frame: edge_front = edge_back = edge_left = edge_right = False

st.sidebar.header("6. Подсистема")
joist_choice = st.sidebar.selectbox("Лаги (60х40):", list(PIPES_JOIST.keys()))
frame_choice = st.sidebar.selectbox("Каркас (80х80):", list(PIPES_FRAME.keys())) if "Грунт" in base_type else None
steps_m = st.sidebar.number_input("Ступени (пог.м):", 0.0, 50.0, 0.0)

# --- БЛОКИРОВКА СЛОЖНЫХ РАСЧЕТОВ ---
is_complex = (shape_type != "⬜ Прямоугольная (Стандарт)") or has_pool

if is_complex:
    st.warning("Интерфейс для сложных форм и бассейнов активирован.")
    st.info("💡 Модуль математического вырезания фигур отключен, чтобы не мешать стабильной работе прямоугольного калькулятора.\n\nПожалуйста, переключитесь на «Прямоугольную (Стандарт)» и уберите галочку бассейна, чтобы увидеть расчёты.")
    st.stop()

# --- 4. РАСЧЕТЫ ДЛЯ ПРЯМОУГОЛЬНОЙ ТЕРРАСЫ ---
area = length * width

offset_front = eff_w if edge_front else 0
offset_back = eff_w if edge_back else 0
offset_left = eff_w if edge_left else 0
offset_right = eff_w if edge_right else 0

inner_X = round(length - offset_left - offset_right, 3)
inner_Y = round(width - offset_front - offset_back, 3)

if inner_X <= 0 or inner_Y <= 0:
    st.error("Терраса слишком мала."); st.stop()

board_len_axis = inner_X if "Вдоль" in direction_choice else inner_Y
board_row_axis = inner_Y if "Вдоль" in direction_choice else inner_X

# Раскладка основной доски (ИДЕАЛЬНАЯ А-Б-А-Б)
layout_matrix, best_joints, main_board = get_best_symmetric_layout(board_len_axis, board_row_axis, eff_w, collection_boards)

# Нарезка торцевой доски (Копирование швов основной палубы)
M = main_board['length_m']
min_allowed = max(0.8, M / 3.0)

edge_pieces = []
if use_frame:
    if "Вдоль" in direction_choice:
        front_pieces = get_shifted_edge(layout_matrix, True, offset_left, offset_right) if edge_front else []
        back_pieces = get_shifted_edge(layout_matrix, False, offset_left, offset_right) if edge_back else []
        left_pieces = get_1d_symmetric_pieces(width, M, min_allowed, JOIST_STEP_M) if edge_left else []
        right_pieces = get_1d_symmetric_pieces(width, M, min_allowed, JOIST_STEP_M) if edge_right else []
    else:
        left_pieces = get_shifted_edge(layout_matrix, True, offset_front, offset_back) if edge_left else []
        right_pieces = get_shifted_edge(layout_matrix, False, offset_front, offset_back) if edge_right else []
        front_pieces = get_1d_symmetric_pieces(length, M, min_allowed, JOIST_STEP_M) if edge_front else []
        back_pieces = get_1d_symmetric_pieces(length, M, min_allowed, JOIST_STEP_M) if edge_back else []

    edge_pieces = front_pieces + back_pieces + left_pieces + right_pieces

flat_pieces = [p for row in layout_matrix for p in row] + edge_pieces
board_totals = optimize_waste(flat_pieces, main_board)

# Расчет подсистемы
extra_joists = len(best_joints) * 2 
joist_count_base = math.ceil(board_len_axis / JOIST_STEP_M) + 1
joist_count_total = joist_count_base + extra_joists

j_m = math.ceil((math.ceil(length / JOIST_STEP_M) + 1 + extra_joists) * width)
j_total = j_m * round(PIPES_JOIST[joist_choice] * METAL_MARGIN)

pr = math.ceil(length/PILE_STEP_M) + 1; pc = math.ceil(width/PILE_STEP_M) + 1
piles = pr * pc if "Грунт" in base_type else 0
f_m = math.ceil(pc * length) if "Вдоль" in direction_choice else math.ceil(pr * width)
f_total = f_m * round(PIPES_FRAME[frame_choice] * METAL_MARGIN) if frame_choice and "Грунт" in base_type else 0

clips_packs = math.ceil((math.ceil(width/eff_w) * joist_count_total) / 100)
clips_total = clips_packs * 2200

work_base = area * 2400; work_steps = steps_m * 5200; work_piles = piles * 3600

# Таблицы
mat_data = [{"Позиция": f"Доска террасная/торцевая: {name}", "Кол-во": f"{data['qty']} шт", "Сумма": data['sum']} for name, data in board_totals.items()]
mat_data.extend([{"Позиция": f"Лага {joist_choice} (вкл. парные лаги на стыках)", "Кол-во": f"{j_m} м.п.", "Сумма": j_total}, {"Позиция": "Кляймеры (уп. 100 шт)", "Кол-во": f"{clips_packs} уп.", "Сумма": clips_total}])
if frame_choice and "Грунт" in base_type: mat_data.insert(len(board_totals), {"Позиция": f"Каркас {frame_choice}", "Кол-во": f"{f_m} м.п.", "Сумма": f_total})

work_data = [{"Позиция": "Монтаж настила", "Сумма": work_base}]
if steps_m > 0: work_data.append({"Позиция": "Монтаж ступеней", "Сумма": work_steps})
if piles > 0: work_data.append({"Позиция": f"Монтаж свай ({piles} шт)", "Сумма": work_piles})

grand_total = sum(d['Сумма'] for d in mat_data) + sum(d['Сумма'] for d in work_data)

# --- 5. ЧЕРТЕЖИ ---
def get_plot(mode):
    fig, ax = plt.subplots(figsize=(10, 6))
    step_x = length / (pr - 1) if pr > 1 else length
    step_y = width / (pc - 1) if pc > 1 else width

    if mode == "board":
        draw_w = eff_w * 0.8
        if use_frame:
            flags = {'F': True, 'B': True, 'L': True, 'R': True}
            draw_edge(ax, front_pieces, 'front', length, width, draw_w, flags)
            draw_edge(ax, back_pieces, 'back', length, width, draw_w, flags)
            draw_edge(ax, left_pieces, 'left', length, width, draw_w, flags)
            draw_edge(ax, right_pieces, 'right', length, width, draw_w, flags)

        if "Вдоль" in direction_choice:
            for r, row_pieces in enumerate(layout_matrix):
                y, x = offset_front + r * eff_w, offset_left
                for w in row_pieces:
                    ax.add_patch(patches.Rectangle((x, y), w, draw_w, color='#8d6e63', ec='black', lw=0.5))
                    x += w
        else:
            for r, row_pieces in enumerate(layout_matrix):
                x, y = offset_left + r * eff_w, offset_front
                for w in row_pieces:
                    ax.add_patch(patches.Rectangle((x, y), draw_w, w, color='#8d6e63', ec='black', lw=0.5))
                    y += w
        ax.text(length/2, -0.4, f"Длина фасада: {int(length*1000)} мм", ha='center', fontweight='bold', fontsize=10)
        ax.text(-0.6, width/2, f"Глубина: {int(width*1000)} мм", va='center', rotation=90, fontweight='bold', fontsize=10)

    elif mode == "frame":
        abs_joints = set()
        if "Вдоль" in direction_choice:
            for jx in best_joints: abs_joints.add(offset_left + jx)
            for i in range(math.ceil(length / JOIST_STEP_M) + 1): 
                cx = min(i * JOIST_STEP_M, length)
                ax.plot([cx, cx], [0, width], color='blue', lw=1, alpha=0.3)
            for jx in abs_joints:
                ax.plot([jx-0.02, jx-0.02], [0, width], color='c', lw=1.5, alpha=0.9)
                ax.plot([jx+0.02, jx+0.02], [0, width], color='c', lw=1.5, alpha=0.9)
            if frame_choice and "Грунт" in base_type:
                for j in range(pc):
                    cy = j * step_y
                    ax.plot([0, length], [cy, cy], color='red', lw=3)
        else:
            for jy in best_joints: abs_joints.add(offset_front + jy)
            for i in range(math.ceil(width / JOIST_STEP_M) + 1): 
                cy = min(i * JOIST_STEP_M, width)
                ax.plot([0, length], [cy, cy], color='blue', lw=1, alpha=0.3)
            for jy in abs_joints:
                ax.plot([0, length], [jy-0.02, jy-0.02], color='c', lw=1.5, alpha=0.9)
                ax.plot([0, length], [jy+0.02, jy+0.02], color='c', lw=1.5, alpha=0.9)
            if frame_choice and "Грунт" in base_type:
                for i in range(pr):
                    cx = i * step_x
                    ax.plot([cx, cx], [0, width], color='red', lw=3)
                    
        ax.text(length/2, -0.3, "Синим: Сетка лаг | Голубым: Парные лаги | Красным: Несущие балки", color='blue', ha='center', fontsize=10)

    elif mode == "piles":
        for i in range(pr):
            for j in range(pc):
                px, py = i * step_x, j * step_y
                ax.add_patch(patches.Circle((px, py), 0.15, color='black'))
                if i < pr - 1 and j == 0: ax.text(px + step_x/2, py-0.4, f"{int(step_x*1000)} мм", ha='center', fontsize=9)
                if j < pc - 1 and i == 0: ax.text(px-0.8, py + step_y/2, f"{int(step_y*1000)} мм", va='center', rotation=90, fontsize=9)

    ax.set_xlim(-1.0, length+1.0); ax.set_ylim(-1.2, width+0.5); ax.set_aspect('equal'); plt.axis('off')
    buf = io.BytesIO(); plt.savefig(buf, format='png', bbox_inches='tight', dpi=150); plt.close(fig); buf.seek(0)
    return buf

# --- 6. ГЕНЕРАЦИЯ PDF ---
def create_pdf():
    pdf = FPDF(); pdf.add_page(); pdf.set_font('Arial', '', 12)
    try: pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True); pdf.set_font('DejaVu', '', 12)
    except: pass
    pdf.cell(200, 10, txt="Смета и чертежи на устройство террасы", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Клиент: {client_name} | Габариты: {int(length*1000)}x{int(width*1000)} мм", ln=True, align='L'); pdf.ln(5)
    
    pdf.set_fill_color(235, 235, 235); pdf.cell(110, 10, "Материалы", 1, 0, 'L', True); pdf.cell(30, 10, "Кол-во", 1, 0, 'C', True); pdf.cell(50, 10, "Сумма", 1, 1, 'C', True)
    for r in mat_data: pdf.cell(110, 10, str(r["Позиция"])[:45], 1); pdf.cell(30, 10, str(r["Кол-во"]), 1, 0, 'C'); pdf.cell(50, 10, f"{r['Сумма']:,.0f} р.", 1, 1, 'R')
        
    pdf.ln(5); pdf.cell(140, 10, "Строительно-монтажные работы", 1, 0, 'L', True); pdf.cell(50, 10, "Сумма", 1, 1, 'C', True)
    for r in work_data: pdf.cell(140, 10, str(r["Позиция"]), 1); pdf.cell(50, 10, f"{r['Сумма']:,.0f} р.", 1, 1, 'R')
    
    pdf.ln(5); pdf.set_font('DejaVu', '', 14); pdf.cell(190, 10, txt=f"ИТОГО: {grand_total:,.0f} руб.", ln=True, align='R')
    for m, t in [("board", f"Настил"), ("frame", "Схема подсистемы"), ("piles", "Свайное поле")]:
        if m == "piles" and piles == 0: continue
        pdf.add_page(); pdf.cell(200, 10, t, ln=True, align='C'); pdf.image(get_plot(m), x=15, y=30, w=180)
    return bytes(pdf.output())

# --- 7. UI ---
st.markdown(f"<h2 style='text-align: center; color: #1b5e20;'>Итоговая стоимость: {grand_total:,.0f} руб.</h2>", unsafe_allow_html=True)
colA, colB = st.columns(2); colA.markdown("#### 🪵 Смета материалов"); colA.table(mat_data)
colB.markdown("#### ⚒️ Смета работ"); colB.table(work_data); st.divider()
col_dl1, col_dl2, col_dl3 = st.columns([1, 2, 1])
with col_dl2: st.download_button("📥 СКАЧАТЬ ПОЛНЫЙ ПРОЕКТ (PDF)", data=create_pdf(), file_name=f"Terrasa_{client_name}.pdf", mime="application/pdf", use_container_width=True)
st.divider(); st.subheader("📐 Технические схемы")
t1, t2, t3 = st.tabs(["Вид настила", "Металлокаркас", "Свайное поле"])
with t1: st.image(get_plot("board"), caption="Швы окантовки математически выровнены со швами прилегающих рядов настила.")
with t2: st.image(get_plot("frame"), caption="Голубые линии — парные лаги под каждый стык.")
with t3: 
    if piles > 0: st.image(get_plot("piles"))
    else: st.info("Основание — бетон")
