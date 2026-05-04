import streamlit as st
import os
import json
import urllib.request
import csv
import ssl
import pandas as pd
import re

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CUSTOM_PRICES_FILE = os.path.join(DATA_DIR, "custom_prices.json")
PARSED_PRICES_FILE = os.path.join(DATA_DIR, "parsed_prices.json")
TERRACE_PARSED_FILE = os.path.join(DATA_DIR, "terrace_parsed_prices.json")

os.makedirs(DATA_DIR, exist_ok=True)

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


@st.cache_data(ttl=300)
def get_fence_prices():
    """Загружает цены из Google Sheets или локального JSON кэша."""
    # Если есть локальные кастомные цены
    if os.path.exists(CUSTOM_PRICES_FILE):
        with open(CUSTOM_PRICES_FILE, "r", encoding="utf-8") as f:
            custom_data = json.load(f)
            if "fence" in custom_data:
                return custom_data["fence"]["prices"], custom_data["fence"]["proflist"], custom_data["fence"]["shtaket"], custom_data["fence"]["parsed_data"]

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
        with open(PARSED_PRICES_FILE, "w", encoding="utf-8") as f:
            json.dump(parsed_data, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"Failed to fetch prices: {e}")
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
                width_m = 0.100
                match = re.search(r'(\d+)', item["name"])
                if match:
                    width_m = int(match.group(1)) / 1000.0
                shtaket[item["name"]] = {
                    "price": item["price"],
                    "width_m": width_m
                }

    return prices, proflist, shtaket, parsed_data

@st.cache_data(ttl=300)
def get_terrace_prices():
    # Если есть локальные кастомные цены
    if os.path.exists(CUSTOM_PRICES_FILE):
        with open(CUSTOM_PRICES_FILE, "r", encoding="utf-8") as f:
            custom_data = json.load(f)
            if "terrace" in custom_data:
                return custom_data["terrace"]["boards"], custom_data["terrace"]["pipes_joist"], custom_data["terrace"]["pipes_frame"]

    SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRgxTJ2JPrhh_da9pEBWMoKU3iT5x0DZkzKmKrOKcJBbAos8XmYJDzJyHKvcTtAfPrcpMKDzHW4AWG6/pub?gid=0&single=true&output=csv"
    
    boards = {}
    pipes_joist = {"Труба 60х40х2": 219, "Труба 60х40х3": 290}
    pipes_frame = {"Труба 80х80х2": 403, "Труба 80х80х3": 475}

    try:
        df = pd.read_csv(SHEET_URL)
        for index, row in df.iterrows():
            brand = str(row['Бренд']).strip()
            raw_name = str(row['Наименование']).strip()
            price = float(row['Цена'])
            unit = str(row['Единица']).strip()
            width = int(row['Ширина (мм)'])
            length_m = float(row['Длина (м)'])

            base_name = re.sub(r'\d{4}[хx*]\d{2,3}[хx*]\d{2,3}', '', raw_name, flags=re.IGNORECASE)
            base_name = re.sub(r'\s*\d+(\.\d+)?\s*м\b', '', base_name, flags=re.IGNORECASE).replace('  ', ' ').strip()
            
            if brand not in boards: boards[brand] = {}
            if base_name not in boards[brand]: boards[brand][base_name] = []
            
            board_cost = price if unit.lower() == 'шт' else price * length_m

            boards[brand][base_name].append({
                "name": raw_name,
                "length_m": length_m,
                "price": price,
                "unit": unit,
                "width_mm": width,
                "board_cost": board_cost
            })
    except Exception as e:
        st.error(f"Ошибка загрузки данных террас из Google Sheets: {e}")

    return boards, pipes_joist, pipes_frame

def save_custom_prices(fence_data, terrace_data):
    """Сохраняет изменённые пользователем цены локально."""
    custom_data = {
        "fence": fence_data,
        "terrace": terrace_data
    }
    with open(CUSTOM_PRICES_FILE, "w", encoding="utf-8") as f:
        json.dump(custom_data, f, ensure_ascii=False, indent=2)
    # Очищаем кэш Streamlit
    get_fence_prices.clear()
    get_terrace_prices.clear()

def reset_to_default_prices():
    """Удаляет файл с кастомными ценами, чтобы грузилось с Google Sheets."""
    if os.path.exists(CUSTOM_PRICES_FILE):
        os.remove(CUSTOM_PRICES_FILE)
    get_fence_prices.clear()
    get_terrace_prices.clear()
