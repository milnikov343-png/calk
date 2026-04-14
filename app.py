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

# --- 2. ИДЕАЛЬНАЯ СИММЕТРИЧНАЯ РАСКЛАДКА ---
def generate_symmetric_layout(length, width, eff_w, step, collection_boards):
    rows_count = math.ceil(width / eff_w)
    layout = []
    joint_xs = set()
    
    # Берем самую длинную доску в коллекции за основу
    collection_boards = sorted(collection_boards, key=lambda x: x['length_m'], reverse=True)
    main_len = collection_boards[0]['length_m']
    
    # Выравниваем длину доски и ее половину строго по лагам (шаг 400 мм)
    eff_main = math.floor(main_len / step) * step
    if eff_main == 0: eff_main = step
    
    half_shift = math.floor((eff_main / 2) / step) * step
    if half_shift == 0: half_shift = step

    for r in range(rows_count):
        pieces = []
        cx = 0
        
        # Четные ряды начинаются с целой доски, нечетные - с половинки
        first_len = eff_main if r % 2 == 0 else half_shift
        
        # Кладем первую доску
        if cx + first_len >= length:
            pieces.append(round(length - cx, 2))
            cx = length
        else:
            pieces.append(round(first_len, 2))
            cx += first_len
            joint_xs.add(round(cx, 2))
            
        # Заполняем остаток ряда целыми досками
        while cx < length:
            nxt = eff_main
            if cx + nxt >= length:
                pieces.append(round(length - cx, 2))
                cx = length
            else:
                pieces.append(round(nxt, 2))
                cx += nxt
                joint_xs.add(round(cx, 2))
                
        layout.append(pieces)
            
    return layout, joint_xs

def optimize_waste(pieces_list, collection_boards):
    # Виртуально укладываем обрезки в целые хлысты для минимизации стоимости
    boards_sorted = sorted(collection_boards, key=lambda x: x['length_m'])
    pieces_list = sorted(pieces_list, reverse=True)
    bins = []
    
    for p in pieces_list:
        placed = False
        bins.sort(key=lambda b: b['board']['length_m'] - b['used'])
        for b in bins:
            if round(b['board']['length_m'] - b['used'], 2) >= p:
                b['used'] = round(b['used'] + p, 2)
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

# --- 3. ИНТЕРФЕЙС ---
st.set_page_config(page_title="Дача 2000 | Умный Калькулятор", layout="wide")
st.title("🏗️ Профессиональный проект террасы")

col_h1, col_h2 = st.columns([8, 2])
with col_h2:
    if st.button("🔄 Обновить прайс", use_container_width=True):
        st.cache_data.clear(); st.rerun()

st.sidebar.header("1. Параметры объекта")
client_name = st.sidebar.text_input("ФИО Клиента:", "Иван Иванович")
length = st.sidebar.number_input("Длина (вдоль досок), м:", 1.0, 50.0, 7.0)
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

st.sidebar.header("3. Подсистема")
joist_choice = st.sidebar.selectbox("Лаги (60х40):", list(PIPES_JOIST.keys()))
frame_choice = st.sidebar.selectbox("Каркас (80х80):", list(PIPES_FRAME.keys())) if "Грунт" in base_type else None
steps_m = st.sidebar.number_input("Ступени (пог.м):", 0.0, 50.0, 0.0)

# --- 4. ОСНОВНЫЕ РАСЧЕТЫ ---
area = length * width

# Генерация СИММЕТРИЧНОГО настила и стыков
layout_matrix, joint_xs = generate_symmetric_layout(length, width, eff_w, JOIST_STEP_M, collection_boards)

# Сбор и упаковка обрезков в целые доски
flat_pieces = [p for row in layout_matrix for p in row]
board_totals = optimize_waste(flat_pieces, collection_boards)

# Расчет подсистемы с учетом ДВОЙНЫХ ЛАГ
extra_joists = len(joint_xs) # Каждому стыку по дополнительной лаге
j_m = math.ceil((math.ceil(length / JOIST_STEP_M) + 1 + extra_joists) * width)
j_total = j_m * round(PIPES_JOIST[joist_choice] * METAL_MARGIN)

piles = 0; f_m = 0; f_total = 0
if "Грунт" in base_type:
    pr = math.ceil(length/PILE_STEP_M) + 1; pc = math.ceil(width/PILE_STEP_M) + 1
    piles = pr * pc
    f_m = math.ceil(pc * length)
    f_total = f_m * round(PIPES_FRAME[frame_choice] * METAL_MARGIN)

clips_packs = math.ceil((width/eff_w * (math.ceil(length/JOIST_STEP_M) + extra_joists)) / 100)
clips_total = clips_packs * 2200

work_base = area * 2400; work_steps = steps_m * 5200; work_piles = piles * 3600

# Таблицы
mat_data = []
for name, data in board_totals.items():
    mat_data.append({"Позиция": name, "Кол-во": f"{data['qty']} шт", "Сумма": data['sum']})

mat_data.extend([
    {"Позиция": f"Лага {joist_choice} (с учетом усиления стыков)", "Кол-во": f"{j_m} м.п.", "Сумма": j_total},
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
        # Сетка лаг (синяя)
        for i in range(math.ceil(length / JOIST_STEP_M) + 1): 
            cx = min(i * JOIST_STEP_M, length); ax.plot([cx, cx], [0, width], color='blue', lw=1, alpha=0.3)
            if i == 0:
                ax.annotate('', xy=(JOIST_STEP_M, width*0.1), xytext=(0, width*0.1), arrowprops=dict(arrowstyle='<->', color='blue'))
                ax.text(JOIST_STEP_M/2, width*0.12, f"{int(JOIST_STEP_M*1000)} мм", color='blue', ha='center', fontsize=9)
        
        # Двойные лаги (голубые)
        for jx in joint_xs:
            ax.plot([jx-0.03, jx-0.03], [0, width], color='c', lw=1.5, alpha=0.9)
            ax.plot([jx+0.03, jx+0.03], [0, width], color='c', lw=1.5, alpha=0.9)
            
        # Несущие балки (красные)
        if frame_choice:
            for j in range(num_p_y):
                cy = j * step_y; ax.plot([0, length], [cy, cy], color='red', lw=3)
                ax.text(0.1, cy+0.05, "Труба 80х80", color='red', fontsize=9, fontweight='bold')
        ax.text(length/2, -0.3, "Синим: Сетка лаг | Голубым: Усиление стыков (Двойная лага) | Красным: Балки", color='blue', ha='center', fontsize=10)

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

    for m, t in [("board", "Монтажная схема: Симметричная раскладка"), ("frame", "Схема подсистемы (показаны двойные лаги)"), ("piles", "Свайное поле")]:
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
with t1: st.image(get_plot("board"), caption="Идеальная симметричная раскладка. Каждый стык опирается на центр лаги.")
with t2: st.image(get_plot("frame"), caption="Голубые линии — парные лаги. Они автоматически добавлены под каждый стык торцов доски.")
with t3: 
    if piles > 0: st.image(get_plot("piles"))
    else: st.info("Основание — бетон, сваи не требуются.")
