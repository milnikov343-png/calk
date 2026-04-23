import streamlit as st
import math
import json
import os
import datetime
from fpdf import FPDF
import io

# ============================================================
# КОНФИГУРАЦИЯ
# ============================================================
PRICES_FILE = os.path.join(os.path.dirname(__file__), "fence_prices.json")

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
# РАБОТА С ЦЕНАМИ (JSON)
# ============================================================
def load_prices():
    """Загружает цены из JSON, если файла нет — использует дефолтные."""
    if os.path.exists(PRICES_FILE):
        try:
            with open(PRICES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Мержим с дефолтами (если добавились новые позиции)
            prices = {**DEFAULT_PRICES, **data.get("prices", {})}
            proflist = {**DEFAULT_PROFLIST, **data.get("proflist", {})}
            shtaket = {}
            for k, v in DEFAULT_SHTAKET.items():
                shtaket[k] = {**v}
            for k, v in data.get("shtaket", {}).items():
                shtaket[k] = v
            return prices, proflist, shtaket
        except Exception:
            pass
    return dict(DEFAULT_PRICES), dict(DEFAULT_PROFLIST), {k: dict(v) for k, v in DEFAULT_SHTAKET.items()}


def save_prices(prices, proflist, shtaket):
    """Сохраняет текущие цены в JSON."""
    data = {"prices": prices, "proflist": proflist, "shtaket": shtaket}
    with open(PRICES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ============================================================
# РАСЧЕТЫ (все формулы из Excel)
# ============================================================
def calculate_fence(params, prices, proflist, shtaket):
    """Воспроизводит ВСЕ формулы из Excel-калькулятора заборов."""
    calc_mode = params.get("calc_mode", "express")

    if calc_mode == "detailed":
        sides_data = params.get("sides_data", [])
        fence_length = sum(s["length"] for s in sides_data)
        n_kalitka = sum(s["kalitka_count"] for s in sides_data)
        n_otkatnye = sum(s["otkatnye_count"] for s in sides_data)
        n_raspashnye = sum(s["raspashnye_count"] for s in sides_data)

        stolby_pod_zabor = 0
        for s in sides_data:
            s_len = s["length"] - s["kalitka_count"] * 1 - s["otkatnye_count"] * 4 - s["raspashnye_count"] * 4
            stolby_pod_zabor += max(math.ceil(s_len / 3), 0)
    else:
        fence_length = params.get("fence_length", 0)  # общая длина забора (м.п.)
        has_kalitka = params.get("has_kalitka", False)
        kalitka_count = params.get("kalitka_count", 0)
        has_otkatnye = params.get("has_otkatnye", False)
        otkatnye_count = params.get("otkatnye_count", 0)
        has_raspashnye = params.get("has_raspashnye", False)
        raspashnye_count = params.get("raspashnye_count", 0)

        n_kalitka = kalitka_count if has_kalitka else 0
        n_otkatnye = otkatnye_count if has_otkatnye else 0
        n_raspashnye = raspashnye_count if has_raspashnye else 0

        stolby_pod_zabor = math.ceil((fence_length - n_kalitka * 1 - n_otkatnye * 4 - n_raspashnye * 4) / 3)
        stolby_pod_zabor = max(stolby_pod_zabor, 0)

    fence_height = params["fence_height"]  # высота забора (м)
    material_type = params["material_type"]  # Профнастил / Штакет / Шахматка
    material_name = params["material_name"]  # конкретный выбранный материал
    gap = params["gap"]  # зазор для штакета (м)
    fastener = params["fastener"]  # Саморез кровельный / Саморез с пресс-шайбой
    color_ral = params["color_ral"]

    stolb_type = params["stolb_type"]  # индекс 1-4
    lag_rows = params["lag_rows"]  # 2 или 3
    distance_km = params["distance_km"]

    has_fundament = params["has_fundament"]
    fund_length = params["fund_length"]
    fund_width = params["fund_width"]
    fund_height = params["fund_height"]

    address = params["address"]
    contact = params["contact"]

    # Столбы под ворота и калитки
    stolby_pod_vorota = (n_kalitka * 2) + (n_otkatnye * 2) + (n_raspashnye * 2)

    # --- Цены установки/монтажа ---
    if fence_length < 31:
        price_stolb_install = 500
        base_m = 1300; base_3l = 1800; base_2s = 2000
    elif fence_length < 51:
        price_stolb_install = 450
        base_m = 1200; base_3l = 1700; base_2s = 1900
    elif fence_length < 71:
        price_stolb_install = 400
        base_m = 1100; base_3l = 1600; base_2s = 1800
    elif fence_length < 101:
        price_stolb_install = 400
        base_m = 1000; base_3l = 1500; base_2s = 1700
    elif fence_length < 201:
        price_stolb_install = 400
        base_m = 900; base_3l = 1400; base_2s = 1600
    elif fence_length < 351:
        price_stolb_install = 400
        base_m = 600; base_3l = 850; base_2s = 1050
    elif fence_length < 501:
        price_stolb_install = 400
        base_m = 550; base_3l = 750; base_2s = 850
    else:
        price_stolb_install = 400
        base_m = 500; base_3l = 700; base_2s = 800

    if material_type == "Шахматка" or (material_type == "Штакет" and params.get("double_sided", False)):
        price_montazh = math.ceil((base_2s * 1.2) / 10) * 10
    elif lag_rows == 3:
        price_montazh = math.ceil((base_3l * 1.2) / 10) * 10
    else:
        price_montazh = math.ceil((base_m * 1.2) / 10) * 10

    price_pokraska = 50 if fence_length < 30 else (30 if fence_length < 50 else 25)

    # Длина монтажа забора (м.п.)
    montazh_length = fence_length - n_otkatnye * 4 - n_raspashnye * 4 - n_kalitka

    # --- Цена столба (выбранного типа) ---
    stolb_names = {
        "60х60х2мм": "Столб 60х60х2мм",
        "73мм НКТ": "Столб 73мм НКТ",
        "60х40х2мм": "Столб 60х40х2мм",
        "80х80х2мм": "Столб 80х80х2мм",
    }
    stolb_price_key = stolb_names.get(stolb_type, "Столб 60х60х2мм")
    stolb_price_per_mp = prices.get(stolb_price_key, 944)

    # --- Лаги ---
    lagi_count = lag_rows * stolby_pod_zabor

    # --- Финишный материал ---
    finish_qty = 0
    finish_price_total = 0
    finish_name = material_name

    if material_type == "Профнастил":
        # Кол-во листов (м.п., с коэфф 1.15 на нахлест) + ворота/калитки
        finish_qty = math.ceil(fence_length / 1.15 + n_kalitka + n_otkatnye + n_raspashnye)
        # Цена за лист = 1.22 * высота * цена_за_м2
        price_m2 = proflist.get(material_name, 465)
        finish_price_total = round(finish_qty * 1.22 * fence_height * price_m2)
    elif material_type == "Штакет":
        sh_data = shtaket.get(material_name, {"price": 55, "width_m": 0.1})
        sh_width = sh_data["width_m"]
        sh_price = sh_data["price"]
        finish_qty = math.ceil(fence_length / (sh_width + gap))
        finish_price_total = round(finish_qty * sh_price * fence_height)
    elif material_type == "Шахматка":
        sh_data = shtaket.get(material_name, {"price": 55, "width_m": 0.1})
        sh_width = sh_data["width_m"]
        sh_price = sh_data["price"]
        finish_qty = math.ceil(fence_length / (sh_width + gap)) * 2
        finish_price_total = round(finish_qty * sh_price * fence_height)

    # --- Саморезы (креплёж) ---
    fastener_price = prices.get(fastener, 3.5)
    if material_type == "Профнастил":
        samorez_qty = math.ceil(fence_length * fence_height * 6)
    else:
        samorez_qty = finish_qty * 4  # 4 самореза на штакетину
    samorez_qty = math.ceil(samorez_qty / 250) * 250  # Округляем до упаковки

    # --- Расходные материалы ---
    elektrod_packs = max(math.ceil(fence_length / 120), 1)
    kraska_cans = max(math.ceil(fence_length / 30), 1)
    cement_bags = math.ceil(stolby_pod_zabor / 4 + n_kalitka / 2 + n_raspashnye / 2 + n_otkatnye * 4)
    scheben_bags = math.ceil(stolby_pod_zabor + n_kalitka * 2 + n_otkatnye * 6 + n_raspashnye * 2 - stolby_pod_zabor / 2)
    otsev_bags = scheben_bags

    # Покраска (м.п.)
    pokraska_mp = (lagi_count * 3) + (stolby_pod_zabor * 2) + (n_kalitka * 7) + (n_otkatnye * 70) + (n_raspashnye * 40)

    # Валики
    valik_qty = 3 if fence_length < 50 else 6
    # Цинк
    zink_qty = 1 if fence_length <= 100 else 2
    # Диски
    disk_qty = math.ceil(fence_length / 10)

    # Доставка + ГСМ
    delivery_cost = round(distance_km * prices.get("Доставка (коэфф. расстояния)", 204))

    # --- ФУНДАМЕНТ (опционально) ---
    fund_items = []
    if has_fundament:
        beton_m3 = fund_length * fund_width * fund_height
        # Объём фундамента определяет единицу измерения работ
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

    # ============================================================
    # ФОРМИРОВАНИЕ ИТОГОВОЙ ТАБЛИЦЫ (как в листе «Итог»)
    # ============================================================
    works = []  # работы
    materials = []  # материалы

    # 1. Монтаж столбов
    works.append({
        "name": "Монтаж столбов на глубину бурения, выставление по уровню, заливка бетоном",
        "unit": "шт.", "qty": stolby_pod_zabor, "price": price_stolb_install,
        "total": stolby_pod_zabor * price_stolb_install
    })

    # 2. Бурение
    works.append({
        "name": "Бурение отверстий в грунте глубиной 1500мм",
        "unit": "шт", "qty": stolby_pod_zabor, "price": price_stolb_install,
        "total": stolby_pod_zabor * price_stolb_install
    })

    # 3. Монтаж забора
    works.append({
        "name": "Монтаж забора",
        "unit": "м.п.", "qty": montazh_length, "price": price_montazh,
        "total": round(montazh_length * price_montazh)
    })

    # 4. Монтаж ворот откатных
    if n_otkatnye > 0:
        works.append({
            "name": "Монтаж ворот откатных",
            "unit": "шт", "qty": n_otkatnye, "price": prices.get("Монтаж ворот откатных", 36000),
            "total": n_otkatnye * prices.get("Монтаж ворот откатных", 36000)
        })
        # Если есть привод (здесь мы проверяем выбран ли привод. Предположим, если "Привод для откатных ворот" есть в опциях, 
        # то добавим. Но поскольку в старом коде это был просто материал, мы добавим работу по монтажу привода всегда, 
        # когда выбраны откатные ворота, если он включен. Добавим опцию в форму позже или просто добавим сейчас.)
        if params.get("has_otkatnye_privod", True):
            works.append({
                "name": "Монтаж привода под откатные ворота",
                "unit": "шт", "qty": n_otkatnye, "price": prices.get("Монтаж привода под откатные ворота", 5400),
                "total": n_otkatnye * prices.get("Монтаж привода под откатные ворота", 5400)
            })

    # 5. Монтаж ворот распашных
    if n_raspashnye > 0:
        works.append({
            "name": "Монтаж ворот распашных",
            "unit": "шт", "qty": n_raspashnye, "price": prices.get("Монтаж ворот распашных", 11880),
            "total": n_raspashnye * prices.get("Монтаж ворот распашных", 11880)
        })

    # 6. Монтаж калитки
    if n_kalitka > 0:
        works.append({
            "name": "Монтаж калитки",
            "unit": "шт", "qty": n_kalitka, "price": prices.get("Монтаж калитки", 6600),
            "total": n_kalitka * prices.get("Монтаж калитки", 6600)
        })

    # 7. Покраска
    works.append({
        "name": "Покраска металлоконструкции",
        "unit": "м.п.", "qty": pokraska_mp, "price": price_pokraska,
        "total": pokraska_mp * price_pokraska
    })

    # 8. Фундаментные работы
    if has_fundament:
        works.append({
            "name": "Монтажные работы по заливке фундамента",
            "unit": fund_work_unit, "qty": round(fund_work_qty, 1), "price": fund_work_price,
            "total": round(fund_work_qty * fund_work_price)
        })

    # ======== МАТЕРИАЛЫ ========

    # Финишный материал
    materials.append({
        "name": finish_name,
        "unit": "шт" if material_type != "Профнастил" else "лист",
        "qty": finish_qty,
        "price": round(finish_price_total / max(finish_qty, 1)),
        "total": finish_price_total
    })

    # Саморезы
    materials.append({
        "name": fastener,
        "unit": "шт", "qty": samorez_qty,
        "price": fastener_price,
        "total": round(samorez_qty * fastener_price)
    })

    # Столбы заборные
    materials.append({
        "name": f"Столб заборный {stolb_type}",
        "unit": "шт", "qty": stolby_pod_zabor,
        "price": stolb_price_per_mp,
        "total": stolby_pod_zabor * stolb_price_per_mp
    })

    # Столбы под ворота/калитки (80х80)
    if stolby_pod_vorota > 0:
        stolb_vor_price = prices.get("Столб под ворота 80х80х3000", 1275)
        materials.append({
            "name": "Столб под ворота и калитки 80х80х3000",
            "unit": "шт", "qty": stolby_pod_vorota,
            "price": stolb_vor_price,
            "total": stolby_pod_vorota * stolb_vor_price
        })

    # Электроды
    materials.append({
        "name": "Электроды сварочные Ок-46 3мм",
        "unit": "пачка", "qty": elektrod_packs,
        "price": prices.get("Электроды сварочные Ок-46 3мм (пачка)", 2600),
        "total": elektrod_packs * prices.get("Электроды сварочные Ок-46 3мм (пачка)", 2600)
    })

    # Краска
    materials.append({
        "name": "Краска грунт-эмаль 3в1",
        "unit": "банка", "qty": kraska_cans,
        "price": prices.get("Краска грунт-эмаль 3в1", 2200),
        "total": kraska_cans * prices.get("Краска грунт-эмаль 3в1", 2200)
    })

    # Лаги
    materials.append({
        "name": "Лага заборная 40х20х3000мм",
        "unit": "шт", "qty": lagi_count,
        "price": prices.get("Лага заборная 40х20х3000мм", 362),
        "total": lagi_count * prices.get("Лага заборная 40х20х3000мм", 362)
    })

    # Цемент
    materials.append({
        "name": "Цемент (мешок 50кг)",
        "unit": "мешок", "qty": cement_bags,
        "price": prices.get("Цемент (мешок 50кг)", 550),
        "total": cement_bags * prices.get("Цемент (мешок 50кг)", 550)
    })

    # Щебень
    materials.append({
        "name": "Щебень (мешок 50кг)",
        "unit": "мешок", "qty": scheben_bags,
        "price": prices.get("Щебень (мешок 50кг)", 170),
        "total": scheben_bags * prices.get("Щебень (мешок 50кг)", 170)
    })

    # Отсев
    materials.append({
        "name": "Отсев (мешок 50кг)",
        "unit": "мешок", "qty": otsev_bags,
        "price": prices.get("Отсев (мешок 50кг)", 170),
        "total": otsev_bags * prices.get("Отсев (мешок 50кг)", 170)
    })

    # Ворота откатные (материал)
    if n_otkatnye > 0:
        otk_price = prices.get("Ворота откатные со швеллером балкой и роликами", 24000)
        materials.append({
            "name": "Ворота откатные (каркас, швеллер, балка, ролики)",
            "unit": "комплект", "qty": n_otkatnye,
            "price": otk_price,
            "total": n_otkatnye * otk_price
        })
        # Привод
        privod_price = prices.get("Привод для откатных ворот", 33500)
        materials.append({
            "name": "Привод для откатных ворот",
            "unit": "шт", "qty": n_otkatnye,
            "price": privod_price,
            "total": n_otkatnye * privod_price
        })

    # Ворота распашные (материал)
    if n_raspashnye > 0:
        rasp_price = prices.get("Ворота распашные стандарт", 9000)
        materials.append({
            "name": "Ворота распашные (каркас с шарнирами и фиксаторами)",
            "unit": "комплект", "qty": n_raspashnye,
            "price": rasp_price,
            "total": n_raspashnye * rasp_price
        })

    # Калитка (материал)
    if n_kalitka > 0:
        kal_price = prices.get("Калитка стандарт", 5400)
        materials.append({
            "name": "Калитка стандарт (каркас)",
            "unit": "комплект", "qty": n_kalitka,
            "price": kal_price,
            "total": n_kalitka * kal_price
        })
        zamok_price = prices.get("Замок в калитку", 2250)
        materials.append({
            "name": "Замок в калитку",
            "unit": "шт", "qty": n_kalitka,
            "price": zamok_price,
            "total": n_kalitka * zamok_price
        })

    # Диски
    materials.append({
        "name": "Диски отрезные 125х1,2",
        "unit": "шт", "qty": disk_qty,
        "price": prices.get("Диски отрезные 125х1,2", 35),
        "total": disk_qty * prices.get("Диски отрезные 125х1,2", 35)
    })

    # Валики
    materials.append({
        "name": "Валик с бюгелем полиакриловый",
        "unit": "шт", "qty": valik_qty,
        "price": prices.get("Валик с бюгелем", 250),
        "total": valik_qty * prices.get("Валик с бюгелем", 250)
    })

    # Цинк
    materials.append({
        "name": "Цинк холодный (баллончик)",
        "unit": "шт", "qty": zink_qty,
        "price": prices.get("Цинк холодный (баллончик)", 450),
        "total": zink_qty * prices.get("Цинк холодный (баллончик)", 450)
    })

    # Ветошь
    materials.append({
        "name": "Ветошь для обработки",
        "unit": "шт", "qty": 1,
        "price": prices.get("Ветошь", 100),
        "total": prices.get("Ветошь", 100)
    })

    # Обезжириватель
    materials.append({
        "name": "Обезжириватель",
        "unit": "шт", "qty": 1,
        "price": prices.get("Обезжириватель", 190),
        "total": prices.get("Обезжириватель", 190)
    })

    # Фундамент — материалы
    for fi in fund_items:
        materials.append({
            "name": fi["name"],
            "unit": fi["unit"], "qty": fi["qty"],
            "price": fi["price"],
            "total": round(fi["qty"] * fi["price"])
        })

    # Доставка
    materials.append({
        "name": "Доставка + ГСМ монтажников",
        "unit": "шт", "qty": 1,
        "price": delivery_cost,
        "total": delivery_cost
    })

    total_works = sum(w["total"] for w in works)
    total_materials = sum(m["total"] for m in materials)
    grand_total = total_works + total_materials

    return {
        "works": works,
        "materials": materials,
        "total_works": total_works,
        "total_materials": total_materials,
        "grand_total": grand_total,
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
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

/* Скрываем сайдбар */
[data-testid="collapsedControl"] { display: none; }
section[data-testid="stSidebar"] { display: none; }

/* Основной фон */
.stApp {
    background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 40%, #16213e 100%);
}

/* Шрифт и читаемость текста */
html, body, [class*="css"], p, span, div, h1, h2, h3, h4, h5, h6, label, li {
    font-family: 'Inter', sans-serif;
    color: #f8f9fa !important;
}

/* Исправление цвета текста в выпадающих списках (selectbox) */
div[data-baseweb="select"] * {
    color: #000000 !important;
}
ul[role="listbox"] * {
    color: #000000 !important;
}

/* Заголовок-шапка */
.header-bar {
    background: linear-gradient(135deg, rgba(30, 60, 90, 0.95), rgba(20, 40, 70, 0.95));
    backdrop-filter: blur(12px);
    border-bottom: 2px solid #00b894;
    padding: 0.7rem 1.5rem;
    border-radius: 0 0 16px 16px;
    box-shadow: 0 4px 20px rgba(0, 184, 148, 0.15);
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 1rem;
}
.header-bar h2 {
    color: #e0e0e0;
    margin: 0;
    font-weight: 800;
    font-size: 1.4rem;
}
.header-bar span {
    color: #00b894;
    font-weight: 300;
    font-size: 1rem;
}

/* Карточки метрик */
.metric-card {
    background: linear-gradient(135deg, rgba(30, 50, 80, 0.8), rgba(20, 35, 60, 0.9));
    border: 1px solid rgba(0, 184, 148, 0.3);
    border-radius: 16px;
    padding: 1.2rem 1.5rem;
    text-align: center;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    transition: all 0.3s ease;
}
.metric-card:hover {
    transform: translateY(-3px);
    border-color: rgba(0, 184, 148, 0.6);
    box-shadow: 0 8px 30px rgba(0, 184, 148, 0.2);
}
.metric-card .label {
    color: #8899aa;
    font-size: 0.85rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 0.4rem;
}
.metric-card .value {
    font-size: 1.8rem;
    font-weight: 800;
    background: linear-gradient(135deg, #00b894, #00cec9);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.metric-card .value.orange {
    background: linear-gradient(135deg, #fdcb6e, #e17055);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.metric-card .value.blue {
    background: linear-gradient(135deg, #74b9ff, #0984e3);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.metric-card .value.total {
    font-size: 2.2rem;
    background: linear-gradient(135deg, #ffeaa7, #fdcb6e, #e17055);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

/* Секция-панель */
.panel {
    background: rgba(25, 40, 65, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
    backdrop-filter: blur(8px);
}
.panel h4 {
    color: #00b894;
    margin-top: 0;
    margin-bottom: 0.8rem;
    font-weight: 700;
}

/* Таблица */
.stDataFrame, table {
    border-radius: 12px !important;
    overflow: hidden;
}

/* Вкладки */
div[data-testid="stTabs"] button {
    color: #8899aa !important;
    font-weight: 600 !important;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
    color: #00b894 !important;
    border-bottom-color: #00b894 !important;
}

/* Фикс стилей инпутов */
div[data-testid="stNumberInput"] label p,
div[data-testid="stSelectbox"] label p,
div[data-testid="stRadio"] label p,
div[data-testid="stCheckbox"] label p,
div[data-testid="stTextInput"] label p {
    font-size: 13px !important;
    font-weight: 500 !important;
    color: #b0bec5 !important;
}

/* Экспандеры */
div[data-testid="stExpander"] details summary p {
    font-size: 1.1rem;
    font-weight: 700;
    color: #00b894;
}

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
        st.markdown("""
        <div>
            <h2 style='margin:0; padding-top:8px; font-weight:800; color: #e0e0e0;'>
                🏗️ Калькулятор заборов
            </h2>
            <span style='color: #00b894; font-size: 0.9rem;'>ООО "Дача 2000" — Профессиональный расчёт стоимости</span>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ============================================================
# ВВОД ДАННЫХ
# ============================================================
with st.expander("🛠️ ПАРАМЕТРЫ ЗАБОРА (Нажмите, чтобы развернуть/свернуть)", expanded=True):
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
        st.markdown("#### 📐 1. Габариты и Материал")
        
        if calc_mode == "express":
            fence_length = st.number_input("Общая длина забора (м.п.):", 1, 500, 128)
        else:
            num_sides = st.number_input("Количество сторон:", 1, 4, 1)
            for i in range(1, num_sides + 1):
                with st.container(border=True):
                    st.markdown(f"**Сторона {i}**")
                    s_len = st.number_input(f"Длина стороны {i} (м.п.):", 1.0, 500.0, 30.0, key=f"s_len_{i}")
                    
                    col_k, col_o, col_r = st.columns(3)
                    with col_k:
                        s_kal = st.number_input(f"Калитки (шт):", 0, 5, 0, key=f"s_kal_{i}")
                        s_kal_pos = ""
                        if s_kal > 0:
                            s_kal_pos = st.text_input("Отступ (м):", "2", key=f"s_kal_pos_{i}")
                    with col_o:
                        s_otk = st.number_input(f"Отк. ворота:", 0, 5, 0, key=f"s_otk_{i}")
                        s_otk_pos = ""
                        if s_otk > 0:
                            s_otk_pos = st.text_input("Отступ (м):", "5", key=f"s_otk_pos_{i}")
                    with col_r:
                        s_rasp = st.number_input(f"Расп. ворота:", 0, 5, 0, key=f"s_rasp_{i}")
                        s_rasp_pos = ""
                        if s_rasp > 0:
                            s_rasp_pos = st.text_input("Отступ (м):", "5", key=f"s_rasp_pos_{i}")
                    
                    sides_data.append({
                        "length": s_len,
                        "kalitka_count": s_kal,
                        "kalitka_pos": s_kal_pos,
                        "otkatnye_count": s_otk,
                        "otkatnye_pos": s_otk_pos,
                        "raspashnye_count": s_rasp,
                        "raspashnye_pos": s_rasp_pos
                    })
            
            fence_length = sum(s["length"] for s in sides_data)

        fence_height = st.number_input("Высота забора (м):", 1.0, 4.0, 2.0, step=0.1)

        st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.2;'>", unsafe_allow_html=True)

        material_type = st.radio("Тип финишного материала:", ["Профнастил", "Штакет", "Шахматка"], horizontal=True)

        if material_type == "Профнастил":
            material_name = st.selectbox("Выберите профлист:", list(proflist.keys()))
            gap_m = 0.0
        else:
            material_name = st.selectbox("Выберите штакет:", list(shtaket.keys()))
            gap_m = st.number_input("Зазор между штакетинами (м):", 0.01, 0.10, 0.04, step=0.01)

        color_ral = st.text_input("Цвет RAL:", "RAL 8017")
        fastener = st.selectbox("Способ крепления:", ["Саморез кровельный в цвет", "Саморез с пресс-шайбой"])

    with c2:
        st.markdown("#### 🚪 2. Ворота, Калитки, Столбы")

        if calc_mode == "express":
            has_kalitka = st.checkbox("Калитка", value=True)
            kalitka_count = st.number_input("Кол-во калиток:", 1, 5, 1, key="kalitka_n") if has_kalitka else 0

            has_otkatnye = st.checkbox("Ворота откатные", value=True)
            otkatnye_count = st.number_input("Кол-во откатных ворот:", 1, 5, 1, key="otkat_n") if has_otkatnye else 0

            has_raspashnye = st.checkbox("Ворота распашные", value=False)
            raspashnye_count = st.number_input("Кол-во распашных ворот:", 1, 5, 1, key="rasp_n") if has_raspashnye else 0
        else:
            st.info("Ворота и калитки настраиваются для каждой стороны в блоке слева.")

        st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.2;'>", unsafe_allow_html=True)

        stolb_type = st.selectbox("Тип столбов:", ["60х60х2мм", "73мм НКТ", "60х40х2мм", "80х80х2мм"])
        lag_rows = st.radio("Количество рядов лаг:", [2, 3], horizontal=True)

    with c3:
        st.markdown("#### 📦 3. Доставка и Фундамент")
        distance_km = st.number_input("Расстояние до объекта (км):", 0, 500, 60)

        st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.2;'>", unsafe_allow_html=True)

        has_fundament = st.checkbox("Рассчитать фундамент", value=True)
        if has_fundament:
            fund_length = st.number_input("Длина фундамента (м.п.):", 1.0, 500.0, 64.0)
            fund_width = st.number_input("Ширина фундамента (м):", 0.1, 2.0, 0.25, step=0.05)
            fund_height = st.number_input("Высота фундамента (м):", 0.1, 2.0, 0.6, step=0.1)
        else:
            fund_length = fund_width = fund_height = 0

        st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.2;'>", unsafe_allow_html=True)

        address = st.text_input("Адрес объекта:", "КП Заповедник парк Совята уч 81")
        contact = st.text_input("Контактное лицо:", "Борис Борисович +7-912-297-11-79")

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
    "fastener": fastener,
    "color_ral": color_ral,
    "has_kalitka": has_kalitka,
    "kalitka_count": kalitka_count if has_kalitka else 0,
    "has_otkatnye": has_otkatnye,
    "otkatnye_count": otkatnye_count if has_otkatnye else 0,
    "has_raspashnye": has_raspashnye,
    "raspashnye_count": raspashnye_count if has_raspashnye else 0,
    "stolb_type": stolb_type,
    "lag_rows": lag_rows,
    "distance_km": distance_km,
    "has_fundament": has_fundament,
    "fund_length": fund_length,
    "fund_width": fund_width,
    "fund_height": fund_height,
    "address": address,
    "contact": contact,
}

result = calculate_fence(params, prices, proflist, shtaket)

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

# Таблицы
tab_works, tab_materials, tab_all = st.tabs(["⚒️ Работы", "📦 Материалы", "📋 Полная калькуляция"])

with tab_works:
    works_table = []
    for idx, w in enumerate(result["works"], 1):
        works_table.append({
            "№": idx,
            "Наименование": w["name"],
            "Ед.": w.get("unit", ""),
            "Кол-во": w.get("qty", ""),
            "Цена": f'{w.get("price", 0):,.0f}',
            "Сумма": f'{w["total"]:,.0f}',
        })
    st.dataframe(works_table, use_container_width=True, hide_index=True)
    st.markdown(f"**Итого работы: {result['total_works']:,.0f} руб.**")

with tab_materials:
    mat_table = []
    for idx, m in enumerate(result["materials"], 1):
        mat_table.append({
            "№": idx,
            "Наименование": m["name"],
            "Ед.": m.get("unit", ""),
            "Кол-во": m.get("qty", ""),
            "Цена": f'{m.get("price", 0):,.0f}',
            "Сумма": f'{m["total"]:,.0f}',
        })
    st.dataframe(mat_table, use_container_width=True, hide_index=True)
    st.markdown(f"**Итого материалы: {result['total_materials']:,.0f} руб.**")

with tab_all:
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
    st.markdown(f"### 💰 ИТОГО: {result['grand_total']:,.0f} руб.")

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
