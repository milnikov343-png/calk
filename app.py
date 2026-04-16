import streamlit as st
import math
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import io
from fpdf import FPDF
import datetime
import pandas as pd
import re
from shapely.geometry import Polygon, box, Point, LineString

# --- 1. ЗАГРУЗКА БАЗЫ ИЗ GOOGLE ТАБЛИЦ ---
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

# --- 2. МАТЕМАТИКА ПРЯМОУГОЛЬНИКОВ (ИДЕАЛЬНАЯ А-Б-А-Б) ---
def fill_segment(L, M, min_allowed, step):
    if L <= 0.01: return []
    pieces = []; rem = L
    while rem > M + 0.01: pieces.append(M); rem = round(rem - M, 2)
    if rem > 0.01: pieces.append(round(rem, 2))
    if len(pieces) > 1 and pieces[-1] < min_allowed:
        deficit = math.ceil((min_allowed - pieces[-1]) / step) * step
        if pieces[-2] - deficit >= min_allowed: pieces[-2] = round(pieces[-2] - deficit, 2); pieces[-1] = round(pieces[-1] + deficit, 2)
        else:
            combined = pieces[-2] + pieces[-1]; half = math.floor((combined / 2) / step) * step
            if half <= 0: half = step
            pieces[-2] = round(half, 2); pieces[-1] = round(combined - half, 2)
    return pieces

def get_1d_symmetric_pieces(L, M, min_allowed, step):
    if L <= 0.01: return []
    eff_M = math.floor(M / step) * step
    if eff_M <= 0: eff_M = M
    if L <= eff_M: return [round(L, 2)]
    cx = math.floor((L / 2) / step) * step
    left = fill_segment(cx, eff_M, min_allowed, step); right = fill_segment(round(L - cx, 2), eff_M, min_allowed, step)
    return [round(x, 2) for x in left[::-1] + right]

def get_best_symmetric_layout(target_len, target_width, eff_w, collection_boards):
    rows_count = math.ceil(target_width / eff_w); best_cost = float('inf'); best_layout = None; best_joints = None; best_base_board = None
    for base_board in collection_boards:
        M = base_board['length_m']; eff_M = math.floor(M / JOIST_STEP_M) * JOIST_STEP_M
        if eff_M <= 0: continue
        min_allowed = max(0.8, eff_M / 3.0)
        if target_len <= eff_M: row_A = [round(target_len, 2)]; row_B = [round(target_len, 2)]
        else:
            cx = math.floor((target_len / 2) / JOIST_STEP_M) * JOIST_STEP_M
            row_A = fill_segment(cx, eff_M, min_allowed, JOIST_STEP_M)[::-1] + fill_segment(round(target_len - cx, 2), eff_M, min_allowed, JOIST_STEP_M)
            left_x = math.floor(((target_len - eff_M) / 2) / JOIST_STEP_M) * JOIST_STEP_M
            if left_x < 0: left_x = 0
            right_x = left_x + eff_M
            if right_x > target_len: right_x = target_len
            row_B = fill_segment(left_x, eff_M, min_allowed, JOIST_STEP_M)[::-1] + fill_segment(round(right_x - left_x, 2), eff_M, min_allowed, JOIST_STEP_M) + fill_segment(round(target_len - right_x, 2), eff_M, min_allowed, JOIST_STEP_M)
        
        layout_matrix = []; joints = set()
        for r in range(rows_count):
            current_row = row_A if r % 2 == 0 else row_B
            layout_matrix.append(current_row); jx = 0
            for p in current_row[:-1]: jx = round(jx + p, 2); joints.add(jx)
            
        flat_pieces = sorted([p for row in layout_matrix for p in row], reverse=True); bins = []
        for p in flat_pieces:
            placed = False; bins.sort(key=lambda b: M - b)
            for i in range(len(bins)):
                if round(M - bins[i], 2) >= p: bins[i] = round(bins[i] + p, 2); placed = True; break
            if not placed: bins.append(p)
        total_cost = len(bins) * base_board['board_cost']
        if total_cost < best_cost: best_cost = total_cost; best_layout = layout_matrix; best_joints = joints; best_base_board = base_board
    return best_layout, best_joints, best_base_board

def optimize_waste(pieces_list, allowed_board):
    pieces_list = sorted(pieces_list, reverse=True); bins = []
    for p in pieces_list:
        placed = False; bins.sort(key=lambda b: allowed_board['length_m'] - b['used'])
        for b in bins:
            if round(allowed_board['length_m'] - b['used'], 2) >= p: b['used'] = round(b['used'] + p, 2); placed = True; break
        if not placed: bins.append({"board": allowed_board, "used": p})
    qty = len(bins); sum_cost = qty * allowed_board['board_cost']
    return {allowed_board['name']: {"qty": qty, "sum": sum_cost, "unit": allowed_board['unit']}}

def get_shifted_edge(matrix, is_front_or_left, offset_start, offset_end):
    if not matrix: return []
    row_to_copy = matrix[1] if len(matrix) > 1 and is_front_or_left else matrix[-2] if len(matrix) > 1 else matrix[0]
    p = list(row_to_copy)
    if not p: return []
    if len(p) == 1: p[0] = round(p[0] + offset_start + offset_end, 2)
    else: p[0] = round(p[0] + offset_start, 2); p[-1] = round(p[-1] + offset_end, 2)
    return p

# --- 3. ИНТЕРФЕЙС И ВЫБОР ФОРМЫ ---
st.set_page_config(page_title="Дача 2000 | Умный Калькулятор", layout="wide")
st.title("🏗️ Профессиональный проект террасы")

col_h1, col_h2 = st.columns([8, 2])
with col_h2:
    if st.button("🔄 Обновить прайс", use_container_width=True): st.cache_data.clear(); st.rerun()

st.sidebar.header("1. Форма террасы")
shape_type = st.sidebar.selectbox("Выберите конфигурацию:", [
    "⬜ Прямоугольная", "📐 Г-образная", "🔲 П-образная"
])

st.sidebar.header("2. Параметры объекта")
client_name = st.sidebar.text_input("ФИО Клиента:", "Иван Иванович")

if shape_type == "⬜ Прямоугольная":
    length = st.sidebar.number_input("Длина фасада (X), м:", 1.0, 50.0, 9.0)
    width = st.sidebar.number_input("Глубина (Y), м:", 1.0, 50.0, 4.0)
    coords = [(0,0), (length,0), (length,width), (0,width)]
elif shape_type == "📐 Г-образная":
    length = st.sidebar.number_input("Общая длина X, м:", 1.0, 50.0, 6.0)
    width = st.sidebar.number_input("Общая глубина Y, м:", 1.0, 50.0, 5.0)
    cut_x = st.sidebar.number_input("Вырез X, м:", 0.5, length-0.5, 3.0)
    cut_y = st.sidebar.number_input("Вырез Y, м:", 0.5, width-0.5, 2.0)
    coords = [(0,0), (length,0), (length, width-cut_y), (length-cut_x, width-cut_y), (length-cut_x, width), (0,width)]
else:
    length = st.sidebar.number_input("Общая длина X, м:", 1.0, 50.0, 8.0)
    width = st.sidebar.number_input("Общая глубина Y, м:", 1.0, 50.0, 4.0)
    cw = st.sidebar.number_input("Ширина выреза X, м:", 0.5, length-1.0, 4.0)
    cd = st.sidebar.number_input("Глубина выреза Y, м:", 0.5, width-0.5, 2.0)
    x1 = (length-cw)/2
    coords = [(0,0), (length,0), (length,width), (length-x1, width), (length-x1, width-cd), (x1, width-cd), (x1, width), (0,width)]

terrace_poly = Polygon(coords)
area = terrace_poly.area

base_type = st.sidebar.radio("Основание:", ["Грунт (Сваи)", "Бетон"])

st.sidebar.header("3. Выбор коллекции")
brand_choice = st.sidebar.selectbox("Бренд:", list(PARSED_BOARDS.keys()))
if PARSED_BOARDS[brand_choice]:
    collection_name = st.sidebar.selectbox("Коллекция:", list(PARSED_BOARDS[brand_choice].keys()))
    collection_boards = PARSED_BOARDS[brand_choice][collection_name]
    eff_w = (collection_boards[0]["width_mm"] + GAP_MM) / 1000
else:
    st.stop()

direction_choice = st.sidebar.radio("Направление укладки основной доски:", ["Вдоль фасада (по длине X)", "Поперек фасада (по глубине Y)"])

st.sidebar.header("4. Окантовка (Торцевая доска)")
use_frame = st.sidebar.checkbox("Сделать окантовку по периметру (Picture Frame)", value=True)

st.sidebar.header("5. Подсистема")
joist_choice = st.sidebar.selectbox("Лаги (60х40):", list(PIPES_JOIST.keys()))
frame_choice = st.sidebar.selectbox("Каркас (80х80):", list(PIPES_FRAME.keys())) if "Грунт" in base_type else None
steps_m = st.sidebar.number_input("Ступени (пог.м):", 0.0, 50.0, 0.0)

# --- 4. ЕДИНЫЙ БЛОК РАСЧЕТОВ ---
is_complex = shape_type != "⬜ Прямоугольная"

if not is_complex:
    # Обычный точный расчет
    offset = eff_w if use_frame else 0
    inner_X = round(length - offset*2, 3); inner_Y = round(width - offset*2, 3)
    if inner_X <= 0 or inner_Y <= 0: st.error("Терраса слишком мала."); st.stop()
    
    board_len_axis = inner_X if "Вдоль" in direction_choice else inner_Y
    board_row_axis = inner_Y if "Вдоль" in direction_choice else inner_X
    layout_matrix, best_joints, main_board = get_best_symmetric_layout(board_len_axis, board_row_axis, eff_w, collection_boards)
    
    M = main_board['length_m']; eff_M = math.floor(M / JOIST_STEP_M) * JOIST_STEP_M
    if eff_M <= 0: eff_M = M
    min_allowed = max(0.8, eff_M / 3.0)
    
    edge_pieces = []
    if use_frame:
        if "Вдоль" in direction_choice:
            edge_pieces = get_shifted_edge(layout_matrix, True, offset, offset) + get_shifted_edge(layout_matrix, False, offset, offset) + get_1d_symmetric_pieces(width, M, min_allowed, JOIST_STEP_M)*2
        else:
            edge_pieces = get_shifted_edge(layout_matrix, True, offset, offset) + get_shifted_edge(layout_matrix, False, offset, offset) + get_1d_symmetric_pieces(length, M, min_allowed, JOIST_STEP_M)*2

    flat_pieces = [p for row in layout_matrix for p in row] + edge_pieces
    board_totals = optimize_waste(flat_pieces, main_board)
    
    extra_joists = len(best_joints) * 2; joist_count_base = math.ceil(board_len_axis / JOIST_STEP_M) + 1
    j_m = math.ceil((joist_count_base + extra_joists) * width)
    j_total = j_m * round(PIPES_JOIST[joist_choice] * METAL_MARGIN)
    
    pr = math.ceil(length/PILE_STEP_M) + 1; pc = math.ceil(width/PILE_STEP_M) + 1
    piles = pr * pc if "Грунт" in base_type else 0
    f_m = math.ceil(pc * length) if "Вдоль" in direction_choice else math.ceil(pr * width)
    f_total = f_m * round(PIPES_FRAME[frame_choice] * METAL_MARGIN) if frame_choice else 0
    
    clips_packs = math.ceil((math.ceil(width/eff_w) * (joist_count_base + extra_joists)) / 100)

else:
    # Сложный геометрический расчет (Shapely)
    visual_poly = terrace_poly.buffer(-eff_w, join_style=2) if use_frame else terrace_poly
    minx, miny, maxx, maxy = visual_poly.bounds
    full_w = maxx - minx; full_h = maxy - miny
    
    target_len = full_w if "Вдоль" in direction_choice else full_h
    target_side = full_h if "Вдоль" in direction_choice else full_w
    
    # Ищем лучшую доску условно по габаритам
    main_board = collection_boards[-1] # берем самую длинную для базы
    for b in collection_boards:
        if b['length_m'] >= target_len: main_board = b; break
        
    M = main_board['length_m']; eff_M = math.floor(M / JOIST_STEP_M) * JOIST_STEP_M
    if eff_M <= 0: eff_M = M
    min_allowed = max(0.8, eff_M / 3.0)
    
    row_A, row_B = get_row_patterns(target_len, eff_M, min_allowed) if target_len > eff_M else ([target_len], [target_len])
    
    boards_in_poly = []; joints_x = set(); num_rows = math.ceil(target_side / eff_w)
    for r in range(num_rows):
        curr = row_A if r % 2 == 0 else row_B
        y_offset = r * eff_w; cx = 0
        for p_len in curr:
            if "Вдоль" in direction_choice: b_rect = box(minx + cx, miny + y_offset, minx + cx + p_len, miny + y_offset + eff_w * 0.8)
            else: b_rect = box(minx + y_offset, miny + cx, minx + y_offset + eff_w * 0.8, miny + cx + p_len)
            
            intersect = b_rect.intersection(visual_poly)
            if not intersect.is_empty and intersect.area > 0.01:
                boards_in_poly.append(intersect)
                if cx > 0: joints_x.add(round(cx, 2))
            cx += p_len

    est_qty = math.ceil((area * 1.05) / (main_board['width_mm']/1000 * main_board['length_m']))
    if use_frame: est_qty += math.ceil(terrace_poly.length / main_board['length_m'])
    
    board_totals = {main_board['name']: {"qty": est_qty, "sum": est_qty * main_board['board_cost'], "unit": main_board['unit']}}
    
    j_m = math.ceil((area / JOIST_STEP_M) * 1.1) + (len(joints_x)*2 * maxy)
    j_total = j_m * round(PIPES_JOIST[joist_choice] * METAL_MARGIN)
    
    piles = 0; f_m = 0; f_total = 0
    if "Грунт" in base_type:
        pr = math.ceil(length/PILE_STEP_M) + 1; pc = math.ceil(width/PILE_STEP_M) + 1
        p_count = 0
        for i in range(pr):
            for j in range(pc):
                if terrace_poly.contains(Point(i * (length/(pr-1)), j * (width/(pc-1)))): p_count += 1
        piles = p_count
        f_m = math.ceil(p_count * PILE_STEP_M * 1.1)
        f_total = f_m * round(PIPES_FRAME[frame_choice] * METAL_MARGIN)
        
    clips_packs = math.ceil((area * 22) / 100)

# Финальная Смета
clips_total = clips_packs * 2200
work_base = area * 2400; work_steps = steps_m * 5200; work_piles = piles * 3600

mat_data = [{"Позиция": f"Доска террасная/торцевая: {name}", "Кол-во": f"{data['qty']} шт", "Сумма": data['sum']} for name, data in board_totals.items()]
mat_data.extend([{"Позиция": f"Лага {joist_choice}", "Кол-во": f"{j_m} м.п.", "Сумма": j_total}, {"Позиция": "Кляймеры (уп. 100 шт)", "Кол-во": f"{clips_packs} уп.", "Сумма": clips_total}])
if frame_choice: mat_data.insert(len(board_totals), {"Позиция": f"Каркас {frame_choice}", "Кол-во": f"{f_m} м.п.", "Сумма": f_total})

work_data = [{"Позиция": "Монтаж настила", "Сумма": work_base}]
if steps_m > 0: work_data.append({"Позиция": "Монтаж ступеней", "Сумма": work_steps})
if piles > 0: work_data.append({"Позиция": f"Монтаж свай ({piles} шт)", "Сумма": work_piles})

grand_total = sum(d['Сумма'] for d in mat_data) + sum(d['Сумма'] for d in work_data)

# --- 5. УНИВЕРСАЛЬНЫЕ ЧЕРТЕЖИ ---
def get_plot(mode):
    fig, ax = plt.subplots(figsize=(10, 6))
    if not is_complex:
        pr = math.ceil(length/PILE_STEP_M) + 1; pc = math.ceil(width/PILE_STEP_M) + 1
        step_x = length / (pr - 1) if pr > 1 else length; step_y = width / (pc - 1) if pc > 1 else width
        if mode == "board":
            draw_w = eff_w * 0.8
            if use_frame:
                flags = {'F': True, 'B': True, 'L': True, 'R': True}
                draw_edge(ax, edge_pieces[:len(edge_pieces)//4], 'front', length, width, draw_w, flags)
                draw_edge(ax, edge_pieces[len(edge_pieces)//4:len(edge_pieces)//2], 'back', length, width, draw_w, flags)
                draw_edge(ax, edge_pieces[len(edge_pieces)//2:int(len(edge_pieces)*0.75)], 'left', length, width, draw_w, flags)
                draw_edge(ax, edge_pieces[int(len(edge_pieces)*0.75):], 'right', length, width, draw_w, flags)
            
            offset = eff_w if use_frame else 0
            if "Вдоль" in direction_choice:
                for r, row_pieces in enumerate(layout_matrix):
                    y, x = offset + r * eff_w, offset
                    for w in row_pieces: ax.add_patch(patches.Rectangle((x, y), w, draw_w, color='#8d6e63', ec='black', lw=0.5)); x += w
            else:
                for r, row_pieces in enumerate(layout_matrix):
                    x, y = offset + r * eff_w, offset
                    for w in row_pieces: ax.add_patch(patches.Rectangle((x, y), draw_w, w, color='#8d6e63', ec='black', lw=0.5)); y += w
            ax.text(length/2, -0.4, f"Длина: {int(length*1000)} мм", ha='center', fontweight='bold', fontsize=10)
        
        elif mode == "frame":
            abs_joints = set()
            offset = eff_w if use_frame else 0
            if "Вдоль" in direction_choice:
                for jx in best_joints: abs_joints.add(offset + jx)
                for i in range(math.ceil(length / JOIST_STEP_M) + 1): ax.plot([min(i * JOIST_STEP_M, length)]*2, [0, width], color='blue', lw=1, alpha=0.3)
                for jx in abs_joints: ax.plot([jx-0.02, jx-0.02], [0, width], color='c', lw=1.5); ax.plot([jx+0.02, jx+0.02], [0, width], color='c', lw=1.5)
                if frame_choice: 
                    for j in range(pc): ax.plot([0, length], [j * step_y]*2, color='red', lw=3)
            else:
                for jy in best_joints: abs_joints.add(offset + jy)
                for i in range(math.ceil(width / JOIST_STEP_M) + 1): ax.plot([0, length], [min(i * JOIST_STEP_M, width)]*2, color='blue', lw=1, alpha=0.3)
                for jy in abs_joints: ax.plot([0, length], [jy-0.02, jy-0.02], color='c', lw=1.5); ax.plot([0, length], [jy+0.02, jy+0.02], color='c', lw=1.5)
                if frame_choice:
                    for i in range(pr): ax.plot([i * step_x]*2, [0, width], color='red', lw=3)
        elif mode == "piles":
            for i in range(pr):
                for j in range(pc): ax.add_patch(patches.Circle((i * step_x, j * step_y), 0.15, color='black'))
    
    else: # СЛОЖНАЯ ФОРМА
        if mode == "board":
            for b_geom in boards_in_poly:
                if isinstance(b_geom, Polygon):
                    x, y = b_geom.exterior.xy
                    ax.fill(x, y, color='#8d6e63', ec='black', lw=0.5, alpha=0.9)
            if use_frame:
                frame_geom = terrace_poly.difference(visual_poly)
                if isinstance(frame_geom, Polygon):
                    x, y = frame_geom.exterior.xy; ax.fill(x, y, color='#5d4037', ec='black', lw=1.2)
                elif hasattr(frame_geom, 'geoms'):
                    for g in frame_geom.geoms:
                        x, y = g.exterior.xy; ax.fill(x, y, color='#5d4037', ec='black', lw=1.2)
        elif mode == "frame":
            minx, miny, maxx, maxy = terrace_poly.bounds
            # Рисуем лаги, пересекая их с полигоном террасы!
            if "Вдоль" in direction_choice:
                for i in range(int(maxx / JOIST_STEP_M) + 2):
                    line = LineString([(i * JOIST_STEP_M, miny-1), (i * JOIST_STEP_M, maxy+1)])
                    inter = line.intersection(terrace_poly)
                    if not inter.is_empty:
                        if inter.geom_type == 'LineString': ax.plot(*inter.xy, color='blue', lw=1, alpha=0.4)
                        elif inter.geom_type == 'MultiLineString':
                            for g in inter.geoms: ax.plot(*g.xy, color='blue', lw=1, alpha=0.4)
                if frame_choice: # Балки поперек
                    for j in range(int(maxy / PILE_STEP_M) + 2):
                        line = LineString([(minx-1, j * PILE_STEP_M), (maxx+1, j * PILE_STEP_M)])
                        inter = line.intersection(terrace_poly)
                        if not inter.is_empty:
                            if inter.geom_type == 'LineString': ax.plot(*inter.xy, color='red', lw=3)
                            elif inter.geom_type == 'MultiLineString':
                                for g in inter.geoms: ax.plot(*g.xy, color='red', lw=3)
            else:
                # Поперек
                for j in range(int(maxy / JOIST_STEP_M) + 2):
                    line = LineString([(minx-1, j * JOIST_STEP_M), (maxx+1, j * JOIST_STEP_M)])
                    inter = line.intersection(terrace_poly)
                    if not inter.is_empty:
                        if inter.geom_type == 'LineString': ax.plot(*inter.xy, color='blue', lw=1, alpha=0.4)
                        elif inter.geom_type == 'MultiLineString':
                            for g in inter.geoms: ax.plot(*g.xy, color='blue', lw=1, alpha=0.4)
                if frame_choice:
                    for i in range(int(maxx / PILE_STEP_M) + 2):
                        line = LineString([(i * PILE_STEP_M, miny-1), (i * PILE_STEP_M, maxy+1)])
                        inter = line.intersection(terrace_poly)
                        if not inter.is_empty:
                            if inter.geom_type == 'LineString': ax.plot(*inter.xy, color='red', lw=3)
                            elif inter.geom_type == 'MultiLineString':
                                for g in inter.geoms: ax.plot(*g.xy, color='red', lw=3)

        elif mode == "piles":
            minx, miny, maxx, maxy = terrace_poly.bounds
            pr = math.ceil(maxx/PILE_STEP_M) + 1; pc = math.ceil(maxy/PILE_STEP_M) + 1
            for i in range(pr):
                for j in range(pc):
                    pt = Point(i * (maxx/(pr-1) if pr>1 else maxx), j * (maxy/(pc-1) if pc>1 else maxy))
                    if terrace_poly.contains(pt) or terrace_poly.touches(pt):
                        ax.add_patch(patches.Circle((pt.x, pt.y), 0.15, color='black'))

    def draw_edge(ax, pieces, side, L, W, ew, flags): # helper для прямоугольника
        cur = 0
        for p in pieces:
            xs = cur; xe = cur + p
            if side == 'front': pts = [[xs, 0], [xe, 0], [xe, ew], [xs, ew]]; pts[3][0] = ew if xs == 0 and flags['L'] else xs; pts[2][0] = L-ew if round(xe,2) >= round(L,2) and flags['R'] else xe
            elif side == 'back': pts = [[xs, W], [xe, W], [xe, W-ew], [xs, W-ew]]; pts[3][0] = ew if xs == 0 and flags['L'] else xs; pts[2][0] = L-ew if round(xe,2) >= round(L,2) and flags['R'] else xe
            elif side == 'left': pts = [[0, xs], [0, xe], [ew, xe], [ew, xs]]; pts[3][1] = ew if xs == 0 and flags['F'] else xs; pts[2][1] = W-ew if round(xe,2) >= round(W,2) and flags['B'] else xe
            elif side == 'right': pts = [[L, xs], [L, xe], [L-ew, xe], [L-ew, xs]]; pts[3][1] = ew if xs == 0 and flags['F'] else xs; pts[2][1] = W-ew if round(xe,2) >= round(W,2) and flags['B'] else xe
            ax.add_patch(patches.Polygon(pts, color='#5d4037', ec='black', lw=1.2)); cur += p

    ax.set_aspect('equal'); plt.axis('off')
    buf = io.BytesIO(); plt.savefig(buf, format='png', bbox_inches='tight', dpi=150); plt.close(fig); buf.seek(0)
    return buf

# --- UI Рендер ---
st.markdown(f"<h2 style='text-align: center; color: #1b5e20;'>Итоговая стоимость: {grand_total:,.0f} руб.</h2>", unsafe_allow_html=True)
colA, colB = st.columns(2); colA.markdown("#### 🪵 Смета материалов"); colA.table(mat_data); colB.markdown("#### ⚒️ Смета работ"); colB.table(work_data)
st.divider()
t1, t2, t3 = st.tabs(["Вид настила", "Металлокаркас", "Свайное поле"])
with t1: st.image(get_plot("board"))
with t2: st.image(get_plot("frame"))
with t3: 
    if piles > 0: st.image(get_plot("piles"))
    else: st.info("Основание — бетон, сваи не требуются.")
