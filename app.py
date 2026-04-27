import streamlit as st
import base64
import os

st.set_page_config(
    page_title="OOO Дача 2000 | Умный Калькулятор",
    page_icon=":material/home:",
    layout="wide"
)

if 'theme' not in st.session_state:
    st.session_state.theme = 'dark'

# Функция для конвертации картинки в base64
def get_image_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    return ""

# Пути к картинкам
terrace_img_path = os.path.join(os.path.dirname(__file__), "terrace_thumb.png")
fence_img_path = os.path.join(os.path.dirname(__file__), "fence_thumb.png")
money_img_path = os.path.join(os.path.dirname(__file__), "money_thumb.png")

terrace_b64 = get_image_base64(terrace_img_path)
fence_b64 = get_image_base64(fence_img_path)
money_b64 = get_image_base64(money_img_path)

# --- Переключатель темы ---
col_empty, col_toggle = st.columns([8, 2])
with col_toggle:
    theme_choice = st.radio("Тема", [":material/dark_mode: Тёмная", ":material/light_mode: Светлая"], horizontal=True, label_visibility="collapsed")
    st.session_state.theme = 'light' if "Светлая" in theme_choice else 'dark'

is_light = st.session_state.theme == 'light'

# Переменные для CSS
bg_app = "linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)" if is_light else "linear-gradient(135deg, #0a0e17 0%, #111827 50%, #1f2937 100%)"
text_main = "#1e293b" if is_light else "#e5e7eb"
h1_color = "#0f172a" if is_light else "#ffffff"
h1_shadow = "none" if is_light else "0 4px 15px rgba(0,0,0,0.4)"
p_color = "#059669" if is_light else "#10b981"
card_bg = "rgba(255, 255, 255, 0.9)" if is_light else "rgba(30, 41, 59, 0.7)"
card_border = "rgba(16, 185, 129, 0.4)" if is_light else "rgba(16, 185, 129, 0.2)"
card_shadow = "0 4px 10px rgba(0,0,0,0.05)" if is_light else "0 10px 25px rgba(0,0,0,0.3)"
card_hover_bg = "#ffffff" if is_light else "rgba(30, 41, 59, 0.9)"
card_hover_shadow = "0 10px 20px rgba(16, 185, 129, 0.15)" if is_light else "0 15px 35px rgba(16, 185, 129, 0.2)"
card_title = "#0f172a" if is_light else "#ffffff"
card_desc = "#475569" if is_light else "#94a3b8"
dummy_img_bg = "#e2e8f0" if is_light else "#333"

# --- Эстетика стартовой страницы ---
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
}}

/* Фон страницы */
.stApp {{
    background: {bg_app};
    color: {text_main};
}}

/* Заголовок-шапка */
.header-bar {{
    text-align: center;
    padding: 0rem 0 2rem 0;
}}
.header-bar h1 {{
    color: {h1_color};
    font-weight: 800;
    font-size: 2.8rem;
    margin-bottom: 0.5rem;
    text-shadow: {h1_shadow};
}}
.header-bar p {{
    color: {p_color};
    font-size: 1.2rem;
    font-weight: 400;
}}

/* Контейнеры колонок */
div[data-testid="column"] {{
    display: flex;
    flex-direction: column;
}}

/* Карточки действий */
.action-card {{
    background: {card_bg};
    border: 1px solid {card_border};
    border-radius: 16px;
    padding: 1.5rem;
    text-align: center;
    transition: all 0.3s ease;
    box-shadow: {card_shadow};
    margin-bottom: 1rem;
    backdrop-filter: blur(10px);
    
    /* Flexbox для одинаковой высоты */
    display: flex;
    flex-direction: column;
    flex: 1 1 auto;
    height: 100%;
}}
.action-card:hover {{
    transform: translateY(-5px);
    border-color: rgba(16, 185, 129, 0.6);
    box-shadow: {card_hover_shadow};
    background: {card_hover_bg};
}}
.card-image {{
    width: 100%;
    height: 220px;
    object-fit: cover;
    border-radius: 12px;
    margin-bottom: 1.2rem;
    border: 1px solid rgba(255,255,255,0.05);
}}
.card-title {{
    font-size: 1.5rem;
    font-weight: 800;
    color: {card_title};
    margin-bottom: 1rem;
}}
.card-desc {{
    color: {card_desc};
    font-size: 0.95rem;
    line-height: 1.5;
    margin-bottom: 1.5rem;
    flex-grow: 1; /* Описание занимает всё свободное место, выравнивая низ */
}}

/* Скрываем боковую панель на главной */
[data-testid="collapsedControl"] {{
    display: none;
}}
section[data-testid="stSidebar"] {{ 
    display: none !important; 
}}
</style>
""", unsafe_allow_html=True)

# --- Логотип и заголовок ---
st.markdown("""
<div class="header-bar">
    <h1>ООО "Дача 2000"</h1>
    <p>Рабочая панель строительных калькуляторов</p>
</div>
<br>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3, gap="large")

with col1:
    img_tag_1 = f'<img src="data:image/png;base64,{terrace_b64}" class="card-image">' if terrace_b64 else f'<div class="card-image" style="background:{dummy_img_bg}; display:flex; align-items:center; justify-content:center; font-size:3rem;">:material/construction:</div>'
    
    st.markdown(f"""
    <div class="action-card">
        {img_tag_1}
        <div class="card-title">:material/deck: Расчёт Террас</div>
        <div class="card-desc">
            Визуальный расчёт прямых, угловых и П-образных террас.
            Калькуляция материалов, смета шурфов и лаг.
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Открыть Калькулятор Террас", use_container_width=True, type="primary"):
        st.switch_page("pages/terrace_calculator.py")

with col2:
    img_tag_2 = f'<img src="data:image/png;base64,{fence_b64}" class="card-image">' if fence_b64 else f'<div class="card-image" style="background:{dummy_img_bg}; display:flex; align-items:center; justify-content:center; font-size:3rem;">:material/shield:</div>'
    
    st.markdown(f"""
    <div class="action-card">
        {img_tag_2}
        <div class="card-title">:material/fence: Расчёт Заборов</div>
        <div class="card-desc">
            Профлист, штакет, шахматка, жалюзи. Автоматический расчёт
            столбов, ворот, калиток и стоимости фундамента.
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Открыть Калькулятор Заборов", use_container_width=True, type="primary"):
        st.switch_page("pages/fence_calculator.py")

with col3:
    img_tag_3 = f'<img src="data:image/png;base64,{money_b64}" class="card-image">' if money_b64 else f'<div class="card-image" style="background:{dummy_img_bg}; display:flex; align-items:center; justify-content:center; font-size:3rem;">:material/bar_chart:</div>'
    
    st.markdown(f"""
    <div class="action-card">
        {img_tag_3}
        <div class="card-title">:material/request_quote: Прайс на работы</div>
        <div class="card-desc">
            Актуальные расценки на строительные и монтажные работы по заборам.
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Открыть Прайс на работы по забору", use_container_width=True, type="primary"):
        st.switch_page("pages/fence_prices.py")

st.markdown("<br><hr style='opacity: 0.1;'><div style='text-align: center; color: #64748b; font-size: 0.8rem;'>Внутренняя система Дача 2000 | Версия 2.0</div>", unsafe_allow_html=True)
