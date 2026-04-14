import streamlit as st
import math
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import io
from fpdf import FPDF
import datetime
import pandas as pd
import re
import itertools

# --- 1. ЗАГРУЗКА И УМНАЯ ГРУППИРОВКА БАЗЫ ---
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

            # Умное удаление длины из названия (например "3м", "4.0м") для создания единой коллекции
            base_name = re.sub(r'\s*\d+(\.\d+)?\s*м\b', '', raw_name, flags=re.IGNORECASE).strip()
            
            if brand not in boards: boards[brand] = {}
            if base_name not in boards[brand]: boards[brand][base_name] = []
            
            # Высчитываем цену за 1 штуку (если в базе цена за м.п., умножаем на длину)
            board_cost = price if unit.lower() == 'шт' else price * length_m

            boards[brand][base_name].append({
                "original_name": raw_name,
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

# Глобальные настройки
METAL_MARGIN = 1.15
GAP_MM = 5
JOIST_STEP_M = 0.4
PILE_STEP_M = 2.0

# --- АЛГОРИТМ РАСКРОЯ (ПОИСК ИДЕАЛЬНОЙ ДЛИНЫ) ---
def get_optimal_row_cut(target_len, available_boards):
    best_combo = None
    min_cost = float('inf')
    
    if not available_boards: return [], 0
    
    # Сортируем доски по длине (от больших к меньшим)
    available_boards = sorted(available_boards, key=lambda x: x['length_m'], reverse=True)
    min_len = min(b['length_m'] for b in available_boards)
    if min_len <= 0: return [], 0
    
    max_boards = math.ceil(target_len / min_len)
    
    # Перебираем все возможные комбинации досок, чтобы закрыть 1 ряд
    for num in range(1, max_boards + 1):
        for combo in itertools.combinations_with_replacement(available_boards, num):
            total_len = sum(b['length_m'] for b in combo)
            if total_len >= target_len:
                total_cost = sum(b['board_cost'] for b in combo)
                if total_cost < min_cost:
                    min_cost = total_cost
                    best_combo = combo
                    
    return best_combo, min_cost

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

st.sidebar.header("2. Выбор коллекции (Авто-длина)")
brand_choice = st.sidebar.selectbox("Бренд:", list(PARSED_BOARDS.keys()))

if PARSED_BOARDS[brand_choice]:
    # Теперь мы выбираем не конкретную доску, а Коллекцию
    collection_name = st.sidebar.selectbox("Коллекция:", list(PARSED_BOARDS[brand_choice].keys()))
    collection_boards = PARSED_BOARDS[brand_choice][collection_name]
    eff_w = (collection_boards[0]["width_mm"] + GAP_MM) / 1000
else:
    st.stop()

st.sidebar.header("3. Подсистема")
joist_choice = st.sidebar.selectbox("Лаги (60х40):", list(PIPES_JOIST.keys()))
frame_choice = st.sidebar.selectbox("Каркас (80х80):", list(PIPES_FRAME.keys())) if "Грунт" in base_type else None
steps_m = st.sidebar.number_input("Ступени (пог.м):", 0.0, 50.0, 0.0)

# --- 3. РАСЧЕТЫ С АВТОМАТИЗАЦИЕЙ ---
area = length * width
rows = math.ceil(width / eff_w)

# Ищем оптимальный раскрой для 1 ряда
best_row_combo, row_cost = get_optimal_row_cut(length, collection_boards)

# Считаем общее количество нужных досок
board_totals = {}
for b in best_row_combo:
    name = b['original_name']
    if name not in board_totals:
        board_totals[name] = {"qty": 0, "sum": 0, "price": b['price'], "unit": b['unit']}
    board_totals[name]["qty"] += rows
    board_totals[name]["sum"] += (rows * b['board_cost'])

b_total = sum(data["sum"] for data in board_totals.values())

# Подсистема
j_rows = math.ceil(length / JOIST_STEP_M) + 1
j_m = math.ceil(j_rows * width)
j_total = j_m * round(PIPES_JOIST[joist_choice] * METAL_MARGIN)

piles = 0; f_m = 0; f_total = 0
if "Грунт" in base_type:
    pr = math.ceil(length/PILE_STEP_M) + 1; pc = math.ceil(width/PILE_STEP_M) + 1
    piles = pr * pc
    f_m = math.ceil(pc * length)
    f_total = f_m * round(PIPES_FRAME[frame_choice] * METAL_MARGIN)

clips_packs = math.ceil((area * 22) / 100)
clips_total = clips_packs * 2200

work_base = area * 2400; work_steps = steps_m * 5200; work_piles = piles * 3600

# Формируем динамическую таблицу материалов (строк досок может быть несколько!)
mat_data = []
for name, data in board_totals.items():
    mat_data.append({"Позиция": name, "Кол-во": f"{data['qty']} шт", "Сумма": data['sum']})

mat_data.extend([
    {"Позиция": f"Лага {joist_choice}", "Кол-во": f"{j_m} м.п.", "Сумма": j_total},
    {"Позиция": "Кляймеры (уп. 100 шт)", "Кол-во": f"{clips_packs} уп.", "Сумма": clips_total}
])
if frame_choice: mat_data.insert(len(board_totals), {"Позиция": f"Каркас {frame_choice}", "Кол-во": f"{f_m} м.п.", "Сумма": f_total})

work_data = [{"Позиция": "Монтаж настила", "Сумма": work_base}]
if steps_m > 0: work_data.append({"Позиция": "Монтаж ступеней", "Сумма": work_steps})
if piles > 0: work_data.append({"Позиция": f"Монтаж свай ({piles} шт)", "Сумма": work_piles})

grand_total = sum(item["Сумма"] for item in mat_data) + sum(item["Сумма"] for item in work_data)

# --- 4. ЧЕРТЕЖИ ---
def get_plot(mode):
    fig, ax = plt.subplots(figsize=(10, 6))
    num_p_x = math.ceil(length/PILE_STEP_M) + 1; num_p_y = math.ceil(width/PILE_STEP_M) + 1
    step_x = length / (num_p_x - 1) if num_p_x > 1 else length
    step_y = width / (num_p_y - 1) if num_p_y > 1 else width

    if mode == "board":
        row_lengths = [b['length_m'] for b in best_row_combo]
        for r in range(rows):
            y, x = r * eff_w, 0
            # Создаем шахматку, переворачивая комбинацию досок каждый второй ряд
            current_lengths = row_lengths[::-1] if r % 2 != 0 else row_lengths
            
            for bl in current_lengths:
                if x >= length: break
                w = min(bl, length - x)
                ax.add_patch(patches.Rectangle((x, y), w, eff_w*0.8, color='#8d6e63', ec='black', lw=0.5))
                x += bl
        ax.text(length/2, -0.4, f"Длина: {int(length*1000)} мм", ha='center', fontweight='bold')
        ax.text(-0.6, width/2, f"Ширина: {int(width*1000)} мм", va='center', rotation=90, fontweight='bold')

    elif mode == "frame":
        for i in range(j_rows): 
            cx = min(i * JOIST_STEP_M, length)
            ax.plot([cx, cx], [0, width], color='blue', lw=1, alpha=0.4)
        if frame_choice:
            for j in range(num_p_y):
                cy = j * step_y; ax.plot([0, length], [cy, cy], color='red', lw=3)
        ax.text(length/2, -0.3, "Синим: Лаги 60х40, Красным: Балки 80х80", color='blue', ha='center')

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

    for m, t in [("board", "Схема настила"), ("frame", "Схема каркаса"), ("piles", "Свайное поле")]:
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
with t1: st.image(get_plot("board"))
with t2: st.image(get_plot("frame"))
with t3: 
    if piles > 0: st.image(get_plot("piles"))
    else: st.info("Основание — бетон, сваи не требуются.")
