import streamlit as st
import pandas as pd
from data_loader import get_fence_prices, get_terrace_prices, save_custom_prices, reset_to_default_prices
from theme import apply_theme
import os

theme = apply_theme()

st.title("⚙️ Управление ценами")

# Простая авторизация
def check_password():
    """Returns `True` if the user had the correct password."""
    def password_entered():
        if st.session_state["password"] == os.environ.get("ADMIN_PASSWORD", "admin2000"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Введите пароль", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Введите пароль", type="password", on_change=password_entered, key="password")
        st.error("😕 Неверный пароль")
        return False
    else:
        return True

if check_password():
    st.success("Вы авторизованы.")
    
    st.markdown("Здесь вы можете изменить цены, которые используются в расчетах. Изменения сохранятся в базе данных приложения и перезапишут цены из Google Таблиц.")

    # Загружаем текущие цены (кастомные или дефолтные)
    fence_prices, fence_proflist, fence_shtaket, fence_parsed_data = get_fence_prices()
    terrace_boards, terrace_pipes_joist, terrace_pipes_frame = get_terrace_prices()

    tab1, tab2, tab3 = st.tabs(["Заборы (Одиночные цены)", "Террасы (Трубы)", "Сброс настроек"])

    with tab1:
        st.subheader("Цены на элементы заборов")
        # Преобразуем словарь в DataFrame для удобного редактирования
        df_fence = pd.DataFrame(list(fence_prices.items()), columns=["Наименование", "Цена"])
        
        edited_fence = st.data_editor(
            df_fence,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "Наименование": st.column_config.TextColumn("Наименование", disabled=False),
                "Цена": st.column_config.NumberColumn("Цена (руб)", min_value=0, step=1)
            }
        )

        st.subheader("Профлист")
        df_proflist = pd.DataFrame(list(fence_proflist.items()), columns=["Наименование", "Цена"])
        edited_proflist = st.data_editor(
            df_proflist,
            use_container_width=True,
            num_rows="dynamic"
        )

    with tab2:
        st.subheader("Трубы для террас")
        df_joist = pd.DataFrame(list(terrace_pipes_joist.items()), columns=["Труба (Лаги)", "Цена"])
        edited_joist = st.data_editor(df_joist, use_container_width=True, num_rows="dynamic")

        df_frame = pd.DataFrame(list(terrace_pipes_frame.items()), columns=["Труба (Каркас)", "Цена"])
        edited_frame = st.data_editor(df_frame, use_container_width=True, num_rows="dynamic")

    if st.button("Сохранить изменения", type="primary"):
        # Обновляем словари
        new_fence_prices = dict(zip(edited_fence["Наименование"], edited_fence["Цена"]))
        new_fence_proflist = dict(zip(edited_proflist["Наименование"], edited_proflist["Цена"]))
        
        new_terrace_joist = dict(zip(edited_joist["Труба (Лаги)"], edited_joist["Цена"]))
        new_terrace_frame = dict(zip(edited_frame["Труба (Каркас)"], edited_frame["Цена"]))

        # Формируем структуру данных для сохранения
        fence_data = {
            "prices": new_fence_prices,
            "proflist": new_fence_proflist,
            "shtaket": fence_shtaket,
            "parsed_data": fence_parsed_data
        }
        terrace_data = {
            "boards": terrace_boards,
            "pipes_joist": new_terrace_joist,
            "pipes_frame": new_terrace_frame
        }
        
        save_custom_prices(fence_data, terrace_data)
        st.success("Цены успешно сохранены и применены ко всем калькуляторам!")

    with tab3:
        st.warning("Внимание! При сбросе настроек все ваши ручные изменения будут удалены, и приложение снова начнет скачивать цены из Google Таблиц.")
        if st.button("Сбросить к настройкам по умолчанию"):
            reset_to_default_prices()
            st.success("Настройки успешно сброшены. Перезагрузите страницу для обновления таблиц.")
