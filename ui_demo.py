import streamlit as st
import pandas as pd

st.set_page_config(layout="wide", page_title="Демо Интерфейса")

variant = st.sidebar.radio(
    "Выберите вариант дизайна (кликните для смены):", 
    [
        "1. Вкладки (Tabs)", 
        "2. Кнопки-меню (Popovers)", 
        "3. Умный аккордеон (Expander)", 
        "4. Классический (Sidebar)"
    ]
)

st.sidebar.info("💡 Попробуйте покрутить страницу вниз, чтобы увидеть, как себя ведет шапка в каждом варианте.")

# Имитация большого контента внизу, чтобы можно было поскроллить
def draw_dummy_content():
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; color: #1b5e20;'>Итоговая стоимость: 341,901 руб.</h2>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 🪵 Смета материалов")
        st.dataframe(pd.DataFrame({
            "Позиция": ["Доска террасная", "Каркас", "Лага", "Кляймеры"],
            "Кол-во": ["72 шт", "27 м.п.", "128 м.п.", "9 уп."],
            "Сумма": ["126,144", "12,501", "32,256", "19,800"]
        }), use_container_width=True)
    with c2:
        st.markdown("#### ⚒️ Смета работ")
        st.dataframe(pd.DataFrame({
            "Позиция": ["Монтаж настила", "Монтаж свай"],
            "Сумма": ["86,400", "64,800"]
        }), use_container_width=True)
        
    st.subheader("📐 Технические схемы")
    st.info("Здесь будут схемы террасы...")
    # Добавим пустые блоки для прокрутки
    for i in range(5):
        st.markdown("<div style='height: 200px; background-color: #f0f2f6; margin: 10px 0; border-radius: 10px; display: flex; align-items: center; justify-content: center;'>Блок с чертежом "+str(i+1)+"</div>", unsafe_allow_html=True)


if variant == "1. Вкладки (Tabs)":
    # Делаем верхний контейнер липким
    st.markdown("""<style>
    div[data-testid="stVerticalBlock"] > div:first-of-type {
        position: sticky; top: 0px; z-index: 999; background-color: white; 
        padding: 10px 0; border-bottom: 2px solid #ddd; margin-bottom: 20px;
    }
    @media (prefers-color-scheme: dark) {
        div[data-testid="stVerticalBlock"] > div:first-of-type { background-color: #0e1117; border-bottom: 2px solid #333; }
    }
    </style>""", unsafe_allow_html=True)
    
    # Очень компактная шапка
    col_logo, col_title, col_btn = st.columns([1, 6, 2])
    with col_logo:
        st.markdown("### 🟢 ДАЧА 2000")
    with col_title:
        st.markdown("#### Профессиональный проект террасы")
    with col_btn:
         st.button("🔄 Обновить прайс", key="btn1")
         
    # Сами настройки
    t1, t2, t3, t4 = st.tabs(["1. Объект и Форма", "2. Материал Обшивки", "3. Бассейн", "4. Подсистема"])
    with t1:
        st.text_input("ФИО Клиента:")
        c1, c2 = st.columns(2)
        c1.selectbox("Конфигурация:", ["Прямоугольная", "Г-образная"])
        c2.number_input("Длина (м):", 1, 50, 9)
    with t2:
        st.selectbox("Бренд:", ["LikeWood"])
    with t3:
        st.checkbox("Встроенный бассейн", value=False)
    with t4:
        st.radio("Основание:", ["Грунт (Сваи)", "Бетон"], horizontal=True)

    draw_dummy_content()


elif variant == "2. Кнопки-меню (Popovers)":
    st.markdown("""<style>
    div[data-testid="stVerticalBlock"] > div:first-of-type {
        position: sticky; top: 0px; z-index: 999; background-color: white; 
        padding: 10px 0; border-bottom: 2px solid #ddd; margin-bottom: 20px;
    }
    @media (prefers-color-scheme: dark) {
        div[data-testid="stVerticalBlock"] > div:first-of-type { background-color: #0e1117; border-bottom: 2px solid #333; }
    }
    </style>""", unsafe_allow_html=True)
    
    col_logo, col_title, col_btn = st.columns([1, 6, 2])
    with col_logo: st.markdown("### 🟢 ДАЧА 2000")
    with col_title: st.markdown("#### Профессиональный проект террасы")
    with col_btn: st.button("🔄 Обновить прайс", key="btn2")
    
    # 4 кнопки-попапа в ряд (очень экономит место!)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        with st.popover("🔲 1. Объект и Форма", use_container_width=True):
            st.text_input("ФИО Клиента:")
            st.selectbox("Конфигурация:", ["Прямоугольная", "Г-образная"], key="p_form")
            st.number_input("Длина (м):", 1, 50, 9, key="p_len")
    with c2:
        with st.popover("🪵 2. Материал Обшивки", use_container_width=True):
            st.selectbox("Бренд:", ["LikeWood"], key="p_brand")
            st.radio("Направление:", ["Вдоль", "Поперек"])
    with c3:
        with st.popover("🏊 3. Бассейн", use_container_width=True):
            st.checkbox("Встроенный бассейн", key="p_pool")
    with c4:
        with st.popover("⚙️ 4. Подсистема", use_container_width=True):
            st.radio("Основание:", ["Грунт (Сваи)", "Бетон"], key="p_base")

    draw_dummy_content()


elif variant == "3. Умный аккордеон (Expander)":
    st.markdown("""<style>
    div[data-testid="stVerticalBlock"] > div:first-of-type {
        position: sticky; top: 0px; z-index: 999; background-color: white; 
        padding: 10px 0;
    }
    @media (prefers-color-scheme: dark) {
        div[data-testid="stVerticalBlock"] > div:first-of-type { background-color: #0e1117; }
    }
    </style>""", unsafe_allow_html=True)

    col_logo, col_title, col_btn = st.columns([1, 6, 2])
    with col_logo: st.markdown("### 🟢 ДАЧА 2000")
    with col_title: st.markdown("#### Профессиональный проект")
    with col_btn: st.button("🔄 Обновить прайс", key="btn3")

    with st.expander("🛠️ РАЗВЕРНУТЬ НАСТРОЙКИ ТЕРРАСЫ (Кликните чтобы скрыть)", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown("**1. Объект**")
            st.text_input("ФИО Клиента:")
            st.selectbox("Конфигурация:", ["Прямоугольная", "Г-образная"], key="e_form")
        with c2:
            st.markdown("**2. Материал**")
            st.selectbox("Бренд:", ["LikeWood"], key="e_brand")
        with c3:
            st.markdown("**3. Бассейн**")
            st.checkbox("Встроенный бассейн", key="e_pool")
        with c4:
            st.markdown("**4. Каркас**")
            st.radio("Основание:", ["Грунт (Сваи)", "Бетон"], key="e_base")

    draw_dummy_content()


elif variant == "4. Классический (Sidebar)":
    # Убираем кастомный CSS (нет липкой верхней шапки, кроме стандартного хедера Streamlit)
    
    col_logo, col_title, col_btn = st.columns([1, 6, 2])
    with col_logo: st.markdown("### 🟢 ДАЧА 2000")
    with col_title: st.markdown("#### Профессиональный проект террасы")
    with col_btn: st.button("🔄 Обновить прайс", key="btn4")
    st.divider()

    with st.sidebar:
        st.markdown("### Настройки проекта")
        
        st.markdown("**1. Объект и Форма**")
        st.text_input("ФИО Клиента:")
        st.selectbox("Конфигурация:", ["Прямоугольная", "Г-образная"], key="s_form")
        st.divider()
        
        st.markdown("**2. Материал**")
        st.selectbox("Бренд:", ["LikeWood"], key="s_brand")
        st.divider()

        st.markdown("**3. Бассейн**")
        st.checkbox("Встроенный бассейн", key="s_pool")
        st.divider()

        st.markdown("**4. Подсистема**")
        st.radio("Основание:", ["Грунт", "Бетон"], key="s_base")
        st.divider()

    draw_dummy_content()
