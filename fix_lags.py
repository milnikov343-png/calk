import re

with open("pages/fence_calculator.py", "r") as f:
    content = f.read()

replacement = """
        # --- Тип трубы для лаг ---
        show_lags = False
        if calc_mode == "express":
            show_lags = material_type in ["Профнастил", "Штакет", "Шахматка"]
        else:
            show_lags = any(s["material_type"] in ["Профнастил", "Штакет", "Шахматка"] for s in sides_data)

        if show_lags:
            lag_pipe_type = st.selectbox("Труба для лаг:", ["40x20x1.5 мм", "40x20x2 мм"], key="lag_pipe_sel")
            lag_pipe_val = "40x20x2" if "2 мм" in lag_pipe_type else "40x20x1.5"
            lag_rows = st.radio("Количество рядов лаг:", [2, 3], horizontal=True)
        else:
            lag_pipe_type = "40x20x1.5 мм"
            lag_pipe_val = "40x20x1.5"
            lag_rows = 2
"""

# Find the lag UI block
content = re.sub(
    r'(\s+)# --- Тип трубы для лаг ---\n\s+lag_pipe_type = st\.selectbox\("Труба для лаг:", \["40x20x1\.5 мм", "40x20x2 мм"\], key="lag_pipe_sel"\)\n\s+lag_pipe_val = "40x20x2" if "2 мм" in lag_pipe_type else "40x20x1\.5"\n\s+lag_rows = st\.radio\("Количество рядов лаг:", \[2, 3\], horizontal=True\)',
    replacement,
    content
)

with open("pages/fence_calculator.py", "w") as f:
    f.write(content)

print("Done")
