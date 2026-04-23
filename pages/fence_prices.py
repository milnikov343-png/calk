import streamlit as st
import pandas as pd
import math

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
.header {
    text-align: center;
    padding: 2rem 0;
}
.header h1 {
    color: #ffffff;
    font-weight: 800;
}
.header p {
    color: #10b981;
    font-size: 1.2rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="header"><h1>Прайс на работы по забору</h1><p>Актуальные расценки на монтаж и дополнительные работы (включая наценку 20%)</p></div>', unsafe_allow_html=True)

import os

FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fence_works_prices.xlsx')

try:
    df = pd.read_excel(FILE_PATH)
    
    # Разделяем таблицу на две части: "Погонный метр" и "Дополнительные работы"
    # Первые 4 колонки - это расценки за м.п.
    df_mp = df.iloc[:8, :4].copy()
    
    # Добавляем наценку 20% и округляем до 10 рублей
    def add_margin(val):
        if pd.isna(val) or not isinstance(val, (int, float)):
            return val
        return math.ceil(val * 1.2 / 10) * 10

    for col in df_mp.columns[1:]:
        df_mp[col] = df_mp[col].apply(add_margin)
        
    # Колонки с дополнительными работами
    df_add = df.iloc[:, 6:9].copy().dropna(how='all')
    df_add['цена'] = df_add['цена'].apply(add_margin)
    
    st.markdown("### 📏 Стоимость монтажа за 1 м.п.")
    st.dataframe(df_mp, width="stretch", hide_index=True)
    
    st.markdown("---")
    st.markdown("### 🛠️ Дополнительные работы")
    st.dataframe(df_add, width="stretch", hide_index=True)
    
except Exception as e:
    st.error(f"Не удалось загрузить прайс-лист. Ошибка: {e}")

if st.button("⬅ Назад на главную", type="primary"):
    st.switch_page("app.py")
