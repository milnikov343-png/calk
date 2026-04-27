import os

def replace_in_file(filepath, replacements):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    for old, new in replacements:
        content = content.replace(old, new)
        
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

fence_replacements = [
    ("#### 📐 1. Габариты и Материал", "#### 📏 1. Габариты и Материал"),
    ("#### 🚪 2. Ворота, Калитки, Столбы", "#### 🛡️ 2. Ворота, Калитки, Столбы"),
    ("#### 📦 3. Доставка и Фундамент", "#### 🚚 3. Доставка и Фундамент"),
    ('st.tabs(["⚒️ Работы", "📦 Материалы", "📋 Полная калькуляция"])', 'st.tabs(["🛠️ Работы", "🧱 Материалы", "📊 Полная калькуляция"])'),
    ('st.expander("🛠️ ПАРАМЕТРЫ ЗАБОРА', 'st.expander("⚙️ ПАРАМЕТРЫ ЗАБОРА'),
    ('🏗️ Калькулятор заборов', '🏡 Калькулятор заборов')
]

terrace_replacements = [
    ("#### 📐 1. Габариты и Бассейн", "#### 📏 1. Габариты и Бассейн"),
    ("#### 🪵 2. Обшивка и Периметр", "#### 🪵 2. Обшивка и Периметр"), # leave log for wood
    ("#### ⛓️ 3. Фундамент и Каркас", "#### 🏗️ 3. Фундамент и Каркас"),
    ('colA.markdown("#### 🪵 Смета материалов")', 'colA.markdown("#### 🧱 Смета материалов")'),
    ('colB.markdown("#### ⚒️ Смета работ")', 'colB.markdown("#### 🛠️ Смета работ")'),
    ('st.expander("🛠️ ПАРАМЕТРЫ ТЕРРАСЫ', 'st.expander("⚙️ ПАРАМЕТРЫ ТЕРРАСЫ'),
    ('🏗️ Калькулятор террас', '🏡 Калькулятор террас')
]

replace_in_file("pages/fence_calculator.py", fence_replacements)
replace_in_file("pages/terrace_calculator.py", terrace_replacements)

print("Updated emojis")
