import streamlit as st
import math
import json
import os

st.set_page_config(
    page_title="Прайс на работы по забору",
    page_icon="📋",
    layout="wide"
)

# --- Стили ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');

.stApp {
    background: linear-gradient(135deg, #0a0e17 0%, #111827 50%, #1f2937 100%);
    color: #f8f9fa;
    font-family: 'Inter', sans-serif;
}
.header-prices {
    text-align: center;
    padding: 2rem 0 1rem 0;
}
.header-prices h1 {
    color: #ffffff;
    font-weight: 800;
    font-size: 2rem;
}
.price-section {
    margin-top: 2.5rem;
    margin-bottom: 0.5rem;
}
.price-section-title {
    font-size: 1.4rem;
    font-weight: 700;
    margin-bottom: 1rem;
    padding: 10px 16px;
    border-radius: 8px 8px 0 0;
}
.price-section-title.blue { background: rgba(0, 168, 255, 0.15); color: #00a8ff; }
.price-section-title.green { background: rgba(16, 185, 129, 0.15); color: #10b981; }
.price-section-title.purple { background: rgba(156, 136, 255, 0.15); color: #9c88ff; }
.price-section-title.orange { background: rgba(251, 197, 49, 0.15); color: #fbc531; }
.price-section-title.pink { background: rgba(232, 67, 147, 0.15); color: #e84393; }

.price-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 2rem;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 0 0 8px 8px;
    overflow: hidden;
}
.price-table th {
    background: rgba(255, 255, 255, 0.06);
    color: #a0aec0;
    padding: 12px 18px;
    text-align: left;
    font-weight: 600;
    font-size: 0.9rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}
.price-table th.price-col {
    text-align: right;
    min-width: 120px;
}
.price-table td {
    padding: 11px 18px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    color: #e2e8f0;
}
.price-table tr:last-child td {
    border-bottom: none;
}
.price-table tr:hover td {
    background: rgba(255, 255, 255, 0.06);
}
.pv {
    font-weight: 700;
    color: #fbc531;
    text-align: right;
    font-size: 1.05rem;
}
.range-cell {
    font-weight: 600;
    color: #cbd5e0;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="header-prices"><h1>📋 Прайс на работы по забору</h1></div>', unsafe_allow_html=True)

# --- Загрузка данных из кэша ---
PARSED_PRICES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "parsed_prices.json")

def load_works_data():
    """Загружает данные из кэшированного JSON (parsed_prices.json)."""
    if os.path.exists(PARSED_PRICES_FILE):
        with open(PARSED_PRICES_FILE, "r", encoding="utf-8") as f:
            parsed = json.load(f)
        return parsed.get("works", {})
    return {}

def add_margin(val):
    """Наценка 20% с округлением до 10 руб."""
    if not isinstance(val, (int, float)):
        return val
    return math.ceil(val * 1.2 / 10) * 10

works_data = load_works_data()

if not works_data:
    st.error("⚠️ Данные о ценах не найдены. Сначала откройте калькулятор заборов, чтобы загрузить актуальные цены из Google Таблицы.")
else:
    standard = works_data.get("standard", [])
    premium = works_data.get("premium", [])
    additional = works_data.get("additional", [])

    # ==========================================
    # 1. Профнастил / 3D сетка / Рабица — 2 ЛАГИ
    # ==========================================
    st.markdown("""
    <div class="price-section">
        <div class="price-section-title blue">🏗️ Профнастил, 3D сетка, Рабица, Штакетник односторонний — монтаж с 2 лагами (₽/м.п.)</div>
        <table class="price-table">
            <tr><th>Общий метраж забора</th><th class="price-col">Цена за м.п.</th></tr>
    """, unsafe_allow_html=True)
    rows_html = ""
    for item in standard:
        rows_html += f'<tr><td class="range-cell">{item["range"]} м</td><td class="pv">{add_margin(item["prof_2lag"]):,.0f} ₽</td></tr>'
    st.markdown(rows_html + "</table></div>", unsafe_allow_html=True)

    # ==========================================
    # 2. Профнастил / Штакетник — 3 ЛАГИ
    # ==========================================
    st.markdown("""
    <div class="price-section">
        <div class="price-section-title green">🏗️ Профнастил, Штакетник односторонний, Сайдинг, Каменное дерево — монтаж с 3 лагами (₽/м.п.)</div>
        <table class="price-table">
            <tr><th>Общий метраж забора</th><th class="price-col">Цена за м.п.</th></tr>
    """, unsafe_allow_html=True)
    rows_html = ""
    for item in standard:
        rows_html += f'<tr><td class="range-cell">{item["range"]} м</td><td class="pv">{add_margin(item["prof_3lag"]):,.0f} ₽</td></tr>'
    st.markdown(rows_html + "</table></div>", unsafe_allow_html=True)

    # ==========================================
    # 3. Штакетник двусторонний / Шахматка
    # ==========================================
    st.markdown("""
    <div class="price-section">
        <div class="price-section-title orange">🚧 Штакетник двусторонний / Шахматка — монтаж (₽/м.п.)</div>
        <table class="price-table">
            <tr><th>Общий метраж забора</th><th class="price-col">Цена за м.п.</th></tr>
    """, unsafe_allow_html=True)
    rows_html = ""
    for item in standard:
        rows_html += f'<tr><td class="range-cell">{item["range"]} м</td><td class="pv">{add_margin(item["shtaket_2side"]):,.0f} ₽</td></tr>'
    st.markdown(rows_html + "</table></div>", unsafe_allow_html=True)

    # ==========================================
    # 4. Жалюзи / Ранчо
    # ==========================================
    st.markdown("""
    <div class="price-section">
        <div class="price-section-title purple">✨ Жалюзи / Ранчо — монтаж (₽/м.п.)</div>
        <table class="price-table">
            <tr><th>Общий метраж забора</th><th class="price-col">Цена за м.п.</th></tr>
    """, unsafe_allow_html=True)
    rows_html = ""
    for item in premium:
        rows_html += f'<tr><td class="range-cell">{item["range"]} м</td><td class="pv">{add_margin(item["price"]):,.0f} ₽</td></tr>'
    st.markdown(rows_html + "</table></div>", unsafe_allow_html=True)

    # ==========================================
    # Разделяем additional на категории
    # ==========================================
    montazh_works = []
    otkatnye_gates = []
    raspashnye_gates = []
    kalitki_items = []

    for item in additional:
        nl = item["name"].lower()
        if "ворота откатные под" in nl:
            otkatnye_gates.append(item)
        elif "ворота распашные под" in nl:
            raspashnye_gates.append(item)
        elif "калитка под" in nl:
            kalitki_items.append(item)
        else:
            montazh_works.append(item)

    # ==========================================
    # 5. Дополнительные работы (монтаж)
    # ==========================================
    st.markdown("""
    <div class="price-section">
        <div class="price-section-title green">🛠️ Дополнительные работы (Монтаж)</div>
        <table class="price-table">
            <tr><th>Наименование работы</th><th>Ед. изм.</th><th class="price-col">Цена</th></tr>
    """, unsafe_allow_html=True)
    rows_html = ""
    for item in montazh_works:
        rows_html += f'<tr><td>{item["name"]}</td><td>{item["unit"]}</td><td class="pv">{add_margin(item["price"]):,.0f} ₽</td></tr>'
    st.markdown(rows_html + "</table></div>", unsafe_allow_html=True)

    # ==========================================
    # 6. Ворота откатные (комплекты)
    # ==========================================
    st.markdown("""
    <div class="price-section">
        <div class="price-section-title blue">🚪 Ворота откатные — комплекты</div>
        <table class="price-table">
            <tr><th>Модель</th><th>Ед.</th><th class="price-col">Цена</th></tr>
    """, unsafe_allow_html=True)
    rows_html = ""
    for item in otkatnye_gates:
        rows_html += f'<tr><td>{item["name"]}</td><td>{item["unit"]}</td><td class="pv">{add_margin(item["price"]):,.0f} ₽</td></tr>'
    st.markdown(rows_html + "</table></div>", unsafe_allow_html=True)

    # ==========================================
    # 7. Ворота распашные (комплекты)
    # ==========================================
    st.markdown("""
    <div class="price-section">
        <div class="price-section-title pink">🚪 Ворота распашные — комплекты</div>
        <table class="price-table">
            <tr><th>Модель</th><th>Ед.</th><th class="price-col">Цена</th></tr>
    """, unsafe_allow_html=True)
    rows_html = ""
    for item in raspashnye_gates:
        rows_html += f'<tr><td>{item["name"]}</td><td>{item["unit"]}</td><td class="pv">{add_margin(item["price"]):,.0f} ₽</td></tr>'
    st.markdown(rows_html + "</table></div>", unsafe_allow_html=True)

    # ==========================================
    # 8. Калитки (комплекты)
    # ==========================================
    st.markdown("""
    <div class="price-section">
        <div class="price-section-title orange">🚪 Калитки — комплекты</div>
        <table class="price-table">
            <tr><th>Модель</th><th>Ед.</th><th class="price-col">Цена</th></tr>
    """, unsafe_allow_html=True)
    rows_html = ""
    for item in kalitki_items:
        rows_html += f'<tr><td>{item["name"]}</td><td>{item["unit"]}</td><td class="pv">{add_margin(item["price"]):,.0f} ₽</td></tr>'
    st.markdown(rows_html + "</table></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
if st.button("⬅ Назад на главную", type="primary"):
    st.switch_page("app.py")
