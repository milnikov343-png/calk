import os

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

# Refactor the rectangle inputs
old_rect = """        if shape_type == "⬜ Прямоугольная (Стандарт)":
            length = st.number_input("Длина фасада (X), м:", 1.0, 50.0, 9.0)
            width = st.number_input("Глубина (Y), м:", 1.0, 50.0, 4.0)"""

new_rect = """        if shape_type == "⬜ Прямоугольная (Стандарт)":
            c_l, c_w = st.columns(2)
            length = c_l.number_input("Длина (X), м:", 1.0, 50.0, 9.0)
            width = c_w.number_input("Глубина (Y), м:", 1.0, 50.0, 4.0)"""
content = content.replace(old_rect, new_rect)

# Refactor columns for Subsystem
old_sub = """    with c4:
        st.subheader("4. Подсистема")
        base_type = st.radio("Основание:", ["Грунт (Сваи)", "Бетон"])
        joist_choice = st.selectbox("Лаги (60х40):", list(PIPES_JOIST.keys()))
        frame_choice = st.selectbox("Каркас (80х80):", list(PIPES_FRAME.keys())) if "Грунт" in base_type else None
        steps_m = st.number_input("Ступени (пог.м):", 0.0, 50.0, 0.0)"""

new_sub = """    with c4:
        st.subheader("4. Подсистема")
        c_sub1, c_sub2 = st.columns(2)
        with c_sub1:
             base_type = st.radio("Основание:", ["Грунт (Сваи)", "Бетон"])
             steps_m = st.number_input("Ступени (м):", 0.0, 50.0, 0.0)
        with c_sub2:
             joist_choice = st.selectbox("Лаги:", list(PIPES_JOIST.keys()))
             frame_choice = st.selectbox("Каркас:", list(PIPES_FRAME.keys())) if "Грунт" in base_type else None"""
content = content.replace(old_sub, new_sub)

# Inject CSS to make inputs even smaller natively using gap and padding
css_to_add = """/* Компактные поля ввода */
div[data-baseweb="input"] {
    font-size: 14px;
}
div[data-testid="stNumberInput"] label p, div[data-testid="stSelectbox"] label p {
    font-size: 13px !important;
}"""

if "Компактные поля ввода" not in content:
    content = content.replace("</style>", css_to_add + "\n</style>")

with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)
