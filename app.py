import streamlit as st
import math
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import io
from fpdf import FPDF
import datetime
import pandas as pd

# --- 1. ЗАГРУЗКА ДАННЫХ ИЗ ВАШЕЙ GOOGLE ТАБЛИЦЫ ---

@st.cache_data(ttl=300) # Кэш на 5 минут
def load_google_sheet():
    # Ваша ссылка на CSV экспорт
    SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRgxTJ2JPrhh_da9pEBWMoKU3iT5x0DZkzKmKrOKcJBbAos8XmYJDzJyHKvcTtAfPrcpMKDzHW4AWG6/pub?gid=0&single=true&output=csv"
    
    boards = {}
    pipes_joist = {"Труба 60х40х2": 219, "Труба 60х40х3": 290}
    pipes_frame = {"Труба 80х80х2": 403, "Труба 80х80х3": 475}

    try:
        # Читаем таблицу через pandas
        df = pd.read_csv(SHEET_URL)
        
        # Проходим по строкам и строим иерархию Бренд -> Товар
        for index, row in df.iterrows():
            brand = str(row['Бренд']).strip()
            name = str(row['Наименование']).strip()
            
            if brand not in boards:
                boards[brand] = {}
            
            boards[brand][name] = {
                "price": float(row['Цена']),
                "unit": str(row['Единица']).strip(),
                "width_mm": int(row['Ширина (мм)']),
                "length_m": float(row['Длина (м)'])
            }
    except Exception as e:
        st.error(f"Ошибка загрузки данных из таблицы: {e}")
        # Резервный вариант, чтобы приложение не падало
        boards = {"Ошибка": {"Проверьте таблицу": {"price": 0, "unit": "шт", "width_mm": 140, "length_m": 3.0}}}

    return boards, pipes_joist, pipes_frame

# Запускаем загрузку
PARSED_BOARDS, PIPES_JOIST, PIPES_FRAME = load_google_sheet()

# Глобальные настройки
METAL_MARGIN = 1.15
GAP_MM = 5
JOIST_STEP_M = 0.4
PILE_STEP_M = 2.0

# --- 2. ИНТЕРФЕЙС ---
st.set_page_config(page_title="Дача 2000 | Калькулятор террас", layout="wide")
st.title("🏗️ Профессиональный расчет террасы")

# Кнопка обновления в верхней части
col_header1, col_header2 = st.columns([7, 3])
with col_header2:
    if st.button("🔄 Обновить прайс из Google Таблицы", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.sidebar.header("1. Параметры объекта")
client_name = st.sidebar.text_input("ФИО Клиента:", "Иван Иванович")
length = st.sidebar.number_input("Длина террасы (м):", 1.0, 50.0, 6.0)
width = st.sidebar.number_input("Ширина террасы (м):", 1.0, 50.0, 4.0)
base_type = st.sidebar.radio("Тип основания:", ["Грунт (Сваи)", "Бетонное основание"])

st.sidebar.header("2. Выбор материалов")
# Каскадный выбор: Бренд -> Товар
brand_choice = st.sidebar.selectbox("Выберите производителя (Бренд):", list(PARSED_BOARDS.keys()))
board_name = st.sidebar.selectbox("Выберите модель доски:", list(PARSED_BOARDS[brand_choice].keys()))

# Берем данные конкретной выбранной доски
b_info = PARSED_BOARDS[brand_choice][board_name]

st.sidebar.header("3. Конструкция")
joist_choice = st.sidebar.selectbox("Лаги (60х40):", list(PIPES_JOIST.keys()))
frame_choice = st.sidebar.selectbox("Несущая труба (80х80):", list(PIPES_FRAME.keys())) if "Грунт" in base_type else None
steps_m = st.sidebar.number_input("Ступени (пог.м):", 0.0, 50.0, 0.0)

# --- 3. МАТЕМАТИЧЕСКИЕ РАСЧЕТЫ ---
area = length * width
eff_w = (b_info["width_mm"] + GAP_MM) / 1000 # Эффективная ширина доски с зазором в метрах
rows = math.ceil(width / eff_w) # Количество рядов досок
total_bm = rows * length # Всего погонных метров доски

# Расчет количества (в шт или м.п.)
if b_info["unit"] == "шт":
    b_qty = math.ceil(total_bm / b_info["length_m"])
else:
    b_qty = math.ceil(total_bm)

b_total = b_qty * b_info["price"]

# Расчет лаг (поперек досок через 400 мм)
j_rows = math.ceil(length / JOIST_STEP_M) + 1
j_m = math.ceil(j_rows * width)
j_price = round(PIPES_JOIST[joist_choice] * METAL_MARGIN)
j_total = j_m * j_price

# Расчет свай и несущего каркаса (80х80)
piles = 0; f_m = 0; f_total = 0
if "Грунт" in base_type:
    # Количество свай
    pr = math.ceil(length/PILE_STEP_M) + 1
    pc = math.ceil(width/PILE_STEP_M) + 1
    piles = pr * pc
    # Метраж несущей трубы (идет вдоль досок, ложится на сваи)
    f_m = math.ceil(pc * length)
    f_total = f_m * round(PIPES_FRAME[frame_choice] * METAL_MARGIN)

# Кляймеры (из расчета 22 шт на 1 м2)
clips_packs = math.ceil((area * 22) / 100)
clips_total = clips_packs * 2200 # Цена за упаковку 100 шт

# Стоимость работ
work_base = area * 2400 # Монтаж террасы
work_steps = steps_m * 5200 # Монтаж ступеней
work_piles = piles * 3600 # Установка свай

grand_total = b_total + j_total + f_total + clips_total + work_base + work_steps + work_piles

# Формирование таблиц для экрана
mat_data = [
    {"Позиция": board_name, "Кол-во": f"{b_qty} {b_info['unit']}", "Сумма": b_total},
    {"Позиция": f"Лага {joist_choice}", "Кол-во": f"{j_m} м.п.", "Сумма": j_total},
    {"Позиция": "Кляймеры (уп. 100 шт)", "Кол-во": f"{clips_packs} уп.", "Сумма": clips_total}
]
if frame_choice: mat_data.insert(1, {"Позиция": f"Каркас {frame_choice}", "Кол-во": f"{f_m} м.п.", "Сумма": f_total})

work_data = [{"Позиция": "Монтаж настила", "Сумма": work_base}]
if steps_m > 0: work_data.append({"Позиция": "Монтаж ступеней", "Сумма": work_steps})
if piles > 0: work_data.append({"Позиция": f"Монтаж свай ({piles} шт)", "Сумма": work_piles})

# --- 4. ФУНКЦИИ ГРАФИКИ (В ММ) ---
def get_plot(mode):
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Расчетные шаги для свай и несущих балок (всегда соосно!)
    num_p_x = math.ceil(length/PILE_STEP_M) + 1
    num_p_y = math.ceil(width/PILE_STEP_M) + 1
    step_x = length / (num_p_x - 1) if num_p_x > 1 else length
    step_y = width / (num_p_y - 1) if num_p_y > 1 else width

    if mode == "board":
        bl = b_info["length_m"]
        for r in range(rows):
            y, x = r * eff_w, 0
            # Имитация разбежки (шахматки)
            if r % 2 != 0:
                offset = min(bl/2, length)
                ax.add_patch(patches.Rectangle((0, y), offset, eff_w*0.8, color='#8d6e63', ec='black', lw=0.3))
                x = offset
            while x < length:
                w = min(bl, length - x)
                ax.add_patch(patches.Rectangle((x, y), w, eff_w*0.8, color='#8d6e63', ec='black', lw=0.5))
                x += bl
        ax.text(length/2, -0.4, f"Длина: {int(length*1000)} мм", ha='center', fontweight='bold')
        ax.text(-0.6, width/2, f"Ширина: {int(width*1000)} мм", va='center', rotation=90, fontweight='bold')

    elif mode == "frame":
        # Лаги (синие)
        for i in range(j_rows):
            cx = min(i * JOIST_STEP_M, length)
            ax.plot([cx, cx], [0, width], color='blue', lw=1, alpha=0.4)
        # Несущие балки 80х80 (красные) - строго по сваям
        if frame_choice:
            for j in range(num_p_y):
                cy = j * step_y
                ax.plot([0, length], [cy, cy], color='red', lw=3)
                ax.text(0.1, cy + 0.05, "80х80", color='red', fontsize=8, fontweight='bold')
        ax.text(length-1.5, -0.3, "Синим: Лаги 60х40 (шаг 400), Красным: Балки 80х80", color='blue', fontsize=9)

    elif mode == "piles":
        for i in range(num_p_x):
            for j in range(num_p_y):
                px, py = i * step_x, j * step_y
                ax.add_patch(patches.Circle((px, py), 0.1, color='black'))
                # Осевые размеры в ММ
                if i < num_p_x - 1 and j == 0:
                    ax.text(px + step_x/2, py-0.4, f"{int(step_x*1000)} мм", ha='center', fontsize=9)
                if j < num_p_y - 1 and i == 0:
                    ax.text(px-0.8, py + step_y/2, f"{int(step_y*1000)} мм", va='center', rotation=90, fontsize=9)

    ax.set_xlim(-1.0, length+1.0); ax.set_ylim(-1.2, width+0.5); ax.set_aspect('equal'); plt.axis('off')
    buf = io.BytesIO(); plt.savefig(buf, format='png', bbox_inches='tight', dpi=150); plt.close(fig); buf.seek(0)
    return buf

# --- 5. ГЕНЕРАЦИЯ PDF ---
def create_pdf():
    pdf = FPDF()
    try: pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True); pdf.set_font('DejaVu', '', 12)
    except: pdf.set_font('Arial', '', 12)
    
    pdf.add_page()
    pdf.cell(200, 10, txt="Приложение: Расчет материалов и работ", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Клиент: {client_name} | Дата: {datetime.date.today()}", ln=True, align='L')
    pdf.ln(5)
    
    pdf.set_fill_color(235, 235, 235)
    pdf.cell(110, 10, "Материалы", 1, 0, 'L', True); pdf.cell(40, 10, "Кол-во", 1, 0, 'C', True); pdf.cell(40, 10, "Сумма", 1, 1, 'C', True)
    for r in mat_data:
        pdf.cell(110, 10, str(r["Позиция"])[:45], 1); pdf.cell(40, 10, str(r["Кол-во"]), 1, 0, 'C'); pdf.cell(40, 10, f"{r['Сумма']:,.0f} р.", 1, 1, 'R')
        
    pdf.ln(5)
    pdf.cell(150, 10, "Строительно-монтажные работы", 1, 0, 'L', True); pdf.cell(40, 10, "Сумма", 1, 1, 'C', True)
    for r in work_data:
        pdf.cell(150, 10, str(r["Позиция"]), 1); pdf.cell(40, 10, f"{r['Сумма']:,.0f} р.", 1, 1, 'R')
    
    pdf.ln(5); pdf.set_font('DejaVu', '', 14); pdf.cell(190, 10, txt=f"ИТОГО: {grand_total:,.0f} руб.", ln=True, align='R')

    # Добавляем чертежи
    for m, t in [("board", "Схема настила"), ("frame", "Схема каркаса"), ("piles", "Свайное поле")]:
        if m == "piles" and piles == 0: continue
        pdf.add_page(); pdf.cell(200, 10, t, ln=True, align='C'); pdf.image(get_plot(m), x=15, y=30, w=180)
    
    return bytes(pdf.output())

# --- 6. ЭКРАН РЕЗУЛЬТАТОВ (UI) ---
st.markdown(f"<h2 style='text-align: center; color: #1b5e20;'>Итоговая стоимость: {grand_total:,.0f} руб.</h2>", unsafe_allow_html=True)

col_tab1, col_tab2 = st.columns(2)
with col_tab1:
    st.markdown("#### 🪵 Смета материалов")
    st.table(mat_data)
with col_tab2:
    st.markdown("#### ⚒️ Смета работ")
    st.table(work_data)

st.divider()
col_dl1, col_dl2, col_dl3 = st.columns([1, 2, 1])
with col_dl2:
    st.download_button("📥 СКАЧАТЬ ПОЛНЫЙ ПРОЕКТ (PDF)", data=create_pdf(), file_name=f"Terrasa_{client_name}.pdf", mime="application/pdf", use_container_width=True)

st.divider()
st.subheader("📐 Технические схемы (Размеры в мм)")
t1, t2, t3 = st.tabs(["Вид настила", "Металлокаркас", "Свайное поле"])
with t1: st.image(get_plot("board"))
with t2: st.image(get_plot("frame"))
with t3: 
    if piles > 0: st.image(get_plot("piles"))
    else: st.info("Основание — бетон, сваи не требуются.")
