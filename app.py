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

            # Очищаем имя от размеров для группировки длин в единую коллекцию
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

# Константы
METAL_MARGIN = 1.15
GAP_MM = 5
JOIST_STEP_M = 0.4
PILE_STEP_M = 2.0

# --- АЛГОРИТМ РАСКРОЯ И ОПТИМИЗАЦИИ ОБРЕЗКОВ ---
def generate_deck_layout(length, width, eff_w, step, pattern, collection_boards):
    rows_count = math.ceil(width / eff_w)
    layout = []
    joint_xs = set()
    
    # Ищем самую длинную доску в коллекции, чтобы задать ритм
    main_len = max([b['length_m'] for b in collection_boards])
    
    # Минимальный кусок = 1/3 доски, округленный до шага лаг (400 мм)
    min_piece = max(step, round((main_len / 3) / step) * step)

    for r in range(rows_count):
        if pattern == "Палубная (сдвиг 1/3)":
            offset = (r % 3) * min_piece
        else: # Симметричная (сдвиг 1/2)
            half_shift = round((main_len / 2) / step) * step
            offset = 0 if r % 2 == 0 else half_shift
            
        pieces = []
        rem = length
        
        # Высчитываем первый кусок с учетом сдвига
        first = main_len - offset
        if first > rem: first = rem
        first = math.floor(first / step) * step # Привязываем стык строго к лаге
        if first == 0 and rem > 0: first = min(step, rem)
        
        pieces.append(first)
        rem -= first
        
        # Заполняем середину целыми досками
        while rem > 0.01:
            nxt = min(main_len, rem)
            nxt = math.floor(nxt / step) * step
            if nxt == 0: nxt = rem
            pieces.append(nxt)
            rem -= nxt
            
        # Защита от коротких "огрызков" по краям
        if len(pieces) > 1 and pieces[-1] < min_piece:
            shortfall = math.ceil((min_piece - pieces[-1]) / step) * step
            if pieces[-2] > min_piece + shortfall:
                pieces[-2] -= shortfall
                pieces[-1] += shortfall
        
        row_clean = [round(p, 2) for p in pieces if p > 0.01]
        layout.append(row_clean)
        
        # Запоминаем координаты всех стыков для двойных лаг
        cx = 0
        for p in row_clean[:-1]:
            cx += p
            joint_xs.add(round(cx, 2))
            
    return layout, joint_xs

def optimize_waste(pieces_list, collection_boards):
    # Сортируем доски из коллекции по длине (от меньшей к большей)
    boards_sorted = sorted(collection_boards, key=lambda x: x['length_m'])
    pieces_list = sorted(pieces_list, reverse=True)
    bins = []
    
    # Распределяем обрезки по целым доскам (алгоритм First Fit Decreasing)
    for p in pieces_list:
        placed = False
        bins.sort(key=lambda b: b['board']['length_m'] - b['used'])
        for b in bins:
            if b['board']['length_m'] - b['used'] >= p:
                b['used'] += p
                placed = True
                break
        if not placed:
            chosen = next((b for b in boards_sorted if b['length_m'] >= p), boards_sorted[-1])
            bins.append({"board": chosen, "used": p})
            
    summary = {}
    for b in bins:
        name = b['board']['name']
        if name not in summary: summary[name] = {"qty": 0, "sum": 0, "unit": b['board']['unit']}
        summary[name]["qty"] += 1
        summary[name]["sum"] += b['board']['board_cost']
    return summary

# --- 2. ИНТЕРФЕЙС ---
st.set_page_config(page_title="Дача 2000 | Умный Калькулятор", layout="wide")
st.title("🏗️ Профессиональный расчет террасы")

col_h1, col_h2 = st.columns([8, 2])
with col_h2:
    if st.button("🔄 Обновить прайс", use_container_width=True):
        st.cache_data.clear(); st.rerun()

st.sidebar.header("1. Параметры объекта")
client_name = st.sidebar.text_input("ФИО Клиента:", "Иван Иванович")
length = st.sidebar.number_input("Длина (вдоль досок), м:", 1.0, 50.0, 6.0)
width = st.sidebar.number_input("Ширина террасы, м:", 1.0, 50.0, 4.0)
base_type = st.sidebar.radio("Основание:", ["Грунт (Сваи)", "Бетон"])

st.sidebar.header("2. Выбор коллекции")
brand_choice = st.sidebar.selectbox("Бренд:", list(PARSED_BOARDS.keys()))
if PARSED_BOARDS[brand_choice]:
    collection_name = st.sidebar.selectbox("Коллекция:", list(PARSED_BOARDS[brand_choice].keys()))
    collection_boards = PARSED_BOARDS[brand_choice][collection_name]
    eff_w = (collection_boards[0]["width_mm"] + GAP_MM) / 1000
else:
    st.stop()

pattern_choice = st.sidebar.radio("Раскладка доски:", ["Палубная (сдвиг 1/3)", "Симметричная (сдвиг 1/2)"])

st.sidebar.header("3. Подсистема")
joist_choice = st.sidebar.selectbox("Лаги (60х40):", list(PIPES_JOIST.keys()))
frame_choice = st.sidebar.selectbox("Каркас (80х80):", list(PIPES_FRAME.keys())) if "Грунт" in base_type else None
steps_m = st.sidebar.number_input("Ступени (пог.м):", 0.0, 50.0, 0.0)

# --- 3. РАСЧЕТЫ С АВТОМАТИЗАЦИЕЙ ---
area = length * width

# 1. Генерируем раскладку и находим координаты двойных лаг
layout_matrix, joint_xs = generate_deck_layout(length, width, eff_w, JOIST_STEP_M, pattern_choice, collection_boards)

# 2. Собираем все нарезанные куски и пакуем их в целые доски
flat_pieces = [p for row in layout_matrix for p in row]
board_totals = optimize_waste(flat_pieces, collection_boards)

# 3. Расчет подсистемы (УЧИТЫВАЕМ ДВОЙНЫЕ ЛАГИ!)
extra_joists = len(joint_xs) # Каждому стыку по дополнительной лаге!
j_m = math.ceil((math.ceil(length / JOIST_STEP_M) + 1 + extra_joists) * width)
j_total = j_m * round(PIPES_JOIST[joist_choice] * METAL_MARGIN)

piles = 0; f_m = 0; f_total = 0
if "Грунт" in base_type:
    pr = math.ceil(length/PILE_STEP_M) + 1; pc = math.ceil(width/PILE_STEP_M) + 1
    piles = pr * pc
    f_m = math.ceil(pc * length)
    f_total = f_m * round(PIPES_FRAME[frame_choice] * METAL_MARGIN)

clips_packs = math.ceil((width/eff_w * (length/JOIST_STEP_M + extra_joists)) / 100)
clips_total = clips_packs * 2200

work_base = area * 2400; work_steps = steps_m * 5200; work_piles = piles * 3600

# Формируем таблицы
mat_data = []
for name, data in board_totals.items():
    mat_data.append({"Позиция": name, "Кол-во": f"{data['qty']} шт", "Сумма": data['sum']})

mat_data.extend([
    {"Позиция": f"Лага {joist_choice}", "Кол-во": f"{j_m} м.п.", "Сумма": j_total},
    {"Позиция": "Кляймеры (уп. 100 шт)", "Кол-во": f"{clips_packs} уп.", "Сумма": clips_total}
])
if frame_choice: mat_data.insert(len(board_totals)+1, {"Позиция": f"Каркас {frame_choice}", "Кол-во": f"{f_m} м.п.", "Сумма": f_total})

work_data = [{"Позиция": "Монтаж настила", "Сумма": work_base}]
if steps_m > 0: work_data.append({"Позиция": "Монтаж ступеней", "Сумма": work_steps})
if piles > 0: work_data.append({"Позиция": f"Монтаж свай ({piles} шт)", "Сумма": work_piles})

grand_total = sum(d['Сумма'] for d in mat_data) + sum(d['Сумма'] for d in work_data)

# --- 4. ЧЕРТЕЖИ ---
def get_plot(mode):
    fig, ax = plt.subplots(figsize=(10, 6))
    num_p_x = math.ceil(length/PILE_STEP_M) + 1; num_p_y = math.ceil(width/PILE_STEP_M) + 1
    step_x = length / (num_p_x - 1) if num_p_x > 1 else length
    step_y = width / (num_p_y - 1) if num_p_y > 1 else width

    if mode == "board":
        for r, row_pieces in enumerate(layout_matrix):
            y, x = r * eff_w, 0
            for w in row_pieces:
                ax.add_patch(patches.Rectangle((x, y), w, eff_w*0.8, color='#8d6e63', ec='black', lw=0.5))
                x += w
        ax.text(length/2, -0.4, f"Длина: {int(length*1000)} мм", ha='center', fontweight='bold', fontsize=10)
        ax.text(-0.6, width/2, f"Ширина: {int(width*1000)} мм", va='center', rotation=90, fontweight='bold', fontsize=10)

    elif mode == "frame":
        # 1. Стандартная сетка лаг (синяя)
        for i in range(math.ceil(length / JOIST_STEP_M) + 1): 
            cx = min(i * JOIST_STEP_M, length); ax.plot([cx, cx], [0, width], color='blue', lw=1, alpha=0.4)
            if i == 0:
                ax.annotate('', xy=(JOIST_STEP_M, width*0.1), xytext=(0, width*0.1), arrowprops=dict(arrowstyle='<->', color='blue'))
                ax.text(JOIST_STEP_M/2, width*0.12, f"{int(JOIST_STEP_M*1000)} мм", color='blue', ha='center', fontsize=9)
        
        # 2. ДВОЙНЫЕ ЛАГИ ПОД СТЫКАМИ (голубые, сдвиг +50мм)
        for jx in joint_xs:
            ax.plot([jx+0.05, jx+0.05], [0, width], color='cyan', lw=1.5, alpha=0.9)
            
        # 3. Несущие балки (красные)
        if frame_choice:
            for j in range(num_p_y):
                cy = j * step_y; ax.plot([0, length], [cy, cy], color='red', lw=3)
                ax.text(0.1, cy+0.05, "Труба 80х80", color='red', fontsize=9, fontweight='bold')
        ax.text(length/2, -0.3, "Синим: Сетка лаг. Голубым: Двойные лаги (усиление стыков). Красным: Балки", color='blue', ha='center')

    elif mode == "piles":
        for i in range(num_p_x):
            for j in range(num_p_y):
                px, py = i * step_x, j * step_y
                ax.add_patch(patches.Circle((px, py), 0.15, color='black'))
                if i < num_p_x - 1 and j == 0: ax.text(px + step_x/2, py-0.4, f"{int(step_x*1000)} мм", ha='center', fontsize=9)
                if j < num_p_y - 1 and i == 0: ax.text(px-0.8, py + step_y/2, f"{int(step_y*1000)} мм", va='center', rotation=90, fontsize=9)

    ax.set_xlim(-1.0, length+1.0); ax.set_ylim(-1.2, width+0.5); ax.set_aspect('equal'); plt.axis('off')
    buf = io.BytesIO(); plt.savefig(buf, format='png', bbox_inches='tight', dpi=150); plt.close(fig); buf.seek(0)
    return buf

# --- 5. ГЕНЕРАЦИЯ PDF ---
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

    for m, t in [("board", f"Схема настила: {pattern_choice}"), ("frame", "Схема каркаса (с двойными лагами)"), ("piles", "Свайное поле")]:
        if m == "piles" and piles == 0: continue
        pdf.add_page(); pdf.cell(200, 10, t, ln=True, align='C'); pdf.image(get_plot(m), x=15, y=30, w=180)
    return bytes(pdf.output())

# --- 6. UI ---
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
with t1: st.image(get_plot("board"), caption="Каждый стык доски математически выровнен строго по центрам лаг!")
with t2: st.image(get_plot("frame"), caption="Голубые линии — это вторые (усиливающие) лаги, которые автоматически ставятся под каждый стык.")
with t3: 
    if piles > 0: st.image(get_plot("piles"))
    else: st.info("Основание — бетон, сваи не требуются.")
