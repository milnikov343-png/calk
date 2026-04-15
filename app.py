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

            # Очищаем имя от длины, чтобы сгруппировать разные хлысты в одну коллекцию
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

# --- 2. КЛАССИЧЕСКИЙ АЛГОРИТМ РАСКЛАДКИ В ПОЛДОСКИ ---
def optimize_waste(pieces_list, allowed_board):
    # Упаковка обрезков ТОЛЬКО в выбранную длину хлыста (чтобы не смешивать 3м и 4м)
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

def get_best_offset_layout(target_len, target_width, eff_w, collection_boards):
    rows_count = math.ceil(target_width / eff_w)
    best_cost = float('inf')
    best_layout = None
    best_joints = None
    best_summary = None

    # Проверяем каждую длину в коллекции отдельно
    for base_board in collection_boards:
        M = base_board['length_m']
        min_allowed = 0.8 # Запрет на куски меньше 80 см

        # Если доска длиннее террасы - кладем целиком без единого шва!
        if target_len <= M:
            row_A = [round(target_len, 2)]
            row_B = [round(target_len, 2)]
        else:
            # Функция сборки ряда
            def make_row(first_piece_len):
                pieces = []
                rem = target_len
                
                # Кладем первый кусок
                p1 = min(first_piece_len, rem)
                pieces.append(p1)
                rem = round(rem - p1, 2)
                
                # Заполняем середину целыми
                while rem > M + 0.01:
                    pieces.append(M)
                    rem = round(rem - M, 2)
                    
                # Докидываем остаток
                if rem > 0.01:
                    pieces.append(rem)
                    
                # ЗАЩИТА: Если последний огрызок слишком мал
                if len(pieces) > 1 and pieces[-1] < min_allowed:
                    deficit = min_allowed - pieces[-1]
                    if pieces[0] - deficit >= min_allowed:
                        pieces[0] = round(pieces[0] - deficit, 2)
                        pieces[-1] = round(pieces[-1] + deficit, 2)
                    else:
                        combined = pieces[-2] + pieces[-1]
                        pieces[-2] = round(combined / 2, 2)
                        pieces[-1] = round(combined - pieces[-2], 2)
                return pieces

            # Ряд А (начинаем с целой)
            row_A = make_row(M)
            # Ряд Б (начинаем с половинки)
            row_B = make_row(M / 2.0)

        # Собираем матрицу
        layout_matrix = []
        joints = set()
        for r in range(rows_count):
            current_row = row_A if r % 2 == 0 else row_B
            layout_matrix.append(current_row)
            jx = 0
            for p in current_row[:-1]:
                jx = round(jx + p, 2)
                joints.add(jx)

        # Считаем смету ТОЛЬКО для этой длины доски
        flat_pieces = [p for row in layout_matrix for p in row]
        summary = optimize_waste(flat_pieces, base_board)
        total_cost = sum(d['sum'] for d in summary.values())

        # Ищем самый выгодный вариант
        if total_cost < best_cost:
            best_cost = total_cost
            best_layout = layout_matrix
            best_joints = joints
            best_summary = summary

    return best_layout, best_joints, best_summary

# --- 3. ИНТЕРФЕЙС ---
st.set_page_config(page_title="Дача 2000 | Умный Калькулятор", layout="wide")
st.title("🏗️ Профессиональный проект террасы")

col_h1, col_h2 = st.columns([8, 2])
with col_h2:
    if st.button("🔄 Обновить прайс", use_container_width=True):
        st.cache_data.clear(); st.rerun()

st.sidebar.header("1. Параметры объекта")
client_name = st.sidebar.text_input("ФИО Клиента:", "Иван Иванович")
length = st.sidebar.number_input("Длина фасада (X), м:", 1.0, 50.0, 9.0)
width = st.sidebar.number_input("Глубина (Y), м:", 1.0, 50.0, 4.0)
base_type = st.sidebar.radio("Основание:", ["Грунт (Сваи)", "Бетон"])

st.sidebar.header("2. Выбор коллекции")
brand_choice = st.sidebar.selectbox("Бренд:", list(PARSED_BOARDS.keys()))
if PARSED_BOARDS[brand_choice]:
    collection_name = st.sidebar.selectbox("Коллекция:", list(PARSED_BOARDS[brand_choice].keys()))
    collection_boards = PARSED_BOARDS[brand_choice][collection_name]
    eff_w = (collection_boards[0]["width_mm"] + GAP_MM) / 1000
else:
    st.stop()

direction_choice = st.sidebar.radio("Направление укладки доски:", ["Вдоль фасада (по длине X)", "Поперек фасада (по глубине Y)"])

st.sidebar.header("3. Подсистема")
joist_choice = st.sidebar.selectbox("Лаги (60х40):", list(PIPES_JOIST.keys()))
frame_choice = st.sidebar.selectbox("Каркас (80х80):", list(PIPES_FRAME.keys())) if "Грунт" in base_type else None
steps_m = st.sidebar.number_input("Ступени (пог.м):", 0.0, 50.0, 0.0)

# --- 4. ОСНОВНЫЕ РАСЧЕТЫ ---
area = length * width

if "Вдоль" in direction_choice:
    board_len_axis = length
    board_row_axis = width
else:
    board_len_axis = width
    board_row_axis = length

layout_matrix, best_joints, board_totals = get_best_offset_layout(board_len_axis, board_row_axis, eff_w, collection_boards)

# Подсистема: двойные лаги на каждый шов
extra_joists = len(best_joints) * 2 
joist_count_base = math.ceil(board_len_axis / JOIST_STEP_M) + 1
joist_count_total = joist_count_base + extra_joists

j_m = math.ceil(joist_count_total * board_row_axis)
j_total = j_m * round(PIPES_JOIST[joist_choice] * METAL_MARGIN)

piles = 0; f_m = 0; f_total = 0
pr = math.ceil(length/PILE_STEP_M) + 1
pc = math.ceil(width/PILE_STEP_M) + 1

if "Грунт" in base_type:
    piles = pr * pc
    if "Вдоль" in direction_choice: f_m = math.ceil(pc * length)
    else: f_m = math.ceil(pr * width)
    f_total = f_m * round(PIPES_FRAME[frame_choice] * METAL_MARGIN)

rows_count = math.ceil(board_row_axis / eff_w)
clips_packs = math.ceil((rows_count * joist_count_total) / 100)
clips_total = clips_packs * 2200

work_base = area * 2400; work_steps = steps_m * 5200; work_piles = piles * 3600

# Формирование таблиц
mat_data = []
for name, data in board_totals.items():
    mat_data.append({"Позиция": name, "Кол-во": f"{data['qty']} шт", "Сумма": data['sum']})

mat_data.extend([
    {"Позиция": f"Лага {joist_choice} (вкл. парные лаги на стыках)", "Кол-во": f"{j_m} м.п.", "Сумма": j_total},
    {"Позиция": "Кляймеры (уп. 100 шт)", "Кол-во": f"{clips_packs} уп.", "Сумма": clips_total}
])
if frame_choice: mat_data.insert(len(board_totals)+1, {"Позиция": f"Каркас {frame_choice}", "Кол-во": f"{f_m} м.п.", "Сумма": f_total})

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
        if "Вдоль" in direction_choice:
            for r, row_pieces in enumerate(layout_matrix):
                y, x = r * eff_w, 0
                for w in row_pieces:
                    ax.add_patch(patches.Rectangle((x, y), w, eff_w*0.8, color='#8d6e63', ec='black',
