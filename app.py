import streamlit as st
import math
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import io
from fpdf import FPDF
import datetime
import pandas as pd
import re
from shapely.geometry import Polygon, box, LineString

# --- 1. ЗАГРУЗКА БАЗЫ ---
@st.cache_data(ttl=300)
def load_google_sheet():
    SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRgxTJ2JPrhh_da9pEBWMoKU3iT5x0DZkzKmKrOKcJBbAos8XmYJDzJyHKvcTtAfPrcpMKDzHW4AWG6/pub?gid=0&single=true&output=csv"
    boards = {}; pipes_joist = {"Труба 60х40х2": 219, "Труба 60х40х3": 290}; pipes_frame = {"Труба 80х80х2": 403, "Труба 80х80х3": 475}
    try:
        df = pd.read_csv(SHEET_URL)
        for index, row in df.iterrows():
            brand = str(row['Бренд']).strip(); raw_name = str(row['Наименование']).strip(); price = float(row['Цена']); unit = str(row['Единица']).strip(); width = int(row['Ширина (мм)']); length_m = float(row['Длина (м)'])
            base_name = re.sub(r'\d{4}[хx*]\d{2,3}[хx*]\d{2,3}', '', raw_name, flags=re.IGNORECASE)
            base_name = re.sub(r'\s*\d+(\.\d+)?\s*м\b', '', base_name, flags=re.IGNORECASE).replace('  ', ' ').strip()
            if brand not in boards: boards[brand] = {}
            if base_name not in boards[brand]: boards[brand][base_name] = []
            board_cost = price if unit.lower() == 'шт' else price * length_m
            boards[brand][base_name].append({"name": raw_name, "length_m": length_m, "price": price, "unit": unit, "width_mm": width, "board_cost": board_cost})
    except Exception as e: st.error(f"Ошибка загрузки данных: {e}")
    return boards, pipes_joist, pipes_frame

PARSED_BOARDS, PIPES_JOIST, PIPES_FRAME = load_google_sheet()

METAL_MARGIN = 1.15; GAP_MM = 5; JOIST_STEP_M = 0.4; PILE_STEP_M = 2.0

# --- 2. ГЕОМЕТРИЧЕСКИЙ ДВИЖОК ---

def get_row_patterns(length, M, min_allowed):
    """Генерирует два эталонных ряда А и Б для сетки"""
    if length <= M: return [length], [length]
    
    # Ряд А (Шов по центру)
    half = length / 2.0
    num = int(half // M)
    edge = half - num * M
    h_a = ([edge] if edge > 0.01 else []) + [M] * num
    if len(h_a) > 1 and h_a[0] < min_allowed:
        comb = h_a[0] + h_a[1]; h_a[0] = comb/2; h_a[1] = comb/2
    row_A = h_a + h_a[::-1]
    
    # Ряд Б (Целая по центру)
    half_rem = (length - M) / 2.0
    num = int(half_rem // M)
    edge = half_rem - num * M
    h_b = ([edge] if edge > 0.01 else []) + [M] * num
    if len(h_b) > 1 and h_b[0] < min_allowed:
        comb = h_b[0] + h_b[1]; h_b[0] = comb/2; h_b[1] = comb/2
    row_B = h_b + [M] + h_b[::-1]
    
    return [round(x, 2) for x in row_A], [round(x, 2) for x in row_B]

def clip_decking_to_polygon(poly, direction, eff_w, collection_boards):
    """Укладывает доски по полигону любой формы"""
    minx, miny, maxx, maxy = poly.bounds
    full_w = maxx - minx; full_h = maxy - miny
    
    best_cost = float('inf'); best_res = None
    
    for base_board in collection_boards:
        M = base_board['length_m']
        eff_M = math.floor(M / JOIST_STEP_M) * JOIST_STEP_M
        min_allowed = max(0.8, eff_M / 3.0)
        
        target_len = full_w if "Вдоль" in direction else full_h
        target_side = full_h if "Вдоль" in direction else full_w
        
        row_A, row_B = get_row_patterns(target_len, eff_M, min_allowed)
        
        boards_in_poly = []
        joints = set()
        num_rows = math.ceil(target_side / eff_w)
        
        for r in range(num_rows):
            curr_pattern = row_A if r % 2 == 0 else row_B
            y_offset = r * eff_w
            
            x_cursor = 0
            for p_len in curr_pattern:
                # Создаем 'тело' доски как прямоугольник
                if "Вдоль" in direction:
                    b_rect = box(minx + x_cursor, miny + y_offset, minx + x_cursor + p_len, miny + y_offset + eff_w * 0.8)
                else:
                    b_rect = box(minx + y_offset, miny + x_cursor, minx + y_offset + eff_w * 0.8, miny + x_cursor + p_len)
                
                # Пересекаем доску с формой террасы
                intersect = b_rect.intersection(poly)
                if not intersect.is_empty and intersect.area > 0.01:
                    # Если доска попала в террасу, сохраняем её геометрию
                    boards_in_poly.append(intersect)
                    # Если это не крайняя точка ряда, запоминаем шов
                    if x_cursor > 0:
                        joints.add(round(x_cursor, 2))
                x_cursor += p_len
        
        # Считаем стоимость (упрощенно по площади + 10% на обрез)
        total_len = sum([b.length for b in boards_in_poly if hasattr(b, 'length')]) # shapely area/length logic
        # В Streamlit проще считать поштучно через упаковку. 
        # Здесь мы зафиксируем выбор лучшей доски по M.
        
        # Для простоты берем первую подходящую или самую длинную
        best_res = (boards_in_poly, joints, base_board)
        break 
        
    return best_res

# --- 3. ИНТЕРФЕЙС ---
st.set_page_config(page_title="Дача 2000 | Конструктор террас", layout="wide")
st.title("🏗️ Профессиональный расчет сложных террас")

st.sidebar.header("1. Форма террасы")
shape_type = st.sidebar.selectbox("Выберите конфигурацию:", [
    "⬜ Прямоугольная", "📐 Г-образная", "🔲 П-образная"
])

st.sidebar.header("2. Параметры объекта")
client_name = st.sidebar.text_input("ФИО Клиента:", "Иван Иванович")

if shape_type == "⬜ Прямоугольная":
    L = st.sidebar.number_input("Длина фасада X, м:", 1.0, 50.0, 6.0)
    W = st.sidebar.number_input("Глубина Y, м:", 1.0, 50.0, 4.0)
    coords = [(0,0), (L,0), (L,W), (0,W)]
elif shape_type == "📐 Г-образная":
    L = st.sidebar.number_input("Общая длина X, м:", 1.0, 50.0, 6.0)
    W = st.sidebar.number_input("Общая глубина Y, м:", 1.0, 50.0, 5.0)
    cx = st.sidebar.number_input("Вырез X, м:", 0.5, L-0.5, 3.0)
    cy = st.sidebar.number_input("Вырез Y, м:", 0.5, W-0.5, 2.0)
    # Координаты Г-формы (вырез в углу)
    coords = [(0,0), (L,0), (L, W-cy), (L-cx, W-cy), (L-cx, W), (0,W)]
else: # П-образная
    L = st.sidebar.number_input("Общая длина X, м:", 1.0, 50.0, 8.0)
    W = st.sidebar.number_input("Общая глубина Y, м:", 1.0, 50.0, 4.0)
    cw = st.sidebar.number_input("Ширина выреза X, м:", 0.5, L-1.0, 4.0)
    cd = st.sidebar.number_input("Глубина выреза Y, м:", 0.5, W-0.5, 2.0)
    x1 = (L-cw)/2
    coords = [(0,0), (L,0), (L,W), (L-x1, W), (L-x1, W-cd), (x1, W-cd), (x1, W), (0,W)]

terrace_poly = Polygon(coords)

st.sidebar.header("3. Материалы")
brand = st.sidebar.selectbox("Бренд:", list(PARSED_BOARDS.keys()))
collection = st.sidebar.selectbox("Коллекция:", list(PARSED_BOARDS[brand].keys()))
coll_boards = PARSED_BOARDS[brand][collection]
eff_w = (coll_boards[0]["width_mm"] + GAP_MM) / 1000

direction = st.sidebar.radio("Укладка:", ["Вдоль фасада (X)", "Поперек фасада (Y)"])

st.sidebar.header("4. Окантовка")
use_frame = st.sidebar.checkbox("Торцевая доска по периметру", value=True)

# --- 4. РАСЧЕТ И ОТРИСОВКА ---

# Если есть рамка - уменьшаем полигон внутрь на ширину доски
if use_frame:
    visual_poly = terrace_poly.buffer(-eff_w, join_style=2) # join_style=2 это острые углы
else:
    visual_poly = terrace_poly

# Выполняем раскладку
boards_geoms, joints_x, used_board = clip_decking_to_polygon(visual_poly, direction, eff_w, coll_boards)

# --- ВИЗУАЛИЗАЦИЯ ---
fig, ax = plt.subplots(figsize=(10, 8))

# 1. Рисуем основную доску (обрезанную полигоном)
for b_geom in boards_geoms:
    if isinstance(b_geom, Polygon):
        x, y = b_geom.exterior.xy
        ax.fill(x, y, color='#8d6e63', ec='black', lw=0.5, alpha=0.9)

# 2. Рисуем окантовку (Picture Frame)
if use_frame:
    # Окантовка это разность между внешним и внутренним полигоном
    frame_geom = terrace_poly.difference(visual_poly)
    if isinstance(frame_geom, Polygon):
        x, y = frame_geom.exterior.xy
        ax.fill(x, y, color='#5d4037', ec='black', lw=1.2)
    elif hasattr(frame_geom, 'geoms'): # MultiPolygon
        for g in frame_geom.geoms:
            x, y = g.exterior.xy
            ax.fill(x, y, color='#5d4037', ec='black', lw=1.2)

# Настройка осей
ax.set_aspect('equal')
plt.axis('off')

# Смета (упрощенная для теста)
area = terrace_poly.area
est_qty = math.ceil((area * 1.1) / (used_board['width_mm']/1000 * used_board['length_m']))
total_sum = est_qty * used_board['board_cost']

st.markdown(f"### Итоговая стоимость (ориентировочно): {total_sum:,.0f} руб.")
st.pyplot(fig)

st.info("Геометрическое ядро (Boolean Masking) успешно подключено. Стыки досок теперь автоматически подрезаются под форму террасы, а рамка огибает периметр.")
