import streamlit as st
import math
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import io
from fpdf import FPDF
import datetime
import requests
from bs4 import BeautifulSoup
import re

# --- 1. УМНЫЙ ПАРСЕР САЙТА DACHA2000.RU ---
@st.cache_data(ttl=43200) # Кэшируем цены на 12 часов, чтобы сайт работал быстро
def load_price_data():
    boards = {}
    pipes_joist = {"Труба 60х40х2": 219, "Труба 60х40х3": 290}
    pipes_frame = {"Труба 80х80х2": 403, "Труба 80х80х3": 475}

    try:
        # Робот стучится на страницу каталога (берем сразу много товаров)
        url = "https://dacha2000.ru/terrasnaya-doska?limit=500"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        resp = requests.get(url, headers=headers, timeout=15)

        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            units = soup.find_all('div', class_='unit')

            for unit in units:
                name_meta = unit.find('meta', itemprop='name')
                price_meta = unit.find('meta', itemprop='price')
                price_div = unit.find('div', class_='unit_price')

                if name_meta and price_meta and price_div:
                    raw_name = name_meta['content']
                    clean_name = raw_name.replace('Террасная доска ', '').replace('Террасная доска', '').strip()
                    price_val = float(price_meta['content'])
                    price_text = price_div.text.strip().lower()

                    # 1. Определение единицы измерения
                    unit_type = "шт" if "шт" in price_text else "м.п."

                    # 2. Определение производителя
                    manufacturer = "Другие бренды"
                    brands = ["LikeWood", "Woodvex", "Террапол", "RusDecking", "Polivan Group", "CM Decking", "TimberTex", "Deckron", "TalverWood", "AIWOOD"]
                    for b in brands:
                        if b.lower() in clean_name.lower():
                            manufacturer = b
                            break

                    # 3. Умный поиск ширины доски (ищем число от 130 до 200)
                    width_mm = 140 # По умолчанию
                    match_w = re.search(r'(1[3-9]\d|200)', clean_name)
                    if match_w: width_mm = int(match_w.group(1))

                    # 4. Умный поиск длины
                    length_m = 3.0 # По умолчанию
                    match_l = re.search(r'(2900|3000|4000|5800|6000)', clean_name)
                    if match_l:
                        length_m = int(match_l.group(1)) / 1000.0
                    elif "3м" in clean_name or "3 м" in clean_name: length_m = 3.0
                    elif "4м" in clean_name or "4 м" in clean_name: length_m = 4.0

                    if manufacturer not in boards:
                        boards[manufacturer] = {}

                    # Сохраняем товар в базу
                    boards[manufacturer][clean_name] = {
                        "price": price_val,
                        "unit": unit_type,
                        "width_mm": width_mm,
                        "length_m": length_m
                    }
    except Exception as e:
        print(f"Парсер не смог загрузить данные: {e}")

    # Fallback-база (если парсер вдруг не сработал из-за защиты сайта)
    if not boards:
        boards = {
            "Резервная база (Сайт недоступен)": {
                "LikeWood Вельвет 140x22 4м": {"price": 438, "unit": "м.п.", "width_mm": 140, "length_m": 4.0},
                "Woodvex Select 146x22 3м": {"price": 2054, "unit": "шт", "width_mm": 146, "length_m": 3.0}
            }
        }

    return boards, pipes_joist, pipes_frame

# Запуск парсера
PARSED_BOARDS, PIPES_JOIST, PIPES_FRAME = load_price_data()

METAL_MARGIN = 1.15
GAP_MM = 5
JOIST_STEP_M = 0.4
PILE_STEP_M = 2.0

# --- 2. ИНТЕРФЕЙС ---
st.set_page_config(page_title="Дача 2000 | Умный Калькулятор", layout="wide")
st.title("🏗️ Проектный расчет террасы")

# Кнопка принудительного обновления
col_btn1, col_btn2 = st.columns([8, 2])
with col_btn2:
    if st.button("🔄 Обновить прайс с сайта", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.sidebar.header("1. Размеры объекта")
client_name = st.sidebar.text_input("ФИО Клиента:", "Иван Иванович")
length = st.sidebar.number_input("Длина (м):", 1.0, 30.0, 6.0)
width = st.sidebar.number_input("Ширина (м):", 1.0, 30.0, 4.0)
base_type = st.sidebar.radio("Основание:", ["Грунт (Сваи)", "Бетон"])

# --- ИНТЕРФЕЙС ВЫБОРА ТОВАРА ---
st.sidebar.header("2. Выбор доски (с сайта)")
manufacturer = st.sidebar.selectbox("Бренд:", list(PARSED_BOARDS.keys()))

# Если у бренда есть товары, показываем их
if PARSED_BOARDS[manufacturer]:
    board_name_full = st.sidebar.selectbox("Наименование:", list(PARSED_BOARDS[manufacturer].keys()))
    b_info = PARSED_BOARDS[manufacturer][board_name_full]
else:
    st.sidebar.warning("Нет товаров в этой категории")
    st.stop()

st.sidebar.header("3. Подсистема")
joist_choice = st.sidebar.selectbox("Лаги (60х40):", list(PIPES_JOIST.keys()))
frame_choice = st.sidebar.selectbox("Каркас (80х80):", list(PIPES_FRAME.keys())) if "Грунт" in base_type else None
steps_m = st.sidebar.number_input("Ступени (пог.м):", 0.0, 30.0, 3.0)

# --- 3. РАСЧЕТЫ ---
area = length * width
eff_w = (b_info["width_mm"] + GAP_MM) / 1000
rows = math.ceil(width / eff_w)
total_bm = rows * length
b_qty = math.ceil(total_bm) if b_info["unit"] == "м.п." else math.ceil(total_bm / b_info["length_m"])
b_total = b_qty * b_info["price"]

j_rows = math.ceil(length / JOIST_STEP_M) + 1
j_m = math.ceil(j_rows * width)
j_price = round(PIPES_JOIST[joist_choice] * METAL_MARGIN)
j_total = j_m * j_price

piles = 0; f_m = 0; f_total = 0
if "Грунт" in base_type:
    pr, pc = math.ceil(length/PILE_STEP_M)+1, math.ceil(width/PILE_STEP_M)+1
    piles = pr * pc
    f_m = math.ceil(pc * length)
    f_total = f_m * round(PIPES_FRAME[frame_choice] * METAL_MARGIN)

clips_packs = math.ceil((j_rows * rows) / 100)
clips_total = clips_packs * 2000

mat_table = [
    {"Наименование": board_name_full, "Кол-во": f"{b_qty} {b_info['unit']}", "Сумма": b_total},
    {"Наименование": f"Лага {joist_choice}", "Кол-во": f"{j_m} м.п.", "Сумма": j_total},
    {"Наименование": "Кляймеры (уп. 100шт)", "Кол-во": f"{clips_packs} уп", "Сумма": clips_total}
]
if frame_choice: mat_table.insert(1, {"Наименование": f"Каркас {frame_choice}", "Кол-во": f"{f_m} м.п.", "Сумма": f_total})

work_table = [{"Наименование": "Монтаж настила и лаг", "Сумма": area * 2400}]
if steps_m > 0: work_table.append({"Наименование": "Монтаж ступеней", "Сумма": steps_m * 5200})
if piles > 0: work_table.append({"Наименование": f"Установка свай ({piles} шт)", "Сумма": piles * 3600})

grand_total = sum(item["Сумма"] for item in mat_table) + sum(item["Сумма"] for item in work_table)

# --- 4. ФУНКЦИИ РИСОВАНИЯ ---
def get_plot(mode):
    fig, ax = plt.subplots(figsize=(10, 6))
    if mode == "board":
        bl = b_info["length_m"]
        for r in range(rows):
            y, x = r * eff_w, 0
            if r % 2 != 0:
                w = min(bl/2, length); ax.add_patch(patches.Rectangle((0, y), w, eff_w*0.8, color='#8d6e63', ec='black', lw=0.3))
                x = w
            while x < length:
                w = min(bl, length-x); ax.add_patch(patches.Rectangle((x, y), w, eff_w*0.8, color='#8d6e63', ec='black', lw=0.5))
                x += bl
        ax.text(length/2, -0.4, f"Длина: {int(length*1000)} мм", ha='center', fontweight='bold', fontsize=10)
        ax.text(-0.6, width/2, f"Ширина: {int(width*1000)} мм", va='center', rotation=90, fontweight='bold', fontsize=10)

    elif mode == "frame":
        for i in range(j_rows): 
            cx = min(i*JOIST_STEP_M, length)
            ax.plot([cx, cx], [0, width], color='blue', lw=1, alpha=0.5)
            if i == 0:
                ax.annotate('', xy=(JOIST_STEP_M, width*0.1), xytext=(0, width*0.1), arrowprops=dict(arrowstyle='<->', color='blue'))
                ax.text(JOIST_STEP_M/2, width*0.12, f"{int(JOIST_STEP_M*1000)} мм", color='blue', ha='center', fontsize=9)
        if frame_choice:
            num_f = math.ceil(width/PILE_STEP_M)+1
            for j in range(num_f): 
                cy = min(j*PILE_STEP_M, width)
                ax.plot([0, length], [cy, cy], color='red', lw=2.5)
                ax.text(0.1, cy+0.05, "Труба 80х80", color='red', fontsize=9, fontweight='bold')
        ax.text(length-1.5, -0.3, "Лаги 60х40", color='blue', fontsize=11)

    elif mode == "piles":
        pr, pc = math.ceil(length/PILE_STEP_M)+1, math.ceil(width/PILE_STEP_M)+1
        sp_x = length/(pr-1) if pr>1 else length
        sp_y = width/(pc-1) if pc>1 else width
        for i in range(pr):
            for j in range(pc):
                px, py = i*sp_x, j*sp_y
                ax.add_patch(patches.Circle((px, py), 0.1, color='black'))
                if i < pr-1 and j == 0: ax.text(px + sp_x/2, py-0.4, f"{int(sp_x*1000)} мм", ha='center', fontsize=9)
                if j < pc-1 and i == 0: ax.text(px-0.8, py + sp_y/2, f"{int(sp_y*1000)} мм", va='center', rotation=90, fontsize=9)

    ax.set_xlim(-1.0, length+0.5); ax.set_ylim(-1.0, width+0.5); ax.set_aspect('equal'); plt.axis('off')
    buf = io.BytesIO(); plt.savefig(buf, format='png', bbox_inches='tight', dpi=150); plt.close(fig); buf.seek(0)
    return buf

# --- 5. ГЕНЕРАЦИЯ PDF ---
def create_pdf():
    pdf = FPDF()
    try: pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True); pdf.set_font('DejaVu', '', 12)
    except: pdf.set_font('Arial', '', 12)
    
    pdf.add_page()
    pdf.cell(200, 10, txt="Смета и чертежи на устройство террасы", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Клиент: {client_name} | Габариты: {int(length*1000)}x{int(width*1000)} мм", ln=True, align='L')
    pdf.ln(5)
    
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(110, 10, "Наименование", 1, 0, 'L', True); pdf.cell(40, 10, "Кол-во", 1, 0, 'C', True); pdf.cell(40, 10, "Сумма", 1, 1, 'C', True)
    for row in mat_table:
        # Обрезаем длинные названия с сайта, чтобы они поместились в таблицу PDF
        short_name = str(row["Наименование"])[:45] + "..." if len(str(row["Наименование"])) > 45 else str(row["Наименование"])
        pdf.cell(110, 10, short_name, 1); pdf.cell(40, 10, str(row["Кол-во"]), 1, 0, 'C'); pdf.cell(40, 10, f"{row['Сумма']:,.0f} р.", 1, 1, 'R')
        
    pdf.ln(5)
    pdf.cell(150, 10, "Строительно-монтажные работы", 1, 0, 'L', True); pdf.cell(40, 10, "Сумма", 1, 1, 'C', True)
    for row in work_table:
        pdf.cell(150, 10, str(row["Наименование"]), 1); pdf.cell(40, 10, f"{row['Сумма']:,.0f} р.", 1, 1, 'R')
    
    pdf.ln(5); pdf.set_font('DejaVu', '', 14); pdf.cell(190, 10, txt=f"ИТОГО: {grand_total:,.0f} руб.", ln=True, align='R')

    for m, title in [("board", "Раскладка настила"), ("frame", "Металлокаркас"), ("piles", "Свайное поле")]:
        if m == "piles" and piles == 0: continue
        pdf.add_page(); pdf.cell(200, 10, f"Схема: {title}", ln=True, align='C'); pdf.image(get_plot(m), x=15, y=40, w=180)
    return bytes(pdf.output())

# --- 6. UI ---
st.markdown(f"<h2 style='text-align: center; color: #2e7d32;'>Итого: {grand_total:,.0f} руб.</h2>", unsafe_allow_html=True)
colA, colB = st.columns(2)
with colA: st.markdown("#### 🧱 Материалы"); st.dataframe(mat_table, use_container_width=True, hide_index=True)
with colB: st.markdown("#### 🛠️ Работы"); st.dataframe(work_table, use_container_width=True, hide_index=True)
st.divider()
col1, col2, col3 = st.columns([1, 2, 1])
with col2: st.download_button("📥 СКАЧАТЬ ПРОЕКТ (PDF)", data=create_pdf(), file_name=f"Project_{client_name}.pdf", mime="application/pdf", use_container_width=True)
st.divider()
st.subheader("📐 Техническая визуализация (ММ)")
t1, t2, t3 = st.tabs(["Настил", "Каркас", "Сваи"])
with t1: st.image(get_plot("board"))
with t2: st.image(get_plot("frame"))
with t3: 
    if piles > 0: st.image(get_plot("piles"))
    else: st.write("Фундамент не требуется.")
