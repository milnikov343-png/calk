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
from streamlit_drawable_canvas import st_canvas
import json

try:
    import google.generativeai as genai
    from PIL import Image
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False
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
    MIN_STAGGER = 1.0  # Минимальная разбежка швов (визуальная красота)
    
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

    # ─── СЛУЧАЙ 2: Асимметричная разбежка (например, 4-4-2 и 2-4-4) ───
    # Применяем только если остаток допустим И визуальная разбежка швов (M - R) достаточно большая
    if R >= MIN_CUT_LENGTH and abs(M - R) >= MIN_STAGGER:
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

# --- 3. ИНТЕРФЕЙС И ВЫБОР ФОРМЫ ---
st.set_page_config(page_title="Дача 2000 | Умный Калькулятор", layout="wide", initial_sidebar_state="collapsed")

# --- Тема оформления ---
is_light = st.session_state.get('theme', 'dark') == 'light'

bg_app = "linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)" if is_light else "linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 40%, #16213e 100%)"
text_color = "#1e293b !important" if is_light else "#f8f9fa !important"
header_bg = "linear-gradient(135deg, rgba(255, 255, 255, 0.95), rgba(241, 245, 249, 0.95))" if is_light else "linear-gradient(135deg, rgba(30, 60, 90, 0.95), rgba(20, 40, 70, 0.95))"
header_text = "#0f172a" if is_light else "#e0e0e0"
card_bg = "linear-gradient(135deg, rgba(255, 255, 255, 0.9), rgba(241, 245, 249, 0.95))" if is_light else "linear-gradient(135deg, rgba(30, 50, 80, 0.8), rgba(20, 35, 60, 0.9))"
card_border = "rgba(16, 185, 129, 0.3)" if is_light else "rgba(0, 184, 148, 0.3)"
card_shadow = "0 4px 10px rgba(0,0,0,0.05)" if is_light else "0 4px 20px rgba(0, 0, 0, 0.3)"
card_hover_shadow = "0 8px 20px rgba(16, 185, 129, 0.15)" if is_light else "0 8px 30px rgba(0, 184, 148, 0.2)"
panel_bg = "rgba(255, 255, 255, 0.7)" if is_light else "rgba(25, 40, 65, 0.6)"
panel_border = "rgba(0, 0, 0, 0.1)" if is_light else "rgba(255, 255, 255, 0.08)"
label_color = "#64748b" if is_light else "#8899aa"
metric_val = "linear-gradient(135deg, #059669, #10b981)" if is_light else "linear-gradient(135deg, #00b894, #00cec9)"
input_label = "#475569 !important" if is_light else "#b0bec5 !important"
tab_text = "#64748b !important" if is_light else "#8899aa !important"
tab_active = "#059669 !important" if is_light else "#00b894 !important"
expander_text = "#059669" if is_light else "#00b894"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

/* Скрываем сайдбар */
[data-testid="collapsedControl"] {{ display: none; }}
section[data-testid="stSidebar"] {{ display: none; }}

/* Основной фон */
.stApp {{
    background: {bg_app};
}}

/* Шрифт и читаемость текста */
html, body, [class*="css"], p, span, div, h1, h2, h3, h4, h5, h6, label, li {{
    font-family: 'Inter', sans-serif;
    color: {text_color};
}}

/* Исправление цвета текста в выпадающих списках (selectbox) */
div[data-baseweb="select"] * {{ color: #000000 !important; }}
div[data-baseweb="popover"] * {{ color: #000000 !important; }}
li[role="option"] * {{ color: #000000 !important; }}

/* Заголовок-шапка */
.header-bar {{
    background: {header_bg};
    backdrop-filter: blur(12px);
    border-bottom: 2px solid #00b894;
    padding: 0.7rem 1.5rem;
    border-radius: 0 0 16px 16px;
    box-shadow: 0 4px 20px rgba(0, 184, 148, 0.15);
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 1rem;
}}
.header-bar h2 {{
    color: {header_text};
    margin: 0;
    font-weight: 800;
    font-size: 1.4rem;
}}
.header-bar span {{
    color: #00b894;
    font-weight: 300;
    font-size: 1rem;
}}

/* Карточки метрик */
.metric-card {{
    background: {card_bg};
    border: 1px solid {card_border};
    border-radius: 16px;
    padding: 1.2rem 1.5rem;
    text-align: center;
    box-shadow: {card_shadow};
    transition: all 0.3s ease;
}}
.metric-card:hover {{
    transform: translateY(-3px);
    border-color: rgba(0, 184, 148, 0.6);
    box-shadow: {card_hover_shadow};
}}
.metric-card .label {{
    color: {label_color};
    font-size: 0.85rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 0.4rem;
}}
.metric-card .value {{
    font-size: 1.8rem;
    font-weight: 800;
    background: {metric_val};
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}}
.metric-card .value.orange {{
    background: linear-gradient(135deg, #f59e0b, #ea580c);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}}
.metric-card .value.blue {{
    background: linear-gradient(135deg, #3b82f6, #2563eb);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}}
.metric-card .value.total {{
    font-size: 2.2rem;
    background: linear-gradient(135deg, #f59e0b, #ea580c, #dc2626);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}}

/* Секция-панель */
.panel {{
    background: {panel_bg};
    border: 1px solid {panel_border};
    border-radius: 16px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
    backdrop-filter: blur(8px);
}}
.panel h4 {{
    color: #00b894;
    margin-top: 0;
    margin-bottom: 0.8rem;
    font-weight: 700;
}}

/* Таблица */
.stDataFrame, table {{
    border-radius: 12px !important;
    overflow: hidden;
}}

/* Вкладки */
div[data-testid="stTabs"] button {{
    color: {tab_text};
    font-weight: 600 !important;
}}
div[data-testid="stTabs"] button[aria-selected="true"] {{
    color: {tab_active};
    border-bottom-color: {tab_active};
}}

/* Фикс стилей инпутов */
div[data-testid="stNumberInput"] label p,
div[data-testid="stSelectbox"] label p,
div[data-testid="stRadio"] label p,
div[data-testid="stCheckbox"] label p,
div[data-testid="stTextInput"] label p {{
    font-size: 13px !important;
    font-weight: 500 !important;
    color: {input_label};
}}

/* Экспандеры */
div[data-testid="stExpander"] {
    background: {panel_bg};
    border-radius: 12px;
    border: 1px solid {panel_border};
}
div[data-testid="stExpander"] details summary {
    background: transparent !important;
}
div[data-testid="stExpander"] details summary p,
div[data-testid="stExpander"] details summary span {
    font-size: 1.1rem !important;
    font-weight: 700 !important;
    color: {expander_text} !important;
}
div[data-testid="stExpander"] details summary svg {
    fill: {expander_text} !important;
}
</style>
""", unsafe_allow_html=True)

with st.container():
    col_logo, col_title, col_btn = st.columns([1.5, 7, 1.5], gap="small")
    with col_logo:
        try:
            st.image("logo.png", width=160)
        except:
            st.markdown("<h3 style='color:#00b894; margin:0;'>Дача 2000</h3>", unsafe_allow_html=True)
    with col_title:
        st.markdown(f"""
        <div>
            <h2 style='margin:0; padding-top:8px; font-weight:800; color: {header_text};'>
                :material/construction: Умный Калькулятор Террас
            </h2>
            <span style='color: #00b894; font-size: 0.9rem;'>ООО "Дача 2000" — Профессиональный расчёт стоимости</span>
        </div>
        """, unsafe_allow_html=True)
    with col_btn:
        st.markdown("<div style='padding-top:10px;'></div>", unsafe_allow_html=True)
        if st.button(":material/refresh: Обновить прайс", use_container_width=True):
            st.cache_data.clear(); st.rerun()

with st.expander(":material/build: ПАРАМЕТРЫ РАСЧЕТА ТЕРРАСЫ (Нажмите, чтобы развернуть/свернуть)", expanded=True):
    # ПЕРЕВОДИМ ИЗ 4 в 3 КОЛОНКИ: это уберет дыры и сделает всё плотнее
    c1, c2, c3 = st.columns(3, gap="medium")
    
    with c1:
        st.markdown("#### :material/straighten: 1. Габариты и Бассейн")
        client_name = st.text_input("ФИО Клиента:", "Иван Иванович")
        
        st.markdown("**Менеджер проекта**")
        manager_name = st.text_input("Имя менеджера:", "Иван Иванов")
        manager_phone = st.text_input("Телефон менеджера:", "+7 (999) 000-00-00")
        st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.3;'>", unsafe_allow_html=True)
        shape_type = st.selectbox("Конфигурация:", [":material/rectangle: Прямоугольная (Стандарт)", ":material/architecture: Г-образная (Угловая)", ":material/crop_din: П-образная (С вырезом)", ":material/circle: Округлая (Овал / Круг)", ":material/draw: Свой контур (По координатам)"])
        
        st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.3;'>", unsafe_allow_html=True)
        
        if shape_type == ":material/rectangle: Прямоугольная (Стандарт)":
            c_l, c_w = st.columns(2)
            length = c_l.number_input("Длина (X), м:", 1.0, 50.0, 9.0)
            width = c_w.number_input("Глубина (Y), м:", 1.0, 50.0, 4.0)
        elif shape_type == ":material/circle: Округлая (Овал / Круг)":
            length = st.number_input("Длина (Диам X), м:", 1.0, 50.0, 6.0)
            width = st.number_input("Глубина (Диам Y), м:", 1.0, 50.0, 4.0)
        else:
            # Нестандартные формы — переменные-заглушки для совместимости
            length = 1.0; width = 1.0

        st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.3;'>", unsafe_allow_html=True)
        has_pool = st.checkbox(":material/pool: Встроенный бассейн", value=False)
        if has_pool:
            pool_shape = st.radio("Форма бассейна:", [":material/rectangle: Прямоугольный", ":material/circle: Круглый", "⬭ Овальный"], horizontal=True)
            c_pl, c_pw = st.columns(2)
            if pool_shape in [":material/rectangle: Прямоугольный", "⬭ Овальный"]:
                pool_l = c_pl.number_input("Длина X, м:", 0.5, 20.0, 4.0)
                pool_w = c_pw.number_input("Ширина Y, м:", 0.5, 20.0, 2.5)
            else:
                pool_d = st.number_input("Диаметр бассейна, м:", 0.5, 20.0, 3.0)
            
            c_ox, c_oy = st.columns(2)
            pool_offset_x = c_ox.number_input("Смещение X, м:", 0.0, 50.0, 1.0)
            pool_offset_y = c_oy.number_input("Смещение Y, м:", 0.0, 50.0, 1.0)

    with c2:
        st.markdown("#### :material/forest: 2. Обшивка и Периметр")
        brand_choice = st.selectbox("Бренд:", list(PARSED_BOARDS.keys()))
        if PARSED_BOARDS[brand_choice]:
            collection_name = st.selectbox("Коллекция:", list(PARSED_BOARDS[brand_choice].keys()))
            collection_boards = PARSED_BOARDS[brand_choice][collection_name]
            eff_w = (collection_boards[0]["width_mm"] + GAP_MM) / 1000
        else:
            st.stop()
        direction_choice = st.radio("Направление укладки:", ["Вдоль фасада (по длине X)", "Поперек фасада (по глубине Y)"])
        
        st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.3;'>", unsafe_allow_html=True)
        
        use_frame = st.checkbox(":material/crop_din: Окантовка (Picture Frame)", value=True)
        if use_frame:
            c_f1, c_f2 = st.columns(2)
            edge_front = c_f1.checkbox("Спереди", value=True)
            edge_left = c_f1.checkbox("Слева", value=True)
            edge_back = c_f2.checkbox("Сзади", value=False)
            edge_right = c_f2.checkbox("Справа", value=True)
        else:
            edge_front = edge_back = edge_left = edge_right = False

    with c3:
        st.markdown("#### :material/foundation: 3. Фундамент и Каркас")
        base_type = st.radio("Основание:", ["Грунт (Сваи)", "Бетон"], horizontal=True)
        
        st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.3;'>", unsafe_allow_html=True)
        use_adjustable_supports = st.checkbox("На регулируемых опорах (HILST LIFT)", value=False)
        if use_adjustable_supports:
            joist_support_type = st.selectbox("Тип лаги для опор:", ["Лага ДПК", "Алюминиевая лага"])
        else:
            joist_support_type = None
            
        st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.3;'>", unsafe_allow_html=True)
        steps_m = st.number_input("Ступени (м.п.):", 0.0, 50.0, 0.0)
        
        st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.3;'>", unsafe_allow_html=True)
        joist_choice = st.selectbox("Лаги (металлокаркас):", list(PIPES_JOIST.keys()))
        frame_choice = st.selectbox("Каркас несущий:", list(PIPES_FRAME.keys())) if "Грунт" in base_type else None


# --- НЕСТАНДАРТНЫЕ ФОРМЫ: ИНТЕРАКТИВНЫЙ КОНСТРУКТОР ---
is_complex = shape_type in [":material/architecture: Г-образная (Угловая)", ":material/crop_din: П-образная (С вырезом)", ":material/draw: Свой контур (По координатам)"]

if is_complex:
    st.markdown("---")
    st.subheader(":material/architecture: Конструктор нестандартной террасы")

    # --- Панель управления холстом ---
    ctrl1, ctrl2 = st.columns([3, 1])
    with ctrl2:
        scale_label = st.selectbox("Масштаб:", ["Мелкий (до 7м)", "Средний (до 14м)", "Крупный (до 28м)"], index=1)
        mm_per_cell = {"Мелкий (до 7м)": 200, "Средний (до 14м)": 500, "Крупный (до 28м)": 1000}[scale_label]
        draw_label = st.radio("Режим:", [":material/edit: Рисовать", ":material/swap_horiz: Двигать"], horizontal=True)
        drawing_mode = "polygon" if "Рисовать" in draw_label else "transform"

    canvas_w, canvas_h = 700, 450
    grid_px = 25
    mm_per_px = mm_per_cell / grid_px

    with ctrl1:
        if "Рисовать" in draw_label:
            st.info(":material/mouse: **Кликайте** по сетке, чтобы расставить вершины террасы. **Двойной клик** — замкнуть контур.")
        else:
            st.info(":material/mouse: **Перетаскивайте** фигуру для настройки. Переключите на :material/edit: для рисования новой.")
        st.caption(f":material/straighten: 1 клетка = {mm_per_cell} мм ({mm_per_cell/1000:.1f} м) | Область: {canvas_w * mm_per_px / 1000:.0f} × {canvas_h * mm_per_px / 1000:.0f} м")

    # --- Фон холста ---

    # --- Предустановленные шаблоны для Г и П ---
    s = 1.0 / mm_per_px  # mm → px
    ox, oy = 2 * grid_px, 2 * grid_px

    if "ai_drawing" not in st.session_state:
        st.session_state.ai_drawing = None

    # Блок работы с ИИ
    st.markdown("### :material/smart_toy: Автоматическое распознавание чертежа (ИИ)")
    with st.container():
        c_ai1, c_ai2 = st.columns([1, 1])
        with c_ai1:
            uploaded_img = st.file_uploader("Загрузите фото или скан чертежа с размерами (jpg, png)", type=["jpg", "jpeg", "png"])
        with c_ai2:
            api_key = st.text_input("Gemini API Key (Токен доступа)", type="password", help="Получите ключ бесплатно на aistudio.google.com")
            if st.button(":material/auto_awesome: Перевести чертеж в проект", use_container_width=True, type="primary"):
                if not HAS_GENAI:
                    st.error("Библиотека google-generativeai не установлена. Введите в терминале: pip install google-generativeai pillow")
                elif not api_key:
                    st.warning(":material/warning: Введите API ключ Gemini")
                elif not uploaded_img:
                    st.warning(":material/warning: Загрузите изображение чертежа")
                else:
                    with st.spinner("Анализирую чертеж и размеры... это займет 5-10 секунд"):
                        try:
                            genai.configure(api_key=api_key)
                            model = genai.GenerativeModel("gemini-1.5-flash")
                            img = Image.open(uploaded_img)
                            
                            prompt = '''
                            Вы - опытный инженер-проектировщик. Пользователь загрузил чертеж террасы.
                            Определите форму террасы и найдите все длины сторон (размеры).
                            Переведите все размеры в миллиметры (например, если написано 4м, то это 4000).
                            Постройте 2D полигон этой террасы. Первый угол всегда должен быть в координатах [0, 0].
                            Следующие точки высчитайте по длинам сторон. Идите строго по часовой стрелке.
                            Верните ТОЛЬКО валидный JSON массив координат вершин.
                            Например: [[0, 0], [4000, 0], [4000, 3000], [0, 3000]]
                            Не добавляйте текст markdown! Только JSON-массив из списков.
                            '''
                            response = model.generate_content([prompt, img])
                            raw_resp = response.text.strip().removeprefix('```json').removesuffix('```').strip()
                            
                            ai_pts = json.loads(raw_resp)
                            
                            if len(ai_pts) >= 3:
                                # Конвертируем [Xmm, Ymm] в [Xpx, Ypx]
                                # Но у Canvas Y-ось идет вниз, поэтому:
                                path_ai = [["M", ox + ai_pts[0][0] * s, oy + ai_pts[0][1] * s]]
                                for p in ai_pts[1:]:
                                    path_ai.append(["L", ox + p[0] * s, oy + p[1] * s])
                                path_ai.append(["z"])
                                
                                st.session_state.ai_drawing = {
                                    "version": "4.4.0", "objects": [{
                                        "type": "path", "version": "4.4.0",
                                        "left": 0, "top": 0, "fill": "rgba(41, 182, 246, 0.4)",
                                        "stroke": "#0288d1", "strokeWidth": 2, "path": path_ai
                                    }]
                                }
                                st.success(":material/check_circle: Чертеж успешно распознан и перенесен на сетку!")
                            else:
                                st.error("Не удалось составить полигон из чертежа.")
                        except Exception as e:
                            st.error(f"Ошибка ИИ: {e}")

    initial_drawing = st.session_state.ai_drawing

    if initial_drawing is None:
        if shape_type == ":material/architecture: Г-образная (Угловая)":
            pts = [(ox, oy), (ox + 6000 * s, oy), (ox + 6000 * s, oy + 3000 * s),
                   (ox + 3000 * s, oy + 3000 * s), (ox + 3000 * s, oy + 5000 * s), (ox, oy + 5000 * s)]
            path = [["M", pts[0][0], pts[0][1]]]
            for p in pts[1:]:
                path.append(["L", p[0], p[1]])
            path.append(["z"])
            initial_drawing = {"version": "4.4.0", "objects": [{"type": "path", "version": "4.4.0",
                "left": 0, "top": 0, "fill": "rgba(165,214,167,0.3)", "stroke": "#2e7d32",
                "strokeWidth": 2, "path": path}]}


    elif shape_type == ":material/crop_din: П-образная (С вырезом)":
        A, B, E, F = 8000, 5000, 4000, 3000
        pts = [(ox, oy), (ox + A * s, oy), (ox + A * s, oy + B * s),
               (ox + (A + E) / 2 * s, oy + B * s), (ox + (A + E) / 2 * s, oy + (B - F) * s),
               (ox + (A - E) / 2 * s, oy + (B - F) * s), (ox + (A - E) / 2 * s, oy + B * s),
               (ox, oy + B * s)]
        path = [["M", pts[0][0], pts[0][1]]]
        for p in pts[1:]:
            path.append(["L", p[0], p[1]])
        path.append(["z"])
        initial_drawing = {"version": "4.4.0", "objects": [{"type": "path", "version": "4.4.0",
            "left": 0, "top": 0, "fill": "rgba(165,214,167,0.3)", "stroke": "#2e7d32",
            "strokeWidth": 2, "path": path}]}

    # --- Холст для рисования ---
    canvas_result = st_canvas(
        fill_color="rgba(165, 214, 167, 0.3)",
        stroke_width=2,
        stroke_color="#2e7d32",
        background_color="#f8f8f8",
        drawing_mode=drawing_mode,
        point_display_radius=6,
        width=canvas_w,
        height=canvas_h,
        initial_drawing=initial_drawing,
        key=f"canvas_{shape_type}_{mm_per_cell}",
    )

    # --- Извлечение вершин из нарисованного полигона ---
    vertices_mm = []
    if canvas_result.json_data is not None:
        objects = canvas_result.json_data.get("objects", [])
        for obj in objects:
            if "path" in obj:
                left = obj.get("left", 0)
                top = obj.get("top", 0)
                scaleX = obj.get("scaleX", 1)
                scaleY = obj.get("scaleY", 1)
                verts = []
                for cmd in obj["path"]:
                    if len(cmd) >= 3 and cmd[0] in ["M", "L"]:
                        raw_x = cmd[1] * scaleX + left
                        raw_y = cmd[2] * scaleY + top
                        gx = round(raw_x / grid_px) * grid_px
                        gy = round(raw_y / grid_px) * grid_px
                        mm_x = int(round(gx * mm_per_px))
                        mm_y = int(round(gy * mm_per_px))
                        if not verts or (mm_x, mm_y) != verts[-1]:
                            verts.append((mm_x, mm_y))
                if len(verts) > 1 and verts[0] == verts[-1]:
                    verts.pop()
                if len(verts) >= 3:
                    vertices_mm = verts

    if len(vertices_mm) >= 3:
        n = len(vertices_mm)

        # Длины сторон
        sides_mm = []
        for i in range(n):
            p1, p2 = vertices_mm[i], vertices_mm[(i + 1) % n]
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            sides_mm.append(int(round((dx ** 2 + dy ** 2) ** 0.5)))

        # Габариты
        xs = [v[0] for v in vertices_mm]
        ys = [v[1] for v in vertices_mm]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        range_x = max(max_x - min_x, 1)
        range_y = max(max_y - min_y, 1)

        # Площадь (формула Шнурка)
        area_mm2 = 0
        for i in range(n):
            j = (i + 1) % n
            area_mm2 += vertices_mm[i][0] * vertices_mm[j][1]
            area_mm2 -= vertices_mm[j][0] * vertices_mm[i][1]
        area_m2 = abs(area_mm2) / 2_000_000

        # --- SVG чертёж с размерами ---
        svg_w, svg_h = 650, 400
        pad = 65
        sc_svg = min((svg_w - 2 * pad) / range_x, (svg_h - 2 * pad) / range_y)
        svg_pts = [(pad + (vx - min_x) * sc_svg, pad + (vy - min_y) * sc_svg) for vx, vy in vertices_mm]
        poly_str = " ".join([f"{p[0]:.1f},{p[1]:.1f}" for p in svg_pts])

        labels = ""
        for i in range(n):
            p1, p2 = svg_pts[i], svg_pts[(i + 1) % n]
            mx_l, my_l = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
            nx_d, ny_d = -(p2[1] - p1[1]), p2[0] - p1[0]
            nd = max((nx_d ** 2 + ny_d ** 2) ** 0.5, 0.001)
            off = 18
            labels += f'<text x="{mx_l + nx_d / nd * off:.1f}" y="{my_l + ny_d / nd * off:.1f}" '
            labels += f'text-anchor="middle" font-size="12" fill="#1b5e20" font-weight="bold">{sides_mm[i]} мм</text>'
            labels += f'<circle cx="{p1[0]:.1f}" cy="{p1[1]:.1f}" r="5" fill="#2e7d32" stroke="white" stroke-width="1.5"/>'
            labels += f'<text x="{p1[0]:.1f}" y="{p1[1] - 10:.1f}" text-anchor="middle" font-size="10" fill="#444" font-weight="bold">{i + 1}</text>'

        svg_code = f'''<svg width="{svg_w}" height="{svg_h}" xmlns="http://www.w3.org/2000/svg">
            <defs><pattern id="g2" width="20" height="20" patternUnits="userSpaceOnUse">
                <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#eee" stroke-width="0.5"/></pattern></defs>
            <rect width="100%" height="100%" fill="url(#g2)" rx="8"/>
            <polygon points="{poly_str}" fill="#a5d6a7" fill-opacity="0.35" stroke="#2e7d32" stroke-width="2.5" stroke-linejoin="round"/>
            {labels}
            <text x="{svg_w / 2}" y="{svg_h - 12}" text-anchor="middle" font-size="13" fill="#555">
                Площадь: {area_m2:.2f} м² | Габариты: {range_x} × {range_y} мм | Вершин: {n}
            </text>
        </svg>'''

        st.markdown("### :material/straighten: Чертёж с размерами")
        st.markdown(svg_code, unsafe_allow_html=True)

        with st.expander(":material/list_alt: Таблица сторон", expanded=False):
            side_data = [{"Сторона": f"{i + 1} → {(i + 1) % n + 1}", "Длина (мм)": sides_mm[i],
                          "Вершина": f"({vertices_mm[i][0]}, {vertices_mm[i][1]})"} for i in range(n)]
            st.dataframe(pd.DataFrame(side_data), use_container_width=True, hide_index=True)

        length = range_x / 1000.0
        width = range_y / 1000.0
    else:
        st.markdown("<div style='text-align:center; padding: 1rem; color: #888; font-size: 1.1rem;'>" +
                    ":material/touch_app: Нарисуйте контур террасы на холсте выше</div>", unsafe_allow_html=True)
        length = 1.0
        width = 1.0

    # --- ПОЛНЫЙ РАСЧЁТ НЕСТАНДАРТНОЙ ТЕРРАСЫ ---
    if len(vertices_mm) < 3:
        st.info(":material/touch_app: Нарисуйте контур на холсте, затем нажмите кнопку.")
        st.stop()

    # Координаты в метрах
    verts_m = [(v[0] / 1000.0, v[1] / 1000.0) for v in vertices_mm]
    n_v = len(verts_m)
    xs_m = [v[0] for v in verts_m]
    ys_m = [v[1] for v in verts_m]
    min_xm, max_xm = min(xs_m), max(xs_m)
    min_ym, max_ym = min(ys_m), max(ys_m)
    poly_w = max_xm - min_xm
    poly_h = max_ym - min_ym

    # Площадь (Шнурок)
    a_mm2 = 0
    for i in range(n_v):
        j = (i + 1) % n_v
        a_mm2 += verts_m[i][0] * verts_m[j][1]
        a_mm2 -= verts_m[j][0] * verts_m[i][1]
    poly_area = abs(a_mm2) / 2.0

    # Scanline: разбиваем полигон на ряды досок
    row_segments = []  # (y_pos, x_start, x_end, seg_len)
    y_cur = min_ym
    while y_cur < max_ym - eff_w * 0.1:
        segs = polygon_row_segments(verts_m, y_cur + eff_w / 2)
        for sx, ex in segs:
            sl = round(ex - sx, 3)
            if sl > 0.05:
                row_segments.append((y_cur, sx, ex, sl))
        y_cur = round(y_cur + eff_w, 4)

    if not row_segments:
        st.error("Не удалось разбить контур на ряды. Проверьте форму.")
        st.stop()

    row_lengths_arr = [rs[3] for rs in row_segments]

    # Раскладка доски
    layout_matrix, best_joints, main_board = get_best_symmetric_layout(row_lengths_arr, eff_w, collection_boards)
    M = main_board['length_m']
    name = main_board['name']

    flat_pieces = [p for row in layout_matrix for p in row]
    board_totals = optimize_waste(flat_pieces, main_board)

    # Лаги
    extra_joists = len(best_joints) * 2
    joist_lines = math.ceil(poly_w / JOIST_STEP_M) + 1 + extra_joists
    j_m = math.ceil(joist_lines * poly_h)
    j_total = j_m * round(PIPES_JOIST[joist_choice] * METAL_MARGIN)

    # Сваи (только внутри полигона)
    pr = math.ceil(poly_w / PILE_STEP_M) + 1
    pc = math.ceil(poly_h / PILE_STEP_M) + 1
    step_x_p = poly_w / (pr - 1) if pr > 1 else poly_w
    step_y_p = poly_h / (pc - 1) if pc > 1 else poly_h
    pile_positions = []
    if "Грунт" in base_type:
        for i in range(pr):
            for j in range(pc):
                px = min_xm + i * step_x_p
                py = min_ym + j * step_y_p
                if point_in_polygon(px, py, verts_m):
                    pile_positions.append((px, py))
    piles = len(pile_positions)

    # Регулируемые опоры HILST LIFT
    support_positions = []
    if use_adjustable_supports:
        support_step_x = 0.4 # Шаг между лагами
        support_step_y = 0.4 if joist_support_type == "Лага ДПК" else 1.0
        
        sr = math.ceil(poly_w / support_step_x) + 1
        sc = math.ceil(poly_h / support_step_y) + 1
        step_x_s = poly_w / (sr - 1) if sr > 1 else poly_w
        step_y_s = poly_h / (sc - 1) if sc > 1 else poly_h
        
        for i in range(sr):
            for j in range(sc):
                px = min_xm + i * step_x_s
                py = min_ym + j * step_y_s
                if point_in_polygon(px, py, verts_m):
                    support_positions.append((px, py))
    supports_count = len(support_positions)
    supports_total = supports_count * 450 # Примерная цена за опору 450 руб

    # Каркас
    f_m = math.ceil(pc * poly_w) if frame_choice and "Грунт" in base_type else 0
    f_total = f_m * round(PIPES_FRAME[frame_choice] * METAL_MARGIN) if frame_choice and "Грунт" in base_type else 0

    # Кляймеры
    clips_packs = math.ceil((len(row_segments) * joist_lines) / 100)
    clips_total = clips_packs * 2200

    # Работы
    work_base = poly_area * 2400
    work_steps = steps_m * 5200
    work_piles = piles * 3600
    work_supports = supports_count * 200 # Монтаж опор

    # Сметы
    mat_data = [{"Позиция": f"Доска террасная: {nm}", "Кол-во": f"{dt['qty']} шт", "Сумма": dt['sum']} for nm, dt in board_totals.items()]
    mat_data.extend([
        {"Позиция": f"Лага {joist_choice}", "Кол-во": f"{j_m} м.п.", "Сумма": j_total},
        {"Позиция": "Кляймеры (уп. 100 шт)", "Кол-во": f"{clips_packs} уп.", "Сумма": clips_total},
    ])
    if f_total > 0:
        mat_data.insert(len(board_totals), {"Позиция": f"Каркас {frame_choice}", "Кол-во": f"{f_m} м.п.", "Сумма": f_total})
        
    if supports_count > 0:
        mat_data.append({"Позиция": f"Регулируемые опоры HILST LIFT (под {joist_support_type})", "Кол-во": f"{supports_count} шт.", "Сумма": supports_total})

    work_data = [{"Позиция": "Монтаж настила", "Сумма": work_base}]
    if steps_m > 0:
        work_data.append({"Позиция": "Монтаж ступеней", "Сумма": work_steps})
    if piles > 0:
        work_data.append({"Позиция": f"Монтаж свай ({piles} шт)", "Сумма": work_piles})
    if supports_count > 0:
        work_data.append({"Позиция": f"Монтаж регулируемых опор ({supports_count} шт)", "Сумма": work_supports})

    grand_total = sum(d['Сумма'] for d in mat_data) + sum(d['Сумма'] for d in work_data)

    # --- ЧЕРТЕЖИ ---
    def get_poly_plot(mode):
        fig, ax = plt.subplots(figsize=(10, 6))
        # Контур полигона
        poly_patch = patches.Polygon(verts_m, closed=True, fill=False, edgecolor='#333', linewidth=2)
        ax.add_patch(poly_patch)

        if mode == "board":
            draw_w = eff_w * 0.85
            for idx, (y_pos, x_start, x_end, seg_len) in enumerate(row_segments):
                if idx < len(layout_matrix):
                    x = x_start
                    for w in layout_matrix[idx]:
                        ax.add_patch(patches.Rectangle((x, y_pos), w, draw_w, color='#8d6e63', ec='black', lw=0.5))
                        x += w
            ax.text((min_xm + max_xm) / 2, min_ym - 0.5, f"Габариты: {int(poly_w*1000)} × {int(poly_h*1000)} мм | Площадь: {poly_area:.2f} м²", ha='center', fontweight='bold', fontsize=10)

        elif mode == "frame":
            abs_joints = set()
            for jx in best_joints:
                abs_joints.add(min_xm + jx)
            for i in range(math.ceil(poly_w / JOIST_STEP_M) + 1):
                cx = min_xm + min(i * JOIST_STEP_M, poly_w)
                # Вертикальная лага — только внутри полигона
                segs = polygon_row_segments(verts_m, (min_ym + max_ym) / 2)
                ax.plot([cx, cx], [min_ym, max_ym], color='blue', lw=1, alpha=0.3)
            for jx in abs_joints:
                ax.plot([jx - 0.02, jx - 0.02], [min_ym, max_ym], color='c', lw=1.5, alpha=0.9)
                ax.plot([jx + 0.02, jx + 0.02], [min_ym, max_ym], color='c', lw=1.5, alpha=0.9)
            if frame_choice and "Грунт" in base_type:
                for j in range(pc):
                    cy = min_ym + j * step_y_p
                    ax.plot([min_xm, max_xm], [cy, cy], color='red', lw=3)
            ax.text((min_xm + max_xm) / 2, min_ym - 0.4, "Синим: Сетка лаг | Голубым: Парные лаги | Красным: Несущие балки", color='blue', ha='center', fontsize=10)

        elif mode == "piles":
            if use_adjustable_supports:
                for px, py in support_positions:
                    ax.add_patch(patches.Circle((px, py), 0.08, color='orange', alpha=0.7))
                if len(support_positions) >= 2:
                    ax.text((min_xm + max_xm) / 2, min_ym - 0.4, f"Опор HILST: {supports_count} шт | Шаг: ~{int(step_x_s*1000)}×{int(step_y_s*1000)} мм", ha='center', fontsize=10, color='darkorange')
            else:
                for px, py in pile_positions:
                    ax.add_patch(patches.Circle((px, py), 0.12, color='black'))
                # Размеры между сваями
                if len(pile_positions) >= 2:
                    ax.text((min_xm + max_xm) / 2, min_ym - 0.4, f"Свай: {piles} шт | Шаг: ~{int(step_x_p*1000)}×{int(step_y_p*1000)} мм", ha='center', fontsize=10)

        ax.set_xlim(min_xm - 1.0, max_xm + 1.0)
        ax.set_ylim(min_ym - 1.2, max_ym + 0.5)
        ax.set_aspect('equal')
        plt.axis('off')
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
        plt.close(fig)
        buf.seek(0)
        return buf

    # --- UI вывод ---
    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    total_mat = sum(d['Сумма'] for d in mat_data)
    total_work = sum(d['Сумма'] for d in work_data)
    with m1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Стоимость работ</div>
            <div class="value blue">{total_work:,.0f} ₽</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Стоимость материалов</div>
            <div class="value orange">{total_mat:,.0f} ₽</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Площадь</div>
            <div class="value">{poly_area:.1f} м²</div>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Итого</div>
            <div class="value total">{grand_total:,.0f} ₽</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    colA, colB = st.columns(2)
    colA.markdown("#### :material/inventory: Смета материалов")
    colA.table(mat_data)
    colB.markdown("#### :material/construction: Смета работ")
    colB.table(work_data)
    st.divider()

    # PDF
    def create_poly_pdf():
        pdf = FPDF(); pdf.add_page(); pdf.set_font('Arial', '', 12)
        font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "DejaVuSans.ttf")
        try: pdf.add_font('DejaVu', '', font_path); pdf.set_font('DejaVu', '', 12)
        except: pass
        pdf.cell(200, 10, txt="Смета: нестандартная терраса", ln=True, align='C')
        pdf.cell(200, 10, txt=f"Клиент: {client_name} | Площадь: {poly_area:.2f} м²", ln=True, align='L')
        if manager_name or manager_phone:
            pdf.cell(200, 10, txt=f"Менеджер проекта: {manager_name} {manager_phone}", ln=True, align='L')
        pdf.ln(5)
        pdf.set_fill_color(235, 235, 235)
        pdf.cell(110, 10, "Материалы", 1, 0, 'L', True); pdf.cell(30, 10, "Кол-во", 1, 0, 'C', True); pdf.cell(50, 10, "Сумма", 1, 1, 'C', True)
        for r in mat_data: pdf.cell(110, 10, str(r["Позиция"])[:45], 1); pdf.cell(30, 10, str(r["Кол-во"]), 1, 0, 'C'); pdf.cell(50, 10, f"{r['Сумма']:,.0f} р.", 1, 1, 'R')
        pdf.ln(5); pdf.cell(140, 10, "Строительно-монтажные работы", 1, 0, 'L', True); pdf.cell(50, 10, "Сумма", 1, 1, 'C', True)
        for r in work_data: pdf.cell(140, 10, str(r["Позиция"]), 1); pdf.cell(50, 10, f"{r['Сумма']:,.0f} р.", 1, 1, 'R')
        pdf.ln(5); pdf.set_font('DejaVu', '', 14); pdf.cell(190, 10, txt=f"ИТОГО: {grand_total:,.0f} руб.", ln=True, align='R')
        
        # ================= УТП Terrasy66 =================
        pdf.add_page()
        pdf.set_font('DejaVu', '', 14)
        pdf.set_fill_color(0, 184, 148)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(190, 12, "Почему выбирают ООО «Дача 2000»:", ln=True, align='C', fill=True)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('DejaVu', '', 11)
        pdf.ln(8)
        
        usps = [
            "- Террасы под ключ: полный цикл работ от проектирования до сдачи.",
            "- Гарантия на монтажные работы 24 месяца.",
            "- Используем только качественные материалы премиум-класса.",
            "- Уникальные дизайнерские решения и нестандартные формы.",
            "- Профессиональные бригады с многолетним опытом.",
            "- Строгое соблюдение сроков по договору.",
            "- Бесплатный выезд на замер и составление сметы."
        ]
        for usp in usps:
            pdf.cell(190, 8, usp, ln=True)
            
        pdf.ln(10)
        pdf.set_font('DejaVu', '', 12)
        pdf.set_text_color(0, 184, 148)
        pdf.cell(190, 8, "Создаем идеальные террасы для вашего отдыха!", ln=True, align='C')
        pdf.set_text_color(0, 0, 0)

        for m, t in [("board", "Настил"), ("frame", "Схема подсистемы"), ("piles", "Свайное поле")]:
            if m == "piles" and piles == 0: continue
            pdf.add_page(); pdf.cell(200, 10, t, ln=True, align='C'); pdf.image(get_poly_plot(m), x=15, y=30, w=180)
        return bytes(pdf.output())

    col_dl1, col_dl2, col_dl3 = st.columns([1, 2, 1])
    with col_dl2:
        st.download_button(":material/download: СКАЧАТЬ ПРОЕКТ (PDF)", data=create_poly_pdf(), file_name=f"Terrasa_{client_name}.pdf", mime="application/pdf", use_container_width=True)

    st.divider()
    st.subheader(":material/architecture: Технические схемы")
    t1, t2, t3 = st.tabs(["Вид настила", "Металлокаркас", "Свайное поле"])
    with t1: st.image(get_poly_plot("board"), caption="Раскладка доски внутри контура.")
    with t2: st.image(get_poly_plot("frame"), caption="Голубые линии — парные лаги под стыки.")
    with t3:
        if piles > 0: st.image(get_poly_plot("piles"), caption="Сваи внутри контура.")
        else: st.info("Основание — бетон, сваи не требуются.")

    st.stop()

# Блокировка округлой формы и бассейна
if shape_type == ":material/circle: Округлая (Овал / Круг)":
    st.warning(":material/circle: Модуль расчёта округлых террас в разработке.")
    st.info("Переключитесь на «Прямоугольную (Стандарт)» для полного расчёта.")
    st.stop()

if has_pool:
    st.warning(":material/pool: Модуль вырезов под бассейн в разработке.")
    st.info("Уберите галочку бассейна для полного расчёта.")
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
    st.error("Размеры террасы слишком малы для установки торцевой доски.")
    st.stop()

row_lengths_arr = []
if "Вдоль" in direction_choice:
    board_len_axis = inner_X
    board_row_axis = inner_Y
    rows_count = math.ceil(board_row_axis / eff_w)
    for r in range(rows_count):
        row_lengths_arr.append(inner_X)
else:
    board_len_axis = inner_Y
    board_row_axis = inner_X
    rows_count = math.ceil(board_row_axis / eff_w)
    for r in range(rows_count):
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
piles = pr * pc if "Грунт" in base_type else 0

supports_count = 0
supports_total = 0
if use_adjustable_supports:
    support_step_x = 0.4
    support_step_y = 0.4 if joist_support_type == "Лага ДПК" else 1.0
    sr = math.ceil(length / support_step_x) + 1
    sc = math.ceil(width / support_step_y) + 1
    supports_count = sr * sc
    supports_total = supports_count * 450 # Примерная цена за опору

f_m = math.ceil(pc * length) if "Вдоль" in direction_choice else math.ceil(pr * width)
f_total = f_m * round(PIPES_FRAME[frame_choice] * METAL_MARGIN) if frame_choice and "Грунт" in base_type else 0

clips_packs = math.ceil((math.ceil(width/eff_w) * joist_count_total) / 100)
clips_total = clips_packs * 2200

work_base = area * 2400; work_steps = steps_m * 5200; work_piles = piles * 3600
work_supports = supports_count * 200

# Таблицы
mat_data = [{"Позиция": f"Доска террасная/торцевая: {name}", "Кол-во": f"{data['qty']} шт", "Сумма": data['sum']} for name, data in board_totals.items()]
mat_data.extend([{"Позиция": f"Лага {joist_choice} (вкл. парные лаги на стыках)", "Кол-во": f"{j_m} м.п.", "Сумма": j_total}, {"Позиция": "Кляймеры (уп. 100 шт)", "Кол-во": f"{clips_packs} уп.", "Сумма": clips_total}])
if frame_choice and "Грунт" in base_type: mat_data.insert(len(board_totals), {"Позиция": f"Каркас {frame_choice}", "Кол-во": f"{f_m} м.п.", "Сумма": f_total})
if supports_count > 0: mat_data.append({"Позиция": f"Регулируемые опоры HILST LIFT (под {joist_support_type})", "Кол-во": f"{supports_count} шт.", "Сумма": supports_total})

work_data = [{"Позиция": "Монтаж настила", "Сумма": work_base}]
if steps_m > 0: work_data.append({"Позиция": "Монтаж ступеней", "Сумма": work_steps})
if piles > 0: work_data.append({"Позиция": f"Монтаж свай ({piles} шт)", "Сумма": work_piles})
if supports_count > 0: work_data.append({"Позиция": f"Монтаж регулируемых опор ({supports_count} шт)", "Сумма": work_supports})

grand_total = sum(d['Сумма'] for d in mat_data) + sum(d['Сумма'] for d in work_data)

# --- ФОРМИРОВАНИЕ ТАБЛИЦЫ ДЕТАЛИЗАЦИИ ПО РЯДАМ ---
detail_rows = []

def format_row_data(row_name, pieces, standard_len):
    full_count = {}
    cut_count = {}
    total_len = 0.0
    for p in pieces:
        p_val = round(p, 3)
        total_len += p_val
        if abs(p_val - standard_len) <= 0.01:
            full_count[p_val] = full_count.get(p_val, 0) + 1
        else:
            cut_count[p_val] = cut_count.get(p_val, 0) + 1
            
    full_str = ", ".join([f"{l} м – {c} шт." for l, c in full_count.items()]) if full_count else "-"
    cut_str = ", ".join([f"{l} м – {c} шт." for l, c in cut_count.items()]) if cut_count else "-"
    
    return {
        "№ ряда / Элемент": row_name,
        "Целые доски": full_str,
        "Обрезанные доски": cut_str,
        "Суммарная длина": f"{round(total_len, 3)} м"
    }

for i, row_pieces in enumerate(layout_matrix):
    detail_rows.append(format_row_data(f"Ряд {i+1}", row_pieces, M))

if use_frame:
    if "Вдоль" in direction_choice:
        if edge_front: detail_rows.append(format_row_data("Торцевая: Спереди", front_pieces, M))
        if edge_back: detail_rows.append(format_row_data("Торцевая: Сзади", back_pieces, M))
        if edge_left: detail_rows.append(format_row_data("Торцевая: Слева", left_pieces, M))
        if edge_right: detail_rows.append(format_row_data("Торцевая: Справа", right_pieces, M))
    else:
        if edge_left: detail_rows.append(format_row_data("Торцевая: Слева", left_pieces, M))
        if edge_right: detail_rows.append(format_row_data("Торцевая: Справа", right_pieces, M))
        if edge_front: detail_rows.append(format_row_data("Торцевая: Спереди", front_pieces, M))
        if edge_back: detail_rows.append(format_row_data("Торцевая: Сзади", back_pieces, M))

detail_df = pd.DataFrame(detail_rows)

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
        if use_adjustable_supports:
            support_step_x = 0.4
            support_step_y = 0.4 if joist_support_type == "Лага ДПК" else 1.0
            sr = math.ceil(length / support_step_x) + 1
            sc = math.ceil(width / support_step_y) + 1
            step_x_s = length / (sr - 1) if sr > 1 else length
            step_y_s = width / (sc - 1) if sc > 1 else width
            
            for i in range(sr):
                for j in range(sc):
                    px, py = i * step_x_s, j * step_y_s
                    ax.add_patch(patches.Circle((px, py), 0.1, color='orange', alpha=0.7))
                    if i < sr - 1 and j == 0: ax.text(px + step_x_s/2, py-0.4, f"{int(step_x_s*1000)} мм", ha='center', fontsize=8, color='darkorange')
                    if j < sc - 1 and i == 0: ax.text(px-0.6, py + step_y_s/2, f"{int(step_y_s*1000)} мм", va='center', rotation=90, fontsize=8, color='darkorange')
        else:
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
    font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "DejaVuSans.ttf")
    try: pdf.add_font('DejaVu', '', font_path); pdf.set_font('DejaVu', '', 12)
    except: pass
    pdf.cell(200, 10, txt="Смета и чертежи на устройство террасы", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Клиент: {client_name} | Габариты: {int(length*1000)}x{int(width*1000)} мм", ln=True, align='L')
    if manager_name or manager_phone:
        pdf.cell(200, 10, txt=f"Менеджер проекта: {manager_name} {manager_phone}", ln=True, align='L')
    pdf.ln(5)
    
    pdf.set_fill_color(235, 235, 235); pdf.cell(110, 10, "Материалы", 1, 0, 'L', True); pdf.cell(30, 10, "Кол-во", 1, 0, 'C', True); pdf.cell(50, 10, "Сумма", 1, 1, 'C', True)
    for r in mat_data: pdf.cell(110, 10, str(r["Позиция"])[:45], 1); pdf.cell(30, 10, str(r["Кол-во"]), 1, 0, 'C'); pdf.cell(50, 10, f"{r['Сумма']:,.0f} р.", 1, 1, 'R')
        
    pdf.ln(5); pdf.cell(140, 10, "Строительно-монтажные работы", 1, 0, 'L', True); pdf.cell(50, 10, "Сумма", 1, 1, 'C', True)
    for r in work_data: pdf.cell(140, 10, str(r["Позиция"]), 1); pdf.cell(50, 10, f"{r['Сумма']:,.0f} р.", 1, 1, 'R')
    
    pdf.ln(5); pdf.set_font('DejaVu', '', 14); pdf.cell(190, 10, txt=f"ИТОГО: {grand_total:,.0f} руб.", ln=True, align='R')
    
    # ================= УТП Terrasy66 =================
    pdf.add_page()
    pdf.set_font('DejaVu', '', 14)
    pdf.set_fill_color(0, 184, 148)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 12, "Почему выбирают ООО «Дача 2000»:", ln=True, align='C', fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('DejaVu', '', 11)
    pdf.ln(8)
    
    usps = [
        "- Террасы под ключ: полный цикл работ от проектирования до сдачи.",
        "- Гарантия на монтажные работы 24 месяца.",
        "- Используем только качественные материалы премиум-класса.",
        "- Уникальные дизайнерские решения и нестандартные формы.",
        "- Профессиональные бригады с многолетним опытом.",
        "- Строгое соблюдение сроков по договору.",
        "- Бесплатный выезд на замер и составление сметы."
    ]
    for usp in usps:
        pdf.cell(190, 8, usp, ln=True)
        
    pdf.ln(10)
    pdf.set_font('DejaVu', '', 12)
    pdf.set_text_color(0, 184, 148)
    pdf.cell(190, 8, "Создаем идеальные террасы для вашего отдыха!", ln=True, align='C')
    pdf.set_text_color(0, 0, 0)

    for m, t in [("board", f"Настил"), ("frame", "Схема подсистемы"), ("piles", "Свайное поле")]:
        if m == "piles" and piles == 0: continue
        pdf.add_page(); pdf.cell(200, 10, t, ln=True, align='C'); pdf.image(get_plot(m), x=15, y=30, w=180)
    return bytes(pdf.output())

# --- 7. UI ---
st.markdown("---")
m1, m2, m3, m4 = st.columns(4)
total_mat = sum(d['Сумма'] for d in mat_data)
total_work = sum(d['Сумма'] for d in work_data)
with m1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Стоимость работ</div>
        <div class="value blue">{total_work:,.0f} ₽</div>
    </div>
    """, unsafe_allow_html=True)
with m2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Стоимость материалов</div>
        <div class="value orange">{total_mat:,.0f} ₽</div>
    </div>
    """, unsafe_allow_html=True)
with m3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Площадь</div>
        <div class="value">{area:.1f} м²</div>
    </div>
    """, unsafe_allow_html=True)
with m4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Итого</div>
        <div class="value total">{grand_total:,.0f} ₽</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

with st.expander(":material/bar_chart: Детализация по рядам (Точный расчет)", expanded=False):
    st.dataframe(detail_df, use_container_width=True, hide_index=True)

st.markdown("<br>", unsafe_allow_html=True)
colA, colB = st.columns(2)
colA.markdown("#### :material/inventory: Смета материалов")
colA.table(mat_data)
colB.markdown("#### :material/construction: Смета работ")
colB.table(work_data)
col_dl1, col_dl2, col_dl3 = st.columns([1, 2, 1])
with col_dl2: st.download_button(":material/download: СКАЧАТЬ ПОЛНЫЙ ПРОЕКТ (PDF)", data=create_pdf(), file_name=f"Terrasa_{client_name}.pdf", mime="application/pdf", use_container_width=True)
st.divider(); st.subheader(":material/architecture: Технические схемы (Размеры в мм)")
t1, t2, t3 = st.tabs(["Вид настила", "Металлокаркас", "Свайное поле"])
with t1: st.image(get_plot("board"), caption="Ритм 'кирпичная кладка'. Без внутренних обрезков. Швы разведены.")
with t2: st.image(get_plot("frame"), caption="Голубые линии — парные лаги под каждый стык.")
with t3: 
    if piles > 0: st.image(get_plot("piles"))
    else: st.info("Основание — бетон, сваи не требуются.")

# ============================================================
# CRM И ЭКСПОРТ (БИЗНЕС-БЛОК)
# ============================================================
st.markdown("---")
st.markdown("### :material/work: Интеграции и Сохранение")

# Собираем параметры проекта
export_params = {
    "client_name": client_name,
    "manager_name": manager_name,
    "manager_phone": manager_phone,
    "shape_type": shape_type,
    "length": length,
    "width": width,
    "has_pool": has_pool,
    "brand_choice": brand_choice,
    "collection_name": collection_name,
    "direction_choice": direction_choice,
    "use_frame": use_frame,
    "base_type": base_type,
    "steps_m": steps_m,
    "grand_total": grand_total
}

col_export, col_crm = st.columns(2)

with col_export:
    st.info("Экспорт данных проекта в формате JSON для интеграций или архива.")
    export_json = json.dumps(export_params, ensure_ascii=False, indent=2)
    st.download_button(
        ":material/save: Сохранить проект (JSON)",
        data=export_json,
        file_name=f"project_terrace_{datetime.date.today()}.json",
        mime="application/json",
        use_container_width=True
    )

with col_crm:
    st.info("Отправка заявки в CRM-систему через Webhook (Битрикс24, amoCRM).")
    crm_webhook = st.text_input("Webhook URL CRM:", placeholder="https://your-crm.bitrix24.ru/rest/...", label_visibility="collapsed")
    if st.button(":material/rocket_launch: Отправить лид в CRM", use_container_width=True):
        if crm_webhook:
            try:
                import requests
                resp = requests.post(crm_webhook, json={"project_type": "terrace", "data": export_params, "total": grand_total})
                if resp.status_code in [200, 201]:
                    st.success(":material/check_circle: Заявка успешно отправлена в CRM!")
                else:
                    st.error(f":material/cancel: Ошибка отправки: статус {resp.status_code}")
            except Exception as e:
                st.error(f":material/cancel: Ошибка соединения: {e}")
        else:
            st.warning(":material/warning: Введите URL Webhook")
