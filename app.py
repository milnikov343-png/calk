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
PILE_PRICE = 3600

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
                w = min(bl, length-x); ax.add_patch(patches.Rectangle((x, y), w, eff_w*0.8, color='#8d6e63', ec='black'))
                x += bl
    elif mode == "frame":
        for i in range(j_rows): ax.plot([i*JOIST_STEP_M, i*JOIST_STEP_M], [0, width], color='blue', lw=1)
        if frame_choice:
            for j in range(math.ceil(width/2)+1): ax.plot([0, length], [j*2, j*2], color='red', lw=2)
    ax.set_xlim(0, length); ax.set_ylim(0, width); plt.axis('off')
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close()
    return buf

# --- 5. ГЕНЕРАЦИЯ PDF ---
def create_pdf():
    pdf = FPDF()
    pdf.add_page()
    # Пытаемся подключить шрифт (файл DejaVuSans.ttf должен быть в репозитории!)
    try:
        pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
        pdf.set_font('DejaVu', '', 12)
    except:
        pdf.set_font('Arial', '', 12) # Запасной вариант, если файла нет
    
    pdf.cell(200, 10, txt="Приложение №1 к договору: Коммерческое предложение", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Клиент: {client_name} | Дата: {datetime.date.today()}", ln=True, align='L')
    pdf.ln(5)
    
    # Таблица материалов
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(90, 10, "Наименование", 1, 0, 'C', True)
    pdf.cell(30, 10, "Кол-во", 1, 0, 'C', True)
    pdf.cell(30, 10, "Цена", 1, 0, 'C', True)
    pdf.cell(40, 10, "Сумма", 1, 1, 'C', True)
    
    items = [
        [board_choice, f"{b_qty} {b_info['unit']}", f"{b_info['price']}", f"{b_total}"],
        [f"Лага {joist_choice}", f"{j_m} м.п.", f"{j_price}", f"{j_total}"],
        ["Кляймеры", f"{clips_packs} уп", "2000", f"{clips_total}"]
    ]
    if frame_choice: items.insert(1, [f"Каркас {frame_choice}", f"{f_m} м.п.", f"{f_price}", f"{f_total}"])
    
    for row in items:
        pdf.cell(90, 10, row[0], 1)
        pdf.cell(30, 10, row[1], 1)
        pdf.cell(30, 10, row[2], 1)
        pdf.cell(40, 10, row[3], 1, 1)
    
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"ИТОГО: {b_total + j_total + f_total + clips_total + (area*2400) + (piles*3600):,.0f} руб.", ln=True, align='R')
    
    # Вставляем чертеж
    pdf.add_page()
    pdf.cell(200, 10, txt="Схема раскладки доски", ln=True, align='C')
    img_buf = get_plot("board")
    pdf.image(img_buf, x=10, y=30, w=180)
    
    return pdf.output()

# --- 6. ЭКРАН РЕЗУЛЬТАТОВ ---
st.write(f"### Общая сумма: {b_total + j_total + f_total + clips_total + (area*2400) + (piles*3600):,.0f} руб.")

pdf_data = create_pdf()
st.download_button(
    label="📥 СКАЧАТЬ ГОТОВОЕ КП (PDF)",
    data=pdf_data,
    file_name=f"KP_{client_name}.pdf",
    mime="application/pdf"
)

# Вывод чертежей на экран для контроля
t1, t2 = st.tabs(["Чертеж доски", "Чертеж каркаса"])
with t1: st.pyplot(plt.figure(canvas=get_plot("board"))) # Упрощенно для примера
with t2: st.pyplot(plt.figure(canvas=get_plot("frame")))
