import os
import re

replacements = [
    # Fence calculator
    ('st.title("🏡 Калькулятор заборов")', 'st.markdown("# :material/fence: Калькулятор заборов")'),
    ('st.expander("⚙️ ПАРАМЕТРЫ ЗАБОРА"', 'st.expander("ПАРАМЕТРЫ ЗАБОРА", icon=":material/settings:")'),
    ('st.expander("🛠️ ПАРАМЕТРЫ ЗАБОРА"', 'st.expander("ПАРАМЕТРЫ ЗАБОРА", icon=":material/settings:")'),
    ('#### 📏 1. Габариты и Материал', '#### :material/straighten: 1. Габариты и Материал'),
    ('#### 📐 1. Габариты и Материал', '#### :material/straighten: 1. Габариты и Материал'),
    ('#### 🚪 2. Ворота, Калитки, Столбы', '#### :material/sensor_door: 2. Ворота, Калитки, Столбы'),
    ('#### 🛡️ 2. Ворота, Калитки, Столбы', '#### :material/sensor_door: 2. Ворота, Калитки, Столбы'),
    ('#### 🚚 3. Доставка и Фундамент', '#### :material/local_shipping: 3. Доставка и Фундамент'),
    ('#### 📦 3. Доставка и Фундамент', '#### :material/local_shipping: 3. Доставка и Фундамент'),
    ('st.tabs(["🛠️ Работы", "🧱 Материалы", "📊 Полная калькуляция"])', 'st.tabs([":material/construction: Работы", ":material/inventory: Материалы", ":material/calculate: Полная калькуляция"])'),
    ('st.tabs(["⚒️ Работы", "📦 Материалы", "📋 Полная калькуляция"])', 'st.tabs([":material/construction: Работы", ":material/inventory: Материалы", ":material/calculate: Полная калькуляция"])'),

    # Terrace calculator
    ('st.title("🏡 Калькулятор террас")', 'st.markdown("# :material/deck: Калькулятор террас")'),
    ('st.title("🏗️ Профессиональный проект террасы")', 'st.markdown("# :material/deck: Профессиональный проект террасы")'),
    ('st.expander("⚙️ ПАРАМЕТРЫ ТЕРРАСЫ"', 'st.expander("ПАРАМЕТРЫ ТЕРРАСЫ", icon=":material/settings:")'),
    ('st.expander("🛠️ ПАРАМЕТРЫ ТЕРРАСЫ"', 'st.expander("ПАРАМЕТРЫ ТЕРРАСЫ", icon=":material/settings:")'),
    ('#### 📏 1. Габариты и Бассейн', '#### :material/straighten: 1. Габариты и Бассейн'),
    ('#### 📐 1. Габариты и Бассейн', '#### :material/straighten: 1. Габариты и Бассейн'),
    ('#### 🪵 2. Обшивка и Периметр', '#### :material/forest: 2. Обшивка и Периметр'),
    ('#### 🏗️ 3. Фундамент и Каркас', '#### :material/foundation: 3. Фундамент и Каркас'),
    ('#### ⛓️ 3. Фундамент и Каркас', '#### :material/foundation: 3. Фундамент и Каркас'),
    ('colA.markdown("#### 🧱 Смета материалов")', 'colA.markdown("#### :material/inventory: Смета материалов")'),
    ('colA.markdown("#### 🪵 Смета материалов")', 'colA.markdown("#### :material/inventory: Смета материалов")'),
    ('colB.markdown("#### 🛠️ Смета работ")', 'colB.markdown("#### :material/construction: Смета работ")'),
    ('colB.markdown("#### ⚒️ Смета работ")', 'colB.markdown("#### :material/construction: Смета работ")'),
    ('st.sidebar.header("1. Форма террасы")', 'st.sidebar.markdown("### :material/category: 1. Форма террасы")'),
    ('st.sidebar.header("2. Параметры объекта")', 'st.sidebar.markdown("### :material/tune: 2. Параметры объекта")'),
    ('st.sidebar.header("3. Бассейн")', 'st.sidebar.markdown("### :material/pool: 3. Бассейн")'),
    ('st.sidebar.header("4. Комплектация")', 'st.sidebar.markdown("### :material/build: 4. Комплектация")'),
    ('"⬜ Прямоугольная (Стандарт)"', '":material/rectangle: Прямоугольная (Стандарт)"'),
    ('"📐 Г-образная (Угловая)"', '":material/architecture: Г-образная (Угловая)"'),
    ('"🔲 П-образная (С вырезом)"', '":material/crop_din: П-образная (С вырезом)"'),
    ('"⏺️ Округлая (Овал / Круг)"', '":material/circle: Округлая (Овал / Круг)"'),
    ('"✏️ Свой контур (По координатам)"', '":material/draw: Свой контур (По координатам)"'),
    ('🔄 Обновить прайс', ':material/refresh: Обновить прайс'),
    ('⬅ Назад на главную', ':material/arrow_back: Назад на главную'),

    # Other
    ('st.title("🏡 Калькулятор террас")', 'st.markdown("# :material/deck: Калькулятор террас")'),
    ('st.title("🏡 Калькулятор заборов")', 'st.markdown("# :material/fence: Калькулятор заборов")'),
]

for file in ["app.py", "pages/fence_calculator.py", "pages/terrace_calculator.py", "pages/fence_prices.py"]:
    if not os.path.exists(file): continue
    with open(file, "r") as f:
        content = f.read()
    for old, new in replacements:
        content = content.replace(old, new)
    
    # regex for expander headers
    content = re.sub(r'st\.expander\(\"([^"]+)\", icon=\":material/settings:\"\)', r'st.expander("\1", icon=":material/settings:")', content)

    with open(file, "w") as f:
        f.write(content)
print("Done")
