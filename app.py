import streamlit as st
import os
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
MIN_CUT_LENGTH = 1.0  # Минимальная допустимая длина обрезанной доски (м)

# --- 2. ПАЛУБНАЯ РАСКЛАДКА «КИРПИЧНАЯ КЛАДКА» ---
# Правила:
#   1. Внутри ряда — ТОЛЬКО целые (нерезанные) доски длиной M
#   2. Обрезанные доски допустимы ТОЛЬКО по краям (первая и/или последняя в ряду)
#   3. Минимальная длина обрезанной доски — MIN_CUT_LENGTH (1 м)
#   4. Два паттерна (A и B) чередуются для создания рисунка «кирпичная кладка»
#
# Примеры:
#   9м, доска 3м  → ряд A = [3, 3, 3],       ряд B = [1.5, 3, 3, 1.5]
#   10м, доска 4м → ряд A = [4, 4, 2],        ряд B = [2, 4, 4]
#   12м, доска 4м → ряд A = [4, 4, 4],        ряд B = [2, 4, 4, 2]
#   8.5м, доска 4м→ ряд A = [2.25, 4, 2.25],  ряд B = [3.25, 4, 1.25]

def get_row_patterns(length, M):
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
        if half >= MIN_CUT_LENGTH and K > 1:
            row_B = [half] + [M] * (K - 1) + [half]
        else:
            # Половина доски слишком коротка — без разбежки
            row_B = list(row_A)
        return row_A, row_B

    # ─── СЛУЧАЙ 2: Остаток ≥ 1м — допустимый крайний кусок ───
    # Пример: 10м / 4м → [4, 4, 2] и [2, 4, 4]
    if R >= MIN_CUT_LENGTH:
        row_A = [M] * K + [R]       # целые доски + остаток справа
        row_B = [R] + [M] * K       # остаток слева + целые доски
        return row_A, row_B

    # ─── СЛУЧАЙ 3: Остаток < 1м — огрызок недопустим ───
    # Убираем одну целую доску и перераспределяем на края симметрично
    # Пример: 8.5м / 4м → R=0.5 (мало!) → K=1, R_total=4.5
    #         → [2.25, 4, 2.25] и [3.25, 4, 1.25]
    K -= 1
    R_total = round(R + M, 3)
    half_R = round(R_total / 2.0, 3)

    if half_R >= MIN_CUT_LENGTH:
        # Основной ряд: симметричные обрезки по краям
        row_A = [half_R] + [M] * K + [half_R]

        # Ряд со смещением: сдвигаем швы для разбежки
        shift = round(min(half_R - MIN_CUT_LENGTH, M / 4.0), 3)
        if shift >= 0.15:
            edge_left = round(half_R + shift, 3)
            edge_right = round(half_R - shift, 3)
            # Проверяем, что левый край не длиннее доски
            if edge_left <= M and edge_right >= MIN_CUT_LENGTH:
                row_B = [edge_left] + [M] * K + [edge_right]
            else:
                row_B = list(row_A)
        else:
            row_B = list(row_A)
    else:
        # Даже половина слишком коротка — убираем ещё одну доску
        K = max(0, K - 1)
        R_total = round(length - K * M, 3)
        half_R = round(R_total / 2.0, 3)
        if half_R >= MIN_CUT_LENGTH and half_R <= M:
            row_A = [half_R] + [M] * K + [half_R]
        else:
            row_A = [round(length, 3)]
        row_B = list(row_A)

    return row_A, row_B


def get_1d_symmetric_pieces(L, M):
    """Нарезка торцевой доски с сохранением ритма"""
    if L <= 0.01: return []
    row_A, _ = get_row_patterns(L, M)
    return row_A


def get_best_symmetric_layout(row_lengths_arr, eff_w, collection_boards):
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
            row_A, row_B = get_row_patterns(L, M)
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

# --- 3. ИНТЕРФЕЙС И ВЫБОР ФОРМЫ ---
st.set_page_config(page_title="Дача 2000 | Умный Калькулятор", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
[data-testid="collapsedControl"] { display: none; }
section[data-testid="stSidebar"] { display: none; }
/* Делаем липкой только самую первую полосу (с логотипом и названием) */
div[data-testid="stVerticalBlock"] > div:first-of-type {
    position: sticky;
    top: 0px;
    z-index: 999;
    background-color: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(8px);
    padding: 0.5rem 1rem 0.5rem 1rem;
    border-bottom: 2px solid #4CAF50;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
    margin-bottom: 0.5rem;
}
@media (prefers-color-scheme: dark) {
    div[data-testid="stVerticalBlock"] > div:first-of-type {
        background-color: rgba(14, 17, 23, 0.95);
        border-bottom: 2px solid #2E7D32;
    }
}
/* Компактные поля ввода */
div[data-baseweb="input"] { font-size: 14px; }
div[data-testid="stNumberInput"] label p, div[data-testid="stSelectbox"] label p, div[data-testid="stRadio"] label p {
    font-size: 14px !important;
    font-weight: 500 !important;
    color: #444;
}
@media (prefers-color-scheme: dark) {
    div[data-testid="stNumberInput"] label p, div[data-testid="stSelectbox"] label p, div[data-testid="stRadio"] label p { color: #ccc; }
}
/* Кастомный стиль для заголовков экспандера */
button[data-testid="stExpanderToggleIcon"] { display: none !important; }
div[data-testid="stExpander"] details summary p {
    font-size: 1.2rem;
    font-weight: 700;
    color: #2E7D32;
}
@media (prefers-color-scheme: dark) {
    div[data-testid="stExpander"] details summary p { color: #4CAF50; }
}
</style>
""", unsafe_allow_html=True)

with st.container():
    # Используем более гармоничные пропорции для логотипа
    col_logo, col_title, col_btn = st.columns([1.5, 7, 1.5], gap="small")
    with col_logo:
        try:
            st.image("logo.png", width=180)
        except:
            st.markdown("<h3 style='color:#2E7D32; margin:0;'>Дача 2000</h3>", unsafe_allow_html=True)
    with col_title:
        st.markdown("<h2 style='margin:0; padding-top:10px; font-weight:800; color: #333;'>Профессиональный проект террасы</h2>", unsafe_allow_html=True)
    with col_btn:
        st.markdown("<div style='padding-top:10px;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Обновить прайс", use_container_width=True):
            st.cache_data.clear(); st.rerun()

with st.expander("🛠️ ПАРАМЕТРЫ РАСЧЕТА ТЕРРАСЫ (Нажмите, чтобы развернуть/свернуть)", expanded=True):
    # ПЕРЕВОДИМ ИЗ 4 в 3 КОЛОНКИ: это уберет дыры и сделает всё плотнее
    c1, c2, c3 = st.columns(3, gap="medium")
    
    with c1:
        st.markdown("#### 📐 1. Габариты и Бассейн")
        client_name = st.text_input("ФИО Клиента:", "Иван Иванович")
        shape_type = st.selectbox("Конфигурация:", ["⬜ Прямоугольная (Стандарт)", "📐 Г-образная (Угловая)", "🔲 П-образная (С вырезом)", "⏺️ Округлая (Овал / Круг)", "✏️ Свой контур (По координатам)"])
        
        st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.3;'>", unsafe_allow_html=True)
        
        if shape_type == "⬜ Прямоугольная (Стандарт)":
            c_l, c_w = st.columns(2)
            length = c_l.number_input("Длина (X), м:", 1.0, 50.0, 9.0)
            width = c_w.number_input("Глубина (Y), м:", 1.0, 50.0, 4.0)
        elif shape_type == "📐 Г-образная (Угловая)":
            c_l, c_w = st.columns(2)
            length = c_l.number_input("Длина X, м:", 1.0, 50.0, 6.0)
            width = c_w.number_input("Глубина Y, м:", 1.0, 50.0, 5.0)
            cut_x = c_l.number_input("Вырез X, м:", 0.1, float(length-0.1), 3.0)
            cut_y = c_w.number_input("Вырез Y, м:", 0.1, float(width-0.1), 2.0)
        elif shape_type == "🔲 П-образная (С вырезом)":
            length = st.number_input("Общая длина X, м:", 1.0, 50.0, 8.0)
            width = st.number_input("Общая глубина Y, м:", 1.0, 50.0, 5.0)
            c_l, c_w = st.columns(2)
            cut_w = c_l.number_input("Вырез X, м:", 0.1, float(length-0.2), 3.0)
            cut_d = c_w.number_input("Вырез Y, м:", 0.1, float(width-0.1), 2.0)
        elif shape_type == "⏺️ Округлая (Овал / Круг)":
            length = st.number_input("Длина (Диам X), м:", 1.0, 50.0, 6.0)
            width = st.number_input("Глубина (Диам Y), м:", 1.0, 50.0, 4.0)
        elif shape_type == "✏️ Свой контур (По координатам)":
            df_coords = pd.DataFrame([{"X (м)": 0.0, "Y (м)": 0.0}, {"X (м)": 0.0, "Y (м)": 4.0}, {"X (м)": 6.0, "Y (м)": 4.0}, {"X (м)": 6.0, "Y (м)": 0.0}])
            edited_df = st.data_editor(df_coords, num_rows="dynamic", use_container_width=True)
            length = 5.0; width = 5.0

        st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.3;'>", unsafe_allow_html=True)
        has_pool = st.checkbox("🏊 Встроенный бассейн", value=False)
        if has_pool:
            pool_shape = st.radio("Форма бассейна:", ["⬜ Прямоугольный", "⏺️ Круглый", "⬭ Овальный"], horizontal=True)
            c_pl, c_pw = st.columns(2)
            if pool_shape in ["⬜ Прямоугольный", "⬭ Овальный"]:
                pool_l = c_pl.number_input("Длина X, м:", 0.5, 20.0, 4.0)
                pool_w = c_pw.number_input("Ширина Y, м:", 0.5, 20.0, 2.5)
            else:
                pool_d = st.number_input("Диаметр бассейна, м:", 0.5, 20.0, 3.0)
            
            c_ox, c_oy = st.columns(2)
            pool_offset_x = c_ox.number_input("Смещение X, м:", 0.0, 50.0, 1.0)
            pool_offset_y = c_oy.number_input("Смещение Y, м:", 0.0, 50.0, 1.0)

    with c2:
        st.markdown("#### 🪵 2. Обшивка и Периметр")
        brand_choice = st.selectbox("Бренд:", list(PARSED_BOARDS.keys()))
        if PARSED_BOARDS[brand_choice]:
            collection_name = st.selectbox("Коллекция:", list(PARSED_BOARDS[brand_choice].keys()))
            collection_boards = PARSED_BOARDS[brand_choice][collection_name]
            eff_w = (collection_boards[0]["width_mm"] + GAP_MM) / 1000
        else:
            st.stop()
        direction_choice = st.radio("Направление укладки:", ["Вдоль фасада (по длине X)", "Поперек фасада (по глубине Y)"])
        
        st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.3;'>", unsafe_allow_html=True)
        
        use_frame = st.checkbox("🔳 Окантовка (Picture Frame)", value=True)
        if use_frame:
            c_f1, c_f2 = st.columns(2)
            edge_front = c_f1.checkbox("Спереди", value=True)
            edge_left = c_f1.checkbox("Слева", value=True)
            edge_back = c_f2.checkbox("Сзади", value=False)
            edge_right = c_f2.checkbox("Справа", value=True)
        else:
            edge_front = edge_back = edge_left = edge_right = False

    with c3:
        st.markdown("#### ⛓️ 3. Фундамент и Каркас")
        base_type = st.radio("Основание:", ["Грунт (Сваи)", "Бетон"], horizontal=True)
        
        st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.3;'>", unsafe_allow_html=True)
        steps_m = st.number_input("Ступени (м.п.):", 0.0, 50.0, 0.0)
        
        st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.3;'>", unsafe_allow_html=True)
        joist_choice = st.selectbox("Лаги (много):", list(PIPES_JOIST.keys()))
        frame_choice = st.selectbox("Каркас несущий:", list(PIPES_FRAME.keys())) if "Грунт" in base_type else None


# --- БЛОКИРОВКА СЛОЖНЫХ РАСЧЕТОВ ---
is_complex = (shape_type not in ["⬜ Прямоугольная (Стандарт)", "📐 Г-образная (Угловая)"]) or has_pool

if is_complex:
    st.warning("Интерфейс для сложных форм и бассейнов активирован.")
    st.info("💡 Модуль вырезов в разработке.\n\nПожалуйста, переключитесь на «Прямоугольную (Стандарт)» и уберите галочку бассейна, чтобы увидеть расчёты.")
    st.stop()

# --- 4. РАСЧЕТЫ ДЛЯ ПРЯМОУГОЛЬНОЙ И УГЛОВОЙ ТЕРРАСЫ ---
if shape_type == "📐 Г-образная (Угловая)":
    area = length * width - cut_x * cut_y
else:
    area = length * width

offset_front = eff_w if edge_front else 0
offset_back = eff_w if edge_back else 0
offset_left = eff_w if edge_left else 0
offset_right = eff_w if edge_right else 0

inner_X = round(length - offset_left - offset_right, 3)
inner_Y = round(width - offset_front - offset_back, 3)

if inner_X <= 0 or inner_Y <= 0:
    st.error("Размеры террасы слишком малы для установки торцевой доски.")
    st.stop()

row_lengths_arr = []
if "Вдоль" in direction_choice:
    board_len_axis = inner_X
    board_row_axis = inner_Y
    rows_count = math.ceil(board_row_axis / eff_w)
    for r in range(rows_count):
        current_y = r * eff_w
        if shape_type == "📐 Г-образная (Угловая)" and current_y >= inner_Y - cut_y:
            row_lengths_arr.append(max(0.0, inner_X - cut_x))
        else:
            row_lengths_arr.append(inner_X)
else:
    board_len_axis = inner_Y
    board_row_axis = inner_X
    rows_count = math.ceil(board_row_axis / eff_w)
    for r in range(rows_count):
        current_x = r * eff_w
        if shape_type == "📐 Г-образная (Угловая)" and current_x >= inner_X - cut_x:
            row_lengths_arr.append(max(0.0, inner_Y - cut_y))
        else:
            row_lengths_arr.append(inner_Y)

# Раскладка основной доски
layout_matrix, best_joints, main_board = get_best_symmetric_layout(row_lengths_arr, eff_w, collection_boards)

# Нарезка торцевой доски
M = main_board['length_m']

edge_pieces = []
if use_frame:
    if "Вдоль" in direction_choice:
        front_pieces = get_shifted_edge(layout_matrix, True, offset_left, offset_right) if edge_front else []
        back_pieces = get_shifted_edge(layout_matrix, False, offset_left, offset_right) if edge_back else []
        left_pieces = get_1d_symmetric_pieces(width, M) if edge_left else []
        right_pieces = get_1d_symmetric_pieces(width, M) if edge_right else []
    else:
        left_pieces = get_shifted_edge(layout_matrix, True, offset_front, offset_back) if edge_left else []
        right_pieces = get_shifted_edge(layout_matrix, False, offset_front, offset_back) if edge_right else []
        front_pieces = get_1d_symmetric_pieces(length, M) if edge_front else []
        back_pieces = get_1d_symmetric_pieces(length, M) if edge_back else []

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
pcut = math.ceil(cut_x/PILE_STEP_M) * math.ceil(cut_y/PILE_STEP_M) if shape_type == "📐 Г-образная (Угловая)" else 0
piles = pr * pc - pcut if "Грунт" in base_type else 0
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
        flags = {'F': edge_front, 'B': edge_back, 'L': edge_left, 'R': edge_right}
        if edge_front: draw_edge(ax, front_pieces, 'front', length, width, draw_w, flags)
        if edge_back: draw_edge(ax, back_pieces, 'back', length, width, draw_w, flags)
        if edge_left: draw_edge(ax, left_pieces, 'left', length, width, draw_w, flags)
        if edge_right: draw_edge(ax, right_pieces, 'right', length, width, draw_w, flags)

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
                cx = min(i * JOIST_STEP_M, length); ax.plot([cx, cx], [0, width], color='blue', lw=1, alpha=0.3)
            for jx in abs_joints:
                ax.plot([jx-0.02, jx-0.02], [0, width], color='c', lw=1.5, alpha=0.9)
                ax.plot([jx+0.02, jx+0.02], [0, width], color='c', lw=1.5, alpha=0.9)
            if frame_choice and "Грунт" in base_type:
                for j in range(pc):
                    cy = j * step_y; ax.plot([0, length], [cy, cy], color='red', lw=3)
        else:
            for jy in best_joints: abs_joints.add(offset_front + jy)
            for i in range(math.ceil(width / JOIST_STEP_M) + 1): 
                cy = min(i * JOIST_STEP_M, width); ax.plot([0, length], [cy, cy], color='blue', lw=1, alpha=0.3)
            for jy in abs_joints:
                ax.plot([0, length], [jy-0.02, jy-0.02], color='c', lw=1.5, alpha=0.9)
                ax.plot([0, length], [jy+0.02, jy+0.02], color='c', lw=1.5, alpha=0.9)
            if frame_choice and "Грунт" in base_type:
                for i in range(pr):
                    cx = i * step_x; ax.plot([cx, cx], [0, width], color='red', lw=3)
                    
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
st.divider(); st.subheader("📐 Технические схемы (Размеры в мм)")
t1, t2, t3 = st.tabs(["Вид настила", "Металлокаркас", "Свайное поле"])
with t1: st.image(get_plot("board"), caption="Ритм 'кирпичная кладка'. Без внутренних обрезков. Швы разведены.")
with t2: st.image(get_plot("frame"), caption="Голубые линии — парные лаги под каждый стык.")
with t3: 
    if piles > 0: st.image(get_plot("piles"))
    else: st.info("Основание — бетон, сваи не требуются.")
