import os
replacements = [
    ('Тёмная 🌙', ':material/dark_mode: Тёмная'),
    ('Светлая ☀️', ':material/light_mode: Светлая'),
    ('⬅ Назад на главную', ':material/arrow_back: Назад на главную'),
    ('⚠️ Данные о ценах не найдены', ':material/warning: Данные о ценах не найдены'),
    ('⚠️ Ошибка', ':material/error: Ошибка'),
    ('⚠️ Внимание', ':material/warning: Внимание'),
    ('📋 Прайс на работы', ':material/request_quote: Прайс на работы'),
    ('📝 Расчет террасы', ':material/calculate: Расчет террасы'),
    ('📝 Открыть Прайс', ':material/open_in_new: Открыть Прайс'),
]

for file in ["app.py", "pages/fence_calculator.py", "pages/terrace_calculator.py", "pages/fence_prices.py"]:
    if not os.path.exists(file): continue
    with open(file, "r") as f:
        content = f.read()
    for old, new in replacements:
        content = content.replace(old, new)
    with open(file, "w") as f:
        f.write(content)
print("Done")
