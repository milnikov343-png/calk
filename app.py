import streamlit as st
import math
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import io
from fpdf import FPDF
import datetime

# --- 1. БАЗА ДАННЫХ И НАСТРОЙКИ ---
BOARDS = {
    "LikeWood Вельвет 140мм": {"price": 438, "unit": "м.п.", "width_mm": 140, "length_m": 4.0},
    "LikeWood 3D тиснение 140мм": {"price": 530, "unit": "м.п.", "width_mm": 140, "length_m": 4.0},
    "Woodvex Select 146мм 3м": {"price": 2054, "unit": "шт", "width_mm": 146, "length_m": 3.0},
    "Террапол СМАРТ 130мм 3м": {"price": 2019, "unit": "шт", "width_mm": 130, "length_m": 3.0},
}

PIPES_JOIST = {"Труба 60х40х2": 219, "Труба 60х40х3": 290}
PIPES_FRAME = {"Труба 80х80х2": 403, "Труба 80х80х3": 475}

METAL_MARGIN = 1.15
GAP_MM = 5
JOIST_STEP_M = 0.4
PILE_STEP_M = 2.0

# --- 2. ИНТЕРФЕЙС ---
st.set_page_config(page_title="Дача 2000 | КП", layout="wide")
st.title("🏗️ Расчет террасы и генерация КП")

st.sidebar.header("Параметры")
client_name = st.sidebar.text_input("ФИО Клиента:", "Иван Иванович")
length = st.sidebar.number_input("Длина (м):", 1.0, 20.0, 6.0)
width = st.sidebar.number_input("Ширина (м):", 1.0, 20.0, 4.0)
base_type = st.sidebar.radio("Основание:", ["Грунт (Сваи)", "Бетон"])

board_choice = st.sidebar.selectbox("Доска:", list(BOARDS.keys()))
joist_choice = st.sidebar.selectbox("Лаги (60х40):", list(PIPES_JOIST.keys()))
frame_choice = st.sidebar.selectbox("Каркас (80х80):", list(PIPES_FRAME.keys())) if "Грунт" in base_type else None

# --- 3. РАСЧЕТЫ ---
area = length * width
b_info = BOARDS[board_choice]
eff_w = (b_info["width_mm"] + GAP_MM) / 1000
rows = math.ceil(width / eff_w)
total_bm = rows * length
b_qty = math.ceil(total_bm) if b_info["unit"] == "м.п." else math.ceil(total_bm / b_info["length_m"])
b_total = b_qty * b_info["price"]

j_rows = math.ceil(length / JOIST_STEP_M) + 1
j_m = math.ceil(j_rows * width)
j_price = round(PIPES_JOIST[joist_choice] * METAL_MARGIN)
j_total = j_m * j_price

piles = 0
f_m = 0
f_total = 0
f_price = 0
if "Грунт" in base_type:
    pr, pc = math.ceil(length/PILE_STEP_M)+1, math.ceil(width/PILE_STEP_M)+1
    piles = pr * pc
    f_m = math.ceil(pc * length)
    f_price = round(PIPES_FRAME[frame_choice] * METAL_MARGIN)
    f_total = f_m * f_price

clips_packs = math.ceil((j_rows * rows) / 100)
clips_total = clips_packs * 2000

# Формируем таблицы для вывода
mat_table = [
    {"Наименование": board_choice, "Кол-во": f"{b_qty} {b_info['unit']}", "Сумма": b_total},
    {"Наименование": f"Лага {joist_choice}", "Кол-во": f"{j_m} м.п.", "Сумма": j_total},
    {"Наименование": "Кляймеры (уп. 100шт)", "Кол-во": f"{clips_packs} уп", "Сумма": clips_total}
]
if frame_choice: 
    mat_table.insert(1, {"Наименование": f"Каркас {frame_choice}", "Кол-во": f"{f_m} м.п.", "Сумма": f_total})

work_table = [
    {"Наименование": "Монтаж настила и лаг", "Сумма": area * 2400},
]
if piles > 0:
    work_table.append({"Наименование": f"Установка свай ({piles} шт)", "Сумма": piles * 3600})

grand_total = sum(item["Сумма"] for item in mat_table) + sum(item["Сумма"] for item in work_table)

# --- 4. ФУНКЦИИ РИСОВАНИЯ ---
def get_plot(mode):
    fig, ax = plt.subplots(figsize=(8, 4))
    
    if mode == "board":
        bl = b_info["length_m"]
        for r in range(rows):
            y, x = r * eff_w, 0
            if r % 2 != 0:
                w = min(bl/2, length); ax.add_patch(patches.Rectangle((0, y), w, eff_w*0.8, color='#8d6e63'))
                x = w
            while x < length:
                w = min(bl, length-x); ax.add_patch(patches.Rectangle((x, y), w, eff_w*0.8, color='#8d6e63', ec='black', lw=0.5))
                x += bl
                
    elif mode == "frame":
        for i in range(j_rows): 
            cx = min(i*JOIST_STEP_M, length)
            ax.plot([cx, cx], [0, width], color='blue', lw=1, alpha=0.7)
        if frame_choice:
            for j in range(math.ceil(width/PILE_STEP_M)+1): 
                cy = min(j*PILE_STEP_M, width)
                ax.plot([0, length], [cy, cy], color='red', lw=2)
                
    elif mode == "piles":
        pr, pc = math.ceil(length/PILE_STEP_M)+1, math.ceil(width/PILE_STEP_M)+1
        for i in range(pr):
            for j in range(pc):
                px, py = min(i*PILE_STEP_M, length), min(j*PILE_STEP_M, width)
                ax.add_patch(patches.Circle((px, py), 0.1, color='black'))

    ax.set_xlim(-0.2, length+0.2); ax.set_ylim(-0.2, width+0.2); ax.set_aspect('equal')
    plt.axis('off')
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf

# --- 5. ГЕНЕРАЦИЯ PDF ---
def create_pdf():
    pdf = FPDF()
    pdf.add_page()
    try:
        pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
        pdf.set_font('DejaVu', '', 12)
    except:
        pdf.set_font('Arial', '', 12)
    
    pdf.cell(200, 10, txt="Приложение №1 к договору: Смета и чертежи", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Клиент: {client_name} | Дата: {datetime.date.today()}", ln=True, align='L')
    pdf.ln(5)
    
    # Таблица материалов
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(110, 10, "Материалы", 1, 0, 'C', True)
    pdf.cell(40, 10, "Кол-во", 1, 0, 'C', True)
    pdf.cell(40, 10, "Сумма", 1, 1, 'C', True)
    
    for row in mat_table:
        pdf.cell(110, 10, str(row["Наименование"]), 1)
        pdf.cell(40, 10, str(row["Кол-во"]), 1, 0, 'C')
        pdf.cell(40, 10, f"{row['Сумма']:,.0f} р.", 1, 1, 'C')
        
    pdf.ln(5)
    # Таблица работ
    pdf.cell(150, 10, "Строительно-монтажные работы", 1, 0, 'C', True)
    pdf.cell(40, 10, "Сумма", 1, 1, 'C', True)
    for row in work_table:
        pdf.cell(150, 10, str(row["Наименование"]), 1)
        pdf.cell(40, 10, f"{row['Сумма']:,.0f} р.", 1, 1, 'C')
        
    pdf.ln(10)
    pdf.set_font('DejaVu', '', 14)
    pdf.cell(190, 10, txt=f"ИТОГО: {grand_total:,.0f} руб.", ln=True, align='R')
    
    # Вставляем чертежи на новые страницы
    pdf.add_page()
    pdf.cell(200, 10, txt="1. Схема раскладки террасной доски", ln=True, align='C')
    pdf.image(get_plot("board"), x=15, y=30, w=180)
    
    pdf.add_page()
    pdf.cell(200, 10, txt="2. Схема подсистемы (лаги и каркас)", ln=True, align='C')
    pdf.image(get_plot("frame"), x=15, y=30, w=180)
    
    if piles > 0:
        pdf.add_page()
        pdf.cell(200, 10, txt="3. Свайное поле (фундамент)", ln=True, align='C')
        pdf.image(get_plot("piles"), x=15, y=30, w=180)
    
    return bytes(pdf.output())

# --- 6. ЭКРАН РЕЗУЛЬТАТОВ (UI) ---
st.markdown(f"<h2 style='text-align: center; color: #2e7d32;'>Общая смета: {grand_total:,.0f} руб.</h2>", unsafe_allow_html=True)

# Кнопка скачивания по центру
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.download_button(
        label="📥 СКАЧАТЬ СМЕТУ И ЧЕРТЕЖИ (PDF)",
        data=create_pdf(),
        file_name=f"KP_{client_name}.pdf",
        mime="application/pdf",
        use_container_width=True
    )

st.divider()

# Возвращаем таблицы на экран
colA, colB = st.columns(2)
with colA:
    st.markdown("#### 🧱 Материалы")
    st.dataframe(mat_table, use_container_width=True, hide_index=True)
with colB:
    st.markdown("#### 🛠️ Работы")
    st.dataframe(work_table, use_container_width=True, hide_index=True)

st.divider()

# Вывод чертежей во вкладках (теперь картинки будут отображаться корректно!)
st.subheader("📐 Технические чертежи")
if piles > 0:
    t1, t2, t3 = st.tabs(["Чертеж доски", "Чертеж каркаса", "Свайное поле"])
    with t1: st.image(get_plot("board"))
    with t2: st.image(get_plot("frame"))
    with t3: st.image(get_plot("piles"))
else:
    t1, t2 = st.tabs(["Чертеж доски", "Чертеж каркаса"])
    with t1: st.image(get_plot("board"))
    with t2: st.image(get_plot("frame"))
