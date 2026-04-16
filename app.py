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
        elif shape_type == "⏺️ Округлая (Овал / Круг)":
            length = st.number_input("Длина (Диам X), м:", 1.0, 50.0, 6.0)
            width = st.number_input("Глубина (Диам Y), м:", 1.0, 50.0, 4.0)
        else:
            # Нестандартные формы — переменные-заглушки для совместимости
            length = 1.0; width = 1.0

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


# --- НЕСТАНДАРТНЫЕ ФОРМЫ: ВЕКТОРНАЯ СИСТЕМА ВВОДА ---
is_complex = shape_type in ["📐 Г-образная (Угловая)", "🔲 П-образная (С вырезом)", "✏️ Свой контур (По координатам)"]

if is_complex:
    st.markdown("---")
    st.subheader("📐 Векторная система ввода размеров")
    
    if shape_type == "📐 Г-образная (Угловая)":
        st.markdown("Введите размеры всех сторон Г-образной террасы (в мм):")
        # Г-образная: 6 сторон
        #   A ──────────┐
        #   │           │ B
        #   │     ┌─────┘
        #   │  D  │ E
        #   │     │
        #   └─────┘
        #      C
        vc1, vc2, vc3 = st.columns(3)
        v_A = vc1.number_input("A — Длина верхняя (мм):", 500, 50000, 6000, step=100, key="v_A")
        v_B = vc2.number_input("B — Глубина правая (мм):", 500, 50000, 3000, step=100, key="v_B")
        v_C = vc3.number_input("C — Длина нижняя (мм):", 500, 50000, 3000, step=100, key="v_C")
        vc4, vc5, vc6 = st.columns(3)
        v_D = vc4.number_input("D — Глубина левая (мм):", 500, 50000, 5000, step=100, key="v_D")
        v_E = vc5.number_input("E — Ступенька X (мм):", 500, 50000, 3000, step=100, key="v_E")
        v_F = vc6.number_input("F — Ступенька Y (мм):", 500, 50000, 2000, step=100, key="v_F")
        
        # SVG превью Г-образной формы
        svg_w, svg_h = 480, 340
        # Масштаб: вписываем форму в svg
        max_dim = max(v_A, v_D)
        sc = min((svg_w - 100) / v_A, (svg_h - 100) / v_D) if max_dim > 0 else 1
        # Координаты вершин Г-образной (по часовой стрелке от верхнего левого)
        pts = [
            (50, 30),                                          # 0: верхний левый
            (50 + v_A * sc, 30),                               # 1: верхний правый
            (50 + v_A * sc, 30 + v_B * sc),                    # 2: правый нижний угол ступеньки
            (50 + v_C * sc, 30 + v_B * sc),                    # 3: внутренний угол ступеньки
            (50 + v_C * sc, 30 + v_D * sc),                    # 4: нижний правый
            (50, 30 + v_D * sc),                               # 5: нижний левый
        ]
        poly_str = " ".join([f"{p[0]},{p[1]}" for p in pts])
        
        # Метки размеров
        def mid(p1, p2): return ((p1[0]+p2[0])/2, (p1[1]+p2[1])/2)
        labels_svg = ""
        # A — верхняя сторона
        mx, my = mid(pts[0], pts[1])
        labels_svg += f'<text x="{mx}" y="{my - 8}" text-anchor="middle" font-size="13" fill="#1b5e20" font-weight="bold">A = {v_A} мм</text>'
        # B — правая сторона (верхняя часть)
        mx, my = mid(pts[1], pts[2])
        labels_svg += f'<text x="{mx + 10}" y="{my}" text-anchor="start" font-size="13" fill="#1b5e20" font-weight="bold" transform="rotate(90,{mx+10},{my})">B = {v_B}</text>'
        # E — горизонтальная ступенька
        mx, my = mid(pts[2], pts[3])
        labels_svg += f'<text x="{mx}" y="{my + 18}" text-anchor="middle" font-size="13" fill="#e65100" font-weight="bold">E = {v_E} мм</text>'
        # F — вертикальная ступенька
        mx, my = mid(pts[3], pts[4])
        labels_svg += f'<text x="{mx + 10}" y="{my}" text-anchor="start" font-size="13" fill="#e65100" font-weight="bold">F = {v_F}</text>'
        # C — нижняя сторона
        mx, my = mid(pts[4], pts[5])
        labels_svg += f'<text x="{mx}" y="{my + 18}" text-anchor="middle" font-size="13" fill="#1b5e20" font-weight="bold">C = {v_C} мм</text>'
        # D — левая сторона
        mx, my = mid(pts[5], pts[0])
        labels_svg += f'<text x="{mx - 10}" y="{my}" text-anchor="end" font-size="13" fill="#1b5e20" font-weight="bold" transform="rotate(-90,{mx-10},{my})">D = {v_D}</text>'
        
        svg_code = f'''<svg width="{svg_w}" height="{svg_h}" xmlns="http://www.w3.org/2000/svg">
            <defs><pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
                <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#e0e0e0" stroke-width="0.5"/>
            </pattern></defs>
            <rect width="100%" height="100%" fill="url(#grid)" rx="8"/>
            <polygon points="{poly_str}" fill="#a5d6a7" fill-opacity="0.4" stroke="#2e7d32" stroke-width="2.5"/>
            {labels_svg}
        </svg>'''
        st.markdown(svg_code, unsafe_allow_html=True)
        
        # Обновляем length/width для совместимости с нижним кодом
        length = v_A / 1000.0
        width = v_D / 1000.0
    
    elif shape_type == "🔲 П-образная (С вырезом)":
        st.markdown("Введите размеры всех сторон П-образной террасы (в мм):")
        # П-образная: 8 сторон
        #   A ───────────────────────┐
        #   │                        │ B
        #   │    ┌───── E ──────┐    │
        #   │  F │              │ F  │
        #   │    │    ВЫРЕЗ     │    │
        #   │    └──────────────┘    │
        #   │                        │
        #   └────────── A ──────────┘
        vc1, vc2 = st.columns(2)
        vp_A = vc1.number_input("A — Общая длина (мм):", 1000, 50000, 8000, step=100, key="vp_A")
        vp_B = vc2.number_input("B — Общая глубина (мм):", 1000, 50000, 5000, step=100, key="vp_B")
        vc3, vc4 = st.columns(2)
        vp_E = vc3.number_input("E — Ширина выреза (мм):", 500, 50000, 4000, step=100, key="vp_E")
        vp_F = vc4.number_input("F — Глубина выреза (мм):", 500, 50000, 3000, step=100, key="vp_F")
        
        # Боковые «крылья»
        wing = (vp_A - vp_E) / 2.0
        
        # SVG превью П-образной формы
        svg_w, svg_h = 480, 340
        sc = min((svg_w - 100) / vp_A, (svg_h - 100) / vp_B) if max(vp_A, vp_B) > 0 else 1
        ox, oy = 50, 30
        pts = [
            (ox, oy),                                             # 0: верхний левый
            (ox + vp_A * sc, oy),                                 # 1: верхний правый
            (ox + vp_A * sc, oy + vp_B * sc),                     # 2: нижний правый
            (ox + (vp_A + vp_E) / 2 * sc, oy + vp_B * sc),       # 3: вырез правый низ
            (ox + (vp_A + vp_E) / 2 * sc, oy + (vp_B - vp_F) * sc),  # 4: вырез правый верх
            (ox + (vp_A - vp_E) / 2 * sc, oy + (vp_B - vp_F) * sc),  # 5: вырез левый верх
            (ox + (vp_A - vp_E) / 2 * sc, oy + vp_B * sc),       # 6: вырез левый низ
            (ox, oy + vp_B * sc),                                 # 7: нижний левый
        ]
        poly_str = " ".join([f"{p[0]},{p[1]}" for p in pts])
        
        def mid(p1, p2): return ((p1[0]+p2[0])/2, (p1[1]+p2[1])/2)
        labels_svg = ""
        # A — верхняя
        mx, my = mid(pts[0], pts[1])
        labels_svg += f'<text x="{mx}" y="{my - 8}" text-anchor="middle" font-size="13" fill="#1b5e20" font-weight="bold">A = {vp_A} мм</text>'
        # B — правая
        mx, my = mid(pts[1], pts[2])
        labels_svg += f'<text x="{mx + 10}" y="{my}" text-anchor="start" font-size="13" fill="#1b5e20" font-weight="bold">B = {vp_B}</text>'
        # E — ширина выреза
        mx, my = mid(pts[4], pts[5])
        labels_svg += f'<text x="{mx}" y="{my - 5}" text-anchor="middle" font-size="13" fill="#e65100" font-weight="bold">E = {vp_E} мм</text>'
        # F — глубина выреза
        mx, my = mid(pts[3], pts[4])
        labels_svg += f'<text x="{mx + 8}" y="{my}" text-anchor="start" font-size="12" fill="#e65100" font-weight="bold">F = {vp_F}</text>'
        # Крыло
        if wing > 0:
            mx_w = (pts[6][0] + pts[7][0]) / 2
            labels_svg += f'<text x="{mx_w}" y="{pts[7][1] + 16}" text-anchor="middle" font-size="11" fill="#555">крыло: {int(wing)} мм</text>'
            mx_w2 = (pts[2][0] + pts[3][0]) / 2
            labels_svg += f'<text x="{mx_w2}" y="{pts[2][1] + 16}" text-anchor="middle" font-size="11" fill="#555">крыло: {int(wing)} мм</text>'
        
        # Штриховка выреза
        cx1, cy1 = pts[5]
        cx2, cy2 = pts[3][0], pts[3][1]
        hatch_svg = ""
        step_h = 12
        y_start = cy1
        while y_start < cy2:
            hatch_svg += f'<line x1="{cx1}" y1="{y_start}" x2="{cx2}" y2="{y_start}" stroke="#bbb" stroke-width="0.5" stroke-dasharray="4,4"/>'
            y_start += step_h
        
        svg_code = f'''<svg width="{svg_w}" height="{svg_h}" xmlns="http://www.w3.org/2000/svg">
            <defs><pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
                <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#e0e0e0" stroke-width="0.5"/>
            </pattern></defs>
            <rect width="100%" height="100%" fill="url(#grid)" rx="8"/>
            <polygon points="{poly_str}" fill="#a5d6a7" fill-opacity="0.4" stroke="#2e7d32" stroke-width="2.5"/>
            {hatch_svg}
            <text x="{(cx1+cx2)/2}" y="{(cy1+cy2)/2 + 4}" text-anchor="middle" font-size="12" fill="#999" font-style="italic">вырез</text>
            {labels_svg}
        </svg>'''
        st.markdown(svg_code, unsafe_allow_html=True)
        
        length = vp_A / 1000.0
        width = vp_B / 1000.0
    
    elif shape_type == "✏️ Свой контур (По координатам)":
        st.markdown("Введите координаты вершин террасы (в мм). Точки соединяются последовательно, контур замыкается автоматически.")
        
        # Начальные координаты по умолчанию (прямоугольник)
        default_points = [
            {"Точка": "1", "X (мм)": 0, "Y (мм)": 0},
            {"Точка": "2", "X (мм)": 0, "Y (мм)": 5000},
            {"Точка": "3", "X (мм)": 8000, "Y (мм)": 5000},
            {"Точка": "4", "X (мм)": 8000, "Y (мм)": 0},
        ]
        df_coords = pd.DataFrame(default_points)
        edited_df = st.data_editor(
            df_coords, num_rows="dynamic", use_container_width=True,
            column_config={
                "Точка": st.column_config.TextColumn("#", width="small"),
                "X (мм)": st.column_config.NumberColumn("X (мм)", min_value=-50000, max_value=50000, step=100),
                "Y (мм)": st.column_config.NumberColumn("Y (мм)", min_value=-50000, max_value=50000, step=100),
            },
            key="coord_editor"
        )
        
        # SVG превью произвольного контура
        xs = edited_df["X (мм)"].tolist()
        ys = edited_df["Y (мм)"].tolist()
        if len(xs) >= 3:
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            range_x = max_x - min_x if max_x > min_x else 1
            range_y = max_y - min_y if max_y > min_y else 1
            svg_w, svg_h = 480, 340
            pad = 60
            sc = min((svg_w - 2 * pad) / range_x, (svg_h - 2 * pad) / range_y)
            # Трансформируем: SVG Y вниз
            svg_pts = []
            for px, py in zip(xs, ys):
                sx = pad + (px - min_x) * sc
                sy = pad + (max_y - py) * sc  # flip Y
                svg_pts.append((sx, sy))
            
            poly_str = " ".join([f"{p[0]:.1f},{p[1]:.1f}" for p in svg_pts])
            
            # Подписи сторон
            labels_svg = ""
            n = len(svg_pts)
            for i in range(n):
                p1 = svg_pts[i]
                p2 = svg_pts[(i + 1) % n]
                # Длина стороны в мм
                dx = xs[(i + 1) % n] - xs[i]
                dy = ys[(i + 1) % n] - ys[i]
                side_len = int(round((dx**2 + dy**2) ** 0.5))
                mx = (p1[0] + p2[0]) / 2
                my_l = (p1[1] + p2[1]) / 2
                # Нормаль наружу для смещения подписи
                nx_d = -(p2[1] - p1[1])
                ny_d = (p2[0] - p1[0])
                nd = (nx_d**2 + ny_d**2) ** 0.5 if (nx_d**2 + ny_d**2) > 0 else 1
                off = 14
                labels_svg += f'<text x="{mx + nx_d/nd * off:.1f}" y="{my_l + ny_d/nd * off:.1f}" text-anchor="middle" font-size="11" fill="#1b5e20" font-weight="bold">{side_len}</text>'
                # Вершина — маркер
                labels_svg += f'<circle cx="{p1[0]:.1f}" cy="{p1[1]:.1f}" r="4" fill="#2e7d32"/>'
                labels_svg += f'<text x="{p1[0]:.1f}" y="{p1[1] - 8:.1f}" text-anchor="middle" font-size="10" fill="#333">{i+1}</text>'
            
            svg_code = f'''<svg width="{svg_w}" height="{svg_h}" xmlns="http://www.w3.org/2000/svg">
                <defs><pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
                    <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#e0e0e0" stroke-width="0.5"/>
                </pattern></defs>
                <rect width="100%" height="100%" fill="url(#grid)" rx="8"/>
                <polygon points="{poly_str}" fill="#a5d6a7" fill-opacity="0.3" stroke="#2e7d32" stroke-width="2.5"/>
                {labels_svg}
            </svg>'''
            st.markdown(svg_code, unsafe_allow_html=True)
            
            length = range_x / 1000.0
            width = range_y / 1000.0
        else:
            st.warning("Нужно минимум 3 точки для построения контура.")
            length = 1.0; width = 1.0
    
    # Кнопка расчёта для нестандартных форм
    st.markdown("---")
    calc_col1, calc_col2, calc_col3 = st.columns([1, 2, 1])
    with calc_col2:
        calc_pressed = st.button("🔢 РАССЧИТАТЬ НЕСТАНДАРТНУЮ ТЕРРАСУ", use_container_width=True, type="primary")
    
    if calc_pressed:
        st.success("✅ Параметры приняты! Расчётный модуль для нестандартных форм будет подключен на следующем этапе.")
        # Покажем сводную информацию по введённым данным
        info_col1, info_col2 = st.columns(2)
        with info_col1:
            st.markdown("#### 📋 Принятые параметры")
            st.markdown(f"- **Конфигурация:** {shape_type}")
            st.markdown(f"- **Габариты:** {int(length*1000)} × {int(width*1000)} мм")
            st.markdown(f"- **Материал:** {brand_choice} — {collection_name}")
            st.markdown(f"- **Основание:** {base_type}")
        with info_col2:
            st.markdown("#### 🚧 Ожидает реализации")
            st.markdown("- Раскладка террасной доски")
            st.markdown("- Схема свайного поля")
            st.markdown("- Металлокаркас")
            st.markdown("- Смета материалов и работ")
    else:
        st.info("👆 Заполните все размеры и нажмите кнопку для расчёта.")
    
    st.stop()

# Блокировка округлой формы и бассейна
if shape_type == "⏺️ Округлая (Овал / Круг)":
    st.warning("⏺️ Модуль расчёта округлых террас в разработке.")
    st.info("Переключитесь на «Прямоугольную (Стандарт)» для полного расчёта.")
    st.stop()

if has_pool:
    st.warning("🏊 Модуль вырезов под бассейн в разработке.")
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
