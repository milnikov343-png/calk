import streamlit as st

st.set_page_config(
    page_title="OOO Дача 2000 | Умный Калькулятор",
    page_icon="🏗️",
    layout="centered"
)

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

/* Карточки действий */
.action-card {
    background: rgba(30, 41, 59, 0.7);
    border: 1px solid rgba(16, 185, 129, 0.2);
    border-radius: 16px;
    padding: 2rem;
    text-align: center;
    transition: all 0.3s ease;
    box-shadow: 0 10px 25px rgba(0,0,0,0.3);
    margin-bottom: 2rem;
    backdrop-filter: blur(10px);
}
.action-card:hover {
    transform: translateY(-5px);
    border-color: rgba(16, 185, 129, 0.6);
    box-shadow: 0 15px 35px rgba(16, 185, 129, 0.2);
    background: rgba(30, 41, 59, 0.9);
}
.card-icon {
    font-size: 4rem;
    margin-bottom: 1rem;
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
}

/* Скрываем боковую панель на главной (чтобы было похоже на лендинг) */
[data-testid="collapsedControl"] {
    display: none;
}
</style>
""", unsafe_allow_html=True)

# --- Логотип и заголовок ---
st.markdown("""
<div class="header-bar">
    <h1>ООО "Дача 2000"</h1>
    <p>Рабочая панель строительных калькуляторов</p>
</div>
""", unsafe_allow_html=True)

# Спрятать боковое меню на стартовой странице:
st.markdown(
    """
    <style>
        section[data-testid="stSidebar"] { display: none !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<br>", unsafe_allow_html=True)

col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown("""
    <div class="action-card">
        <div class="card-icon">🏗️</div>
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
    st.markdown("""
    <div class="action-card">
        <div class="card-icon">🧱</div>
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
