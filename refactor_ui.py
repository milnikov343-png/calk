import re

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add import os
if "import os" not in content:
    content = content.replace("import streamlit as st", "import streamlit as st\nimport os")

old_ui_block = """st.set_page_config(page_title="Дача 2000 | Умный Калькулятор", layout="wide")
st.title("🏗️ Профессиональный проект террасы")

col_h1, col_h2 = st.columns([8, 2])
with col_h2:
    if st.button("🔄 Обновить прайс", use_container_width=True):
        st.cache_data.clear(); st.rerun()

st.sidebar.header("1. Форма террасы")
shape_type = st.sidebar.selectbox("Выберите конфигурацию:", [
    "⬜ Прямоугольная (Стандарт)", 
    "📐 Г-образная (Угловая)", 
    "🔲 П-образная (С вырезом)", 
    "⏺️ Округлая (Овал / Круг)",
    "✏️ Свой контур (По координатам)"
])

st.sidebar.header("2. Параметры объекта")
client_name = st.sidebar.text_input("ФИО Клиента:", "Иван Иванович")

if shape_type == "⬜ Прямоугольная (Стандарт)":
    length = st.sidebar.number_input("Длина фасада (X), м:", 1.0, 50.0, 9.0)
    width = st.sidebar.number_input("Глубина (Y), м:", 1.0, 50.0, 4.0)

elif shape_type == "📐 Г-образная (Угловая)":
    st.sidebar.caption("Задайте общие габариты и размер выреза:")
    col1, col2 = st.sidebar.columns(2)
    length = col1.number_input("Общая длина X, м:", 1.0, 50.0, 6.0)
    width = col2.number_input("Общая глубина Y, м:", 1.0, 50.0, 5.0)
    cut_x = col1.number_input("Вырез X, м:", 0.1, float(length-0.1), 3.0)
    cut_y = col2.number_input("Вырез Y, м:", 0.1, float(width-0.1), 2.0)

elif shape_type == "🔲 П-образная (С вырезом)":
    st.sidebar.caption("Задайте общие габариты и центральный вырез:")
    length = st.sidebar.number_input("Общая длина X, м:", 1.0, 50.0, 8.0)
    width = st.sidebar.number_input("Общая глубина Y, м:", 1.0, 50.0, 5.0)
    col1, col2 = st.sidebar.columns(2)
    cut_w = col1.number_input("Ширина выреза X, м:", 0.1, float(length-0.2), 3.0)
    cut_d = col2.number_input("Глубина выреза Y, м:", 0.1, float(width-0.1), 2.0)

elif shape_type == "⏺️ Округлая (Овал / Круг)":
    st.sidebar.caption("Задайте габариты овала (для круга X и Y равны):")
    length = st.sidebar.number_input("Общая длина (Диаметр X), м:", 1.0, 50.0, 6.0)
    width = st.sidebar.number_input("Общая глубина (Диаметр Y), м:", 1.0, 50.0, 4.0)

elif shape_type == "✏️ Свой контур (По координатам)":
    st.sidebar.caption("Таблица точек полигона (в метрах):")
    df_coords = pd.DataFrame([{"X (м)": 0.0, "Y (м)": 0.0}, {"X (м)": 0.0, "Y (м)": 4.0}, {"X (м)": 6.0, "Y (м)": 4.0}, {"X (м)": 6.0, "Y (м)": 0.0}])
    edited_df = st.sidebar.data_editor(df_coords, num_rows="dynamic", use_container_width=True)
    length = 5.0
    width = 5.0

base_type = st.sidebar.radio("Основание:", ["Грунт (Сваи)", "Бетон"])

# --- БАССЕЙН ---
st.sidebar.header("3. Бассейн")
has_pool = st.sidebar.checkbox("Встроенный бассейн (вырез в террасе)", value=False)
if has_pool:
    pool_shape = st.sidebar.radio("Форма бассейна:", ["⬜ Прямоугольный", "⏺️ Круглый", "⬭ Овальный"])
    col1, col2 = st.sidebar.columns(2)
    if pool_shape in ["⬜ Прямоугольный", "⬭ Овальный"]:
        pool_l = col1.number_input("Длина басс. X, м:", 0.5, 20.0, 4.0)
        pool_w = col2.number_input("Ширина басс. Y, м:", 0.5, 20.0, 2.5)
    else:
        pool_d = st.sidebar.number_input("Диаметр бассейна, м:", 0.5, 20.0, 3.0)
    
    st.sidebar.caption("Отступы от левого нижнего угла (0,0):")
    col3, col4 = st.sidebar.columns(2)
    pool_offset_x = col3.number_input("Смещение X, м:", 0.0, 50.0, 1.0)
    pool_offset_y = col4.number_input("Смещение Y, м:", 0.0, 50.0, 1.0)


st.sidebar.header("4. Выбор коллекции")
brand_choice = st.sidebar.selectbox("Бренд:", list(PARSED_BOARDS.keys()))
if PARSED_BOARDS[brand_choice]:
    collection_name = st.sidebar.selectbox("Коллекция:", list(PARSED_BOARDS[brand_choice].keys()))
    collection_boards = PARSED_BOARDS[brand_choice][collection_name]
    eff_w = (collection_boards[0]["width_mm"] + GAP_MM) / 1000
else:
    st.stop()

direction_choice = st.sidebar.radio("Направление укладки основной доски:", ["Вдоль фасада (по длине X)", "Поперек фасада (по глубине Y)"])

# --- ВОЗВРАЩЕННЫЕ ГАЛОЧКИ ДЛЯ ОКАНТОВКИ ---
st.sidebar.header("5. Окантовка (Торцевая доска)")
use_frame = st.sidebar.checkbox("Сделать окантовку (Picture Frame)", value=True)

if use_frame:
    col_f1, col_f2 = st.sidebar.columns(2)
    edge_front = col_f1.checkbox("Спереди (X)", value=True)
    edge_back = col_f2.checkbox("Сзади (X)", value=False)
    edge_left = col_f1.checkbox("Слева (Y)", value=True)
    edge_right = col_f2.checkbox("Справа (Y)", value=True)
else:
    edge_front = edge_back = edge_left = edge_right = False

st.sidebar.header("6. Подсистема")
joist_choice = st.sidebar.selectbox("Лаги (60х40):", list(PIPES_JOIST.keys()))
frame_choice = st.sidebar.selectbox("Каркас (80х80):", list(PIPES_FRAME.keys())) if "Грунт" in base_type else None
steps_m = st.sidebar.number_input("Ступени (пог.м):", 0.0, 50.0, 0.0)"""

new_ui_block = """st.set_page_config(page_title="Дача 2000 | Умный Калькулятор", layout="wide", initial_sidebar_state="collapsed")

st.markdown(\"\"\"
<style>
[data-testid="collapsedControl"] { display: none; }
section[data-testid="stSidebar"] { display: none; }
div[data-testid="stVerticalBlock"] > div:first-of-type {
    position: sticky;
    top: 0px;
    z-index: 999;
    background-color: white;
    padding-top: 1rem;
    padding-bottom: 1rem;
    border-bottom: 2px solid #ddd;
    margin-bottom: 2rem;
}
@media (prefers-color-scheme: dark) {
    div[data-testid="stVerticalBlock"] > div:first-of-type {
        background-color: #0e1117;
        border-bottom: 2px solid #333;
    }
}
</style>
\"\"\", unsafe_allow_html=True)

with st.container():
    col_logo, col_title, col_btn = st.columns([1.5, 6, 1.5])
    with col_logo:
        try:
            st.image("logo.png", use_column_width=True)
        except:
            st.markdown("<h2>Дача 2000</h2>", unsafe_allow_html=True)
    with col_title:
        st.title("🏗️ Профессиональный проект террасы")
    with col_btn:
        st.write("")
        st.write("")
        if st.button("🔄 Обновить прайс", use_container_width=True):
            st.cache_data.clear(); st.rerun()

    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.subheader("1. Объект и Форма")
        client_name = st.text_input("ФИО Клиента:", "Иван Иванович")
        shape_type = st.selectbox("Конфигурация:", ["⬜ Прямоугольная (Стандарт)", "📐 Г-образная (Угловая)", "🔲 П-образная (С вырезом)", "⏺️ Округлая (Овал / Круг)", "✏️ Свой контур (По координатам)"])
        
        if shape_type == "⬜ Прямоугольная (Стандарт)":
            length = st.number_input("Длина фасада (X), м:", 1.0, 50.0, 9.0)
            width = st.number_input("Глубина (Y), м:", 1.0, 50.0, 4.0)
        elif shape_type == "📐 Г-образная (Угловая)":
            c_l, c_w = st.columns(2)
            length = c_l.number_input("Длина X, м:", 1.0, 50.0, 6.0)
            width = c_w.number_input("Глубина Y, м:", 1.0, 50.0, 5.0)
            cut_x = c_l.number_input("Вырез X, м:", 0.1, float(length-0.1), 3.0)
            cut_y = c_w.number_input("Вырез Y, м:", 0.1, float(width-0.1), 2.0)
        elif shape_type == "🔲 П-образная (С вырезом)":
            length = st.number_input("Общая длина X, м:", 1.0, 50.0, 8.0)
            width = st.number_input("Общая глубина Y, м:", 1.0, 50.0, 5.0)
            c_l, c_w = st.columns(2)
            cut_w = c_l.number_input("Вырез X, м:", 0.1, float(length-0.2), 3.0)
            cut_d = c_w.number_input("Вырез Y, м:", 0.1, float(width-0.1), 2.0)
        elif shape_type == "⏺️ Округлая (Овал / Круг)":
            length = st.number_input("Длина (Диам X), м:", 1.0, 50.0, 6.0)
            width = st.number_input("Глубина (Диам Y), м:", 1.0, 50.0, 4.0)
        elif shape_type == "✏️ Свой контур (По координатам)":
            df_coords = pd.DataFrame([{"X (м)": 0.0, "Y (м)": 0.0}, {"X (м)": 0.0, "Y (м)": 4.0}, {"X (м)": 6.0, "Y (м)": 4.0}, {"X (м)": 6.0, "Y (м)": 0.0}])
            edited_df = st.data_editor(df_coords, num_rows="dynamic", use_container_width=True)
            length = 5.0; width = 5.0
            
    with c2:
        st.subheader("2. Материал Обшивки")
        brand_choice = st.selectbox("Бренд:", list(PARSED_BOARDS.keys()))
        if PARSED_BOARDS[brand_choice]:
            collection_name = st.selectbox("Коллекция:", list(PARSED_BOARDS[brand_choice].keys()))
            collection_boards = PARSED_BOARDS[brand_choice][collection_name]
            eff_w = (collection_boards[0]["width_mm"] + GAP_MM) / 1000
        else:
            st.stop()
        direction_choice = st.radio("Направление укладки:", ["Вдоль фасада (по длине X)", "Поперек фасада (по глубине Y)"])
        
        use_frame = st.checkbox("Окантовка (Picture Frame)", value=True)
        if use_frame:
            c_f1, c_f2 = st.columns(2)
            edge_front = c_f1.checkbox("Спереди", value=True)
            edge_back = c_f2.checkbox("Сзади", value=False)
            edge_left = c_f1.checkbox("Слева", value=True)
            edge_right = c_f2.checkbox("Справа", value=True)
        else:
            edge_front = edge_back = edge_left = edge_right = False

    with c3:
        st.subheader("3. Бассейн")
        has_pool = st.checkbox("Встроенный бассейн", value=False)
        if has_pool:
            pool_shape = st.radio("Форма бассейна:", ["⬜ Прямоугольный", "⏺️ Круглый", "⬭ Овальный"])
            c_pl, c_pw = st.columns(2)
            if pool_shape in ["⬜ Прямоугольный", "⬭ Овальный"]:
                pool_l = c_pl.number_input("Длина X, м:", 0.5, 20.0, 4.0)
                pool_w = c_pw.number_input("Ширина Y, м:", 0.5, 20.0, 2.5)
            else:
                pool_d = st.number_input("Диаметр бассейна, м:", 0.5, 20.0, 3.0)
            
            c_ox, c_oy = st.columns(2)
            pool_offset_x = c_ox.number_input("Смещение X, м:", 0.0, 50.0, 1.0)
            pool_offset_y = c_oy.number_input("Смещение Y, м:", 0.0, 50.0, 1.0)

    with c4:
        st.subheader("4. Подсистема")
        base_type = st.radio("Основание:", ["Грунт (Сваи)", "Бетон"])
        joist_choice = st.selectbox("Лаги (60х40):", list(PIPES_JOIST.keys()))
        frame_choice = st.selectbox("Каркас (80х80):", list(PIPES_FRAME.keys())) if "Грунт" in base_type else None
        steps_m = st.number_input("Ступени (пог.м):", 0.0, 50.0, 0.0)
"""

content = content.replace(old_ui_block, new_ui_block)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)

print(f"File updated. Done.")
