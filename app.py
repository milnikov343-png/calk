import streamlit as st
import base64
import os

st.set_page_config(
    page_title="OOO Дача 2000 | Умный Калькулятор",
    page_icon="🏗️",
    layout="centered"
)

# Функция для конвертации картинки в base64
def get_image_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    return ""

# Пути к картинкам
terrace_img_path = os.path.join(os.path.dirname(__file__), "terrace_thumb.png")
fence_img_path = os.path.join(os.path.dirname(__file__), "fence_thumb.png")

terrace_b64 = get_image_base64(terrace_img_path)
fence_b64 = get_image_base64(fence_img_path)

# --- Эстетика стартовой страницы ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Фон страницы */
.stApp {
    background: linear-gradient(135deg, #0a0e17 0%, #111827 50%, #1f2937 100%);
    color: #e5e7eb;
}

/* Заголовок-шапка */
.header-bar {
    text-align: center;
    padding: 2rem 0;
}
.header-bar h1 {
    color: #ffffff;
    font-weight: 800;
    font-size: 2.8rem;
    margin-bottom: 0.5rem;
    text-shadow: 0 4px 15px rgba(0,0,0,0.4);
}
.header-bar p {
    color: #10b981;
    font-size: 1.2rem;
    font-weight: 400;
}

/* Контейнеры колонок */
div[data-testid="column"] {
    display: flex;
    flex-direction: column;
}

/* Карточки действий */
.action-card {
    background: rgba(30, 41, 59, 0.7);
    border: 1px solid rgba(16, 185, 129, 0.2);
    border-radius: 16px;
    padding: 1.5rem;
    text-align: center;
    transition: all 0.3s ease;
    box-shadow: 0 10px 25px rgba(0,0,0,0.3);
    margin-bottom: 1rem;
    backdrop-filter: blur(10px);
    
    /* Flexbox для одинаковой высоты */
    display: flex;
    flex-direction: column;
    flex: 1 1 auto;
    height: 100%;
}
.action-card:hover {
    transform: translateY(-5px);
    border-color: rgba(16, 185, 129, 0.6);
    box-shadow: 0 15px 35px rgba(16, 185, 129, 0.2);
    background: rgba(30, 41, 59, 0.9);
}
.card-image {
    width: 100%;
    height: 220px;
    object-fit: cover;
    border-radius: 12px;
    margin-bottom: 1.2rem;
    border: 1px solid rgba(255,255,255,0.05);
}
.card-title {
    font-size: 1.5rem;
    font-weight: 800;
    color: #ffffff;
    margin-bottom: 1rem;
}
.card-desc {
    color: #94a3b8;
    font-size: 0.95rem;
    line-height: 1.5;
    margin-bottom: 1.5rem;
    flex-grow: 1; /* Описание занимает всё свободное место, выравнивая низ */
}

/* Скрываем боковую панель на главной (чтобы было похоже на лендинг) */
[data-testid="collapsedControl"] {
    display: none;
}
section[data-testid="stSidebar"] { 
    display: none !important; 
}
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

col1, col2 = st.columns(2, gap="large")

with col1:
    img_tag_1 = f'<img src="data:image/png;base64,{terrace_b64}" class="card-image">' if terrace_b64 else '<div class="card-image" style="background:#333; display:flex; align-items:center; justify-content:center; font-size:3rem;">🏗️</div>'
    
    st.markdown(f"""
    <div class="action-card">
        {img_tag_1}
        <div class="card-title">Расчёт Террас</div>
        <div class="card-desc">
            Визуальный расчёт прямых, угловых и П-образных террас.
            Калькуляция материалов, смета шурфов и лаг.
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Открыть Калькулятор Террас", use_container_width=True, type="primary"):
        st.switch_page("pages/terrace_calculator.py")

with col2:
    img_tag_2 = f'<img src="data:image/png;base64,{fence_b64}" class="card-image">' if fence_b64 else '<div class="card-image" style="background:#333; display:flex; align-items:center; justify-content:center; font-size:3rem;">🧱</div>'
    
    st.markdown(f"""
    <div class="action-card">
        {img_tag_2}
        <div class="card-title">Расчёт Заборов</div>
        <div class="card-desc">
            Профлист, штакет, шахматка. Автоматический расчёт
            столбов, ворот, калиток и стоимости фундамента.
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Открыть Калькулятор Заборов", use_container_width=True, type="primary"):
        st.switch_page("pages/fence_calculator.py")

st.markdown("<br><hr style='opacity: 0.1;'><div style='text-align: center; color: #64748b; font-size: 0.8rem;'>Внутренняя система Дача 2000 | Версия 2.0</div>", unsafe_allow_html=True)
