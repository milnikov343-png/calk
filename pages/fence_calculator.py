import streamlit as st
import math
import json
import os
import datetime
from fpdf import FPDF
import io
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import urllib.request
import csv
import ssl

# ============================================================
# КОНФИГУРАЦИЯ
# ============================================================
PRICES_FILE = os.path.join(os.path.dirname(__file__), "fence_prices.json")
PARSED_PRICES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "parsed_prices.json")

# Цены по умолчанию (из Excel «Цены»)
DEFAULT_PRICES = {
    # --- Ворота / Калитки ---
    "Замок в калитку": 2250,
    "Ворота откатные со швеллером балкой и роликами": 24000,
    "Ворота распашные стандарт": 9000,
    "Калитка стандарт": 5400,
    # --- Столбы (цена за м.п.) ---
    "Столб 60х60х2мм": 944,
    "Столб 73мм НКТ": 1042,
    "Столб 60х40х2мм": 772,
    "Столб 80х80х2мм": 1273,
    # --- Столбы под ворота/калитки ---
    "Столб под ворота 80х80х3000": 1275,
    # --- Расходные материалы ---
    "Цемент (мешок 50кг)": 550,
    "Щебень (мешок 50кг)": 170,
    "Отсев (мешок 50кг)": 170,
    "Краска грунт-эмаль 3в1": 2200,
    "Электроды сварочные Ок-46 3мм (пачка)": 2600,
    "Лага заборная 40х20х3000мм": 362,
    "Валик с бюгелем": 250,
    "Цинк холодный (баллончик)": 450,
    "Ветошь": 100,
    "Обезжириватель": 190,
    "Диски отрезные 125х1,2": 35,
    "Мусорные мешки (шт)": 10,
    # --- Монтаж ---
    "Монтаж ворот откатных": 36000,
    "Монтаж ворот распашных": 11880,
    "Монтаж калитки": 6600,
    "Монтаж привода под откатные ворота": 5400,
    "Привод для откатных ворот": 33500,
    # --- Саморезы ---
    "Саморез кровельный в цвет": 3.5,
    "Саморез с пресс-шайбой": 1.5,
    # --- Фундамент ---
    "Бетон М300 W8 (м3)": 6900,
    "Доска 40х200х6000 для опалубки": 14500,
    "Фиксатор арматуры стульчик": 3.5,
    "Фиксатор арматуры звездочка": 3.5,
    "Пленка техническая 150мкр": 45,
    "Саморезы для опалубки": 3.2,
    "Арматура 12мм А500С (м.п.)": 63,
    "Катанка 6.5мм (м.п.)": 22,
    "Проволка для связки 3мм (кг)": 350,
    # --- Доставка ---
    "Доставка (коэфф. расстояния)": 204,  # 17*12
    # --- Жалюзи ---
    "Ламель ROYAL Z (м.п.)": 420,
    "Ламель ELITE S-образная (м.п.)": 460,
    "Ламель LUXE V-образная (м.п.)": 450,
    "П-профиль с перфорацией (м.п.)": 280,
    "П-профиль без перфорации (м.п.)": 260,
    "Усилитель 0.5х51 (м.п.)": 220,
    "Профиль завершающий жалюзи (м.п.)": 230,
    "Заклёпка 4х10 (шт)": 3,
    # --- Юнис ---
    "Ламель Твинго (м.п.)": 500,
    "Ламель Твинго Макс (м.п.)": 550,
    "Ламель Твист (м.п.)": 480,
    "Ламель Лина (м.п.)": 490,
    "Ламель Виола (м.п.)": 495,
    "Ламель Гамма (м.п.)": 510,
    "Ламель Хард (м.п.)": 600,
    # --- Локо ---
    "Ламель Loko-60 Люкс (м.п.)": 450,
    "Ламель Loko-60 Лайт (м.п.)": 400,
    "Ламель Loko-80 Люкс (м.п.)": 480,
    "Ламель Loko-80 Лайт (м.п.)": 430,
    "Ламель Loko-100 Люкс (м.п.)": 500,
    "Ламель Loko-100 Лайт (м.п.)": 450,
    # --- Ранчо ---
    "Доска Ранчо 60мм (м.п.)": 350,
    "Доска Ранчо 80мм (м.п.)": 400,
    "Доска Ранчо 100мм (м.п.)": 450,
    "Доска Ранчо 120мм (м.п.)": 500,
    "Доска Ранчо 150мм (м.п.)": 550,
    "Доска Ранчо 190мм (м.п.)": 600,
    "Доска Ранчо 200мм (м.п.)": 620,
    "Доска Ранчо 250мм (м.п.)": 700,
    # --- Кирпичные столбы ---
    "Кирпич полуторный (шт)": 22,
    "Кирпич одинарный (шт)": 16,
    "Раствор кладочный (мешок 25кг)": 350,
    "Колпак металлический на столб": 450,
    "Колпак полимерно-песчаный на столб": 350,
    # --- Парапеты ---
    "Парапет прямой (м.п.)": 650,
    "Парапет угольный (м.п.)": 750,
    # --- Лага альтернативная ---
    "Лага заборная 40х20х2мм": 420,
    # --- Забутовка ---
    "Щебень для забутовки (мешок 50кг)": 170,
}

# Финишные материалы — Профлист (цена за м2)
DEFAULT_PROFLIST = {
    "Профлист оцинкованный 0.4мм С8": 348,
    "Профлист оцинкованный 0.45мм С8": 384,
    "Профлист оцинкованный 0.5мм С8": 400,
    "Профлист RAL 0.4мм С8": 434,
    "Профлист RAL 0.45мм С8": 465,
    "Профлист RAL 0.5мм С8": 486,
    "Профлист покрытие Printech": 603,
    "Профлист двухсторонний 0.45мм С8": 505,
    "Профлист двухсторонний под дерево 0.45мм С8": 674,
}

# Штакет (цена за штуку)
DEFAULT_SHTAKET = {
    "Штакет оцинкованный 75": {"price": 42, "width_m": 0.075},
    "Штакет оцинкованный 100": {"price": 55, "width_m": 0.100},
    "Штакет оцинкованный 110": {"price": 62, "width_m": 0.110},
    "Штакет оцинкованный 120": {"price": 69, "width_m": 0.120},
    "Штакет оцинкованный 131": {"price": 70, "width_m": 0.131},
    "Штакет покрытие Printech одностороннее 75": {"price": 95, "width_m": 0.075},
    "Штакет покрытие Printech одностороннее 100": {"price": 124, "width_m": 0.100},
    "Штакет покрытие Printech одностороннее 110": {"price": 138, "width_m": 0.110},
    "Штакет покрытие Printech одностороннее 120": {"price": 155, "width_m": 0.120},
    "Штакет покрытие Printech одностороннее 131": {"price": 158, "width_m": 0.131},
    "Штакет покрытие Printech двухстороннее 75": {"price": 110, "width_m": 0.075},
    "Штакет покрытие Printech двухстороннее 100": {"price": 144, "width_m": 0.100},
    "Штакет покрытие Printech двухстороннее 110": {"price": 161, "width_m": 0.110},
    "Штакет покрытие Printech двухстороннее 120": {"price": 181, "width_m": 0.120},
    "Штакет покрытие Printech двухстороннее 131": {"price": 184, "width_m": 0.131},
    "Штакет полиэстер односторонний 75": {"price": 68, "width_m": 0.075},
    "Штакет полиэстер односторонний 100": {"price": 89, "width_m": 0.100},
    "Штакет полиэстер односторонний 110": {"price": 99, "width_m": 0.110},
    "Штакет полиэстер односторонний 120": {"price": 111, "width_m": 0.120},
    "Штакет полиэстер односторонний 131": {"price": 113, "width_m": 0.131},
    "Штакет полиэстер двухсторонний 75": {"price": 68, "width_m": 0.075},
    "Штакет полиэстер двухсторонний 100": {"price": 89, "width_m": 0.100},
    "Штакет полиэстер двухсторонний 110": {"price": 99, "width_m": 0.110},
    "Штакет полиэстер двухсторонний 120": {"price": 111, "width_m": 0.120},
    "Штакет полиэстер двухсторонний 131": {"price": 113, "width_m": 0.131},
}


# ============================================================
# РАБОТА С ЦЕНАМИ (ИЗ GOOGLE ТАБЛИЦ)
# ============================================================
@st.cache_data(ttl=300)
def load_prices():
    """Загружает цены из Google Sheets или локального JSON кэша."""
    URL_TEMPLATE = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRgxTJ2JPrhh_da9pEBWMoKU3iT5x0DZkzKmKrOKcJBbAos8XmYJDzJyHKvcTtAfPrcpMKDzHW4AWG6/pub?gid={}&single=true&output=csv"
    
    GIDS = {
        "picket": "1377691245",
        "steel_kit": "536451623",
        "loko": "1979117334",
        "rancho": "72041066",
        "yunis": "1064450846",
        "royal_vip": "1042582915",
        "works": "837530591"
    }
    
    parsed_data = {}
    fetch_success = False
    try:
        context = ssl._create_unverified_context()
        for name, gid in GIDS.items():
            url = URL_TEMPLATE.format(gid)
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, context=context) as response:
                content = response.read().decode('utf-8')
                reader = csv.reader(io.StringIO(content))
                sheet_data = list(reader)
                
                if name == "works":
                    works_data = {"standard": [], "premium": [], "additional": []}
                    for row in sheet_data[1:]: # Skip header
                        if len(row) >= 4 and row[0].strip():
                            try:
                                works_data["standard"].append({
                                    "range": row[0].strip(),
                                    "prof_2lag": float(row[1].strip().replace(',', '.')),
                                    "prof_3lag": float(row[2].strip().replace(',', '.')),
                                    "shtaket_2side": float(row[3].strip().replace(',', '.'))
                                })
                            except ValueError:
                                pass
                        if len(row) >= 6 and row[4].strip():
                            try:
                                works_data["premium"].append({
                                    "range": row[4].strip(),
                                    "price": float(row[5].strip().replace(',', '.'))
                                })
                            except ValueError:
                                pass
                        if len(row) >= 9 and row[6].strip() and row[8].strip():
                            try:
                                works_data["additional"].append({
                                    "name": row[6].strip(),
                                    "unit": row[7].strip(),
                                    "price": float(row[8].strip().replace(',', '.'))
                                })
                            except ValueError:
                                pass
                    parsed_data[name] = works_data
                else:
                    items = []
                    for row in sheet_data:
                        if len(row) >= 3:
                            item_name = row[0].strip()
                            item_cat = row[1].strip()
                            item_price = row[2].strip()
                            if item_name and item_price:
                                try:
                                    items.append({
                                        "name": item_name,
                                        "category": item_cat,
                                        "price": float(item_price.replace(',', '.'))
                                    })
                                except ValueError:
                                    pass
                    parsed_data[name] = items
        fetch_success = True
        
        # Кэшируем локально
        os.makedirs(os.path.dirname(PARSED_PRICES_FILE), exist_ok=True)
        with open(PARSED_PRICES_FILE, "w", encoding="utf-8") as f:
            json.dump(parsed_data, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"Failed to fetch prices: {e}")
        # Если не удалось скачать, пытаемся загрузить из кэша
        if os.path.exists(PARSED_PRICES_FILE):
            with open(PARSED_PRICES_FILE, "r", encoding="utf-8") as f:
                parsed_data = json.load(f)

    # Мержим с дефолтами
    prices = {**DEFAULT_PRICES}
    proflist = {**DEFAULT_PROFLIST}
    shtaket = {}
    for k, v in DEFAULT_SHTAKET.items():
        shtaket[k] = {**v}
        
    # Инъекция динамических цен
    if parsed_data:
        for k in ["steel_kit", "loko", "rancho", "yunis", "royal_vip"]:
            if k in parsed_data:
                for item in parsed_data[k]:
                    prices[item["name"]] = item["price"]
        
        if "picket" in parsed_data:
            for item in parsed_data["picket"]:
                # Пытаемся вытащить ширину штакетины (например из "Штакет ... 100мм" -> 0.100)
                # По дефолту ставим 0.100
                width_m = 0.100
                import re
                match = re.search(r'(\d+)', item["name"])
                if match:
                    width_m = int(match.group(1)) / 1000.0
                shtaket[item["name"]] = {"price": item["price"], "width_m": width_m}
                
    return prices, proflist, shtaket, parsed_data

def save_prices(prices, proflist, shtaket):
    pass # Сохранение в JSON больше не используется напрямую


# ============================================================
# РАСЧЕТЫ (все формулы из Excel)
# ============================================================
def calculate_fence(params, prices, proflist, shtaket, parsed_data):
    calc_mode = params.get("calc_mode", "express")
    fence_height = params["fence_height"]
    material_type = params["material_type"]
    material_name = params["material_name"]
    gap = params["gap"]
    fastener = params["fastener"]
    color_ral = params["color_ral"]

    stolb_type = params["stolb_type"]
    post_type = params.get("post_type", "metal")  # metal / brick / polish
    lag_rows = params["lag_rows"]
    lag_pipe_type = params.get("lag_pipe_type", "40x20x1.5")
    distance_km = params["distance_km"]
    post_pitch = params.get("post_pitch", 3.0)
    hole_depth = params.get("hole_depth", 1.5)
    hole_diameter = params.get("hole_diameter", 0.2)
    ground_distance = params.get("ground_distance", 0.05)
    foundation_type = params.get("foundation_type", "concrete")  # concrete / crushedStone / driving
    brick_type = params.get("brick_type", "полуторный")
    brick_seam = params.get("brick_seam", 10)  # мм
    cap_type = params.get("cap_type", "none")  # none / metal / polymer

    has_fundament = params["has_fundament"]
    fund_length = params["fund_length"]
    fund_width = params["fund_width"]
    fund_height = params["fund_height"]

    # Парапеты
    has_parapet = params.get("has_parapet", False)
    parapet_form = params.get("parapet_form", "прямая")
    parapet_length = params.get("parapet_length", 0)

    address = params["address"]
    contact = params["contact"]

    # Функция расчета одной стороны/элемента (как в JS)
    def calc_side(length, height, gates_and_doors):
        import math
        # Определяем ширину листа
        sheet_width = 1.15
        if "С21" in material_name: sheet_width = 1.00
        elif "С10" in material_name or "HC10" in material_name: sheet_width = 1.10
        elif "С8" in material_name: sheet_width = 1.15

        total_profile_area = 0
        total_sheets_count = 0
        total_screws = 0

        def calc_element_profile(el_length, el_height):
            nonlocal total_profile_area, total_sheets_count, total_screws
            el_area = el_length * max(0, el_height - ground_distance)
            if material_type in ["Жалюзи", "Юнис", "Локо"]:
                jalousie_step = params.get("jalousie_step", 84)
                slats = math.ceil(max(0, el_height - ground_distance) * 1000 / jalousie_step)
                el_sheets = slats
                screws = 0
            elif material_type == "Ранчо":
                rancho_w = params.get("rancho_w", 100) / 1000.0
                gap_rancho = params.get("gap", 0.04)
                el_sheets = round(max(0, el_height - ground_distance) / (rancho_w + gap_rancho))
                screws = 0
            elif material_type == "Профнастил":
                el_sheets = math.ceil(el_length / sheet_width)
                screws_per_sheet = math.ceil(max(0, el_height - ground_distance) / 0.5) * 2
                screws = el_sheets * screws_per_sheet
            elif material_type == "Штакет":
                sh_data = shtaket.get(material_name, {"price": 55, "width_m": 0.1})
                sh_width = sh_data["width_m"]
                el_sheets = math.ceil(el_length / (sh_width + gap))
                screws = el_sheets * 4
            else:  # Шахматка
                sh_data = shtaket.get(material_name, {"price": 55, "width_m": 0.1})
                sh_width = sh_data["width_m"]
                el_sheets = math.ceil(el_length / (sh_width + gap)) * 2
                screws = el_sheets * 4

            total_profile_area += el_area
            total_sheets_count += el_sheets
            total_screws += screws
            return el_sheets

        available_length = length
        gate_door_count = 0
        extra80_posts = 0

        for item in gates_and_doors:
            available_length -= item["width"]
            gate_door_count += 1
            extra80_posts += 2
            calc_element_profile(item["width"], height)

        available_length = max(0, available_length)

        # --- Кирпичные столбы (логика из JS results.js:120-164) ---
        total_bricks = 0
        bricks_per_post = 0
        rows_per_post = 0
        actual_section_width = 0

        if post_type == 'brick':
            post_count = math.ceil(length / post_pitch) + 1
            sections = max(0, post_count - 1)
            total_brick_width = post_count * 0.385  # ширина кирпичного столба 385мм
            free_space = length - total_brick_width

            # Расчёт кирпичей
            brick_h = 0.088 if brick_type == 'полуторный' else 0.065
            seam_m = brick_seam / 1000.0
            post_height = height + (hole_depth or 0)
            rows_per_post = math.ceil(post_height / (brick_h + seam_m))
            bricks_per_row = 4
            bricks_per_post = rows_per_post * bricks_per_row
            total_bricks = bricks_per_post * post_count

            # Лаги — только если есть свободное пространство
            if free_space > 0 and sections > 0:
                actual_section_width = free_space / sections
                lag_total_count = sections * lag_rows
            else:
                actual_section_width = 0
                lag_total_count = 0

            # Профнастил для всей длины
            calc_element_profile(available_length, height)
            for item in gates_and_doors:
                calc_element_profile(item["width"], height)

        else:
            # Металлические столбы (существующая логика)
            if available_length > 0:
                section_count = math.ceil(available_length / post_pitch)
            else:
                section_count = 0

            post_count = max(0, section_count + 1 - gate_door_count)
            if available_length == 0:
                post_count = 0

            lag_total_count = section_count * lag_rows

            if available_length > 0:
                calc_element_profile(available_length, height)

        # Саморезы для лаг
        total_screws += lag_total_count * 2

        # --- Закрепление столбов (бетон / забутовка / вбивание) ---
        radius = hole_diameter / 2
        one_hole_vol = math.pi * radius * radius * hole_depth
        total_posts_for_holes = post_count + (extra80_posts if post_type == 'metal' else 0)

        concrete_vol = 0
        crushed_stone_vol = 0
        crushed_stone_weight = 0

        if foundation_type == 'concrete':
            concrete_vol = one_hole_vol * total_posts_for_holes
        elif foundation_type == 'crushedStone':
            crushed_stone_vol = one_hole_vol * total_posts_for_holes
            crushed_stone_weight = crushed_stone_vol * 1400  # кг (1.4 т/м3)
        # driving — ничего не нужно

        return {
            "post_count": post_count,
            "extra80_posts": extra80_posts,
            "lag_total_count": lag_total_count,
            "profile_area": total_profile_area,
            "sheets_count": total_sheets_count,
            "total_screws": total_screws,
            "concrete_vol": concrete_vol,
            "crushed_stone_vol": crushed_stone_vol,
            "crushed_stone_weight": crushed_stone_weight,
            "montazh_length": available_length,
            "total_bricks": total_bricks,
            "bricks_per_post": bricks_per_post,
            "rows_per_post": rows_per_post,
        }

    # Сбор данных
    total_stolby = 0
    total_stolby_vorota = 0
    total_lagi = 0
    total_finish_qty = 0
    total_screws = 0
    total_concrete_vol = 0
    total_crushed_stone_vol = 0
    total_crushed_stone_weight = 0
    total_montazh_length = 0
    total_bricks = 0

    kalitki_dict = {}
    otkatnye_dict = {}
    raspashnye_dict = {}
    fence_length_total = 0

    def _accumulate(res):
        nonlocal total_stolby, total_stolby_vorota, total_lagi, total_finish_qty
        nonlocal total_screws, total_concrete_vol, total_crushed_stone_vol
        nonlocal total_crushed_stone_weight, total_montazh_length, total_bricks
        total_stolby += res["post_count"]
        total_stolby_vorota += res["extra80_posts"]
        total_lagi += res["lag_total_count"]
        total_finish_qty += res["sheets_count"]
        total_screws += res["total_screws"]
        total_concrete_vol += res["concrete_vol"]
        total_crushed_stone_vol += res.get("crushed_stone_vol", 0)
        total_crushed_stone_weight += res.get("crushed_stone_weight", 0)
        total_montazh_length += res["montazh_length"]
        total_bricks += res.get("total_bricks", 0)

    if calc_mode == "detailed":
        sides_data = params.get("sides_data", [])
        for s in sides_data:
            fence_length_total += s["length"]
            if s.get("kalitka_count", 0) > 0:
                t = s.get("kalitka_type", "Калитка стандарт")
                kalitki_dict[t] = kalitki_dict.get(t, 0) + s["kalitka_count"]
            if s.get("otkatnye_count", 0) > 0:
                t = s.get("otkatnye_type", "Ворота откатные стандарт")
                otkatnye_dict[t] = otkatnye_dict.get(t, 0) + s["otkatnye_count"]
            if s.get("raspashnye_count", 0) > 0:
                t = s.get("raspashnye_type", "Ворота распашные стандарт")
                raspashnye_dict[t] = raspashnye_dict.get(t, 0) + s["raspashnye_count"]
            
            g_d = []
            for _ in range(s.get("kalitka_count", 0)): g_d.append({"type": "door", "width": 1.0})
            for _ in range(s.get("otkatnye_count", 0)): g_d.append({"type": "gate", "width": 4.0})
            for _ in range(s.get("raspashnye_count", 0)): g_d.append({"type": "gate", "width": 4.0})
            
            res = calc_side(s["length"], fence_height, g_d)
            _accumulate(res)
    else:
        fence_length_total = params.get("fence_length", 0)
        has_kalitka = params.get("has_kalitka", False)
        if has_kalitka and params.get("kalitka_count", 0) > 0:
            kalitki_dict[params.get("kalitka_type", "Калитка стандарт")] = params["kalitka_count"]
            
        has_otkatnye = params.get("has_otkatnye", False)
        if has_otkatnye and params.get("otkatnye_count", 0) > 0:
            otkatnye_dict[params.get("otkatnye_type", "Ворота откатные стандарт")] = params["otkatnye_count"]
            
        has_raspashnye = params.get("has_raspashnye", False)
        if has_raspashnye and params.get("raspashnye_count", 0) > 0:
            raspashnye_dict[params.get("raspashnye_type", "Ворота распашные стандарт")] = params["raspashnye_count"]
        
        g_d = []
        for _ in range(sum(kalitki_dict.values())): g_d.append({"type": "door", "width": 1.0})
        for _ in range(sum(otkatnye_dict.values())): g_d.append({"type": "gate", "width": 4.0})
        for _ in range(sum(raspashnye_dict.values())): g_d.append({"type": "gate", "width": 4.0})
        
        res = calc_side(fence_length_total, fence_height, g_d)
        _accumulate(res)

    # --- Цены установки/монтажа ---
    base_m = 1000; base_3l = 1500; base_2s = 1700; base_premium = 2000
    
    works_data = parsed_data.get("works", {})
    if works_data:
        # Standard rates
        for bracket in works_data.get("standard", []):
            range_str = bracket["range"]
            if "-" in range_str:
                parts = range_str.split("-")
                min_l = int(parts[0])
                max_l = int(parts[1])
                if min_l <= fence_length_total <= max_l:
                    base_m = bracket["prof_2lag"]
                    base_3l = bracket["prof_3lag"]
                    base_2s = bracket["shtaket_2side"]
                    break
            elif "более" in range_str:
                parts = range_str.split()
                min_l = int(parts[0])
                if fence_length_total >= min_l:
                    base_m = bracket["prof_2lag"]
                    base_3l = bracket["prof_3lag"]
                    base_2s = bracket["shtaket_2side"]
                    break

        # Premium rates (Жалюзи, Ранчо)
        for bracket in works_data.get("premium", []):
            range_str = bracket["range"]
            if "-" in range_str:
                parts = range_str.split("-")
                min_l = int(parts[0])
                max_l = int(parts[1])
                if min_l <= fence_length_total <= max_l:
                    base_premium = bracket["price"]
                    break
            elif "более" in range_str:
                parts = range_str.split()
                min_l = int(parts[0])
                if fence_length_total >= min_l:
                    base_premium = bracket["price"]
                    break

    # Базовая логика цены столбов для старых расчетов (если потребуется)
    price_stolb_install = 400
    if fence_length_total < 31: price_stolb_install = 500
    elif fence_length_total < 51: price_stolb_install = 450

    if material_type in ["Жалюзи", "Ранчо", "Локо", "Юнис"]:
        price_montazh = base_premium
    elif material_type == "Шахматка" or (material_type == "Штакет" and params.get("double_sided", False)):
        price_montazh = base_2s
    elif lag_rows == 3:
        price_montazh = base_3l
    else:
        price_montazh = base_m

    price_pokraska = 50 if fence_length_total < 30 else (30 if fence_length_total < 50 else 25)

    # --- Цена столба (выбранного типа) ---
    stolb_names = {
        "60х60х2мм": "Столб 60х60х2мм",
        "73мм НКТ": "Столб 73мм НКТ",
        "60х40х2мм": "Столб 60х40х2мм",
        "80х80х2мм": "Столб 80х80х2мм",
    }
    stolb_price_key = stolb_names.get(stolb_type, "Столб 60х60х2мм")
    stolb_price_per_mp = prices.get(stolb_price_key, 944)

    # --- Финишный материал ---
    finish_price_total = 0
    jalousie_items = []  # доп. материалы жалюзи
    
    if material_type in ["Жалюзи", "Юнис", "Локо", "Ранчо"]:
        # Количество секций и ширина секции
        if total_montazh_length > 0 and total_stolby > 0:
            num_sections_fence = max(total_stolby, 1)
            section_width = total_montazh_length / num_sections_fence
        else:
            num_sections_fence = 0
            section_width = post_pitch
            
        effective_height = max(0, fence_height - ground_distance)
        lamella_length = max(0, section_width - 0.006)  # -6мм на П-профили

        if material_type == "Ранчо":
            rancho_w_m = params.get("rancho_w", 100) / 1000.0
            gap_rancho = params.get("gap", 0.04)
            slats_per_section = round(effective_height / (rancho_w_m + gap_rancho))
            real_height = effective_height
            
            item_desc = f"Доска {material_name}"
            lamel_price_mp = prices.get(f"Доска {material_name} (м.п.)", 450)
            jalousie_step = rancho_w_m * 1000  # для расчета ворот
        else:
            jalousie_step = params.get("jalousie_step", 84)
            slats_per_section = math.ceil(effective_height * 1000 / jalousie_step)
            real_height = slats_per_section * jalousie_step / 1000
            
            if material_type == "Жалюзи":
                jalousie_profile = params.get("jalousie_profile", "ROYAL Z")
                lamel_price_keys = {
                    "ROYAL Z": "Ламель ROYAL Z (м.п.)",
                    "ELITE S-образная": "Ламель ELITE S-образная (м.п.)",
                    "LUXE V-образная": "Ламель LUXE V-образная (м.п.)",
                }
                lamel_price_mp = prices.get(lamel_price_keys.get(jalousie_profile, "Ламель ROYAL Z (м.п.)"), 420)
                item_desc = f"Ламель {jalousie_profile} (шаг {jalousie_step}мм)"
            else:
                prof_name = material_name.replace("Юнис ", "").replace("Локо ", "")
                lamel_price_mp = prices.get(f"Ламель {prof_name} (м.п.)", 500)
                item_desc = f"Ламель {prof_name} (шаг {jalousie_step}мм)"

        p_prof_holes_price = prices.get("П-профиль с перфорацией (м.п.)", 280)
        p_prof_plain_price = prices.get("П-профиль без перфорации (м.п.)", 260)
        reinforcer_price = prices.get("Усилитель 0.5х51 (м.п.)", 220)
        finishing_prof_price = prices.get("Профиль завершающий жалюзи (м.п.)", 230)
        rivet_price = prices.get("Заклёпка 4х10 (шт)", 3)

        total_slats = slats_per_section * num_sections_fence
        total_lamel_mp = round(total_slats * lamella_length, 2)
        lamel_total_cost = round(total_lamel_mp * lamel_price_mp)
        
        p_holes_qty = 2 * num_sections_fence
        p_holes_length_each = real_height if material_type != "Ранчо" else effective_height
        p_holes_mp = round(p_holes_qty * p_holes_length_each, 2)
        p_holes_cost = round(p_holes_mp * p_prof_holes_price)
        
        p_plain_qty = num_sections_fence
        p_plain_length_each = lamella_length
        p_plain_mp = round(p_plain_qty * p_plain_length_each, 2)
        p_plain_cost = round(p_plain_mp * p_prof_plain_price)
        
        reinf_per_section = 0
        if section_width > 3.5:
            reinf_per_section = 2
        elif section_width > 2.5:
            reinf_per_section = 1
        reinf_qty = reinf_per_section * num_sections_fence
        reinf_length = lamella_length
        reinf_mp = round(reinf_qty * reinf_length, 2)
        reinf_cost = round(reinf_mp * reinforcer_price)
        
        rivets_qty = math.ceil(total_slats * 4 * 1.01)
        rivets_cost = rivets_qty * rivet_price
        
        finish_prof_qty = num_sections_fence
        finish_prof_mp = round(finish_prof_qty * lamella_length, 2)
        finish_prof_cost = round(finish_prof_mp * finishing_prof_price)
        
        finish_price_total = lamel_total_cost  # основной финишный материал
        
        jalousie_items = [
            {"name": item_desc,
             "unit": "шт", "qty": total_slats, "mp": total_lamel_mp,
             "price_mp": lamel_price_mp, "total": lamel_total_cost},
            {"name": "П-профиль с перфорацией (боковой)",
             "unit": "шт", "qty": p_holes_qty, "mp": p_holes_mp,
             "price_mp": p_prof_holes_price, "total": p_holes_cost},
            {"name": "П-профиль без перфорации (верхний)",
             "unit": "шт", "qty": p_plain_qty, "mp": p_plain_mp,
             "price_mp": p_prof_plain_price, "total": p_plain_cost},
        ]
        
        if material_type != "Ранчо":
            jalousie_items.append(
                {"name": "Профиль завершающий",
                 "unit": "шт", "qty": finish_prof_qty, "mp": finish_prof_mp,
                 "price_mp": finishing_prof_price, "total": finish_prof_cost}
            )
            
        if reinf_qty > 0:
            jalousie_items.append(
                {"name": "Усилитель 0.5х51",
                 "unit": "шт", "qty": reinf_qty, "mp": reinf_mp,
                 "price_mp": reinforcer_price, "total": reinf_cost}
            )
        jalousie_items.append(
            {"name": "Заклёпка 4х10 (запас +1%)",
             "unit": "шт", "qty": rivets_qty, "mp": 0,
             "price_mp": rivet_price, "total": rivets_cost}
        )
        
        # Также считаем ламели в ворота/калитки
        gate_slats_total = 0
        gate_step_mm = jalousie_step if material_type != "Ранчо" else (rancho_w_m + gap_rancho) * 1000

        if n_otkatnye > 0:
            gate_h = fence_height
            gate_w = 4.0
            gate_slats = round(max(0, gate_h - ground_distance) * 1000 / gate_step_mm) if material_type == "Ранчо" else math.ceil(max(0, gate_h - ground_distance) * 1000 / jalousie_step)
            gate_lamel_len = gate_w - 0.006
            gate_slats_n = gate_slats * n_otkatnye
            gate_mp = round(gate_slats_n * gate_lamel_len, 2)
            gate_slats_total += gate_slats_n
            jalousie_items.append(
                {"name": f"{item_desc} (ворота откатные {gate_w}м)",
                 "unit": "шт", "qty": gate_slats_n, "mp": gate_mp,
                 "price_mp": lamel_price_mp, "total": round(gate_mp * lamel_price_mp)}
            )
        if n_raspashnye > 0:
            gate_h = fence_height
            gate_w = 4.0
            gate_slats = round(max(0, gate_h - ground_distance) * 1000 / gate_step_mm) if material_type == "Ранчо" else math.ceil(max(0, gate_h - ground_distance) * 1000 / jalousie_step)
            gate_lamel_len = gate_w - 0.006
            gate_slats_n = gate_slats * n_raspashnye
            gate_mp = round(gate_slats_n * gate_lamel_len, 2)
            gate_slats_total += gate_slats_n
            jalousie_items.append(
                {"name": f"{item_desc} (ворота распашные {gate_w}м)",
                 "unit": "шт", "qty": gate_slats_n, "mp": gate_mp,
                 "price_mp": lamel_price_mp, "total": round(gate_mp * lamel_price_mp)}
            )
        if n_kalitka > 0:
            kal_h = fence_height
            kal_w = 1.0
            kal_slats = round(max(0, kal_h - ground_distance) * 1000 / gate_step_mm) if material_type == "Ранчо" else math.ceil(max(0, kal_h - ground_distance) * 1000 / jalousie_step)
            kal_lamel_len = kal_w - 0.006
            kal_slats_n = kal_slats * n_kalitka
            kal_mp = round(kal_slats_n * kal_lamel_len, 2)
            gate_slats_total += kal_slats_n
            jalousie_items.append(
                {"name": f"{item_desc} (калитка {kal_w}м)",
                 "unit": "шт", "qty": kal_slats_n, "mp": kal_mp,
                 "price_mp": lamel_price_mp, "total": round(kal_mp * lamel_price_mp)}
            )
    elif material_type == "Профнастил":
        price_m2 = proflist.get(material_name, 465)
        finish_price_total = round(total_finish_qty * 1.22 * fence_height * price_m2)
    elif material_type in ["Штакет", "Шахматка"]:
        sh_data = shtaket.get(material_name, {"price": 55, "width_m": 0.1})
        sh_price = sh_data["price"]
        finish_price_total = round(total_finish_qty * sh_price * fence_height)

    # --- Саморезы (креплёж) ---
    fastener_price = prices.get(fastener, 3.5)
    samorez_qty = math.ceil(max(total_screws, 1) / 250) * 250 if material_type != "Жалюзи" else 0

    # --- Расходные материалы ---
    elektrod_packs = max(math.ceil(fence_length_total / 120), 1)
    kraska_cans = max(math.ceil(fence_length_total / 30), 1)
    
    # Конвертация объема бетона лунок в мешки (Примерно: из мешка 50кг = 0.022 м3 бетона, либо цемент+щебень)
    # 1 м3 бетона = ~350 кг цемента (7 мешков) и ~1200 кг щебня (24 мешка)
    cement_bags = math.ceil(total_concrete_vol * 7)
    scheben_bags = math.ceil(total_concrete_vol * 24)
    otsev_bags = scheben_bags

    pokraska_mp = (total_lagi * 3) + (total_stolby * 2) + (n_kalitka * 7) + (n_otkatnye * 70) + (n_raspashnye * 40)
    valik_qty = 3 if fence_length_total < 50 else 6
    zink_qty = 1 if fence_length_total <= 100 else 2
    disk_qty = math.ceil(fence_length_total / 10)
    delivery_cost = round(distance_km * prices.get("Доставка (коэфф. расстояния)", 204))

    # --- ФУНДАМЕНТ (опционально) ---
    fund_items = []
    if has_fundament:
        beton_m3 = fund_length * fund_width * fund_height
        if beton_m3 > 8:
            fund_work_unit = "м3"
            fund_work_qty = beton_m3
            fund_work_price = 7080
        else:
            fund_work_unit = "м.п."
            fund_work_qty = fund_length
            fund_work_price = 2280

        doska_qty = round(33 * fund_height / 10 * 0.2 * 6, 1)
        fix_stul = round(fund_length * 10 / 100) * 100
        fix_zvezda = fix_stul
        plenka_mp = round(fund_length + 10)
        samorezy_opal = math.ceil(fund_length / 10) * 7
        armatura_mp = round(((fund_length / 5.85) + fund_length) * 4, 1)
        katanka_mp = round(((fund_length / 0.3) + 1) / 3 * 5.85, 1)
        provolka_kg = round(fund_length / 10 * 2.5, 1)

        fund_items = [
            {"name": "Бетон М300 W8 Р4", "unit": "м3", "qty": round(beton_m3, 2),
             "price": prices.get("Бетон М300 W8 (м3)", 6900)},
            {"name": "Доска 40х200х6000 для опалубки", "unit": "м3", "qty": doska_qty,
             "price": prices.get("Доска 40х200х6000 для опалубки", 14500)},
            {"name": "Фиксатор арматуры стульчик", "unit": "шт", "qty": fix_stul,
             "price": prices.get("Фиксатор арматуры стульчик", 3.5)},
            {"name": "Фиксатор арматуры звездочка", "unit": "шт", "qty": fix_zvezda,
             "price": prices.get("Фиксатор арматуры звездочка", 3.5)},
            {"name": "Пленка техническая 150мкр", "unit": "м.п.", "qty": plenka_mp,
             "price": prices.get("Пленка техническая 150мкр", 45)},
            {"name": "Саморезы для опалубки", "unit": "шт", "qty": samorezy_opal,
             "price": prices.get("Саморезы для опалубки", 3.2)},
            {"name": "Арматура 12мм А500С", "unit": "м.п.", "qty": armatura_mp,
             "price": prices.get("Арматура 12мм А500С (м.п.)", 63)},
            {"name": "Катанка 6.5мм", "unit": "м.п.", "qty": katanka_mp,
             "price": prices.get("Катанка 6.5мм (м.п.)", 22)},
            {"name": "Проволка для связки 3мм", "unit": "кг", "qty": provolka_kg,
             "price": prices.get("Проволка для связки 3мм (кг)", 350)},
        ]

    def get_additional_price(name_substring, default_price):
        for item in works_data.get("additional", []):
            if name_substring.lower() in item["name"].lower():
                return item["price"]
        return default_price

    price_montazh_otk = get_additional_price("монтаж откатных ворот без привода", 36000)
    price_montazh_privod = get_additional_price("монтаж привода под откатные ворота", 5400)
    price_montazh_rasp = get_additional_price("монтаж распашных ворот", 11900)
    price_montazh_kal = get_additional_price("монтаж калитки", 9000)

    # ======== ФОРМИРОВАНИЕ ИТОГОВОЙ ТАБЛИЦЫ ========
    works = []
    materials = []

    works.append({
        "name": "Монтаж столбов на глубину бурения, выставление по уровню, заливка бетоном",
        "unit": "шт.", "qty": total_stolby, "price": price_stolb_install,
        "total": total_stolby * price_stolb_install
    })
    works.append({
        "name": f"Бурение отверстий в грунте глубиной {hole_depth*1000:.0f}мм",
        "unit": "шт", "qty": total_stolby, "price": price_stolb_install,
        "total": total_stolby * price_stolb_install
    })
    works.append({
        "name": "Монтаж забора",
        "unit": "м.п.", "qty": round(total_montazh_length, 1), "price": price_montazh,
        "total": round(total_montazh_length * price_montazh)
    })

    for gate_type, count in otkatnye_dict.items():
        if count > 0:
            works.append({
                "name": "Монтаж откатных ворот без привода",
                "unit": "шт", "qty": count, "price": price_montazh_otk,
                "total": count * price_montazh_otk
            })
            if params.get("has_avtomatika", False):
                works.append({
                    "name": "Монтаж привода под откатные ворота с настройкой",
                    "unit": "шт", "qty": count, "price": price_montazh_privod,
                    "total": count * price_montazh_privod
                })

    for gate_type, count in raspashnye_dict.items():
        if count > 0:
            works.append({
                "name": "Монтаж распашных ворот с засовами",
                "unit": "шт", "qty": count, "price": price_montazh_rasp,
                "total": count * price_montazh_rasp
            })

    for gate_type, count in kalitki_dict.items():
        if count > 0:
            works.append({
                "name": "Монтаж калитки с ручкой",
                "unit": "шт", "qty": count, "price": price_montazh_kal,
                "total": count * price_montazh_kal
            })

    works.append({
        "name": "Покраска металлоконструкции",
        "unit": "м.п.", "qty": round(pokraska_mp, 1), "price": price_pokraska,
        "total": round(pokraska_mp * price_pokraska)
    })

    if has_fundament:
        works.append({
            "name": "Монтажные работы по заливке фундамента",
            "unit": fund_work_unit, "qty": round(fund_work_qty, 1), "price": fund_work_price,
            "total": round(fund_work_qty * fund_work_price)
        })

    if material_type == "Жалюзи":
        # Добавляем все компоненты жалюзи в смету
        for ji in jalousie_items:
            materials.append({
                "name": ji["name"],
                "unit": ji["unit"],
                "qty": ji["qty"],
                "price": ji["price_mp"],
                "total": ji["total"]
            })
    else:
        materials.append({
            "name": material_name,
            "unit": "шт" if material_type != "Профнастил" else "лист",
            "qty": total_finish_qty,
            "price": round(finish_price_total / max(total_finish_qty, 1)),
            "total": finish_price_total
        })
        materials.append({
            "name": fastener,
            "unit": "шт", "qty": samorez_qty,
            "price": fastener_price,
            "total": round(samorez_qty * fastener_price)
        })
    # --- Столбы ---
    if post_type == 'brick':
        # Кирпичные столбы
        brick_price_key = f"Кирпич {'полуторный' if brick_type == 'полуторный' else 'одинарный'} (шт)"
        brick_price = prices.get(brick_price_key, 22 if brick_type == 'полуторный' else 16)
        materials.append({
            "name": f"Кирпич {brick_type} для столбов",
            "unit": "шт", "qty": total_bricks,
            "price": brick_price,
            "total": total_bricks * brick_price
        })
        # Раствор: ~25кг на 50 кирпичей
        mortar_bags = math.ceil(total_bricks / 50)
        mortar_price = prices.get("Раствор кладочный (мешок 25кг)", 350)
        materials.append({
            "name": "Раствор кладочный (мешок 25кг)",
            "unit": "мешок", "qty": mortar_bags,
            "price": mortar_price,
            "total": mortar_bags * mortar_price
        })
    else:
        # Металлические столбы
        materials.append({
            "name": f"Столб заборный {stolb_type}",
            "unit": "шт", "qty": total_stolby,
            "price": stolb_price_per_mp,
            "total": total_stolby * stolb_price_per_mp
        })
    
    if total_stolby_vorota > 0:
        stolb_vor_price = prices.get("Столб под ворота 80х80х3000", 1275)
        materials.append({
            "name": "Столб под ворота и калитки 80х80х3000",
            "unit": "шт", "qty": total_stolby_vorota,
            "price": stolb_vor_price,
            "total": total_stolby_vorota * stolb_vor_price
        })

    # --- Колпаки на столбы ---
    total_posts_all = total_stolby + total_stolby_vorota
    if cap_type == "metal" and total_posts_all > 0:
        cap_price = prices.get("Колпак металлический на столб", 450)
        materials.append({
            "name": "Колпак металлический на столб",
            "unit": "шт", "qty": total_posts_all,
            "price": cap_price,
            "total": total_posts_all * cap_price
        })
    elif cap_type == "polymer" and total_posts_all > 0:
        cap_price = prices.get("Колпак полимерно-песчаный на столб", 350)
        materials.append({
            "name": "Колпак полимерно-песчаный на столб",
            "unit": "шт", "qty": total_posts_all,
            "price": cap_price,
            "total": total_posts_all * cap_price
        })

    materials.append({
        "name": "Электроды сварочные Ок-46 3мм",
        "unit": "пачка", "qty": elektrod_packs,
        "price": prices.get("Электроды сварочные Ок-46 3мм (пачка)", 2600),
        "total": elektrod_packs * prices.get("Электроды сварочные Ок-46 3мм (пачка)", 2600)
    })
    materials.append({
        "name": "Краска грунт-эмаль 3в1",
        "unit": "банка", "qty": kraska_cans,
        "price": prices.get("Краска грунт-эмаль 3в1", 2200),
        "total": kraska_cans * prices.get("Краска грунт-эмаль 3в1", 2200)
    })

    # --- Лаги (выбор типа трубы) ---
    if lag_pipe_type == "40x20x2":
        lag_price_key = "Лага заборная 40х20х2мм"
        lag_name = "Лага заборная 40х20х2мм"
        lag_price_default = 420
    else:
        lag_price_key = "Лага заборная 40х20х3000мм"
        lag_name = "Лага заборная 40х20х1.5мм"
        lag_price_default = 362
    materials.append({
        "name": lag_name,
        "unit": "шт", "qty": total_lagi,
        "price": prices.get(lag_price_key, lag_price_default),
        "total": total_lagi * prices.get(lag_price_key, lag_price_default)
    })

    # --- Закрепление столбов: бетон / забутовка / вбивание ---
    if foundation_type == 'concrete':
        materials.append({
            "name": "Цемент (мешок 50кг)",
            "unit": "мешок", "qty": cement_bags,
            "price": prices.get("Цемент (мешок 50кг)", 550),
            "total": cement_bags * prices.get("Цемент (мешок 50кг)", 550)
        })
        materials.append({
            "name": "Щебень (мешок 50кг)",
            "unit": "мешок", "qty": scheben_bags,
            "price": prices.get("Щебень (мешок 50кг)", 170),
            "total": scheben_bags * prices.get("Щебень (мешок 50кг)", 170)
        })
        materials.append({
            "name": "Отсев (мешок 50кг)",
            "unit": "мешок", "qty": otsev_bags,
            "price": prices.get("Отсев (мешок 50кг)", 170),
            "total": otsev_bags * prices.get("Отсев (мешок 50кг)", 170)
        })
    elif foundation_type == 'crushedStone':
        # Забутовка — щебень вместо бетона
        butovka_bags = math.ceil(total_crushed_stone_weight / 50)  # мешки по 50кг
        butovka_price = prices.get("Щебень для забутовки (мешок 50кг)", 170)
        materials.append({
            "name": "Щебень для забутовки (мешок 50кг)",
            "unit": "мешок", "qty": butovka_bags,
            "price": butovka_price,
            "total": butovka_bags * butovka_price
        })
    # foundation_type == 'driving' — ничего не добавляем

    # --- Парапеты ---
    if has_parapet and parapet_length > 0:
        parapet_price_key = f"Парапет {'прямой' if parapet_form == 'прямая' else 'угольный'} (м.п.)"
        parapet_price = prices.get(parapet_price_key, 650 if parapet_form == 'прямая' else 750)
        materials.append({
            "name": f"Парапет {parapet_form} (м.п.)",
            "unit": "м.п.", "qty": round(parapet_length, 1),
            "price": parapet_price,
            "total": round(parapet_length * parapet_price)
        })

    for gate_type, count in otkatnye_dict.items():
        if count > 0:
            price = get_additional_price(gate_type, 65000)
            materials.append({
                "name": gate_type,
                "unit": "комплект", "qty": count,
                "price": price,
                "total": count * price
            })
            if params.get("has_avtomatika", False):
                privod_price = prices.get("Привод для откатных ворот", 33500)
                materials.append({
                    "name": "Привод для откатных ворот",
                    "unit": "шт", "qty": count,
                    "price": privod_price,
                    "total": count * privod_price
                })

    for gate_type, count in raspashnye_dict.items():
        if count > 0:
            price = get_additional_price(gate_type, 22000)
            materials.append({
                "name": gate_type,
                "unit": "комплект", "qty": count,
                "price": price,
                "total": count * price
            })

    for gate_type, count in kalitki_dict.items():
        if count > 0:
            price = get_additional_price(gate_type, 12000)
            materials.append({
                "name": gate_type,
                "unit": "комплект", "qty": count,
                "price": price,
                "total": count * price
            })
            zamok_price = prices.get("Замок в калитку", 2250)
            materials.append({
                "name": "Замок в калитку",
                "unit": "шт", "qty": count,
                "price": zamok_price,
                "total": count * zamok_price
            })

    materials.append({
        "name": "Диски отрезные 125х1,2",
        "unit": "шт", "qty": disk_qty,
        "price": prices.get("Диски отрезные 125х1,2", 35),
        "total": disk_qty * prices.get("Диски отрезные 125х1,2", 35)
    })
    materials.append({
        "name": "Валик с бюгелем полиакриловый",
        "unit": "шт", "qty": valik_qty,
        "price": prices.get("Валик с бюгелем", 250),
        "total": valik_qty * prices.get("Валик с бюгелем", 250)
    })
    materials.append({
        "name": "Цинк холодный (баллончик)",
        "unit": "шт", "qty": zink_qty,
        "price": prices.get("Цинк холодный (баллончик)", 450),
        "total": zink_qty * prices.get("Цинк холодный (баллончик)", 450)
    })
    materials.append({
        "name": "Ветошь для обработки",
        "unit": "шт", "qty": 1,
        "price": prices.get("Ветошь", 100),
        "total": prices.get("Ветошь", 100)
    })
    materials.append({
        "name": "Обезжириватель",
        "unit": "шт", "qty": 1,
        "price": prices.get("Обезжириватель", 190),
        "total": prices.get("Обезжириватель", 190)
    })

    for fi in fund_items:
        materials.append({
            "name": fi["name"],
            "unit": fi["unit"], "qty": fi["qty"],
            "price": fi["price"],
            "total": round(fi["qty"] * fi["price"])
        })

    materials.append({
        "name": "Доставка + ГСМ монтажников",
        "unit": "шт", "qty": 1,
        "price": delivery_cost,
        "total": delivery_cost
    })

    total_works = sum(w["total"] for w in works)
    total_materials = sum(m["total"] for m in materials)
    grand_total = total_works + total_materials

    # --- Генерация чертежа ---
    import io
    import matplotlib.pyplot as plt
    plot_bytes = None
    if params.get("calc_mode") == "detailed":
        fig, ax = plt.subplots(figsize=(12, 3))
        current_x = 0
        
        # Рисуем каждую сторону друг за другом (в виде прямой линии)
        for i, s in enumerate(params.get("sides_data", []), 1):
            s_len = s["length"]
            # Рисуем линию забора
            ax.plot([current_x, current_x + s_len], [0, 0], color='black', lw=2)
            
            # Добавляем подпись стороны
            ax.text(current_x + s_len/2, 0.5, f"Сторона {i} ({s_len} м)", ha='center', fontweight='bold', color='blue')
            
            # Ворота и калитки
            if s.get("kalitka_count", 0) > 0:
                pos = float(s.get("kalitka_pos") or 0)
                ax.plot([current_x + pos, current_x + pos + 1], [0, 0], color='green', lw=6, label='Калитка' if i==1 else "")
                ax.text(current_x + pos + 0.5, -0.8, "Калитка", ha='center', color='green', fontsize=8)
                
            if s.get("otkatnye_count", 0) > 0:
                pos = float(s.get("otkatnye_pos") or 0)
                ax.plot([current_x + pos, current_x + pos + 4], [0, 0], color='red', lw=6, label='Откатные' if i==1 else "")
                ax.text(current_x + pos + 2, -0.8, "Отк.ворота", ha='center', color='red', fontsize=8)
                
            if s.get("raspashnye_count", 0) > 0:
                pos = float(s.get("raspashnye_pos") or 0)
                ax.plot([current_x + pos, current_x + pos + 4], [0, 0], color='purple', lw=6, label='Распашные' if i==1 else "")
                ax.text(current_x + pos + 2, -0.8, "Расп.ворота", ha='center', color='purple', fontsize=8)
            
            # Столбы с шагом 3м
            posts_count = math.ceil(s_len / 3) + 1
            for p_i in range(posts_count):
                px = min(current_x + p_i * 3, current_x + s_len)
                ax.plot(px, 0, marker='s', color='black', markersize=4)
                
            current_x += s_len + 2 # Отступ между сторонами на чертеже

        ax.set_ylim(-2, 2)
        ax.set_xlim(-1, current_x)
        ax.axis('off')
        
        # Легенда
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        if by_label:
            ax.legend(by_label.values(), by_label.keys(), loc='upper right')
            
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
        plt.close(fig)
        plot_bytes = buf.getvalue()

    return {
        "works": works,
        "materials": materials,
        "total_works": total_works,
        "total_materials": total_materials,
        "grand_total": grand_total,
        "plot_bytes": plot_bytes,
        "params": params,
    }


# ============================================================
# PDF ГЕНЕРАЦИЯ
# ============================================================
def create_fence_pdf(result, params):
    pdf = FPDF()
    pdf.add_page()

    # Подключаем шрифт с кириллицей
    font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "DejaVuSans.ttf")
    if os.path.exists(font_path):
        pdf.add_font("DejaVu", "", font_path)
        pdf.set_font("DejaVu", "", 10)
        font = "DejaVu"
    else:
        pdf.set_font("Arial", "", 10)
        font = "Arial"

    # Шапка
    pdf.set_font(font, "", 14)
    pdf.cell(0, 8, 'Общество с ограниченной ответственностью', ln=True, align='C')
    pdf.cell(0, 8, '"Дача 2000"', ln=True, align='C')
    pdf.set_font(font, "", 9)
    pdf.cell(0, 6, '624091, Свердловская обл., г. Екатеринбург, ул. 8 Марта, д. 207, оф. 27.', ln=True, align='C')
    pdf.ln(4)

    pdf.set_font(font, "", 13)
    pdf.cell(0, 8, 'Калькуляция №1', ln=True, align='C')
    pdf.ln(2)

    pdf.set_font(font, "", 10)
    pdf.cell(0, 6, f'Наименование объекта: Монтаж забора', ln=True)
    pdf.cell(0, 6, f'Адрес: {params.get("address", "")}', ln=True)
    pdf.cell(0, 6, f'Контактное лицо: {params.get("contact", "")}', ln=True)
    
    m_name = params.get("manager_name", "")
    m_phone = params.get("manager_phone", "")
    if m_name or m_phone:
        pdf.cell(0, 6, f'Менеджер проекта: {m_name} {m_phone}', ln=True)
        
    pdf.ln(3)

    if params.get("calc_mode") == "detailed":
        pdf.set_font(font, "", 11)
        pdf.cell(0, 6, "Конфигурация сторон:", ln=True)
        pdf.set_font(font, "", 9)
        for i, s in enumerate(params.get("sides_data", []), 1):
            s_parts = []
            if s.get("kalitka_count", 0) > 0:
                s_parts.append(f'Калитка: {s["kalitka_count"]} шт. (отступ {s.get("kalitka_pos", "")} м)')
            if s.get("otkatnye_count", 0) > 0:
                s_parts.append(f'Ворота отк.: {s["otkatnye_count"]} шт. (отступ {s.get("otkatnye_pos", "")} м)')
            if s.get("raspashnye_count", 0) > 0:
                s_parts.append(f'Ворота расп.: {s["raspashnye_count"]} шт. (отступ {s.get("raspashnye_pos", "")} м)')
            
            s_desc = f'- Сторона {i}: Длина {s["length"]} м.'
            if s_parts:
                s_desc += " (" + ", ".join(s_parts) + ")"
            
            pdf.cell(0, 5, s_desc, ln=True)
        pdf.ln(3)

    # Сводка
    pdf.set_font(font, "", 11)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(95, 8, f'Стоимость работ: {result["total_works"]:,.0f} руб.', 1, 0, 'L', True)
    pdf.cell(95, 8, f'Стоимость материалов: {result["total_materials"]:,.0f} руб.', 1, 1, 'L', True)
    pdf.set_font(font, "", 13)
    pdf.cell(190, 10, f'Сметная стоимость: {result["grand_total"]:,.0f} руб.', 1, 1, 'C', True)
    pdf.ln(4)

    # Таблица заголовок
    pdf.set_font(font, "", 8)
    col_widths = [10, 70, 15, 15, 20, 30, 30]
    headers = ["№", "Наименование работ и затрат", "Ед.", "Коэфф", "Кол-во", "Цена, руб", "Сумма, руб"]
    pdf.set_fill_color(220, 220, 220)
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 7, h, 1, 0, 'C', True)
    pdf.ln()

    # Работы
    pdf.set_font(font, "", 7)
    for idx, w in enumerate(result["works"], 1):
        name_trunc = w["name"][:42]
        pdf.cell(col_widths[0], 6, str(idx), 1, 0, 'C')
        pdf.cell(col_widths[1], 6, name_trunc, 1, 0, 'L')
        pdf.cell(col_widths[2], 6, w.get("unit", ""), 1, 0, 'C')
        pdf.cell(col_widths[3], 6, "1", 1, 0, 'C')
        pdf.cell(col_widths[4], 6, str(w.get("qty", "")), 1, 0, 'C')
        pdf.cell(col_widths[5], 6, f'{w.get("price", 0):,.0f}', 1, 0, 'R')
        pdf.cell(col_widths[6], 6, f'{w["total"]:,.0f}', 1, 1, 'R')

    # Материалы
    start_idx = len(result["works"]) + 1
    for idx, m in enumerate(result["materials"], start_idx):
        name_trunc = m["name"][:42]
        pdf.cell(col_widths[0], 6, str(idx), 1, 0, 'C')
        pdf.cell(col_widths[1], 6, name_trunc, 1, 0, 'L')
        pdf.cell(col_widths[2], 6, m.get("unit", ""), 1, 0, 'C')
        pdf.cell(col_widths[3], 6, "1", 1, 0, 'C')
        pdf.cell(col_widths[4], 6, str(m.get("qty", "")), 1, 0, 'C')
        pdf.cell(col_widths[5], 6, f'{m.get("price", 0):,.0f}', 1, 0, 'R')
        pdf.cell(col_widths[6], 6, f'{m["total"]:,.0f}', 1, 1, 'R')

        # Проверка: переход на новую страницу
        if pdf.get_y() > 270:
            pdf.add_page()
            pdf.set_font(font, "", 8)
            pdf.set_fill_color(220, 220, 220)
            for i, h in enumerate(headers):
                pdf.cell(col_widths[i], 7, h, 1, 0, 'C', True)
            pdf.ln()
            pdf.set_font(font, "", 7)

    # ИТОГО
    pdf.set_font(font, "", 10)
    pdf.ln(4)
    pdf.cell(130, 8, "ИТОГО:", 1, 0, 'R', True)
    pdf.cell(60, 8, f'{result["grand_total"]:,.0f} руб.', 1, 1, 'R', True)

    pdf.ln(6)
    pdf.set_font(font, "", 10)
    pdf.cell(0, 6, f'Стоимость строительных работ забора по адресу: {params.get("address", "")}', ln=True)
    pdf.cell(0, 6, f'Составляет: {result["grand_total"]:,.0f} руб.', ln=True)

    pdf.ln(10)
    pdf.cell(95, 6, 'СОГЛАСОВАНО:', ln=True)
    pdf.ln(4)
    pdf.cell(95, 6, 'Подрядчик:                     ООО "Дача 2000"')
    pdf.cell(95, 6, 'Заказчик:', ln=True)
    pdf.ln(10)
    pdf.cell(95, 6, '_____________________________')
    pdf.cell(95, 6, '_____________________________', ln=True)
    pdf.cell(95, 6, 'М.П.')

    # ================= УТП (Unique Selling Proposition) =================
    pdf.add_page()
    pdf.set_font(font, "", 14)
    pdf.set_fill_color(0, 184, 148)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 12, "Почему выбирают ООО «Дача 2000»:", ln=True, align='C', fill=True)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font(font, "", 11)
    pdf.ln(8)
    
    usps = [
        "- Работаем строго по договору в Екатеринбурге и области.",
        "- 28 собственных квалифицированных бригад монтажников.",
        "- Собственное производство конструкций.",
        "- Честная гарантия на все выполненные работы до 3 лет.",
        "- Исправляем любые дефекты и несоответствия за свой счет.",
        "- Не поднимаем стоимость: покрываем непредвиденные расходы за свой счет.",
        "- Платим неустойку за срыв сроков монтажа (прописано в договоре).",
        "- Умеем работать в полевых условиях (даже если нет электричества и воды).",
        "- Cashback 5% от суммы договора на другие услуги по благоустройству."
    ]
    
    for usp in usps:
        pdf.cell(190, 8, usp, ln=True)
        
    pdf.ln(10)
    pdf.set_font(font, "", 12)
    pdf.set_text_color(0, 184, 148)
    pdf.cell(190, 8, "Мы строим надежные заборы для вашей безопасности и комфорта!", ln=True, align='C')
    pdf.set_text_color(0, 0, 0)

    # ================= ЧЕРТЕЖ =================
    if "plot_bytes" in result and result["plot_bytes"]:
        pdf.add_page()
        pdf.set_font(font, "", 14)
        pdf.cell(190, 10, "Схема расстановки столбов (вид сверху)", ln=True, align='C')
        pdf.image(result["plot_bytes"], x=15, y=30, w=180)

    return bytes(pdf.output())


# ============================================================
# STREAMLIT UI
# ============================================================
st.set_page_config(
    page_title="Дача 2000 | Калькулятор Заборов",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Стили ---
# --- Тема оформления ---
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

st.markdown(f"""
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
""", unsafe_allow_html=True)

# --- Загрузка цен ---
prices, proflist, shtaket = load_prices()

# --- HEADER ---
with st.container():
    col_logo, col_title, col_spacer = st.columns([1.5, 7, 1.5], gap="small")
    with col_logo:
        try:
            st.image("logo.png", width=160)
        except:
            st.markdown("<h3 style='color:#00b894; margin:0;'>Дача 2000</h3>", unsafe_allow_html=True)
    with col_title:
        st.markdown(f"""
        <div>
            <h2 style='margin:0; padding-top:8px; font-weight:800; color: {header_text};'>
                🏡 Калькулятор заборов
            </h2>
            <span style='color: #00b894; font-size: 0.9rem;'>ООО "Дача 2000" — Профессиональный расчёт стоимости</span>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ============================================================
# ВВОД ДАННЫХ
# ============================================================
with st.expander("⚙️ ПАРАМЕТРЫ ЗАБОРА (Нажмите, чтобы развернуть/свернуть)", expanded=True):
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
        st.markdown("#### 📏 1. Габариты и Материал")
        
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
                    if material_type == "Профнастил":
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
        st.markdown("#### 🛡️ 2. Ворота, Калитки, Столбы")

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
        post_type = st.selectbox("Тип столбов:", ["Металлические", "Кирпичные"], key="post_type_sel")
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
        lag_pipe_type = st.selectbox("Труба для лаг:", ["40x20x1.5 мм", "40x20x2 мм"], key="lag_pipe_sel")
        lag_pipe_val = "40x20x2" if "2 мм" in lag_pipe_type else "40x20x1.5"
        lag_rows = st.radio("Количество рядов лаг:", [2, 3], horizontal=True)

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
        st.markdown("#### 🚚 3. Доставка и Фундамент")
        distance_km = st.number_input("Расстояние до объекта (км):", 0, 500, 60)

        st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.2;'>", unsafe_allow_html=True)

        has_slope = st.checkbox("Участок с уклоном (перепад высот)", value=False)

        st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.2;'>", unsafe_allow_html=True)

        has_fundament = st.checkbox("Рассчитать фундамент", value=True)
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
    "manager_phone": manager_phone,
    "jalousie_step": jalousie_step if material_type == "Жалюзи" else 84,
    "jalousie_profile": jalousie_profile if material_type == "Жалюзи" else "ROYAL Z"
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
tab_works, tab_materials, tab_all = st.tabs(["🛠️ Работы", "🧱 Материалы", "📊 Полная калькуляция"])

def categorize_work(w_name):
    w_lower = w_name.lower()
    if "ворот" in w_lower or "калитк" in w_lower or "привод" in w_lower:
        return "🚪 Ворота и калитки"
    elif "фундамент" in w_lower or "покраск" in w_lower or "бурение" in w_lower:
        return "➕ Дополнительные работы"
    else:
        return "🏗️ Основной монтаж"

def categorize_material(m_name):
    m_lower = m_name.lower()
    if "ворот" in m_lower or "калитк" in m_lower or "привод" in m_lower or "замок" in m_lower:
        return "🚪 Ворота и калитки"
    elif any(x in m_lower for x in ["цемент", "щебень", "отсев", "арматура", "катанка", "провол", "бетон"]):
        return "🏗️ Строительные материалы"
    elif any(x in m_lower for x in ["диск", "валик", "цинк", "ветошь", "обезжириватель", "саморез", "краска", "доставка"]):
        return "➕ Прочее и расходники"
    else:
        return "🧱 Основные материалы"

def render_grouped_table(items, categorize_func, total_sum, theme_text, theme_border, highlight_color):
    groups = {}
    for item in items:
        cat = categorize_func(item["name"])
        if cat not in groups: groups[cat] = []
        groups[cat].append(item)
    
    html = f"<div style='border: 1px solid {theme_border}; border-radius: 8px; overflow: hidden;'>"
    
    for cat, cat_items in groups.items():
        html += f"""
        <div style='background-color: {highlight_color}20; padding: 10px 15px; font-weight: bold; border-bottom: 1px solid {theme_border};'>
            {cat}
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
        html += "</table>"
    
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
        "📥 СКАЧАТЬ КАЛЬКУЛЯЦИЮ (PDF)",
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
st.markdown("### 💼 Интеграции и Сохранение")

col_export, col_crm = st.columns(2)

with col_export:
    st.info("Экспорт данных проекта в формате JSON для интеграций или архива.")
    export_json = json.dumps(params, ensure_ascii=False, indent=2)
    st.download_button(
        "💾 Сохранить проект (JSON)",
        data=export_json,
        file_name=f"project_fence_{datetime.date.today()}.json",
        mime="application/json",
        use_container_width=True
    )

with col_crm:
    st.info("Отправка заявки в CRM-систему через Webhook (Битрикс24, amoCRM).")
    crm_webhook = st.text_input("Webhook URL CRM:", placeholder="https://your-crm.bitrix24.ru/rest/...", label_visibility="collapsed")
    if st.button("🚀 Отправить лид в CRM", use_container_width=True):
        if crm_webhook:
            try:
                import requests
                resp = requests.post(crm_webhook, json={"project_type": "fence", "data": params, "total": result["grand_total"]})
                if resp.status_code in [200, 201]:
                    st.success("✅ Заявка успешно отправлена в CRM!")
                else:
                    st.error(f"❌ Ошибка отправки: статус {resp.status_code}")
            except Exception as e:
                st.error(f"❌ Ошибка соединения: {e}")
        else:
            st.warning("⚠️ Введите URL Webhook")

# ============================================================
# РЕДАКТОР ЦЕН
# ============================================================
st.markdown("---")
with st.expander("💰 РЕДАКТОР ЦЕН (Настройка прайс-листа)", expanded=False):
    st.info("🔒 Цены сохраняются автоматически в файл и не сбрасываются при перезагрузке.")

    price_tab1, price_tab2, price_tab3 = st.tabs(["🔧 Основные цены", "📄 Профлист", "🔳 Штакет"])

    with price_tab1:
        changed = False
        cols = st.columns(3)
        sorted_keys = sorted(prices.keys())
        for i, key in enumerate(sorted_keys):
            with cols[i % 3]:
                new_val = st.number_input(
                    key, value=float(prices[key]), step=10.0,
                    key=f"price_{key}", format="%.1f"
                )
                if new_val != prices[key]:
                    prices[key] = new_val
                    changed = True

        if changed:
            save_prices(prices, proflist, shtaket)
            st.toast("✅ Цены сохранены!")

    with price_tab2:
        changed_p = False
        cols_p = st.columns(3)
        for i, (key, val) in enumerate(proflist.items()):
            with cols_p[i % 3]:
                new_val = st.number_input(
                    f"{key} (₽/м²)", value=float(val), step=10.0,
                    key=f"proflist_{key}", format="%.0f"
                )
                if new_val != proflist[key]:
                    proflist[key] = new_val
                    changed_p = True

        if changed_p:
            save_prices(prices, proflist, shtaket)
            st.toast("✅ Цены на профлист сохранены!")

    with price_tab3:
        changed_s = False
        cols_s = st.columns(2)
        for i, (key, val) in enumerate(shtaket.items()):
            with cols_s[i % 2]:
                new_price = st.number_input(
                    f"{key} (₽/шт)", value=float(val["price"]), step=5.0,
                    key=f"shtaket_p_{key}", format="%.0f"
                )
                if new_price != shtaket[key]["price"]:
                    shtaket[key]["price"] = new_price
                    changed_s = True

        if changed_s:
            save_prices(prices, proflist, shtaket)
            st.toast("✅ Цены на штакет сохранены!")

    # Кнопка сброса
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Сбросить все цены к заводским", type="secondary"):
        if os.path.exists(PRICES_FILE):
            os.remove(PRICES_FILE)
        st.toast("Цены сброшены!")
        st.rerun()
