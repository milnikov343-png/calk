with open("app.py", "r") as f:
    content = f.read()

# 1. Add Material Icons font to the CSS block if missing
if "Material+Symbols+Outlined" not in content:
    content = content.replace("<style>\n", "<style>\n@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0');\n")

# 2. Fix the card icons
content = content.replace(
    ':material/construction:</div>',
    '<span class="material-symbols-outlined" style="vertical-align: bottom;">construction</span></div>'
)
content = content.replace(
    '<div class="card-title">:material/deck: Расчёт Террас</div>',
    '<div class="card-title"><span class="material-symbols-outlined" style="vertical-align: bottom;">deck</span> Расчёт Террас</div>'
)

content = content.replace(
    ':material/shield:</div>',
    '<span class="material-symbols-outlined" style="vertical-align: bottom;">shield</span></div>'
)
content = content.replace(
    '<div class="card-title">:material/fence: Расчёт Заборов</div>',
    '<div class="card-title"><span class="material-symbols-outlined" style="vertical-align: bottom;">fence</span> Расчёт Заборов</div>'
)

content = content.replace(
    ':material/bar_chart:</div>',
    '<span class="material-symbols-outlined" style="vertical-align: bottom;">bar_chart</span></div>'
)
content = content.replace(
    '<div class="card-title">:material/request_quote: Прайс на работы</div>',
    '<div class="card-title"><span class="material-symbols-outlined" style="vertical-align: bottom;">request_quote</span> Прайс на работы</div>'
)

with open("app.py", "w") as f:
    f.write(content)

print("Done")
