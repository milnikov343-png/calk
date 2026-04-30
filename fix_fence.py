import re

with open("pages/fence_calculator.py", "r") as f:
    content = f.read()

# 1. Fix Material Symbol in HTML Title
content = content.replace(
    ":material/home: Калькулятор заборов",
    "<span class='material-symbols-outlined' style='vertical-align: bottom;'>home</span> Калькулятор заборов"
)

# Also ensure we add the Material Symbols stylesheet to global CSS in app.py and fence_calculator.py
css_import = "@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0');\n"
if "Material+Symbols+Outlined" not in content:
    content = content.replace("<style>\n", f"<style>\n{css_import}")

# 2. Fix Brick Pillars logic (only if foundation is checked)
# First add key="has_fund_checkbox" to the checkbox
content = content.replace(
    'has_fundament = st.checkbox("Рассчитать фундамент", value=True)',
    'has_fundament = st.checkbox("Рассчитать фундамент", value=True, key="has_fund_checkbox")'
)

# Then conditionally show post_type
old_post_type_block = """        # --- Тип столбов ---
        post_type = st.selectbox("Тип столбов:", ["Металлические", "Кирпичные"], key="post_type_sel")
        post_type_val = "brick" if post_type == "Кирпичные" else "metal\"\"\""""
# actually we can just regex it
content = re.sub(
    r'(# --- Тип столбов ---\n\s+)post_type = st\.selectbox\("Тип столбов:", \["Металлические", "Кирпичные"\], key="post_type_sel"\)',
    r'\1if st.session_state.get("has_fund_checkbox", True):\n\1    post_type = st.selectbox("Тип столбов:", ["Металлические", "Кирпичные"], key="post_type_sel")\n\1else:\n\1    post_type = "Металлические"',
    content
)

# 3. Fix lag calculation (only for Профнастил, Штакет, Шахматка)
content = re.sub(
    r'(lag_total_count = sections \* lag_rows)',
    r'lag_total_count = \1 if material_type in ["Профнастил", "Штакет", "Шахматка"] else 0',
    content
)

content = re.sub(
    r'(lag_total_count = section_count \* lag_rows)',
    r'lag_total_count = \1 if material_type in ["Профнастил", "Штакет", "Шахматка"] else 0',
    content
)

with open("pages/fence_calculator.py", "w") as f:
    f.write(content)

print("Done")
