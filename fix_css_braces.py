import re

files = ["pages/fence_calculator.py", "pages/terrace_calculator.py"]

for file in files:
    with open(file, "r") as f:
        content = f.read()
        
    # The bad CSS block starts at "/* Экспандеры */" and ends at "</style>"
    # We will replace single braces with double braces ONLY for the structural CSS braces.
    # Note: panel_bg, panel_border, expander_text must remain single-braced inside double braces?
    # No! Variables should be single-braced. The CSS block brackets should be double-braced.
    
    # Let's just hardcode the correct replacement.
    good_css = """/* Экспандеры */
div[data-testid="stExpander"] {{
    background: {panel_bg};
    border-radius: 12px;
    border: 1px solid {panel_border};
}}
div[data-testid="stExpander"] details summary {{
    background: transparent !important;
}}
div[data-testid="stExpander"] details summary p,
div[data-testid="stExpander"] details summary span {{
    font-size: 1.1rem !important;
    font-weight: 700 !important;
    color: {expander_text} !important;
}}
div[data-testid="stExpander"] details summary svg {{
    fill: {expander_text} !important;
}}
"""
    
    # We can use regex to replace the section from "/* Экспандеры */" up to "</style>"
    content = re.sub(
        r'/\* Экспандеры \*/.*?</style>',
        good_css + '</style>',
        content,
        flags=re.DOTALL
    )
    
    with open(file, "w") as f:
        f.write(content)

print("Done")
