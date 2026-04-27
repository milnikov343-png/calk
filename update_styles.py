import re

files_to_update = [
    "pages/fence_calculator.py",
    "pages/terrace_calculator.py"
]

def update_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Find the style block
    style_pattern = r'st\.markdown\("""\n<style>\n@import url\(.*?\n\n.*?</style>\n""", unsafe_allow_html=True\)'
    match = re.search(style_pattern, content, re.DOTALL)
    
    if not match:
        print(f"Could not find style block in {filepath}")
        return
        
    old_style_block = match.group(0)
    
    # Check if we already injected the theme logic
    if "is_light = st.session_state.get('theme', 'dark') == 'light'" in content:
        print(f"Theme logic already present in {filepath}")
        return

    # Create the dynamic style block
    new_style_code = """# --- Тема оформления ---
is_light = st.session_state.get('theme', 'dark') == 'light'

bg_app = "linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)" if is_light else "linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 40%, #16213e 100%)"
text_color = "#1e293b !important" if is_light else "#f8f9fa !important"
header_bg = "linear-gradient(135deg, rgba(255, 255, 255, 0.95), rgba(241, 245, 249, 0.95))" if is_light else "linear-gradient(135deg, rgba(30, 60, 90, 0.95), rgba(20, 40, 70, 0.95))"
header_text = "#0f172a" if is_light else "#e0e0e0"
card_bg = "linear-gradient(135deg, rgba(255, 255, 255, 0.9), rgba(241, 245, 249, 0.95))" if is_light else "linear-gradient(135deg, rgba(30, 50, 80, 0.8), rgba(20, 35, 60, 0.9))"
card_border = "rgba(16, 185, 129, 0.3)" if is_light else "rgba(0, 184, 148, 0.3)"
card_shadow = "0 4px 10px rgba(0,0,0,0.05)" if is_light else "0 4px 20px rgba(0, 0, 0, 0.3)"
card_hover_shadow = "0 8px 20px rgba(16, 185, 129, 0.15)" if is_light else "0 8px 30px rgba(0, 184, 148, 0.2)"
panel_bg = "rgba(255, 255, 255, 0.7)" if is_light else "rgba(25, 40, 65, 0.6)"
panel_border = "rgba(0, 0, 0, 0.1)" if is_light else "rgba(255, 255, 255, 0.08)"
label_color = "#64748b" if is_light else "#8899aa"
metric_val = "linear-gradient(135deg, #059669, #10b981)" if is_light else "linear-gradient(135deg, #00b894, #00cec9)"
input_label = "#475569 !important" if is_light else "#b0bec5 !important"
tab_text = "#64748b !important" if is_light else "#8899aa !important"
tab_active = "#059669 !important" if is_light else "#00b894 !important"
expander_text = "#059669" if is_light else "#00b894"

st.markdown(f\"\"\"
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

/* Скрываем сайдбар */
[data-testid="collapsedControl"] {{ display: none; }}
section[data-testid="stSidebar"] {{ display: none; }}

/* Основной фон */
.stApp {{
    background: {bg_app};
}}

/* Шрифт и читаемость текста */
html, body, [class*="css"], p, span, div, h1, h2, h3, h4, h5, h6, label, li {{
    font-family: 'Inter', sans-serif;
    color: {text_color};
}}

/* Исправление цвета текста в выпадающих списках (selectbox) */
div[data-baseweb="select"] * {{ color: #000000 !important; }}
div[data-baseweb="popover"] * {{ color: #000000 !important; }}
li[role="option"] * {{ color: #000000 !important; }}

/* Заголовок-шапка */
.header-bar {{
    background: {header_bg};
    backdrop-filter: blur(12px);
    border-bottom: 2px solid #00b894;
    padding: 0.7rem 1.5rem;
    border-radius: 0 0 16px 16px;
    box-shadow: 0 4px 20px rgba(0, 184, 148, 0.15);
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 1rem;
}}
.header-bar h2 {{
    color: {header_text};
    margin: 0;
    font-weight: 800;
    font-size: 1.4rem;
}}
.header-bar span {{
    color: #00b894;
    font-weight: 300;
    font-size: 1rem;
}}

/* Карточки метрик */
.metric-card {{
    background: {card_bg};
    border: 1px solid {card_border};
    border-radius: 16px;
    padding: 1.2rem 1.5rem;
    text-align: center;
    box-shadow: {card_shadow};
    transition: all 0.3s ease;
}}
.metric-card:hover {{
    transform: translateY(-3px);
    border-color: rgba(0, 184, 148, 0.6);
    box-shadow: {card_hover_shadow};
}}
.metric-card .label {{
    color: {label_color};
    font-size: 0.85rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 0.4rem;
}}
.metric-card .value {{
    font-size: 1.8rem;
    font-weight: 800;
    background: {metric_val};
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}}
.metric-card .value.orange {{
    background: linear-gradient(135deg, #f59e0b, #ea580c);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}}
.metric-card .value.blue {{
    background: linear-gradient(135deg, #3b82f6, #2563eb);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}}
.metric-card .value.total {{
    font-size: 2.2rem;
    background: linear-gradient(135deg, #f59e0b, #ea580c, #dc2626);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}}

/* Секция-панель */
.panel {{
    background: {panel_bg};
    border: 1px solid {panel_border};
    border-radius: 16px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
    backdrop-filter: blur(8px);
}}
.panel h4 {{
    color: #00b894;
    margin-top: 0;
    margin-bottom: 0.8rem;
    font-weight: 700;
}}

/* Таблица */
.stDataFrame, table {{
    border-radius: 12px !important;
    overflow: hidden;
}}

/* Вкладки */
div[data-testid="stTabs"] button {{
    color: {tab_text};
    font-weight: 600 !important;
}}
div[data-testid="stTabs"] button[aria-selected="true"] {{
    color: {tab_active};
    border-bottom-color: {tab_active};
}}

/* Фикс стилей инпутов */
div[data-testid="stNumberInput"] label p,
div[data-testid="stSelectbox"] label p,
div[data-testid="stRadio"] label p,
div[data-testid="stCheckbox"] label p,
div[data-testid="stTextInput"] label p {{
    font-size: 13px !important;
    font-weight: 500 !important;
    color: {input_label};
}}

/* Экспандеры */
div[data-testid="stExpander"] details summary p {{
    font-size: 1.1rem;
    font-weight: 700;
    color: {expander_text};
}}
</style>
\"\"\", unsafe_allow_html=True)"""
    
    content = content.replace(old_style_block, new_style_code)

    # We also need to fix the title if it has a hardcoded color
    if "<h2 style='margin:0; padding-top:8px; font-weight:800; color: #e0e0e0;'>" in content:
        content = content.replace("<h2 style='margin:0; padding-top:8px; font-weight:800; color: #e0e0e0;'>", "<h2 style='margin:0; padding-top:8px; font-weight:800; color: {header_text};'>")
        content = content.replace('        """, unsafe_allow_html=True)', '        \"\"\", unsafe_allow_html=True)')
        # This part might require making the string an f-string
        content = content.replace("        st.markdown(\"\"\"\n        <div>\n            <h2", "        st.markdown(f\"\"\"\n        <div>\n            <h2")
        
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
        
    print(f"Updated {filepath}")

for f in files_to_update:
    update_file(f)

