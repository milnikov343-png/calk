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
st.set_page_config(page_title="Дача 2000 | Единый стандарт ММ", layout="wide")
st.title("🏗️ Расчет террасы (Размеры в ММ)")

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
if "Грунт" in base_type:
    pr, pc = math.ceil(length/PILE_STEP_M)+1, math.ceil(width/PILE_STEP_M)+1
    piles = pr * pc
    f_m = math.ceil(pc * length)
    f_total = f_m * round(PIPES_FRAME[frame_choice] * METAL_MARGIN)

clips_packs = math.ceil((j_rows * rows) / 100)
clips_total = clips_packs * 2000
grand_total = b_total + j_total + f_total + clips_total + (area * 2400) + (piles * 3600)

# --- 4. ФУНКЦИИ РИСОВАНИЯ (ВСЁ В ММ) ---
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
        # Размеры в ММ
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
                # Размеры по осям в ММ
                if i < pr-1 and j == 0:
                    ax.text(px + sp_x/2, py-0.4, f"{int(sp_x*1000)} мм", ha='center', fontsize=9)
                if j < pc-1 and i == 0:
                    ax.text(px-0.8, py + sp_y/2, f"{int(sp_y*1000)} мм", va='center', rotation=90, fontsize=9)

    ax.set_xlim(-1.0, length+0.5); ax.set_ylim(-1.0, width+0.5); ax.set_aspect('equal')
    plt.axis('off')
    buf = io.BytesIO(); plt.savefig(buf, format='png', bbox_inches='tight', dpi=150); plt.close(fig); buf.seek(0)
    return buf

# --- 5. ГЕНЕРАЦИЯ PDF ---
def create_pdf():
    pdf = FPDF()
    try:
        pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
        pdf.set_font('DejaVu', '', 12)
    except: pdf.set_font('Arial', '', 12)
    
    pdf.add_page()
    pdf.cell(200, 10, txt="Приложение №1: Техническая спецификация (в мм)", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Клиент: {client_name} | Габариты: {int(length*1000)}x{int(width*1000)} мм", ln=True, align='L')
    pdf.ln(10)
    
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(110, 10, "Наименование позиции", 1, 0, 'L', True)
    pdf.cell(80, 10, "Сумма", 1, 1, 'C', True)
    
    items = [(board_choice, b_total), (f"Лаги {joist_choice}", j_total), ("Кляймеры", clips_total)]
    if frame_choice: items.insert(1, (f"Каркас {frame_choice}", f_total))
    if piles > 0: items.append((f"Сваи ({piles} шт)", piles*3600))
    items.append(("Монтажные работы (настил + ступени)", (area*2400) + 15600))
    
    for name, price in items:
        pdf.cell(110, 10, name, 1)
        pdf.cell(80, 10, f"{price:,.0f} руб.", 1, 1, 'R')
    
    pdf.ln(5); pdf.set_font('DejaVu', '', 14)
    pdf.cell(190, 10, txt=f"ИТОГО: {grand_total:,.0f} руб.", ln=True, align='R')

    # Чертежи
    for m, title in [("board", "Раскладка настила"), ("frame", "Металлокаркас"), ("piles", "Свайное поле")]:
        if m == "piles" and piles == 0: continue
        pdf.add_page()
        pdf.cell(200, 10, f"Схема: {title} (размеры в мм)", ln=True, align='C')
        pdf.image(get_plot(m), x=15, y=40, w=180)
    
    return bytes(pdf.output())

# --- 6. UI ---
st.markdown(f"<h2 style='text-align: center; color: #2e7d32;'>Итого: {grand_total:,.0f} руб.</h2>", unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.download_button("📥 СКАЧАТЬ ПРОЕКТ (ММ, PDF)", data=create_pdf(), file_name=f"Project_{client_name}.pdf", mime="application/pdf", use_container_width=True)

st.divider()
st.subheader("📐 Техническая визуализация (ММ)")
t1, t2, t3 = st.tabs(["Настил", "Каркас", "Сваи"])
with t1: st.image(get_plot("board"), caption=f"Габариты: {int(length*1000)}x{int(width*1000)} мм")
with t2: st.image(get_plot("frame"), caption="Лаги 60х40 и Каркас 80х80")
with t3: 
    if piles > 0: st.image(get_plot("piles"), caption="Осевые расстояния между сваями")
    else: st.write("Фундамент не требуется.")
