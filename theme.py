import streamlit as st

def apply_theme():
    is_light = st.session_state.get('theme', 'dark') == 'light'

    # Переменные цветов
    bg_app = "#f4f4f4" if is_light else "#191919"
    text_color = "#191919 !important" if is_light else "#ffffff !important"
    text_main = "#191919" if is_light else "#ffffff"
    
    header_bg = "#ffffff" if is_light else "#252525"
    header_text = "#191919" if is_light else "#ffffff"
    
    card_bg = "#ffffff" if is_light else "#252525"
    card_border = "#e0e0e0" if is_light else "#333333"
    card_shadow = "0 4px 10px rgba(0,0,0,0.05)" if is_light else "0 4px 15px rgba(0,0,0,0.2)"
    card_hover_bg = "#ffffff" if is_light else "#2a2a2a"
    card_hover_shadow = "0 10px 20px rgba(159, 203, 61, 0.2)" if is_light else "0 10px 25px rgba(159, 203, 61, 0.15)"
    
    card_title = "#191919" if is_light else "#ffffff"
    card_desc = "#666666" if is_light else "#a0a0a0"
    
    panel_bg = "#ffffff" if is_light else "#252525"
    panel_border = "#e0e0e0" if is_light else "#333333"
    
    label_color = "#666666" if is_light else "#a0a0a0"
    metric_val = "linear-gradient(135deg, #8eb735, #9fcb3d)"
    input_label = "#666666 !important" if is_light else "#a0a0a0 !important"
    tab_text = "#666666 !important" if is_light else "#a0a0a0 !important"
    tab_active = "#9fcb3d !important"
    expander_text = "#9fcb3d"
    border_color = "#e0e0e0" if is_light else "#333333"

    h1_color = "#191919" if is_light else "#ffffff"
    h1_shadow = "none"
    p_color = "#9fcb3d"
    dummy_img_bg = "#e0e0e0" if is_light else "#333333"

    btn_secondary_bg = "rgba(255,255,255,0.9)" if is_light else "rgba(255,255,255,0.08)"
    btn_secondary_color = "#1e293b" if is_light else "#e2e8f0"
    btn_secondary_border = "1.5px solid #cbd5e1" if is_light else "1.5px solid rgba(255,255,255,0.2)"
    
    btn_secondary_hover_bg = "rgba(159,203,61,0.08)" if is_light else "rgba(159,203,61,0.15)"
    btn_secondary_hover_color = "#191919" if is_light else "#fff"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    /* Скрываем сайдбар */
    [data-testid="collapsedControl"] {{ display: none; }}
    section[data-testid="stSidebar"] {{ display: none !important; }}
    
    /* Основной фон и шрифт */
    .stApp {{
        background: {bg_app};
        color: {text_main};
    }}
    html, body, [class*="css"], p, span, div, h1, h2, h3, h4, h5, h6, label, li {{
        font-family: 'Inter', sans-serif;
    }}
    html, body, [class*="css"] {{
        color: {text_color};
    }}

    /* Заголовок на главной (app.py) */
    .header-bar-main {{
        text-align: center;
        padding: 0rem 0 2rem 0;
    }}
    .header-bar-main h1 {{
        color: {h1_color};
        font-weight: 800;
        font-size: 2.8rem;
        margin-bottom: 0.5rem;
        text-shadow: {h1_shadow};
    }}
    .header-bar-main p {{
        color: {p_color};
        font-size: 1.2rem;
        font-weight: 400;
    }}

    /* Заголовок-шапка на страницах калькуляторов */
    .header-bar {{
        background: {header_bg};
        backdrop-filter: blur(12px);
        border-bottom: 2px solid #9fcb3d;
        padding: 0.7rem 1.5rem;
        border-radius: 0 0 16px 16px;
        box-shadow: 0 4px 20px rgba(159, 203, 61, 0.15);
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
        color: #9fcb3d;
        font-weight: 300;
        font-size: 1rem;
    }}

    /* Контейнеры колонок */
    div[data-testid="column"] {{
        display: flex;
        flex-direction: column;
    }}

    /* Карточки действий (app.py) */
    .action-card {{
        background: {card_bg};
        border: 1px solid {card_border};
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        transition: all 0.3s ease;
        box-shadow: {card_shadow};
        margin-bottom: 1rem;
        backdrop-filter: blur(10px);
        
        display: flex;
        flex-direction: column;
        flex: 1 1 auto;
        height: 100%;
    }}
    .action-card:hover {{
        transform: translateY(-5px);
        border-color: #9fcb3d;
        box-shadow: {card_hover_shadow};
        background: {card_hover_bg};
    }}
    .card-image {{
        width: 100%;
        height: 220px;
        object-fit: cover;
        border-radius: 12px;
        margin-bottom: 1.2rem;
        border: 1px solid rgba(255,255,255,0.05);
    }}
    .card-title {{
        font-size: 1.5rem;
        font-weight: 800;
        color: {card_title};
        margin-bottom: 1rem;
    }}
    .card-desc {{
        color: {card_desc};
        font-size: 0.95rem;
        line-height: 1.5;
        margin-bottom: 1.5rem;
        flex-grow: 1;
    }}

    /* Карточки метрик (калькуляторы) */
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
        border-color: rgba(159, 203, 61, 0.6);
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
        color: #9fcb3d;
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

    /* Исправление цвета текста в выпадающих списках (selectbox) */
    div[data-baseweb="select"] * {{ color: {text_main} !important; }}
    div[data-baseweb="popover"] * {{ color: {text_main} !important; }}
    li[role="option"] * {{ color: {text_main} !important; }}

    /* ====== КНОПКИ — КОНТРАСТ ====== */
    button[data-testid="stBaseButton-primary"] {{
        background: #9fcb3d !important;
        color: #191919 !important;
        border: none !important;
        font-weight: 700 !important;
        border-radius: 10px !important;
        transition: all 0.2s ease !important;
    }}
    button[data-testid="stBaseButton-primary"]:hover {{
        background: #8eb735 !important;
        box-shadow: 0 4px 15px rgba(159, 203, 61, 0.4) !important;
        transform: translateY(-1px) !important;
    }}
    button[data-testid="stBaseButton-primary"] p {{
        color: #191919 !important;
    }}

    button[data-testid="stBaseButton-secondary"] {{
        background: {btn_secondary_bg} !important;
        color: {btn_secondary_color} !important;
        border: {btn_secondary_border} !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
        transition: all 0.2s ease !important;
    }}
    button[data-testid="stBaseButton-secondary"]:hover {{
        background: {btn_secondary_hover_bg} !important;
        border-color: #9fcb3d !important;
        color: {btn_secondary_hover_color} !important;
    }}
    button[data-testid="stBaseButton-secondary"] p {{
        color: {btn_secondary_color} !important;
    }}

    /* Минимальная кнопка */
    button[data-testid="stBaseButton-minimal"] {{
        color: {"#475569" if is_light else "#94a3b8"} !important;
        border: {"1px solid #e2e8f0" if is_light else "1px solid rgba(255,255,255,0.12)"} !important;
        border-radius: 10px !important;
    }}
    </style>
    """, unsafe_allow_html=True)

    return {
        "is_light": is_light,
        "bg_app": bg_app,
        "text_color": text_color,
        "text_main": text_main,
        "header_bg": header_bg,
        "header_text": header_text,
        "card_bg": card_bg,
        "card_border": card_border,
        "card_shadow": card_shadow,
        "card_hover_bg": card_hover_bg,
        "card_hover_shadow": card_hover_shadow,
        "panel_bg": panel_bg,
        "panel_border": panel_border,
        "label_color": label_color,
        "metric_val": metric_val,
        "input_label": input_label,
        "tab_text": tab_text,
        "tab_active": tab_active,
        "expander_text": expander_text,
        "border_color": border_color,
        "card_title": card_title,
        "card_desc": card_desc,
        "h1_color": h1_color,
        "p_color": p_color,
        "dummy_img_bg": dummy_img_bg
    }
