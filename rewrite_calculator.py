import re

with open("pages/fence_calculator.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Replace the calculate_fence function
new_calculate_fence = """def calculate_fence(params, prices, proflist, shtaket):
    calc_mode = params.get("calc_mode", "express")
    fence_height = params["fence_height"]
    material_type = params["material_type"]
    material_name = params["material_name"]
    gap = params["gap"]
    fastener = params["fastener"]
    color_ral = params["color_ral"]

    stolb_type = params["stolb_type"]
    lag_rows = params["lag_rows"]
    distance_km = params["distance_km"]
    post_pitch = params.get("post_pitch", 3.0)
    hole_depth = params.get("hole_depth", 1.5)
    ground_distance = params.get("ground_distance", 0.05)

    has_fundament = params["has_fundament"]
    fund_length = params["fund_length"]
    fund_width = params["fund_width"]
    fund_height = params["fund_height"]

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
            if material_type == "Профнастил":
                el_sheets = math.ceil(el_length / sheet_width)
                screws_per_sheet = math.ceil(max(0, el_height - ground_distance) / 0.5) * 2
                screws = el_sheets * screws_per_sheet
            elif material_type == "Штакет":
                sh_data = shtaket.get(material_name, {"price": 55, "width_m": 0.1})
                sh_width = sh_data["width_m"]
                el_sheets = math.ceil(el_length / (sh_width + gap))
                screws = el_sheets * 4
            else: # Шахматка
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
            extra80_posts += 2  # 2 столба 80х80 на проем
            calc_element_profile(item["width"], height)

        available_length = max(0, available_length)
        
        # Расчет секций
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

        # Объем бетона (в м3) на лунки
        radius = 0.3 / 2  # диаметр 300мм
        one_hole_vol = math.pi * radius * radius * hole_depth
        concrete_vol = one_hole_vol * (post_count + extra80_posts)

        return {
            "post_count": post_count,
            "extra80_posts": extra80_posts,
            "lag_total_count": lag_total_count,
            "profile_area": total_profile_area,
            "sheets_count": total_sheets_count,
            "total_screws": total_screws,
            "concrete_vol": concrete_vol,
            "montazh_length": available_length
        }

    # Сбор данных
    total_stolby = 0
    total_stolby_vorota = 0
    total_lagi = 0
    total_finish_qty = 0
    total_screws = 0
    total_concrete_vol = 0
    total_montazh_length = 0

    n_kalitka = 0
    n_otkatnye = 0
    n_raspashnye = 0
    fence_length_total = 0

    if calc_mode == "detailed":
        sides_data = params.get("sides_data", [])
        for s in sides_data:
            fence_length_total += s["length"]
            n_kalitka += s["kalitka_count"]
            n_otkatnye += s["otkatnye_count"]
            n_raspashnye += s["raspashnye_count"]
            
            g_d = []
            for _ in range(s["kalitka_count"]): g_d.append({"type": "door", "width": 1.0})
            for _ in range(s["otkatnye_count"]): g_d.append({"type": "gate", "width": 4.0})
            for _ in range(s["raspashnye_count"]): g_d.append({"type": "gate", "width": 4.0})
            
            res = calc_side(s["length"], fence_height, g_d)
            total_stolby += res["post_count"]
            total_stolby_vorota += res["extra80_posts"]
            total_lagi += res["lag_total_count"]
            total_finish_qty += res["sheets_count"]
            total_screws += res["total_screws"]
            total_concrete_vol += res["concrete_vol"]
            total_montazh_length += res["montazh_length"]
    else:
        fence_length_total = params.get("fence_length", 0)
        has_kalitka = params.get("has_kalitka", False)
        n_kalitka = params.get("kalitka_count", 0) if has_kalitka else 0
        has_otkatnye = params.get("has_otkatnye", False)
        n_otkatnye = params.get("otkatnye_count", 0) if has_otkatnye else 0
        has_raspashnye = params.get("has_raspashnye", False)
        n_raspashnye = params.get("raspashnye_count", 0) if has_raspashnye else 0
        
        g_d = []
        for _ in range(n_kalitka): g_d.append({"type": "door", "width": 1.0})
        for _ in range(n_otkatnye): g_d.append({"type": "gate", "width": 4.0})
        for _ in range(n_raspashnye): g_d.append({"type": "gate", "width": 4.0})
        
        res = calc_side(fence_length_total, fence_height, g_d)
        total_stolby = res["post_count"]
        total_stolby_vorota = res["extra80_posts"]
        total_lagi = res["lag_total_count"]
        total_finish_qty = res["sheets_count"]
        total_screws = res["total_screws"]
        total_concrete_vol = res["concrete_vol"]
        total_montazh_length = res["montazh_length"]

    # --- Цены установки/монтажа ---
    import math
    if fence_length_total < 31:
        price_stolb_install = 500
        base_m = 1300; base_3l = 1800; base_2s = 2000
    elif fence_length_total < 51:
        price_stolb_install = 450
        base_m = 1200; base_3l = 1700; base_2s = 1900
    elif fence_length_total < 71:
        price_stolb_install = 400
        base_m = 1100; base_3l = 1600; base_2s = 1800
    elif fence_length_total < 101:
        price_stolb_install = 400
        base_m = 1000; base_3l = 1500; base_2s = 1700
    elif fence_length_total < 201:
        price_stolb_install = 400
        base_m = 900; base_3l = 1400; base_2s = 1600
    elif fence_length_total < 351:
        price_stolb_install = 400
        base_m = 600; base_3l = 850; base_2s = 1050
    elif fence_length_total < 501:
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
    if material_type == "Профнастил":
        price_m2 = proflist.get(material_name, 465)
        # В JS считалась точная площадь листа (1.22 * высота) 
        # Или мы можем использовать price_m2 как цену квадрата: qty * 1.22 * height * price_m2
        finish_price_total = round(total_finish_qty * 1.22 * fence_height * price_m2)
    elif material_type in ["Штакет", "Шахматка"]:
        sh_data = shtaket.get(material_name, {"price": 55, "width_m": 0.1})
        sh_price = sh_data["price"]
        finish_price_total = round(total_finish_qty * sh_price * fence_height)

    # --- Саморезы (креплёж) ---
    fastener_price = prices.get(fastener, 3.5)
    samorez_qty = math.ceil(total_screws / 250) * 250

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

    if n_otkatnye > 0:
        works.append({
            "name": "Монтаж ворот откатных",
            "unit": "шт", "qty": n_otkatnye, "price": prices.get("Монтаж ворот откатных", 36000),
            "total": n_otkatnye * prices.get("Монтаж ворот откатных", 36000)
        })
        if params.get("has_avtomatika", True):
            works.append({
                "name": "Монтаж привода под откатные ворота",
                "unit": "шт", "qty": n_otkatnye, "price": prices.get("Монтаж привода под откатные ворота", 5400),
                "total": n_otkatnye * prices.get("Монтаж привода под откатные ворота", 5400)
            })

    if n_raspashnye > 0:
        works.append({
            "name": "Монтаж ворот распашных",
            "unit": "шт", "qty": n_raspashnye, "price": prices.get("Монтаж ворот распашных", 11880),
            "total": n_raspashnye * prices.get("Монтаж ворот распашных", 11880)
        })

    if n_kalitka > 0:
        works.append({
            "name": "Монтаж калитки",
            "unit": "шт", "qty": n_kalitka, "price": prices.get("Монтаж калитки", 6600),
            "total": n_kalitka * prices.get("Монтаж калитки", 6600)
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
    materials.append({
        "name": "Лага заборная 40х20х3000мм",
        "unit": "шт", "qty": total_lagi,
        "price": prices.get("Лага заборная 40х20х3000мм", 362),
        "total": total_lagi * prices.get("Лага заборная 40х20х3000мм", 362)
    })
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

    if n_otkatnye > 0:
        otk_price = prices.get("Ворота откатные со швеллером балкой и роликами", 24000)
        materials.append({
            "name": "Ворота откатные (каркас, швеллер, балка, ролики)",
            "unit": "комплект", "qty": n_otkatnye,
            "price": otk_price,
            "total": n_otkatnye * otk_price
        })
        privod_price = prices.get("Привод для откатных ворот", 33500)
        materials.append({
            "name": "Привод для откатных ворот",
            "unit": "шт", "qty": n_otkatnye,
            "price": privod_price,
            "total": n_otkatnye * privod_price
        })

    if n_raspashnye > 0:
        rasp_price = prices.get("Ворота распашные стандарт", 9000)
        materials.append({
            "name": "Ворота распашные (каркас с шарнирами и фиксаторами)",
            "unit": "комплект", "qty": n_raspashnye,
            "price": rasp_price,
            "total": n_raspashnye * rasp_price
        })

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
"""

start_pattern = r"def calculate_fence\(params, prices, proflist, shtaket\):"
end_pattern = r"    # --- Генерация чертежа ---\n    plot_bytes = None\n"

match = re.search(f"{start_pattern}.*?{end_pattern}", content, re.DOTALL)
if match:
    content = content[:match.start()] + new_calculate_fence + content[match.end():]
else:
    print("Не удалось найти функцию calculate_fence во второй раз!")

with open("pages/fence_calculator.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Успешно заменено!")
