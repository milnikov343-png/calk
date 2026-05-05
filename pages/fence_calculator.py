import streamlit as st
st.set_page_config(
    page_title="Дача 2000 | Умный Калькулятор",
    page_icon=":material/construction:",
    layout="wide",
    initial_sidebar_state="collapsed"
)
import json
import datetime
from data_loader import get_fence_prices
from calculators.fence import calculate_fence, create_fence_pdf

# --- Стили ---
from theme import apply_theme
theme = apply_theme()

is_light = theme["is_light"]
text_color = theme["text_color"]
border_color = theme["border_color"]
header_text = theme["header_text"]

# --- Загрузка цен ---
prices, proflist, shtaket, parsed_data = get_fence_prices()

# --- HEADER ---
with st.container():
    col_logo, col_title, col_spacer = st.columns([1.5, 7, 1.5], gap="small")
    with col_logo:
        try:
            st.image("logo.png", width=160)
        except:
            st.markdown("<h3 style='color:#9fcb3d; margin:0;'>Дача 2000</h3>", unsafe_allow_html=True)
    with col_title:
        st.markdown(f"""
        <div>
            <h2 style='margin:0; padding-top:8px; font-weight:800; color: {header_text};'>
                <span class='material-symbols-outlined' style='vertical-align: bottom;'>home</span> Калькулятор заборов
            </h2>
            <span style='color: #9fcb3d; font-size: 0.9rem;'>ООО "Дача 2000" — Профессиональный расчёт стоимости</span>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ============================================================
# ВВОД ДАННЫХ
# ============================================================
with st.expander(":material/settings: ПАРАМЕТРЫ ЗАБОРА (Нажмите, чтобы развернуть/свернуть)", expanded=True):
    calc_mode_label = st.radio("Режим расчёта:", ["Экспресс-расчёт (по общей длине)", "Детальный расчёт по сторонам"], horizontal=True)
    calc_mode = "express" if "Экспресс" in calc_mode_label else "detailed"
    
    st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.2;'>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3, gap="medium")

    fence_length = 0
    has_kalitka = False
    kalitka_count = 0
    has_otkatnye = False
    otkatnye_count = 0
    has_raspashnye = False
    raspashnye_count = 0
    sides_data = []

    with c1:
        st.markdown("#### :material/straighten: 1. Габариты и Материал")
        
        if calc_mode == "express":
            fence_length = st.number_input("Общая длина забора (м.п.):", 1, 500, 128)
        else:
            num_sides = st.number_input("Количество сторон:", 1, 4, 1)
            for i in range(1, num_sides + 1):
                with st.container(border=True):
                    st.markdown(f"**Сторона {i}**")
                    s_len = st.number_input(f"Длина стороны {i} (м.п.):", 1.0, 500.0, 30.0, key=f"s_len_{i}")
                    
                    col_k, col_o, col_r = st.columns(3)
                    
                    kalitki_opts = [item["name"] for item in parsed_data.get("works", {}).get("additional", []) if "Калитка" in item["name"]]
                    otkatnye_opts = [item["name"] for item in parsed_data.get("works", {}).get("additional", []) if "Ворота откатные" in item["name"]]
                    raspashnye_opts = [item["name"] for item in parsed_data.get("works", {}).get("additional", []) if "Ворота распашные" in item["name"]]
                    
                    if not kalitki_opts: kalitki_opts = ["Калитка стандарт"]
                    if not otkatnye_opts: otkatnye_opts = ["Ворота откатные стандарт"]
                    if not raspashnye_opts: raspashnye_opts = ["Ворота распашные стандарт"]
                    
                    s_kal_type, s_otk_type, s_rasp_type = kalitki_opts[0], otkatnye_opts[0], raspashnye_opts[0]
                    
                    with col_k:
                        s_kal = st.number_input(f"Калитки (шт):", 0, 5, 0, key=f"s_kal_{i}")
                        s_kal_pos = ""
                        if s_kal > 0:
                            s_kal_pos = st.text_input("Отступ (м):", "2", key=f"s_kal_pos_{i}")
                            s_kal_type = st.selectbox("Тип калитки:", kalitki_opts, key=f"s_kal_type_{i}", label_visibility="collapsed")
                    with col_o:
                        s_otk = st.number_input(f"Отк. ворота:", 0, 5, 0, key=f"s_otk_{i}")
                        s_otk_pos = ""
                        s_avto = False
                        if s_otk > 0:
                            s_otk_pos = st.text_input("Отступ (м):", "5", key=f"s_otk_pos_{i}")
                            s_avto = st.checkbox("Автоматика", value=True, key=f"s_avto_{i}")
                            s_otk_type = st.selectbox("Тип откатных ворот:", otkatnye_opts, key=f"s_otk_type_{i}", label_visibility="collapsed")
                    with col_r:
                        s_rasp = st.number_input(f"Расп. ворота:", 0, 5, 0, key=f"s_rasp_{i}")
                        s_rasp_pos = ""
                        if s_rasp > 0:
                            s_rasp_pos = st.text_input("Отступ (м):", "5", key=f"s_rasp_pos_{i}")
                            s_rasp_type = st.selectbox("Тип распашных ворот:", raspashnye_opts, key=f"s_rasp_type_{i}", label_visibility="collapsed")
                    
                    st.markdown("**Материал для стороны:**")
                    s_mat_type = st.radio(f"Тип:", ["Профнастил", "Штакет", "Шахматка", "Жалюзи", "Юнис", "Локо", "Ранчо"], horizontal=True, key=f"s_mat_type_{i}", label_visibility="collapsed")
                    s_jalousie_step = 84
                    if s_mat_type == "Профнастил":
                        s_mat_name = st.selectbox(f"Профлист:", list(proflist.keys()), key=f"s_mat_name_{i}")
                        s_gap = 0.0
                    elif s_mat_type == "Жалюзи":
                        if parsed_data and "steel_kit" in parsed_data:
                            jal_cats = list(dict.fromkeys(item["category"] for item in parsed_data["steel_kit"]))
                            s_jalousie_profile = st.selectbox("Категория жалюзи:", jal_cats, key=f"s_jal_prof_{i}")
                            jal_items = [item["name"] for item in parsed_data["steel_kit"] if item["category"] == s_jalousie_profile]
                            s_mat_name = st.selectbox("Модель и покрытие:", jal_items, key=f"s_mat_name_{i}")
                            if "ROYAL" in s_jalousie_profile: s_jalousie_step = 84
                            elif "ELITE" in s_jalousie_profile: s_jalousie_step = 89
                            elif "LUXE" in s_jalousie_profile: s_jalousie_step = 89
                            else: s_jalousie_step = 84
                        else:
                            s_jalousie_profile = st.radio("Профиль:", ["ROYAL Z", "ELITE S-образная", "LUXE V-образная"], horizontal=True, key=f"s_jal_prof_{i}")
                            s_mat_name = f"Жалюзи {s_jalousie_profile} полиэстер"
                            s_jalousie_step = 84
                        s_gap = 0.0
                    elif s_mat_type == "Юнис":
                        if parsed_data and "yunis" in parsed_data:
                            yunis_cats = list(dict.fromkeys(item["category"] for item in parsed_data["yunis"]))
                            s_yunis_prof = st.selectbox("Профиль Юнис:", yunis_cats, key=f"s_yunis_prof_{i}")
                            yunis_items = [item["name"] for item in parsed_data["yunis"] if item["category"] == s_yunis_prof]
                            s_mat_name = st.selectbox("Модель и покрытие:", yunis_items, key=f"s_mat_name_{i}")
                            yunis_steps = {"Твинго": 55, "Твинго Макс": 75, "Твист": 60, "Лина": 80, "Виола": 80.1, "Гамма": 90, "Хард": 125}
                            s_jalousie_step = yunis_steps.get(s_yunis_prof.split()[0] if s_yunis_prof else "", 55)
                        else:
                            s_yunis_prof = st.selectbox("Профиль Юнис:", ["Твинго", "Твинго Макс", "Твист", "Лина", "Виола", "Гамма", "Хард"], key=f"s_yunis_prof_{i}")
                            s_mat_name = f"Юнис {s_yunis_prof}"
                            s_jalousie_step = 55
                        s_gap = 0.0
                    elif s_mat_type == "Локо":
                        if parsed_data and "loko" in parsed_data:
                            loko_cats = list(dict.fromkeys(item["category"] for item in parsed_data["loko"]))
                            s_loko_prof = st.selectbox("Профиль Локо:", loko_cats, key=f"s_loko_prof_{i}")
                            loko_items = [item["name"] for item in parsed_data["loko"] if item["category"] == s_loko_prof]
                            s_mat_name = st.selectbox("Модель и покрытие:", loko_items, key=f"s_mat_name_{i}")
                            loko_steps = {"Loko-60": 80, "Loko-80": 100, "Loko-100": 120}
                            s_jalousie_step = loko_steps.get(s_loko_prof.replace(" Люкс","").replace(" Лайт",""), 80)
                        else:
                            s_loko_prof = st.selectbox("Профиль Локо:", ["Loko-60 Люкс", "Loko-60 Лайт", "Loko-80 Люкс", "Loko-80 Лайт", "Loko-100 Люкс", "Loko-100 Лайт"], key=f"s_loko_prof_{i}")
                            s_mat_name = f"Локо {s_loko_prof}"
                            s_jalousie_step = 80
                        s_gap = 0.0
                    elif s_mat_type == "Ранчо":
                        if parsed_data and "rancho" in parsed_data:
                            rancho_cats = list(dict.fromkeys(item["category"] for item in parsed_data["rancho"]))
                            s_rancho_prof = st.selectbox("Категория Ранчо:", rancho_cats, key=f"s_rancho_w_{i}")
                            rancho_items = [item["name"] for item in parsed_data["rancho"] if item["category"] == s_rancho_prof]
                            s_mat_name = st.selectbox("Модель и покрытие:", rancho_items, key=f"s_mat_name_{i}")
                            import re
                            match = re.search(r'(\d+)\s*мм', s_rancho_prof)
                            s_rancho_w = int(match.group(1)) if match else 100
                        else:
                            s_rancho_w = st.selectbox("Ширина доски (мм):", [60, 80, 100, 120, 150, 190, 200, 250], key=f"s_rancho_w_{i}")
                            s_mat_name = f"Ранчо {s_rancho_w}мм"
                        s_gap = st.number_input("Зазор (м):", 0.01, 0.20, 0.04, step=0.01, key=f"s_gap_{i}")
                    else:
                        if parsed_data and "picket" in parsed_data:
                            shtaket_cats = list(dict.fromkeys(item["category"] for item in parsed_data["picket"]))
                            s_shtaket_prof = st.selectbox("Форма штакета:", shtaket_cats, key=f"s_shtaket_prof_{i}")
                            shtaket_items = [item["name"] for item in parsed_data["picket"] if item["category"] == s_shtaket_prof]
                            s_mat_name = st.selectbox("Модель и покрытие:", shtaket_items, key=f"s_mat_name_{i}")
                        else:
                            s_mat_name = st.selectbox(f"Штакет:", list(shtaket.keys()), key=f"s_mat_name_{i}")
                        s_gap = st.number_input("Зазор (м):", 0.01, 0.10, 0.04, step=0.01, key=f"s_gap_{i}")
                    
                    sides_data.append({
                        "length": s_len,
                        "kalitka_count": s_kal,
                        "kalitka_pos": s_kal_pos,
                        "kalitka_type": s_kal_type,
                        "otkatnye_count": s_otk,
                        "otkatnye_pos": s_otk_pos,
                        "otkatnye_type": s_otk_type,
                        "has_avtomatika": s_avto,
                        "raspashnye_count": s_rasp,
                        "raspashnye_pos": s_rasp_pos,
                        "raspashnye_type": s_rasp_type,
                        "material_type": s_mat_type,
                        "material_name": s_mat_name,
                        "gap": s_gap,
                        "jalousie_step": s_jalousie_step
                    })
            
            fence_length = sum(s["length"] for s in sides_data)

        fence_height = st.number_input("Высота забора (м):", 1.0, 4.0, 2.0, step=0.1)

        st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.2;'>", unsafe_allow_html=True)

        jalousie_step = 84  # дефолт
        jalousie_profile = "ROYAL Z"  # дефолт
        rancho_w = 100

        if calc_mode == "express":
            material_type = st.radio("Тип финишного материала:", ["Профнастил", "Штакет", "Шахматка", "Жалюзи", "Юнис", "Локо", "Ранчо"], horizontal=True)

            if material_type == "Профнастил":
                material_name = st.selectbox("Выберите профлист:", list(proflist.keys()))
                gap_m = 0.0
            elif material_type == "Жалюзи":
                if parsed_data and "steel_kit" in parsed_data:
                    jal_cats = list(dict.fromkeys(item["category"] for item in parsed_data["steel_kit"]))
                    jalousie_profile = st.selectbox("Категория жалюзи:", jal_cats)
                    jal_items = [item["name"] for item in parsed_data["steel_kit"] if item["category"] == jalousie_profile]
                    material_name = st.selectbox("Модель и покрытие:", jal_items)
                    # Определяем шаг по категории (приблизительно)
                    if "ROYAL" in jalousie_profile: jalousie_step = 84 # или 106
                    elif "ELITE" in jalousie_profile: jalousie_step = 89
                    elif "LUXE" in jalousie_profile: jalousie_step = 89
                    else: jalousie_step = 84
                else:
                    jalousie_profile = st.radio("Профиль ламели:", ["ROYAL Z", "ELITE S-образная", "LUXE V-образная"], horizontal=True)
                    material_name = f"Жалюзи {jalousie_profile} полиэстер"
                    jalousie_step = 84
                gap_m = 0.0
            elif material_type == "Юнис":
                if parsed_data and "yunis" in parsed_data:
                    yunis_cats = list(dict.fromkeys(item["category"] for item in parsed_data["yunis"]))
                    yunis_prof = st.selectbox("Профиль Юнис:", yunis_cats)
                    yunis_items = [item["name"] for item in parsed_data["yunis"] if item["category"] == yunis_prof]
                    material_name = st.selectbox("Модель и покрытие:", yunis_items)
                    yunis_steps = {"Твинго": 55, "Твинго Макс": 75, "Твист": 60, "Лина": 80, "Виола": 80.1, "Гамма": 90, "Хард": 125}
                    jalousie_step = yunis_steps.get(yunis_prof.split()[0] if yunis_prof else "", 55)
                else:
                    yunis_prof = st.selectbox("Профиль Юнис:", ["Твинго", "Твинго Макс", "Твист", "Лина", "Виола", "Гамма", "Хард"])
                    material_name = f"Юнис {yunis_prof}"
                    jalousie_step = 55
                gap_m = 0.0
            elif material_type == "Локо":
                if parsed_data and "loko" in parsed_data:
                    loko_cats = list(dict.fromkeys(item["category"] for item in parsed_data["loko"]))
                    loko_prof = st.selectbox("Профиль Локо:", loko_cats)
                    loko_items = [item["name"] for item in parsed_data["loko"] if item["category"] == loko_prof]
                    material_name = st.selectbox("Модель и покрытие:", loko_items)
                    loko_steps = {"Loko-60": 80, "Loko-80": 100, "Loko-100": 120}
                    jalousie_step = loko_steps.get(loko_prof.replace(" Люкс","").replace(" Лайт",""), 80)
                else:
                    loko_prof = st.selectbox("Профиль Локо:", ["Loko-60 Люкс", "Loko-60 Лайт", "Loko-80 Люкс", "Loko-80 Лайт", "Loko-100 Люкс", "Loko-100 Лайт"])
                    material_name = f"Локо {loko_prof}"
                    jalousie_step = 80
                gap_m = 0.0
            elif material_type == "Ранчо":
                if parsed_data and "rancho" in parsed_data:
                    rancho_cats = list(dict.fromkeys(item["category"] for item in parsed_data["rancho"]))
                    rancho_prof = st.selectbox("Категория Ранчо:", rancho_cats)
                    rancho_items = [item["name"] for item in parsed_data["rancho"] if item["category"] == rancho_prof]
                    material_name = st.selectbox("Модель и покрытие:", rancho_items)
                    rancho_w = 100 # default fallback
                    import re
                    match = re.search(r'(\d+)\s*мм', rancho_prof)
                    if match: rancho_w = int(match.group(1))
                else:
                    rancho_w = st.selectbox("Ширина доски (мм):", [60, 80, 100, 120, 150, 190, 200, 250])
                    material_name = f"Ранчо {rancho_w}мм"
                gap_m = st.number_input("Зазор (м):", 0.01, 0.20, 0.04, step=0.01)
            else:
                if parsed_data and "picket" in parsed_data:
                    shtaket_cats = list(dict.fromkeys(item["category"] for item in parsed_data["picket"]))
                    shtaket_prof = st.selectbox("Форма штакета:", shtaket_cats)
                    shtaket_items = [item["name"] for item in parsed_data["picket"] if item["category"] == shtaket_prof]
                    material_name = st.selectbox("Модель и покрытие:", shtaket_items)
                else:
                    material_name = st.selectbox("Выберите штакет:", list(shtaket.keys()))
                gap_m = st.number_input("Зазор между штакетинами (м):", 0.01, 0.10, 0.04, step=0.01)
        else:
            # Для детального режима материалы уже выбраны для каждой стороны,
            # но мы ставим заглушки для совместимости кода ниже
            material_type = sides_data[0]["material_type"] if sides_data else "Профнастил"
            material_name = sides_data[0]["material_name"] if sides_data else list(proflist.keys())[0]
            gap_m = sides_data[0]["gap"] if sides_data else 0.0
            jalousie_step = sides_data[0].get("jalousie_step", 84) if sides_data else 84
            rancho_w = 100

        color_ral = st.text_input("Цвет RAL:", "RAL 8017")
        fastener = st.selectbox("Способ крепления:", ["Саморез кровельный в цвет", "Саморез с пресс-шайбой"])

    with c2:
        st.markdown("#### :material/sensor_door: 2. Ворота, Калитки, Столбы")

        if calc_mode == "express":
            kalitki_opts = [item["name"] for item in parsed_data.get("works", {}).get("additional", []) if "Калитка" in item["name"]]
            otkatnye_opts = [item["name"] for item in parsed_data.get("works", {}).get("additional", []) if "Ворота откатные" in item["name"]]
            raspashnye_opts = [item["name"] for item in parsed_data.get("works", {}).get("additional", []) if "Ворота распашные" in item["name"]]
            
            if not kalitki_opts: kalitki_opts = ["Калитка стандарт"]
            if not otkatnye_opts: otkatnye_opts = ["Ворота откатные стандарт"]
            if not raspashnye_opts: raspashnye_opts = ["Ворота распашные стандарт"]
            
            has_kalitka = st.checkbox("Калитка", value=True)
            if has_kalitka:
                kalitka_count = st.number_input("Кол-во калиток:", 1, 5, 1, key="kalitka_n")
                kalitka_type = st.selectbox("Тип калитки:", kalitki_opts, key="kalitka_type")
            else:
                kalitka_count = 0
                kalitka_type = kalitki_opts[0]

            has_otkatnye = st.checkbox("Ворота откатные", value=True)
            if has_otkatnye:
                otkatnye_count = st.number_input("Кол-во откатных ворот:", 1, 5, 1, key="otkat_n")
                otkatnye_type = st.selectbox("Тип откатных ворот:", otkatnye_opts, key="otkatnye_type")
                has_avtomatika = st.checkbox("Установить автоматику (привод)", value=True, key="avto_exp")
            else:
                otkatnye_count = 0
                has_avtomatika = False
                otkatnye_type = otkatnye_opts[0]

            has_raspashnye = st.checkbox("Ворота распашные", value=False)
            if has_raspashnye:
                raspashnye_count = st.number_input("Кол-во распашных ворот:", 1, 5, 1, key="rasp_n")
                raspashnye_type = st.selectbox("Тип распашных ворот:", raspashnye_opts, key="raspashnye_type")
            else:
                raspashnye_count = 0
                raspashnye_type = raspashnye_opts[0]
        else:
            has_avtomatika = any(s.get("has_avtomatika", False) for s in sides_data)
            st.info("Ворота и калитки настраиваются для каждой стороны в блоке слева.")

        st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.2;'>", unsafe_allow_html=True)

        # --- Тип столбов ---
        if st.session_state.get("has_fund_checkbox", True):
# --- Тип столбов ---
            post_type = st.selectbox("Тип столбов:", ["Металлические", "Кирпичные"], key="post_type_sel")
# --- Тип столбов ---
        else:
# --- Тип столбов ---
            post_type = "Металлические"
        post_type_val = "brick" if post_type == "Кирпичные" else "metal"

        if post_type_val == "metal":
            stolb_type = st.selectbox("Труба для столбов:", ["60х60х2мм", "73мм НКТ", "60х40х2мм", "80х80х2мм"])
            brick_type_val = "полуторный"
            brick_seam_val = 10
        else:
            stolb_type = "60х60х2мм"  # Внутри кирпичных — арматура, для расчёта неважно
            brick_type = st.selectbox("Тип кирпича:", ["Полуторный", "Одинарный"], key="brick_type_sel")
            brick_type_val = "полуторный" if brick_type == "Полуторный" else "одинарный"
            brick_seam = st.selectbox("Толщина шва:", ["10 мм", "8 мм"], key="brick_seam_sel")
            brick_seam_val = 10 if brick_seam == "10 мм" else 8
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


        st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.2;'>", unsafe_allow_html=True)

        # --- Закрепление столбов ---
        foundation_type_label = st.selectbox("Закрепление столбов:", ["Бетонирование", "Забутовка (щебень)", "Вбивание"], key="found_type_sel")
        foundation_type_map = {"Бетонирование": "concrete", "Забутовка (щебень)": "crushedStone", "Вбивание": "driving"}
        foundation_type_val = foundation_type_map[foundation_type_label]

        post_pitch = st.number_input("Шаг столбов (м):", 1.0, 5.0, 3.0, step=0.1)
        hole_depth = st.number_input("Глубина бурения (м):", 0.5, 3.0, 1.5, step=0.1)
        hole_diameter = st.number_input("Диаметр лунок (м):", 0.1, 0.6, 0.2, step=0.05)
        ground_distance = st.number_input("Зазор снизу (м):", 0.0, 0.5, 0.05, step=0.01)

        st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.2;'>", unsafe_allow_html=True)

        # --- Колпаки ---
        cap_choice = st.selectbox("Колпаки на столбы:", ["Без колпаков", "Металлические", "Полимерно-песчаные"], key="cap_sel")
        cap_map = {"Без колпаков": "none", "Металлические": "metal", "Полимерно-песчаные": "polymer"}
        cap_type_val = cap_map[cap_choice]

    with c3:
        st.markdown("#### :material/local_shipping: 3. Доставка и Фундамент")
        distance_km = st.number_input("Расстояние до объекта (км):", 0, 500, 60)

        st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.2;'>", unsafe_allow_html=True)

        has_slope = st.checkbox("Участок с уклоном (перепад высот)", value=False)

        st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.2;'>", unsafe_allow_html=True)

        has_fundament = st.checkbox("Рассчитать фундамент", value=True, key="has_fund_checkbox")
        if has_fundament:
            fund_length = st.number_input("Длина фундамента (м.п.):", 1.0, 500.0, 64.0)
            fund_width = st.number_input("Ширина фундамента (м):", 0.1, 2.0, 0.25, step=0.05)
            fund_height = st.number_input("Высота фундамента (м):", 0.1, 2.0, 0.6, step=0.1)
        else:
            fund_length = fund_width = fund_height = 0

        st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.2;'>", unsafe_allow_html=True)

        # --- Парапеты ---
        has_parapet = st.checkbox("Парапеты на фундамент", value=False)
        if has_parapet:
            parapet_form = st.selectbox("Форма парапета:", ["Прямая", "Угольная"], key="parapet_form_sel")
            parapet_form_val = "прямая" if parapet_form == "Прямая" else "угольная"
            parapet_length = st.number_input("Длина парапетов (м.п.):", 0.0, 500.0, fund_length if has_fundament else 0.0, step=1.0)
        else:
            parapet_form_val = "прямая"
            parapet_length = 0

        st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.2;'>", unsafe_allow_html=True)

        address = st.text_input("Адрес объекта:", "КП Заповедник парк Совята уч 81")
        contact = st.text_input("Контактное лицо:", "Борис Борисович +7-912-297-11-79")
        
        st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.2;'>", unsafe_allow_html=True)
        st.markdown("**Менеджер проекта**")
        manager_name = st.text_input("Имя менеджера:", "Иван Иванов")
        manager_phone = st.text_input("Телефон менеджера:", "+7 (999) 000-00-00")

# ============================================================
# РАСЧЁТ
# ============================================================
params = {
    "calc_mode": calc_mode,
    "sides_data": sides_data,
    "fence_length": fence_length,
    "fence_height": fence_height,
    "material_type": material_type,
    "material_name": material_name,
    "gap": gap_m,
    "jalousie_step": jalousie_step,
    "jalousie_profile": jalousie_profile,
    "rancho_w": rancho_w,
    "fastener": fastener,
    "color_ral": color_ral,
    "has_kalitka": has_kalitka,
    "kalitka_count": kalitka_count if has_kalitka else 0,
    "kalitka_type": kalitka_type if calc_mode == "express" else "",
    "has_otkatnye": has_otkatnye,
    "otkatnye_count": otkatnye_count if has_otkatnye else 0,
    "otkatnye_type": otkatnye_type if calc_mode == "express" else "",
    "has_avtomatika": has_avtomatika,
    "has_raspashnye": has_raspashnye,
    "raspashnye_count": raspashnye_count if has_raspashnye else 0,
    "raspashnye_type": raspashnye_type if calc_mode == "express" else "",
    "stolb_type": stolb_type,
    "post_type": post_type_val,
    "lag_rows": lag_rows,
    "lag_pipe_type": lag_pipe_val,
    "post_pitch": post_pitch,
    "hole_depth": hole_depth,
    "hole_diameter": hole_diameter,
    "ground_distance": ground_distance,
    "foundation_type": foundation_type_val,
    "brick_type": brick_type_val if post_type_val == "brick" else "полуторный",
    "brick_seam": brick_seam_val if post_type_val == "brick" else 10,
    "cap_type": cap_type_val,
    "distance_km": distance_km,
    "has_slope": has_slope,
    "has_fundament": has_fundament,
    "fund_length": fund_length,
    "fund_width": fund_width,
    "fund_height": fund_height,
    "has_parapet": has_parapet,
    "parapet_form": parapet_form_val if has_parapet else "прямая",
    "parapet_length": parapet_length if has_parapet else 0,
    "address": address,
    "contact": contact,
    "manager_name": manager_name,
    "manager_phone": manager_phone
}

result = calculate_fence(params, prices, proflist, shtaket, parsed_data)

# ============================================================
# ВЫВОД РЕЗУЛЬТАТОВ
# ============================================================
st.markdown("---")

# Метрики (карточки)
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Стоимость работ</div>
        <div class="value blue">{result['total_works']:,.0f} ₽</div>
    </div>
    """, unsafe_allow_html=True)
with m2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Стоимость материалов</div>
        <div class="value orange">{result['total_materials']:,.0f} ₽</div>
    </div>
    """, unsafe_allow_html=True)
with m3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Длина забора</div>
        <div class="value">{fence_length} м.п.</div>
    </div>
    """, unsafe_allow_html=True)
with m4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Итого</div>
        <div class="value total">{result['grand_total']:,.0f} ₽</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

if result.get("plot_bytes"):
    st.markdown("### Схема расстановки столбов")
    st.image(result["plot_bytes"], use_container_width=True)
    st.markdown("<br>", unsafe_allow_html=True)

# Таблицы с группировкой
tab_works, tab_materials, tab_all = st.tabs([":material/construction: Работы", ":material/inventory: Материалы", ":material/calculate: Полная калькуляция"])

def categorize_work(w_name):
    w_lower = w_name.lower()
    if "ворот" in w_lower or "калитк" in w_lower or "привод" in w_lower:
        return ":material/sensor_door: Ворота и калитки"
    elif "фундамент" in w_lower or "покраск" in w_lower or "бурение" in w_lower:
        return "➕ Дополнительные работы"
    else:
        return ":material/construction: Основной монтаж"

def categorize_material(m_name):
    m_lower = m_name.lower()
    if "ворот" in m_lower or "калитк" in m_lower or "привод" in m_lower or "замок" in m_lower:
        return ":material/sensor_door: Ворота и калитки"
    elif any(x in m_lower for x in ["цемент", "щебень", "отсев", "арматура", "катанка", "провол", "бетон"]):
        return ":material/construction: Строительные материалы"
    elif any(x in m_lower for x in ["диск", "валик", "цинк", "ветошь", "обезжириватель", "саморез", "краска", "доставка"]):
        return "➕ Прочее и расходники"
    else:
        return ":material/inventory_2: Основные материалы"

def render_grouped_table(items, categorize_func, total_sum, theme_text, theme_border, highlight_color):
    groups = {}
    for item in items:
        cat = categorize_func(item["name"])
        if cat not in groups: groups[cat] = []
        groups[cat].append(item)
    
    html = f"<div style='border: 1px solid {theme_border}; border-radius: 8px; overflow: hidden;'>"
    
    import re
    for cat, cat_items in groups.items():
        cat_display = re.sub(r':material/(\w+):', r'<span class="material-symbols-outlined" style="vertical-align: middle; margin-right: 5px; font-size: 1.2rem;">\1</span>', cat)
        html += f"""
<div style='background-color: {highlight_color}20; padding: 10px 15px; font-weight: bold; border-bottom: 1px solid {theme_border};'>
{cat_display}
</div>
<table style='width: 100%; border-collapse: collapse; text-align: left; margin: 0; font-size: 0.95rem;'>
<tr style='border-bottom: 1px solid {theme_border}; opacity: 0.7; font-size: 0.85rem;'>
<th style='padding: 8px 15px;'>Наименование</th>
<th style='padding: 8px 15px;'>Ед.</th>
<th style='padding: 8px 15px;'>Кол-во</th>
<th style='padding: 8px 15px;'>Цена</th>
<th style='padding: 8px 15px; text-align: right;'>Сумма</th>
</tr>
"""
        for it in cat_items:
            html += f"""
<tr style='border-bottom: 1px solid {theme_border};'>
<td style='padding: 10px 15px;'>{it['name']}</td>
<td style='padding: 10px 15px;'>{it.get('unit','')}</td>
<td style='padding: 10px 15px;'>{it.get('qty','')}</td>
<td style='padding: 10px 15px;'>{it.get('price',0):,.0f} ₽</td>
<td style='padding: 10px 15px; text-align: right; font-weight: bold;'>{it['total']:,.0f} ₽</td>
</tr>
"""
        html += "</table>\n"
    
    html += f"""
<div style='padding: 15px; text-align: right; font-size: 1.2rem; font-weight: bold; background-color: {highlight_color}10;'>
ИТОГО: <span style='color: {highlight_color};'>{total_sum:,.0f} ₽</span>
</div>
</div>
"""
    return html

with tab_works:
    st.markdown(render_grouped_table(result["works"], categorize_work, result["total_works"], text_color, border_color, "#00a8ff"), unsafe_allow_html=True)

with tab_materials:
    st.markdown(render_grouped_table(result["materials"], categorize_material, result["total_materials"], text_color, border_color, "#fbc531"), unsafe_allow_html=True)

with tab_all:
    # Простая сводная таблица для Полной калькуляции
    all_table = []
    idx = 1
    for w in result["works"]:
        all_table.append({
            "№": idx, "Наименование": w["name"], "Ед.": w.get("unit", ""),
            "Кол-во": w.get("qty", ""), "Цена": f'{w.get("price", 0):,.0f}',
            "Работы": f'{w["total"]:,.0f}', "Материалы": ""
        })
        idx += 1
    for m in result["materials"]:
        all_table.append({
            "№": idx, "Наименование": m["name"], "Ед.": m.get("unit", ""),
            "Кол-во": m.get("qty", ""), "Цена": f'{m.get("price", 0):,.0f}',
            "Работы": "", "Материалы": f'{m["total"]:,.0f}'
        })
        idx += 1
    st.dataframe(all_table, use_container_width=True, hide_index=True)
    c_total_l, c_total_r = st.columns(2)
    c_total_l.markdown(f"**Работы: {result['total_works']:,.0f} руб.**")
    c_total_r.markdown(f"**Материалы: {result['total_materials']:,.0f} руб.**")
    st.markdown(f"### 💰 ИТОГО: <span style='color:#44bd32;'>{result['grand_total']:,.0f} руб.</span>", unsafe_allow_html=True)

# ============================================================
# PDF СКАЧИВАНИЕ
# ============================================================
st.markdown("---")
col_dl1, col_dl2, col_dl3 = st.columns([1, 2, 1])
with col_dl2:
    pdf_data = create_fence_pdf(result, params)
    st.download_button(
        ":material/download: СКАЧАТЬ КАЛЬКУЛЯЦИЮ (PDF)",
        data=pdf_data,
        file_name=f"Забор_{address.replace(' ', '_')[:30]}_{datetime.date.today()}.pdf",
        mime="application/pdf",
        use_container_width=True,
        type="primary"
    )

# ============================================================
# CRM И ЭКСПОРТ (БИЗНЕС-БЛОК)
# ============================================================
st.markdown("---")
st.markdown("### :material/work: Интеграции и Сохранение")

col_export, col_crm = st.columns(2)

with col_export:
    st.info("Экспорт данных проекта в формате JSON для интеграций или архива.")
    export_json = json.dumps(params, ensure_ascii=False, indent=2)
    st.download_button(
        ":material/save: Сохранить проект (JSON)",
        data=export_json,
        file_name=f"project_fence_{datetime.date.today()}.json",
        mime="application/json",
        use_container_width=True
    )

with col_crm:
    st.info("Отправка заявки в CRM-систему через Webhook (Битрикс24, amoCRM).")
    crm_webhook = st.text_input("Webhook URL CRM:", placeholder="https://your-crm.bitrix24.ru/rest/...", label_visibility="collapsed")
    if st.button(":material/rocket_launch: Отправить лид в CRM", use_container_width=True):
        if crm_webhook:
            try:
                import requests
                resp = requests.post(crm_webhook, json={"project_type": "fence", "data": params, "total": result["grand_total"]})
                if resp.status_code in [200, 201]:
                    st.success(":material/check_circle: Заявка успешно отправлена в CRM!")
                else:
                    st.error(f":material/cancel: Ошибка отправки: статус {resp.status_code}")
            except Exception as e:
                st.error(f":material/cancel: Ошибка соединения: {e}")
        else:
            st.warning(":material/warning: Введите URL Webhook")

