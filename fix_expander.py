import re

with open("pages/fence_calculator.py", "r") as f:
    content = f.read()

new_css = """/* Экспандеры */
div[data-testid="stExpander"] {
    background: {panel_bg};
    border-radius: 12px;
    border: 1px solid {panel_border};
}
div[data-testid="stExpander"] details summary {
    background: transparent !important;
}
div[data-testid="stExpander"] details summary p,
div[data-testid="stExpander"] details summary span {
    font-size: 1.1rem !important;
    font-weight: 700 !important;
    color: {expander_text} !important;
}
div[data-testid="stExpander"] details summary svg {
    fill: {expander_text} !important;
}
"""

content = re.sub(
    r'/\* Экспандеры \*/.*?</style>',
    new_css + '</style>',
    content,
    flags=re.DOTALL
)

with open("pages/fence_calculator.py", "w") as f:
    f.write(content)

print("Done")
