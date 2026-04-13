import streamlit as st
import math
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import io

# --- 1. БАЗА ДАННЫХ И НАСТРОЙКИ ---
# Цены на доску (за п.м. или за штуку 3м)
BOARDS = {
    "LikeWood Вельвет 140мм (Венге/Антрацит)": {"price": 438, "unit": "м.п.", "width_mm": 140, "length_m": 4.0},
    "LikeWood 3D тиснение 140мм": {"price": 530, "unit": "м.п.", "width_mm": 140, "length_m": 4.0},
    "Woodvex Select 146мм (Венге) 3м": {"price": 2054, "unit": "шт", "width_mm": 146, "length_m": 3.0},
    "Террапол СМАРТ 130мм 3м": {"price": 2019, "unit": "шт", "width_mm": 130, "length_m": 3.0},
}

# Цены на трубы (базовые с сайта)
PIPES_JOIST = {
    "Труба 60х40х2": {"price_base": 219},
    "Труба 60х40х3": {"price_base": 290},
}

PIPES_FRAME = {
    "Труба 80х80х2": {"price_base": 403},
    "Труба 80х80х3": {"price_base": 475},
}

# Бизнес-логика
METAL_MARGIN = 1.15  # Наценка 15%
GAP_MM = 5           # Зазор между досками
JOIST_STEP_M = 0.4   # Шаг лаг 400мм
PILE_STEP_M = 2.0    # Шаг опор 2000мм
PILE_PRICE = 3600    # Свая + монтаж

# --- 2. ИНТЕРФЕЙС ---
st.set_page_config(page_title="Дача 2000 | Калькулятор террас", layout="wide")
st.title("🏗️ Профессиональный расчет террасы")

st.sidebar.header("1. Размеры и Основание")
length = st.sidebar.number_input("Длина террасы (вдоль доски), м:", min_value=1.0, value=6.0, step=0.1)
width = st.sidebar.number_input("Ширина террасы (поперек доски), м:", min_value=1.0, value=4.0, step=0.1)
base_type = st.sidebar.radio("Тип основания:", ["Грунт (Сваи + Каркас 80х80)", "Бетон (Только лаги)"])

st.sidebar.header("2. Материалы")
board_choice = st.sidebar.selectbox("Выберите доску:", list(BOARDS.keys()))
joist_choice = st.sidebar.selectbox("Труба для лаг (60х40):", list(PIPES_JOIST.keys()))

frame_choice = None
if "Грунт" in base_type:
    frame_choice = st.sidebar.selectbox("Труба каркаса (80х80):", list(PIPES_FRAME.keys()))

st.sidebar.header("3. Дополнительно")
steps_m = st.sidebar.number_input("Ступени (пог.м):", value=3.0)
delivery = st.sidebar.checkbox("Доставка и ГСМ (15 000 руб)", value=True)

# --- 3. РАСЧЕТЫ ---
board_info = BOARDS[board_choice]
# Расчет рядов доски с учетом зазора 5мм
eff_width_m = (board_info["width_mm"] + GAP_MM) / 1000
board_rows = math.ceil(width / eff_width_m)
total_board_meters = board_rows * length

# Итоговое кол-во досок
if board_info["unit"] == "м.п.":
    board_qty = math.ceil(total_board_meters)
    board_total_price = board_qty * board_info["price"]
else:
    board_qty = math.ceil(total_board_meters / board_info["length_m"])
    board_total_price = board_qty * board_info["price"]

# Расчет лаг (60х40)
joist_rows = math.ceil(length / JOIST_STEP_M) + 1
joist_meters = math.ceil(joist_rows * width)
price_joist_client = round(PIPES_JOIST[joist_choice]["price_base"] * METAL_MARGIN)
joist_total_price = joist_meters * price_joist_client

# Расчет каркаса и свай
piles_qty = 0
frame_meters = 0
frame_total_price = 0
price_frame_client = 0

if "Грунт" in base_type:
    p_rows = math.ceil(length / PILE_STEP_M) + 1
    p_cols = math.ceil(width / PILE_STEP_M) + 1
    piles_qty = p_rows * p_cols
    
    # Труба 80х80 идет вдоль длины по рядам свай
    frame_meters = math.ceil(p_cols * length)
    price_frame_client = round(PIPES_FRAME[frame_choice]["price_base"] * METAL_MARGIN)
    frame_total_price = frame_meters * price_frame_client

# Кляймеры
clips_qty = math.ceil((joist_rows * board_rows) / 100) * 100
clips_packs = clips_qty // 100
clips_price = clips_packs * 2000

# Работы
labor_board = (length * width) * 2400
labor_piles = piles_qty * 3600
labor_steps = steps_m * 5200

# --- 4. ВЫВОД СМЕТЫ ---
st.subheader(f"Результаты расчета для террасы {length} x {width} м")

c1, c2 = st.columns(2)
with c1:
    st.markdown("#### 🧱 Материалы (Цены клиента)")
    mat_table = [
        {"Наименование": board_choice, "Кол-во": board_qty, "Ед.": board_info["unit"], "Сумма": board_total_price},
        {"Наименование": f"Лаги {joist_choice}", "Кол-во": joist_meters, "Ед.": "м.п.", "Сумма": joist_total_price},
        {"Наименование": "Кляймеры (уп. 100шт)", "Кол-во": clips_packs, "Ед.": "уп", "Сумма": clips_price},
    ]
    if frame_choice:
        mat_table.insert(1, {"Наименование": f"Каркас {frame_choice}", "Кол-во": frame_meters, "Ед.": "м.п.", "Сумма": frame_total_price})
    
    st.table(mat_table)
    total_m = sum(item["Сумма"] for item in mat_table)
    st.write(f"**Итого за материалы:** {total_m:,.0f} руб.")

with c2:
    st.markdown("#### 🛠️ Работы и Услуги")
    work_table = [
        {"Услуга": "Монтаж настила и лаг", "Сумма": labor_board},
        {"Услуга": "Монтаж ступеней", "Сумма": labor_steps},
    ]
    if piles_qty > 0:
        work_table.append({"Услуга": f"Установка свай ({piles_qty} шт)", "Сумма": labor_piles})
    if delivery:
        work_table.append({"Услуга": "Доставка и логистика", "Сумма": 15000})
        
    st.table(work_table)
    total_w = sum(item["Сумма"] for item in work_table)
    st.write(f"**Итого за работы:** {total_w:,.0f} руб.")

st.success(f"### ОБЩАЯ СТОИМОСТЬ: {total_m + total_w:,.0f} руб.")

# --- 5. ВИЗУАЛИЗАЦИЯ (ЧЕРТЕЖИ) ---
st.divider()
st.subheader("📐 Технические чертежи")

# Создаем вкладки для разных слоев
if "Грунт" in base_type:
    t_board, t_frame, t_piles = st.tabs(["1. Раскладка доски", "2. Металлокаркас", "3. Свайное поле"])
else:
    t_board, t_frame = st.tabs(["1. Раскладка доски", "2. Подсистема (Лаги)"])
    t_piles = None

# Функция для рисования досок
def plot_boards():
    fig, ax = plt.subplots(figsize=(10, 5))
    b_len = board_info["length_m"]
    for r in range(board_rows):
        y = r * eff_width_m
        x = 0
        offset = (b_len / 2) if (r % 2 != 0) else 0
        
        # Первая доска в ряду (с учетом смещения)
        if offset > 0:
            w = min(offset, length)
            ax.add_patch(patches.Rectangle((0, y), w, eff_width_m*0.9, facecolor='#8d6e63', edgecolor='black', linewidth=0.5))
            x = w
            
        while x < length:
            w = min(b_len, length - x)
            ax.add_patch(patches.Rectangle((x, y), w, eff_width_m*0.9, facecolor='#8d6e63', edgecolor='black', linewidth=0.5))
            x += b_len
            
    ax.set_xlim(0, length); ax.set_ylim(0, width); ax.set_aspect('equal')
    plt.axis('off'); return fig

# Функция для рисования каркаса
def plot_frame():
    fig, ax = plt.subplots(figsize=(10, 5))
    # Рисуем лаги 60х40 (вертикальные синие линии)
    for i in range(joist_rows):
        cur_x = i * JOIST_STEP_M if (i * JOIST_STEP_M < length) else length
        ax.plot([cur_x, cur_x], [0, width], color='blue', linewidth=1, alpha=0.6)
    
    # Рисуем трубы 80х80 (горизонтальные красные линии)
    if "Грунт" in base_type:
        num_lines = math.ceil(width / PILE_STEP_M) + 1
        for j in range(num_lines):
            cur_y = j * PILE_STEP_M if (j * PILE_STEP_M < width) else width
            ax.plot([0, length], [cur_y, cur_y], color='red', linewidth=3)
            
    ax.set_xlim(0, length); ax.set_ylim(0, width); ax.set_aspect('equal')
    plt.axis('off'); return fig

# Функция для рисования свай
def plot_piles():
    fig, ax = plt.subplots(figsize=(10, 5))
    p_rows = math.ceil(length / PILE_STEP_M) + 1
    p_cols = math.ceil(width / PILE_STEP_M) + 1
    for i in range(p_rows):
        for j in range(p_cols):
            px = i * PILE_STEP_M if (i * PILE_STEP_M < length) else length
            py = j * PILE_STEP_M if (j * PILE_STEP_M < width) else width
            ax.add_patch(patches.Circle((px, py), 0.1, color='black'))
    ax.set_xlim(-0.5, length+0.5); ax.set_ylim(-0.5, width+0.5); ax.set_aspect('equal')
    plt.axis('off'); return fig

with t_board:
    st.pyplot(plot_boards())
with t_frame:
    st.pyplot(plot_frame())
if t_piles:
    with t_piles:
        st.pyplot(plot_piles())

st.info("💡 Нажмите правой кнопкой мыши на чертеж, чтобы сохранить его как картинку.")
