import streamlit as st
import base64
import os
import datetime

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

from theme import apply_theme
theme = apply_theme()

is_light = theme["is_light"]
card_bg = theme["card_bg"]
card_border = theme["card_border"]
dummy_img_bg = theme["dummy_img_bg"]

# --- Логотип и заголовок ---
st.markdown("""
<div class="header-bar-main">
    <h1>ООО "Дача 2000"</h1>
    <p>Рабочая панель строительных калькуляторов</p>
</div>
""", unsafe_allow_html=True)

# --- Часы UTC+5 ---
utc5 = datetime.timezone(datetime.timedelta(hours=5))
now_utc5 = datetime.datetime.now(utc5)

clock_text = now_utc5.strftime("%H:%M:%S")
clock_date = now_utc5.strftime("%d.%m.%Y")
clock_weekday_num = now_utc5.weekday()
weekdays_ru = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
clock_weekday = weekdays_ru[clock_weekday_num]

clock_bg = "#ffffff" if is_light else "#252525"
clock_border = "#e0e0e0" if is_light else "#333333"
clock_time_color = "#191919" if is_light else "#ffffff"
clock_date_color = "#9fcb3d"
clock_label_color = "#666666" if is_light else "#a0a0a0"

st.markdown(f"""
<div id="clock-container" style="
    text-align: center;
    margin: 0 auto 2rem auto;
    max-width: 480px;
    padding: 1.2rem 2rem;
    background: {clock_bg};
    border: 1px solid {clock_border};
    border-radius: 16px;
    backdrop-filter: blur(12px);
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
">
    <div style="font-size: 0.75rem; text-transform: uppercase; letter-spacing: 3px; color: {clock_label_color}; margin-bottom: 0.3rem; font-weight: 600;">UTC+5</div>
    <div id="live-time" style="
        font-size: 3.5rem;
        font-weight: 800;
        color: {clock_time_color};
        font-family: 'Inter', monospace;
        line-height: 1.1;
        letter-spacing: 2px;
    ">{clock_text}</div>
    <div id="live-date" style="
        font-size: 1.1rem;
        color: {clock_date_color};
        font-weight: 500;
        margin-top: 0.3rem;
    ">{clock_weekday}, {clock_date}</div>
</div>

<script>
(function() {{
    const weekdays = ['Воскресенье','Понедельник','Вторник','Среда','Четверг','Пятница','Суббота'];
    function updateClock() {{
        const now = new Date();
        const utc = now.getTime() + now.getTimezoneOffset() * 60000;
        const utc5 = new Date(utc + 5 * 3600000);
        const h = String(utc5.getHours()).padStart(2, '0');
        const m = String(utc5.getMinutes()).padStart(2, '0');
        const s = String(utc5.getSeconds()).padStart(2, '0');
        const d = String(utc5.getDate()).padStart(2, '0');
        const mo = String(utc5.getMonth() + 1).padStart(2, '0');
        const y = utc5.getFullYear();
        const wd = weekdays[utc5.getDay()];
        const timeEl = document.getElementById('live-time');
        const dateEl = document.getElementById('live-date');
        if (timeEl) timeEl.textContent = h + ':' + m + ':' + s;
        if (dateEl) dateEl.textContent = wd + ', ' + d + '.' + mo + '.' + y;
    }}
    updateClock();
    setInterval(updateClock, 1000);
}})()
</script>
""", unsafe_allow_html=True)


col1, col2, col3 = st.columns(3, gap="large")

with col1:
    img_tag_1 = f'<img src="data:image/png;base64,{terrace_b64}" class="card-image">' if terrace_b64 else f'<div class="card-image" style="background:{dummy_img_bg}; display:flex; align-items:center; justify-content:center; font-size:3rem;"><span class="material-symbols-outlined" style="vertical-align: bottom;">construction</span></div>'
    
    st.markdown(f"""
    <div class="action-card">
        {img_tag_1}
        <div class="card-title"><span class="material-symbols-outlined" style="vertical-align: bottom;">deck</span> Расчёт Террас</div>
        <div class="card-desc">
            Визуальный расчёт прямых, угловых и П-образных террас.
            Калькуляция материалов, смета шурфов и лаг.
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Открыть Калькулятор Террас", use_container_width=True, type="primary"):
        st.switch_page("pages/terrace_calculator.py")

with col2:
    img_tag_2 = f'<img src="data:image/png;base64,{fence_b64}" class="card-image">' if fence_b64 else f'<div class="card-image" style="background:{dummy_img_bg}; display:flex; align-items:center; justify-content:center; font-size:3rem;"><span class="material-symbols-outlined" style="vertical-align: bottom;">shield</span></div>'
    
    st.markdown(f"""
    <div class="action-card">
        {img_tag_2}
        <div class="card-title"><span class="material-symbols-outlined" style="vertical-align: bottom;">fence</span> Расчёт Заборов</div>
        <div class="card-desc">
            Профлист, штакет, шахматка, жалюзи. Автоматический расчёт
            столбов, ворот, калиток и стоимости фундамента.
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Открыть Калькулятор Заборов", use_container_width=True, type="primary"):
        st.switch_page("pages/fence_calculator.py")

with col3:
    img_tag_3 = f'<img src="data:image/png;base64,{money_b64}" class="card-image">' if money_b64 else f'<div class="card-image" style="background:{dummy_img_bg}; display:flex; align-items:center; justify-content:center; font-size:3rem;"><span class="material-symbols-outlined" style="vertical-align: bottom;">bar_chart</span></div>'
    
    st.markdown(f"""
    <div class="action-card">
        {img_tag_3}
        <div class="card-title"><span class="material-symbols-outlined" style="vertical-align: bottom;">request_quote</span> Прайс на работы</div>
        <div class="card-desc">
            Актуальные расценки на строительные и монтажные работы по заборам.
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Открыть Прайс на работы по забору", use_container_width=True, type="primary"):
        st.switch_page("pages/fence_prices.py")

st.markdown("<br><hr style='opacity: 0.1; border-color: #a0a0a0;'><div style='text-align: center; color: #a0a0a0; font-size: 0.8rem;'>Внутренняя система Дача 2000 | Версия 2.0</div>", unsafe_allow_html=True)
