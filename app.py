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

            # Группируем разные длины в одну коллекцию
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

# --- 2. СТРОГИЙ ИНЖЕНЕРНЫЙ РАСКРОЙ ---
def get_best_symmetric_layout(target_len, target_width, eff_w, collection_boards):
    rows_count = math.ceil(target_width / eff_w)
    best_cost = float('inf')
    best_layout = None
    best_joints = None
    best_summary = None

    # Перебираем каждую доступную длину доски отдельно (не смешивая их!)
    for base_board in collection_boards:
        M = base_board['length_m']
        # Доска должна опираться на лаги (шаг 0.4). Например, 3м режется до 2.8м
        eff_M = math.floor(M / JOIST_STEP_M) * JOIST_STEP_M
        if eff_M <= 0: continue
        
        min_allowed = max(0.8, eff_M / 3.0) # Защита от коротких обрезков

        # Если доска длиннее террасы - кладем целиком без швов!
        if target_len <= eff_M:
            row_A = [round(target_len, 2)]
            row_B = [round(target_len, 2)]
        else:
            # Функция распила одного сегмента (с защитой от огрызков)
            def fill_segment(L):
                if L <= 0.01: return []
                pieces = []
                rem = L
                while rem > eff_M + 0.01:
                    pieces.append(eff_M)
                    rem = round(rem - eff_M, 2)
                if rem > 0.01:
                    pieces.append(round(rem, 2))
                
                # Если последний кусок слишком мал - сливаем с предыдущим и делим
                if len(pieces) > 1 and pieces[-1] < min_allowed:
                    deficit = math.ceil((min_allowed - pieces[-1]) / JOIST_STEP_M) * JOIST_STEP_M
                    if pieces[-2] - deficit >= min_allowed:
                        pieces[-2] = round(pieces[-2] - deficit, 2)
                        pieces[-1] = round(pieces[-1] + deficit, 2)
                    else:
                        combined = pieces[-2] + pieces[-1]
                        half = math.floor((combined / 2) / JOIST_STEP_M) * JOIST_STEP_M
                        if half <= 0: half = JOIST_STEP_M
                        pieces[-2] = round(half, 2)
                        pieces[-1] = round(combined - half, 2)
                return pieces

            # Ряд А (Шов строго по центру)
            cx = math.floor((target_len / 2) / JOIST_STEP_M) * JOIST_STEP_M
            row_A = fill_segment(cx) + fill_segment(round(target_len - cx, 2))
            
            # Ряд Б (Целая доска по центру)
            left_x = math.floor(((target_len - eff_M) / 2) / JOIST_STEP_M) * JOIST_STEP_M
            if left_x < 0: left_x = 0
            right_x = left_x + eff_M
            if right_x > target_len: right_x = target_len
            row_B = fill_segment(left_x) + fill_segment(round(right_x - left_x, 2)) + fill_segment(round(target_len - right_x, 2))

        # Формируем матрицу
        layout_matrix = []
        joints = set()
        for r in range(rows_count):
            current_row = row_A if r % 2 == 0 else row_B
            layout_matrix.append(current_row)
            jx = 0
            for p in current_row[:-1]:
                jx = round(jx + p, 2)
                joints.add(jx)

        # Оптимизация обрезков ТОЛЬКО ИЗ ВЫБРАННОЙ ДЛИНЫ (без солянки)
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
                
        qty = len(bins)
        total_cost = qty * base_board['board_cost']
        
        summary = {base_board['name']: {"qty": qty, "sum": total_cost, "unit": base_board['unit']}}

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

# Гениальный расчет раскладки
layout_matrix, best_joints, board_totals = get_best_symmetric_layout(board_len_axis, board_row_axis, eff_w, collection_boards)

# Расчет подсистемы
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

# Таблицы
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
                    ax.add_patch(patches.Rectangle((x, y), w, eff_w*0.8, color='#8d6e63', ec='black', lw=0.5))
                    x += w
        else:
            for r, row_pieces in enumerate(layout_matrix):
                x, y = r * eff_w, 0
                for w in row_pieces:
                    ax.add_patch(patches.Rectangle((x, y), eff_w*0.8, w, color='#8d6e63', ec='black', lw=0.5))
                    y += w
                    
        ax.text(length/2, -0.4, f"Длина фасада: {int(length*1000)} мм", ha='center', fontweight='bold', fontsize=10)
        ax.text(-0.6, width/2, f"Глубина: {int(width*1000)} мм", va='center', rotation=90, fontweight='bold', fontsize=10)

    elif mode == "frame":
        if "Вдоль" in direction_choice:
            for i in range(joist_count_base): 
                cx = min(i * JOIST_STEP_M, length); ax.plot([cx, cx], [0, width], color='blue', lw=1, alpha=0.3)
                if i == 0: ax.text(JOIST_STEP_M/2, width*0.12, f"{int(JOIST_STEP_M*1000)} мм", color='blue', ha='center', fontsize=9)
            for jx in best_joints:
                ax.plot([jx-0.02, jx-0.02], [0, width], color='c', lw=1.5, alpha=0.9)
                ax.plot([jx+0.02, jx+0.02], [0, width], color='c', lw=1.5, alpha=0.9)
            if frame_choice:
                for j in range(pc):
                    cy = j * step_y; ax.plot([0, length], [cy, cy], color='red', lw=3)
                    ax.text(0.1, cy+0.05, "Труба 80х80", color='red', fontsize=9, fontweight='bold')
        else:
            for i in range(joist_count_base): 
                cy = min(i * JOIST_STEP_M, width); ax.plot([0, length], [cy, cy], color='blue', lw=1, alpha=0.3)
                if i == 0: ax.text(length*0.12, JOIST_STEP_M/2, f"{int(JOIST_STEP_M*1000)} мм", color='blue', va='center', fontsize=9)
            for jy in best_joints:
                ax.plot([0, length], [jy-0.02, jy-0.02], color='c', lw=1.5, alpha=0.9)
                ax.plot([0, length], [jy+0.02, jy+0.02], color='c', lw=1.5, alpha=0.9)
            if frame_choice:
                for i in range(pr):
                    cx = i * step_x; ax.plot([cx, cx], [0, width], color='red', lw=3)
                    ax.text(cx+0.05, 0.1, "Труба 80х80", color='red', fontsize=9, fontweight='bold', rotation=90)
                    
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
    pdf = FPDF()
    try: pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True); pdf.set_font('DejaVu', '', 12)
    except: pdf.set_font('Arial', '', 12)
    
    pdf.add_page(); pdf.cell(200, 10, txt="Смета и чертежи на устройство террасы", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Клиент: {client_name} | Габариты: {int(length*1000)}x{int(width*1000)} мм", ln=True, align='L'); pdf.ln(5)
    
    pdf.set_fill_color(235, 235, 235)
    pdf.cell(110, 10, "Материалы", 1, 0, 'L', True); pdf.cell(30, 10, "Кол-во", 1, 0, 'C', True); pdf.cell(50, 10, "Сумма", 1, 1, 'C', True)
    for r in mat_data:
        short_name = str(r["Позиция"])[:45] + "..." if len(str(r["Позиция"])) > 45 else str(r["Позиция"])
        pdf.cell(110, 10, short_name, 1); pdf.cell(30, 10, str(r["Кол-во"]), 1, 0, 'C'); pdf.cell(50, 10, f"{r['Сумма']:,.0f} р.", 1, 1, 'R')
        
    pdf.ln(5); pdf.cell(140, 10, "Строительно-монтажные работы", 1, 0, 'L', True); pdf.cell(50, 10, "Сумма", 1, 1, 'C', True)
    for r in work_data:
        pdf.cell(140, 10, str(r["Позиция"]), 1); pdf.cell(50, 10, f"{r['Сумма']:,.0f} р.", 1, 1, 'R')
    
    pdf.ln(5); pdf.set_font('DejaVu', '', 14); pdf.cell(190, 10, txt=f"ИТОГО: {grand_total:,.0f} руб.", ln=True, align='R')

    for m, t in [("board", f"Настил: Симметрия (А-Б-А-Б), {direction_choice}"), ("frame", "Схема подсистемы (показаны парные лаги)"), ("piles", "Свайное поле")]:
        if m == "piles" and piles == 0: continue
        pdf.add_page(); pdf.cell(200, 10, t, ln=True, align='C'); pdf.image(get_plot(m), x=15, y=30, w=180)
    return bytes(pdf.output())

# --- 7. UI ---
st.markdown(f"<h2 style='text-align: center; color: #1b5e20;'>Итоговая стоимость: {grand_total:,.0f} руб.</h2>", unsafe_allow_html=True)
colA, colB = st.columns(2)
with colA: st.markdown("#### 🪵 Смета материалов"); st.table(mat_data)
with colB: st.markdown("#### ⚒️ Смета работ"); st.table(work_data)
st.divider()
col_dl1, col_dl2, col_dl3 = st.columns([1, 2, 1])
with col_dl2: st.download_button("📥 СКАЧАТЬ ПОЛНЫЙ ПРОЕКТ (PDF)", data=create_pdf(), file_name=f"Terrasa_{client_name}.pdf", mime="application/pdf", use_container_width=True)
st.divider()
st.subheader("📐 Технические схемы (Размеры в мм)")
t1, t2, t3 = st.tabs(["Вид настила", "Металлокаркас", "Свайное поле"])
with t1: st.image(get_plot("board"), caption="Строгая симметрия без огрызков. Все торцы опираются на лаги.")
with t2: st.image(get_plot("frame"), caption="Голубые линии — парные лаги под каждый стык.")
with t3: 
    if piles > 0: st.image(get_plot("piles"))
    else: st.info("Основание — бетон, сваи не требуются.")
