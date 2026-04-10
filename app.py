import streamlit as st
import math

# --- 1. БАЗА ДАННЫХ (ПРАЙС-ЛИСТ) ---
# В будущем эти словари могут заполняться функцией-парсером с вашего сайта
BOARDS = {
    "LikeWood Вельвет 140мм (Венге/Антрацит)": {"price": 438, "unit": "м.п.", "width_mm": 140, "length_m": None},
    "LikeWood 3D тиснение 140мм": {"price": 530, "unit": "м.п.", "width_mm": 140, "length_m": None},
    "Woodvex Select 146мм (Венге) 3м": {"price": 2054, "unit": "шт", "width_mm": 146, "length_m": 3},
    "Террапол СМАРТ 130мм 3м": {"price": 2019, "unit": "шт", "width_mm": 130, "length_m": 3},
}

PIPES_JOIST = {
    "Труба 60х40х1,5": {"price_base": 173},
    "Труба 60х40х2": {"price_base": 219},
    "Труба 60х40х3": {"price_base": 290},
}

PIPES_FRAME = {
    "Труба 80х80х2": {"price_base": 403},
    "Труба 80х80х3": {"price_base": 475},
    "Труба 100х100х3": {"price_base": 602},
}

# Настройки бизнеса
METAL_MARGIN = 1.15 # Наценка на металл 15%
GAP_MM = 5          # Тепловой зазор доски 5мм
JOIST_STEP_M = 0.4  # Максимальный шаг лаг 400мм
PILE_STEP_M = 2.0   # Максимальный шаг свай/каркаса 2м
PILE_PRICE = 3600   # Цена сваи с монтажом

# --- 2. НАСТРОЙКА ИНТЕРФЕЙСА ---
st.set_page_config(page_title="Калькулятор Менеджера | Дача 2000", layout="wide")
st.title("🏗️ Калькулятор расчета террасы")

# --- 3. ВВОД ПАРАМЕТРОВ ---
st.sidebar.header("Параметры объекта")
length = st.sidebar.number_input("Длина террасы (м):", min_value=1.0, value=6.0, step=0.1)
width = st.sidebar.number_input("Ширина террасы (м):", min_value=1.0, value=4.0, step=0.1)
base_type = st.sidebar.radio("Основание:", ["Грунт (Сваи + Каркас)", "Бетон (Только лаги)"])

st.sidebar.header("Материалы")
board_choice = st.sidebar.selectbox("Террасная доска:", list(BOARDS.keys()))
joist_choice = st.sidebar.selectbox("Труба для лаг:", list(PIPES_JOIST.keys()))

frame_choice = None
if base_type == "Грунт (Сваи + Каркас)":
    frame_choice = st.sidebar.selectbox("Труба для каркаса:", list(PIPES_FRAME.keys()))

st.sidebar.header("Доп. работы")
steps_m = st.sidebar.number_input("Ступени (пог.м):", min_value=0.0, value=3.0, step=0.1)
need_delivery = st.sidebar.checkbox("Доставка (15 000 руб)", value=True)


# --- 4. ИНЖЕНЕРНАЯ МАТЕМАТИКА ---
area = length * width

# Раскладка доски (с учетом зазора)
board_data = BOARDS[board_choice]
eff_width_m = (board_data["width_mm"] + GAP_MM) / 1000
board_rows = math.ceil(width / eff_width_m)
total_board_meters = board_rows * length

board_qty = 0
board_total_price = 0
if board_data["unit"] == "м.п.":
    board_qty = math.ceil(total_board_meters)
    board_total_price = board_qty * board_data["price"]
else:
    # Если продается в штуках
    board_qty = math.ceil(total_board_meters / board_data["length_m"])
    board_total_price = board_qty * board_data["price"]

# Подсистема: Лаги
joist_rows = math.ceil(length / JOIST_STEP_M) + 1
joist_meters = math.ceil(joist_rows * width)
# Наценка на лаги
joist_price_client = round(PIPES_JOIST[joist_choice]["price_base"] * METAL_MARGIN)
joist_total_price = joist_meters * joist_price_client

# Подсистема: Каркас и Сваи
piles_qty = 0
frame_meters = 0
frame_total_price = 0
frame_price_client = 0

if base_type == "Грунт (Сваи + Каркас)":
    piles_length = math.ceil(length / PILE_STEP_M) + 1
    piles_width = math.ceil(width / PILE_STEP_M) + 1
    piles_qty = piles_length * piles_width
    
    frame_meters = math.ceil(piles_width * length)
    frame_price_client = round(PIPES_FRAME[frame_choice]["price_base"] * METAL_MARGIN)
    frame_total_price = frame_meters * frame_price_client

# Крепеж (Кляймеры)
clips_exact = joist_rows * board_rows
clips_packs = math.ceil(clips_exact / 100)
clips_price = clips_packs * 2000 # Пример: 2000 руб за упаковку

# Работы
labor_board = area * 2400
labor_steps = steps_m * 5200


# --- 5. ВЫВОД РЕЗУЛЬТАТОВ (СМЕТА) ---
st.subheader(f"Площадь террасы: {area:.1f} м²")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🧱 Материалы")
    st.info("💡 К трубам автоматически применена наценка 15% с округлением")
    
    # Собираем данные для таблицы материалов
    mat_data = [
        {"Наименование": board_choice, "Кол-во": board_qty, "Ед.изм": board_data["unit"], "Цена": board_data["price"], "Сумма": board_total_price},
        {"Наименование": joist_choice, "Кол-во": joist_meters, "Ед.изм": "м.п.", "Цена": joist_price_client, "Сумма": joist_total_price},
        {"Наименование": "Упаковка кляймеров (100шт)", "Кол-во": clips_packs, "Ед.изм": "уп", "Цена": 2000, "Сумма": clips_price},
    ]
    if base_type == "Грунт (Сваи + Каркас)":
        mat_data.insert(1, {"Наименование": frame_choice, "Кол-во": frame_meters, "Ед.изм": "м.п.", "Цена": frame_price_client, "Сумма": frame_total_price})
    
    st.dataframe(mat_data, use_container_width=True)
    total_materials = sum(item["Сумма"] for item in mat_data)
    st.write(f"**Итого материалы:** {total_materials:,.0f} руб.".replace(',', ' '))

with col2:
    st.markdown("### 🛠️ Работы и Услуги")
    
    work_data = [
        {"Наименование": "Монтаж ДПК доски и лаг", "Сумма": labor_board},
        {"Наименование": "Монтаж ступеней", "Сумма": labor_steps},
    ]
    if piles_qty > 0:
        work_data.append({"Наименование": f"Сваи с монтажом ({piles_qty} шт)", "Сумма": piles_qty * PILE_PRICE})
    if need_delivery:
        work_data.append({"Наименование": "Доставка", "Сумма": 15000})
        
    st.dataframe(work_data, use_container_width=True)
    total_works = sum(item["Сумма"] for item in work_data)
    st.write(f"**Итого работы:** {total_works:,.0f} руб.".replace(',', ' '))

st.divider()

# Итоговая панель
grand_total = total_materials + total_works
st.markdown(f"<h2 style='text-align: center; color: #2e7d32;'>Общая смета: {grand_total:,.0f} руб.</h2>", unsafe_allow_html=True)

# Кнопка для будущей интеграции
if st.button("📄 Сгенерировать PDF и отправить в Битрикс24", type="primary"):
    st.success("Эта кнопка будет собирать данные выше и отправлять их по API в ваш Битрикс!")
