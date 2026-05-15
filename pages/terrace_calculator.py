import streamlit as st
st.set_page_config(page_title="Дача 2000 | Умный Калькулятор", layout="wide", initial_sidebar_state="collapsed")
import os
import math
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import io
from fpdf import FPDF
import datetime
import pandas as pd
import re
from streamlit_drawable_canvas import st_canvas
import json
from PIL import Image as PILImage, ImageDraw

try:
    import google.generativeai as genai
    from PIL import Image
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False
from data_loader import get_terrace_prices
PARSED_BOARDS, PIPES_JOIST, PIPES_FRAME = get_terrace_prices()

METAL_MARGIN = 1.15
GAP_MM = 5
JOIST_STEP_M = 0.4
PILE_STEP_M = 2.0
MIN_CUT_LENGTH = 1.0  # Минимальная допустимая длина обрезанной доски (м)

# --- 2. ПАЛУБНАЯ РАСКЛАДКА «КИРПИЧНАЯ КЛАДКА» ---
# Правила:
#   1. Внутри ряда — ТОЛЬКО целые (нерезанные) доски длиной M
#   2. Обрезанные доски допустимы ТОЛЬКО по краям (первая и/или последняя в ряду)
#   3. Минимальная длина обрезанной доски — MIN_CUT_LENGTH (1 м)
#   4. Два паттерна (A и B) чередуются для создания рисунка «кирпичная кладка»
#
# Примеры:
#   9м, доска 3м  → ряд A = [3, 3, 3],       ряд B = [1.5, 3, 3, 1.5]
#   10м, доска 4м → ряд A = [4, 4, 2],        ряд B = [2, 4, 4]
#   12м, доска 4м → ряд A = [4, 4, 4],        ряд B = [2, 4, 4, 2]
#   8.5м, доска 4м→ ряд A = [2.25, 4, 2.25],  ряд B = [3.25, 4, 1.25]

from calculators.terrace import get_row_patterns, get_1d_symmetric_pieces, get_best_symmetric_layout, get_custom_length_layout, consolidate_lengths, round_up_to_custom, optimize_waste, get_shifted_edge, draw_edge, point_in_polygon, polygon_row_segments

# --- Сохранение состояния между шагами (обход очистки Streamlit) ---
if 'ts_data' not in st.session_state:
    st.session_state.ts_data = {}

# Сохраняем все текущие значения виджетов в ts_data
for k in list(st.session_state.keys()):
    if k.startswith('ts_'):
        st.session_state.ts_data[k] = st.session_state[k]

# Восстанавливаем сохраненные значения (если Streamlit их удалил)
for k, v in st.session_state.ts_data.items():
    if k not in st.session_state:
        st.session_state[k] = v

# --- Тема оформления ---
from theme import apply_theme
theme = apply_theme()

is_light = theme["is_light"]
card_bg = theme["card_bg"]
card_border = theme["card_border"]
label_color = theme["label_color"]
header_text = theme["header_text"]

with st.container():
    col_logo, col_title, col_btn = st.columns([1.5, 7, 1.5], gap="small")
    with col_logo:
        try:
            st.image("logo.png", width=160)
        except:
            st.markdown("<h3 style='color:#9fcb3d; margin:0;'>Дача 2000</h3>", unsafe_allow_html=True)
    with col_title:
        st.markdown(f"""
        <div>
            <h2 style='margin:0; padding-top:8px; font-weight:800; color: {header_text};'>
                🏗️ Умный Калькулятор Террас
            </h2>
            <span style='color: #9fcb3d; font-size: 0.9rem;'>ООО "Дача 2000" — Профессиональный расчёт стоимости</span>
        </div>
        """, unsafe_allow_html=True)
    with col_btn:
        st.markdown("<div style='padding-top:10px;'></div>", unsafe_allow_html=True)
        if st.button(":material/refresh: Обновить прайс", use_container_width=True):
            st.cache_data.clear(); st.rerun()

# ============================================================
# WIZARD STATE
# ============================================================
if 'wizard_step' not in st.session_state:
    st.session_state.wizard_step = 1
if 'ts_vertices_mm' not in st.session_state:
    st.session_state.ts_vertices_mm = []

current_step = st.session_state.wizard_step

# ============================================================
# PROGRESS BAR
# ============================================================
step_labels = ["Форма", "Размеры", "Основание", "Доска", "Результат"]
progress_html = '<div style="display:flex;align-items:center;gap:0;margin:1rem 0 2rem 0;">'
for i, label in enumerate(step_labels, 1):
    is_active = i == current_step
    is_done = i < current_step
    if is_done:
        color, bg, border = "#191919", "#9fcb3d", "#9fcb3d"
        circle = f'<div style="width:32px;height:32px;border-radius:50%;background:{bg};color:{color};display:flex;align-items:center;justify-content:center;font-weight:800;font-size:14px;border:2px solid {border};">✓</div>'
    elif is_active:
        color, bg, border = "#191919", "#9fcb3d", "#9fcb3d"
        circle = f'<div style="width:32px;height:32px;border-radius:50%;background:{bg};color:{color};display:flex;align-items:center;justify-content:center;font-weight:800;font-size:14px;border:2px solid {border};box-shadow:0 0 12px rgba(159,203,61,0.5);">{i}</div>'
    else:
        lc = "#666666" if is_light else "#a0a0a0"
        circle = f'<div style="width:32px;height:32px;border-radius:50%;background:transparent;color:{lc};display:flex;align-items:center;justify-content:center;font-weight:600;font-size:14px;border:2px solid {lc};">{i}</div>'
    lbl_color = "#9fcb3d" if (is_active or is_done) else ("#666666" if is_light else "#a0a0a0")
    lbl_weight = "700" if is_active else "500"
    progress_html += f'<div style="display:flex;flex-direction:column;align-items:center;flex:0 0 auto;">{circle}<div style="font-size:11px;margin-top:4px;color:{lbl_color};font-weight:{lbl_weight};">{label}</div></div>'
    if i < 5:
        line_color = "#9fcb3d" if is_done else ("#e0e0e0" if is_light else "#333333")
        progress_html += f'<div style="flex:1;height:3px;background:{line_color};margin:0 4px;border-radius:2px;align-self:flex-start;margin-top:15px;"></div>'
progress_html += '</div>'
st.markdown(progress_html, unsafe_allow_html=True)

# ============================================================
# STEP 1: ФОРМА ТЕРРАСЫ
# ============================================================
if current_step == 1:
    st.markdown("### Выберите форму террасы")
    shapes = [
        ("rect", "▬", "Простая", "Прямоугольная стандартная терраса"),
        ("l_shape", "⌐", "Г-образная", "Угловая конфигурация"),
        ("u_shape", "⊓", "П-образная", "С внутренним вырезом"),
        ("circle", "◯", "Круглая", "Овал или круг"),
        ("custom", "✏", "Своя форма", "Нарисуйте или загрузите чертёж"),
    ]
    cols = st.columns(5, gap="medium")
    for i, (key, icon, title, desc) in enumerate(shapes):
        with cols[i]:
            sel = st.session_state.get('ts_shape', 'rect') == key
            brd = "2px solid #9fcb3d" if sel else f"1px solid {card_border}"
            bg = "rgba(159,203,61,0.08)" if sel else card_bg
            st.markdown(f"""<div style="background:{bg};border:{brd};border-radius:16px;padding:1.5rem 1rem;text-align:center;min-height:180px;transition:all 0.3s ease;cursor:pointer;">
                <div style="font-size:52px;line-height:1;color:#9fcb3d;">{icon}</div>
                <div style="font-weight:700;font-size:1.1rem;margin:0.8rem 0 0.5rem 0;color:{'#191919' if is_light else '#fff'};">{title}</div>
                <div style="font-size:0.8rem;color:{'#666666' if is_light else '#a0a0a0'};">{desc}</div>
            </div>""", unsafe_allow_html=True)
            if st.button(f"Выбрать", key=f"shape_{key}", use_container_width=True,
                         type="primary" if sel else "secondary"):
                st.session_state.ts_shape = key
                st.rerun()

    st.markdown("---")
    st.markdown("#### :material/person: Информация о проекте")
    ci1, ci2, ci3 = st.columns(3)
    if 'ts_client' not in st.session_state: st.session_state.ts_client = "Иван Иванович"
    if 'ts_manager' not in st.session_state: st.session_state.ts_manager = "Иван Иванов"
    if 'ts_manager_phone' not in st.session_state: st.session_state.ts_manager_phone = "+7 (999) 000-00-00"
    ci1.text_input("ФИО Клиента:", key='ts_client')
    ci2.text_input("Имя менеджера:", key='ts_manager')
    ci3.text_input("Телефон менеджера:", key='ts_manager_phone')

    _, col_next = st.columns([5, 1])
    with col_next:
        if st.button("Далее →", type="primary", use_container_width=True, key="next_1"):
            st.session_state.wizard_step = 2; st.rerun()

# ============================================================
# STEP 2: РАЗМЕРЫ
# ============================================================
elif current_step == 2:
    shape_key = st.session_state.get('ts_shape', 'rect')
    shape_map = {'rect': ':material/rectangle: Прямоугольная (Стандарт)',
                 'l_shape': ':material/architecture: Г-образная (Угловая)',
                 'u_shape': ':material/crop_din: П-образная (С вырезом)',
                 'circle': ':material/circle: Округлая (Овал / Круг)',
                 'custom': ':material/draw: Свой контур (По координатам)'}
    shape_type = shape_map.get(shape_key, shape_map['rect'])

    st.markdown("### :material/straighten: Шаг 2: Введите размеры")

    if shape_key == 'rect':
        c_l, c_w = st.columns(2)
        if 'ts_length' not in st.session_state: st.session_state.ts_length = 9.0
        if 'ts_width' not in st.session_state: st.session_state.ts_width = 4.0
        c_l.number_input("Длина (X), м:", 1.0, 50.0, key='ts_length')
        c_w.number_input("Глубина (Y), м:", 1.0, 50.0, key='ts_width')
    elif shape_key == 'circle':
        if 'ts_length' not in st.session_state: st.session_state.ts_length = 6.0
        if 'ts_width' not in st.session_state: st.session_state.ts_width = 4.0
        st.number_input("Длина (Диам X), м:", 1.0, 50.0, key='ts_length')
        st.number_input("Глубина (Диам Y), м:", 1.0, 50.0, key='ts_width')
    else:
        # --- Нестандартные формы: канвас ---
        ctrl1, ctrl2 = st.columns([3, 1])
        with ctrl2:
            scale_label = st.selectbox("Масштаб:", ["Мелкий (до 7м)", "Средний (до 14м)", "Крупный (до 28м)"], index=1, key="ts_scale")
            mm_per_cell = {"Мелкий (до 7м)": 200, "Средний (до 14м)": 500, "Крупный (до 28м)": 1000}[scale_label]
            draw_label = st.radio("Режим:", [":material/edit: Рисовать", ":material/swap_horiz: Двигать"], horizontal=True, key="ts_draw_mode")
            drawing_mode = "polygon" if "Рисовать" in draw_label else "transform"

        canvas_w, canvas_h = 700, 450
        grid_px = 25
        mm_per_px = mm_per_cell / grid_px

        with ctrl1:
            if "Рисовать" in draw_label:
                st.info(":material/mouse: **Кликайте** по сетке, чтобы расставить вершины. **Двойной клик** — замкнуть контур.")
            else:
                st.info(":material/mouse: **Перетаскивайте** фигуру для настройки.")
            st.caption(f":material/straighten: 1 клетка = {mm_per_cell} мм ({mm_per_cell/1000:.1f} м) | Область: {canvas_w * mm_per_px / 1000:.0f} × {canvas_h * mm_per_px / 1000:.0f} м")

        s = 1.0 / mm_per_px
        ox, oy = 2 * grid_px, 2 * grid_px

        if "ai_drawing" not in st.session_state:
            st.session_state.ai_drawing = None

        # Блок ИИ
        st.markdown("### :material/smart_toy: Автоматическое распознавание чертежа (ИИ)")
        with st.container():
            c_ai1, c_ai2 = st.columns([1, 1])
            with c_ai1:
                uploaded_img = st.file_uploader("Загрузите фото или скан чертежа с размерами (jpg, png)", type=["jpg", "jpeg", "png"])
            with c_ai2:
                api_key = st.text_input("Gemini API Key (Токен доступа)", type="password", help="Получите ключ бесплатно на aistudio.google.com")
                if st.button(":material/auto_awesome: Перевести чертеж в проект", use_container_width=True, type="primary"):
                    if not HAS_GENAI:
                        st.error("Библиотека google-generativeai не установлена.")
                    elif not api_key:
                        st.warning(":material/warning: Введите API ключ Gemini")
                    elif not uploaded_img:
                        st.warning(":material/warning: Загрузите изображение чертежа")
                    else:
                        with st.spinner("Анализирую чертеж..."):
                            try:
                                genai.configure(api_key=api_key)
                                model = genai.GenerativeModel("gemini-3-flash")
                                img = Image.open(uploaded_img)
                                prompt = '''Вы - опытный инженер-проектировщик. Пользователь загрузил чертеж террасы.
                                Определите форму террасы и найдите все длины сторон (размеры).
                                Переведите все размеры в миллиметры. Постройте 2D полигон.
                                Первый угол в [0, 0]. По часовой стрелке.
                                Верните ТОЛЬКО валидный JSON массив координат вершин.
                                Например: [[0, 0], [4000, 0], [4000, 3000], [0, 3000]]
                                Не добавляйте текст markdown! Только JSON-массив.'''
                                response = model.generate_content([prompt, img])
                                raw_resp = response.text.strip().removeprefix('```json').removesuffix('```').strip()
                                ai_pts = json.loads(raw_resp)
                                if len(ai_pts) >= 3:
                                    path_ai = [["M", ox + ai_pts[0][0] * s, oy + ai_pts[0][1] * s]]
                                    for p in ai_pts[1:]:
                                        path_ai.append(["L", ox + p[0] * s, oy + p[1] * s])
                                    path_ai.append(["z"])
                                    st.session_state.ai_drawing = {
                                        "version": "4.4.0", "objects": [{"type": "path", "version": "4.4.0",
                                        "left": 0, "top": 0, "fill": "rgba(41, 182, 246, 0.4)",
                                        "stroke": "#0288d1", "strokeWidth": 2, "path": path_ai}]}
                                    st.success(":material/check_circle: Чертеж распознан!")
                                else:
                                    st.error("Не удалось составить полигон.")
                            except Exception as e:
                                st.error(f"Ошибка ИИ: {e}")

        initial_drawing = st.session_state.ai_drawing
        if initial_drawing is None:
            if shape_key == 'l_shape':
                pts = [(ox, oy), (ox + 6000*s, oy), (ox + 6000*s, oy + 3000*s),
                       (ox + 3000*s, oy + 3000*s), (ox + 3000*s, oy + 5000*s), (ox, oy + 5000*s)]
                path = [["M", pts[0][0], pts[0][1]]]
                for p in pts[1:]: path.append(["L", p[0], p[1]])
                path.append(["z"])
                initial_drawing = {"version": "4.4.0", "objects": [{"type": "path", "version": "4.4.0",
                    "left": 0, "top": 0, "fill": "rgba(165,214,167,0.3)", "stroke": "#2e7d32",
                    "strokeWidth": 2, "path": path}]}
            elif shape_key == 'u_shape':
                A, B, E, F = 8000, 5000, 4000, 3000
                pts = [(ox, oy), (ox+A*s, oy), (ox+A*s, oy+B*s),
                       (ox+(A+E)/2*s, oy+B*s), (ox+(A+E)/2*s, oy+(B-F)*s),
                       (ox+(A-E)/2*s, oy+(B-F)*s), (ox+(A-E)/2*s, oy+B*s), (ox, oy+B*s)]
                path = [["M", pts[0][0], pts[0][1]]]
                for p in pts[1:]: path.append(["L", p[0], p[1]])
                path.append(["z"])
                initial_drawing = {"version": "4.4.0", "objects": [{"type": "path", "version": "4.4.0",
                    "left": 0, "top": 0, "fill": "rgba(165,214,167,0.3)", "stroke": "#2e7d32",
                    "strokeWidth": 2, "path": path}]}

        # Фоновая сетка (тема-зависимая)
        _bg = '#1e1e1e' if not is_light else '#f8f8f8'
        _gmin = '#2a2a2a' if not is_light else '#e8e8e8'
        _gmaj = '#3a3a3a' if not is_light else '#d0d0d0'
        _gtxt = '#666' if not is_light else '#999'
        grid_img = PILImage.new('RGB', (canvas_w, canvas_h), _bg)
        draw_grid = ImageDraw.Draw(grid_img)
        for gx in range(0, canvas_w + 1, grid_px):
            c_g = _gmaj if gx % (grid_px*4) == 0 else _gmin
            w_g = 2 if gx % (grid_px*4) == 0 else 1
            draw_grid.line([(gx, 0), (gx, canvas_h)], fill=c_g, width=w_g)
        for gy in range(0, canvas_h + 1, grid_px):
            c_g = _gmaj if gy % (grid_px*4) == 0 else _gmin
            w_g = 2 if gy % (grid_px*4) == 0 else 1
            draw_grid.line([(0, gy), (canvas_w, gy)], fill=c_g, width=w_g)
        try:
            from PIL import ImageFont
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
        except:
            try: font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 10)
            except: font_small = ImageFont.load_default()
        for gx in range(0, canvas_w+1, grid_px*4):
            mv = gx * mm_per_px / 1000
            if mv > 0: draw_grid.text((gx+2, 2), f"{mv:.1f}м", fill=_gtxt, font=font_small)
        for gy in range(0, canvas_h+1, grid_px*4):
            mv = gy * mm_per_px / 1000
            if mv > 0: draw_grid.text((2, gy+2), f"{mv:.1f}м", fill=_gtxt, font=font_small)

        canvas_result = st_canvas(
            fill_color="rgba(165, 214, 167, 0.3)", stroke_width=2, stroke_color="#2e7d32",
            background_image=grid_img, drawing_mode=drawing_mode, point_display_radius=6,
            width=canvas_w, height=canvas_h, initial_drawing=initial_drawing,
            key=f"canvas_{shape_key}_{mm_per_cell}")

        # Извлечение вершин
        vertices_mm = []
        if canvas_result.json_data is not None:
            objects = canvas_result.json_data.get("objects", [])
            for obj in objects:
                if "path" in obj:
                    left = obj.get("left", 0); top = obj.get("top", 0)
                    scaleX = obj.get("scaleX", 1); scaleY = obj.get("scaleY", 1)
                    verts = []
                    for cmd in obj["path"]:
                        if len(cmd) >= 3 and cmd[0] in ["M", "L"]:
                            raw_x = cmd[1] * scaleX + left; raw_y = cmd[2] * scaleY + top
                            gx_s = round(raw_x / grid_px) * grid_px; gy_s = round(raw_y / grid_px) * grid_px
                            mm_x = int(round(gx_s * mm_per_px)); mm_y = int(round(gy_s * mm_per_px))
                            if not verts or (mm_x, mm_y) != verts[-1]: verts.append((mm_x, mm_y))
                    if len(verts) > 1 and verts[0] == verts[-1]: verts.pop()
                    if len(verts) >= 3: vertices_mm = verts

        st.session_state.ts_vertices_mm = vertices_mm

        # --- Интерактивная таблица размеров и углов ---
        if len(vertices_mm) >= 3:
            n = len(vertices_mm)

            # Вычисление длин сторон (мм → м)
            calc_sides_m = []
            for i in range(n):
                p1, p2 = vertices_mm[i], vertices_mm[(i+1) % n]
                dx, dy = p2[0]-p1[0], p2[1]-p1[1]
                calc_sides_m.append(round(math.sqrt(dx**2 + dy**2) / 1000, 2))

            # Вычисление углов
            calc_angles = []
            for i in range(n):
                pp = vertices_mm[(i-1) % n]; pc = vertices_mm[i]; pn = vertices_mm[(i+1) % n]
                v1x, v1y = pp[0]-pc[0], pp[1]-pc[1]
                v2x, v2y = pn[0]-pc[0], pn[1]-pc[1]
                mag1 = math.sqrt(v1x**2+v1y**2); mag2 = math.sqrt(v2x**2+v2y**2)
                if mag1 > 0 and mag2 > 0:
                    cos_a = max(-1, min(1, (v1x*v2x+v1y*v2y)/(mag1*mag2)))
                    calc_angles.append(round(math.degrees(math.acos(cos_a)), 1))
                else:
                    calc_angles.append(0.0)

            # Площадь по Гауссу (из координат)
            area_mm2 = 0
            for i in range(n):
                j = (i+1) % n
                area_mm2 += vertices_mm[i][0] * vertices_mm[j][1]
                area_mm2 -= vertices_mm[j][0] * vertices_mm[i][1]
            area_m2 = abs(area_mm2) / 2_000_000

            # Инициализация редактируемых данных в session_state
            edges_key = 'ts_edges_data'
            if edges_key not in st.session_state or len(st.session_state[edges_key]) != n:
                st.session_state[edges_key] = [
                    {"Сторона": f"{i+1} → {(i+1)%n+1}", "Длина (м)": calc_sides_m[i], "Угол (°)": calc_angles[i]}
                    for i in range(n)
                ]

            st.markdown("### :material/straighten: Размеры и углы контура")

            # Метрики
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric(":material/square_foot: Площадь", f"{area_m2:.2f} м²")
            xs = [v[0] for v in vertices_mm]; ys = [v[1] for v in vertices_mm]
            mc2.metric(":material/straighten: Габариты", f"{(max(xs)-min(xs))/1000:.1f} × {(max(ys)-min(ys))/1000:.1f} м")
            mc3.metric(":material/pentagon: Вершин", str(n))

            # Редактируемая таблица
            st.markdown("##### ✏️ Корректировка размеров")
            st.caption("Измените длины сторон, если нарисованный контур неточен. Площадь пересчитается автоматически.")

            df_edges = pd.DataFrame(st.session_state[edges_key])
            edited_df = st.data_editor(
                df_edges,
                use_container_width=True,
                hide_index=True,
                num_rows="fixed",
                disabled=["Сторона", "Угол (°)"],
                column_config={
                    "Сторона": st.column_config.TextColumn("Сторона", width="small"),
                    "Длина (м)": st.column_config.NumberColumn("Длина (м)", min_value=0.1, max_value=50.0, step=0.01, format="%.2f"),
                    "Угол (°)": st.column_config.NumberColumn("Угол (°)", format="%.1f"),
                },
                key="edges_editor"
            )

            # Обновление session_state из таблицы
            edited_sides_m = edited_df["Длина (м)"].tolist()
            st.session_state[edges_key] = edited_df.to_dict('records')

            # Валидация: проверка что стороны изменены
            sides_changed = any(abs(edited_sides_m[i] - calc_sides_m[i]) > 0.005 for i in range(n))
            if sides_changed:
                # Пересчёт площади по пользовательским длинам (приблизительный — сохраняем углы)
                st.info(":material/info: Длины изменены вручную. Площадь будет пересчитана при расчёте сметы.")

            # Проверка суммы углов
            angle_sum = sum(calc_angles)
            expected_sum = (n - 2) * 180
            if abs(angle_sum - expected_sum) > 5:
                st.warning(f":material/warning: Сумма углов ({angle_sum:.0f}°) отличается от ожидаемой ({expected_sum}°). Проверьте контур.")

            # Сохранение пользовательских длин для расчёта
            st.session_state.ts_user_sides_m = edited_sides_m

        else:
            st.info("✏️ Нарисуйте контур террасы на холсте выше")

    # Бассейн
    st.markdown("---")
    if 'ts_has_pool' not in st.session_state: st.session_state.ts_has_pool = False
    st.checkbox(":material/pool: Встроенный бассейн", key='ts_has_pool')
    if st.session_state.ts_has_pool:
        if 'ts_pool_shape' not in st.session_state: st.session_state.ts_pool_shape = ":material/rectangle: Прямоугольный"
        st.radio("Форма бассейна:", [":material/rectangle: Прямоугольный", ":material/circle: Круглый", "⬭ Овальный"], horizontal=True, key='ts_pool_shape')
        cp1, cp2 = st.columns(2)
        if st.session_state.ts_pool_shape in [":material/rectangle: Прямоугольный", "⬭ Овальный"]:
            if 'ts_pool_l' not in st.session_state: st.session_state.ts_pool_l = 4.0
            if 'ts_pool_w' not in st.session_state: st.session_state.ts_pool_w = 2.5
            cp1.number_input("Длина X, м:", 0.5, 20.0, key='ts_pool_l')
            cp2.number_input("Ширина Y, м:", 0.5, 20.0, key='ts_pool_w')
        else:
            if 'ts_pool_d' not in st.session_state: st.session_state.ts_pool_d = 3.0
            st.number_input("Диаметр бассейна, м:", 0.5, 20.0, key='ts_pool_d')
        co1, co2 = st.columns(2)
        if 'ts_pool_ox' not in st.session_state: st.session_state.ts_pool_ox = 1.0
        if 'ts_pool_oy' not in st.session_state: st.session_state.ts_pool_oy = 1.0
        co1.number_input("Смещение X, м:", 0.0, 50.0, key='ts_pool_ox')
        co2.number_input("Смещение Y, м:", 0.0, 50.0, key='ts_pool_oy')

    # Навигация
    col_back, _, col_next = st.columns([1, 4, 1])
    with col_back:
        if st.button("← Назад", use_container_width=True, key="back_2"):
            st.session_state.wizard_step = 1; st.rerun()
    with col_next:
        if st.button("Далее →", type="primary", use_container_width=True, key="next_2"):
            st.session_state.wizard_step = 3; st.rerun()

# ============================================================
# STEP 3: ОСНОВАНИЕ
# ============================================================
elif current_step == 3:
    st.markdown("### :material/foundation: Шаг 3: Основание и каркас")

    c1, c2 = st.columns(2, gap="large")
    with c1:
        if 'ts_base_type' not in st.session_state: st.session_state.ts_base_type = "Грунт (Сваи)"
        st.radio("Основание:", ["Грунт (Сваи)", "Бетон"], horizontal=True, key='ts_base_type')

        st.markdown("---")
        if 'ts_adjustable' not in st.session_state: st.session_state.ts_adjustable = False
        st.checkbox("На регулируемых опорах (HILST LIFT)", key='ts_adjustable')
        if st.session_state.ts_adjustable:
            if 'ts_joist_support' not in st.session_state: st.session_state.ts_joist_support = "Лага ДПК"
            st.selectbox("Тип лаги для опор:", ["Лага ДПК", "Алюминиевая лага"], key='ts_joist_support')

        st.markdown("---")
        if 'ts_steps' not in st.session_state: st.session_state.ts_steps = 0.0
        st.number_input("Ступени (м.п.):", 0.0, 50.0, key='ts_steps')

    with c2:
        if 'ts_joist' not in st.session_state: st.session_state.ts_joist = list(PIPES_JOIST.keys())[0]
        st.selectbox("Лаги (металлокаркас):", list(PIPES_JOIST.keys()), key='ts_joist')

        if "Грунт" in st.session_state.ts_base_type:
            if 'ts_frame' not in st.session_state: st.session_state.ts_frame = list(PIPES_FRAME.keys())[0]
            st.selectbox("Каркас несущий:", list(PIPES_FRAME.keys()), key='ts_frame')

    col_back, _, col_next = st.columns([1, 4, 1])
    with col_back:
        if st.button("← Назад", use_container_width=True, key="back_3"):
            st.session_state.wizard_step = 2; st.rerun()
    with col_next:
        if st.button("Далее →", type="primary", use_container_width=True, key="next_3"):
            st.session_state.wizard_step = 4; st.rerun()

# ============================================================
# STEP 4: ДОСКА
# ============================================================
elif current_step == 4:
    st.markdown("### :material/forest: Шаг 4: Обшивка и покрытие")

    c1, c2 = st.columns(2, gap="large")
    with c1:
        if 'ts_brand' not in st.session_state: st.session_state.ts_brand = list(PARSED_BOARDS.keys())[0]
        st.selectbox("Бренд:", list(PARSED_BOARDS.keys()), key='ts_brand')
        brand_choice = st.session_state.ts_brand
        if PARSED_BOARDS[brand_choice]:
            colls = list(PARSED_BOARDS[brand_choice].keys())
            if 'ts_collection' not in st.session_state: st.session_state.ts_collection = colls[0]
            st.selectbox("Коллекция:", colls, key='ts_collection')
            
            col_upper = st.session_state.ts_collection.upper()
            if "ПРАКТИК" in col_upper or "АНТИК" in col_upper:
                if 'ts_length_mode' not in st.session_state: st.session_state.ts_length_mode = "Складские доски"
                st.radio("Режим заказа:", ["Складские доски", "Любая длина под заказ"], key='ts_length_mode')
            else:
                st.session_state.ts_length_mode = "Складские доски"
        else:
            st.warning("Нет доступных коллекций для выбранного бренда.")

        shape_key = st.session_state.get('ts_shape', 'rect')
        if shape_key in ('rect', 'circle'):
            if 'ts_direction' not in st.session_state: st.session_state.ts_direction = "Вдоль фасада (по длине X)"
            st.radio("Направление укладки:", ["Вдоль фасада (по длине X)", "Поперек фасада (по глубине Y)"], key='ts_direction')

        st.markdown("---")
        if 'ts_layout_mode' not in st.session_state: st.session_state.ts_layout_mode = ":material/palette: Симметричная (красивая)"
        st.radio("Режим раскладки доски:",
                 [":material/palette: Симметричная (красивая)", ":material/savings: Экономичная (минимум отходов)"],
                 key='ts_layout_mode',
                 help="**Симметричная** — выбирает доску, которая делится ровно по длине (3+3+3 для 9м). "
                      "**Экономичная** — минимизирует общую стоимость с учётом обрезков.")

    with c2:
        st.markdown("#### Окантовка (Picture Frame)")
        if 'ts_use_frame' not in st.session_state: st.session_state.ts_use_frame = True
        st.checkbox(":material/crop_din: Окантовка (Picture Frame)", key='ts_use_frame')
        if st.session_state.ts_use_frame:
            cf1, cf2 = st.columns(2)
            if 'ts_edge_front' not in st.session_state: st.session_state.ts_edge_front = True
            if 'ts_edge_left' not in st.session_state: st.session_state.ts_edge_left = True
            if 'ts_edge_back' not in st.session_state: st.session_state.ts_edge_back = False
            if 'ts_edge_right' not in st.session_state: st.session_state.ts_edge_right = True
            cf1.checkbox("Спереди", key='ts_edge_front')
            cf1.checkbox("Слева", key='ts_edge_left')
            cf2.checkbox("Сзади", key='ts_edge_back')
            cf2.checkbox("Справа", key='ts_edge_right')

        st.markdown("---")
        st.info("💡 Доска рядовая и торцевая считаются отдельно и выводятся двумя строками в смете.")

    col_back, _, col_next = st.columns([1, 4, 1])
    with col_back:
        if st.button("← Назад", use_container_width=True, key="back_4"):
            st.session_state.wizard_step = 3; st.rerun()
    with col_next:
        if st.button("Рассчитать →", type="primary", use_container_width=True, key="next_4"):
            st.session_state.wizard_step = 5; st.rerun()

# ============================================================
# STEP 5: РЕЗУЛЬТАТ
# ============================================================
elif current_step == 5:
    # Восстанавливаем переменные из session_state
    shape_key = st.session_state.get('ts_shape', 'rect')
    shape_map = {'rect': ':material/rectangle: Прямоугольная (Стандарт)',
                 'l_shape': ':material/architecture: Г-образная (Угловая)',
                 'u_shape': ':material/crop_din: П-образная (С вырезом)',
                 'circle': ':material/circle: Округлая (Овал / Круг)',
                 'custom': ':material/draw: Свой контур (По координатам)'}
    shape_type = shape_map.get(shape_key, shape_map['rect'])
    client_name = st.session_state.get('ts_client', '')
    manager_name = st.session_state.get('ts_manager', '')
    manager_phone = st.session_state.get('ts_manager_phone', '')
    base_type = st.session_state.get('ts_base_type', 'Грунт (Сваи)')
    use_adjustable_supports = st.session_state.get('ts_adjustable', False)
    joist_support_type = st.session_state.get('ts_joist_support', 'Лага ДПК') if use_adjustable_supports else None
    steps_m = st.session_state.get('ts_steps', 0.0)
    joist_choice = st.session_state.get('ts_joist', list(PIPES_JOIST.keys())[0])
    frame_choice = st.session_state.get('ts_frame', list(PIPES_FRAME.keys())[0]) if "Грунт" in base_type else None
    brand_choice = st.session_state.get('ts_brand', list(PARSED_BOARDS.keys())[0])
    collection_name = st.session_state.get('ts_collection', '')
    use_frame = st.session_state.get('ts_use_frame', True)
    edge_front = st.session_state.get('ts_edge_front', True) if use_frame else False
    edge_back = st.session_state.get('ts_edge_back', False) if use_frame else False
    edge_left = st.session_state.get('ts_edge_left', True) if use_frame else False
    edge_right = st.session_state.get('ts_edge_right', True) if use_frame else False
    direction_choice = st.session_state.get('ts_direction', "Вдоль фасада (по длине X)")
    layout_mode_label = st.session_state.get('ts_layout_mode', ':material/palette: Симметричная (красивая)')
    layout_mode = 'symmetric' if 'Симметричная' in layout_mode_label else 'economy'
    has_pool = st.session_state.get('ts_has_pool', False)

    # Доска
    if brand_choice not in PARSED_BOARDS or not PARSED_BOARDS[brand_choice]:
        st.error("Ошибка: бренд не найден"); st.stop()
    if collection_name not in PARSED_BOARDS[brand_choice]:
        collection_name = list(PARSED_BOARDS[brand_choice].keys())[0]
    collection_boards = PARSED_BOARDS[brand_choice][collection_name]
    eff_w = (collection_boards[0]["width_mm"] + GAP_MM) / 1000
    
    length_mode_choice = st.session_state.get('ts_length_mode', 'Складские доски')
    is_custom_length = False
    col_upper = collection_name.upper()
    if ("ПРАКТИК" in col_upper or "АНТИК" in col_upper) and length_mode_choice == "Любая длина под заказ":
        is_custom_length = True
        base_price_per_m = collection_boards[0]['board_cost'] / collection_boards[0]['length_m']
        custom_boards = []
        for x in range(5, 61):
            L = round(x / 10.0, 1)
            custom_boards.append({
                "name": f"{collection_name} {L:.1f}м (под заказ)",
                "length_m": L,
                "board_cost": L * base_price_per_m,
                "unit": collection_boards[0]['unit'],
                "width_mm": collection_boards[0]['width_mm']
            })
        collection_boards = custom_boards

    is_complex = shape_key in ('l_shape', 'u_shape', 'custom')

    # --- Блокировки ---
    if shape_key == 'circle':
        st.warning(":material/circle: Модуль расчёта округлых террас в разработке.")
        col_back5, _ = st.columns([1, 5])
        with col_back5:
            if st.button("← Назад", key="back_5c"): st.session_state.wizard_step = 4; st.rerun()
        st.stop()
    if has_pool:
        st.warning(":material/pool: Модуль вырезов под бассейн в разработке.")
        col_back5, _ = st.columns([1, 5])
        with col_back5:
            if st.button("← Назад", key="back_5p"): st.session_state.wizard_step = 4; st.rerun()
        st.stop()

    # ============================================================
    # РАСЧЁТ ДЛЯ НЕСТАНДАРТНЫХ ФОРМ
    # ============================================================
    if is_complex:
        vertices_mm = st.session_state.get('ts_vertices_mm', [])
        if len(vertices_mm) < 3:
            st.error("Контур террасы не задан. Вернитесь на Шаг 2 и нарисуйте контур.")
            col_back5, _ = st.columns([1, 5])
            with col_back5:
                if st.button("← Назад", key="back_5v"): st.session_state.wizard_step = 2; st.rerun()
            st.stop()

        verts_m = [(v[0]/1000.0, v[1]/1000.0) for v in vertices_mm]
        n_v = len(verts_m)
        xs_m = [v[0] for v in verts_m]; ys_m = [v[1] for v in verts_m]
        min_xm, max_xm = min(xs_m), max(xs_m); min_ym, max_ym = min(ys_m), max(ys_m)
        poly_w = max_xm - min_xm; poly_h = max_ym - min_ym
        length = poly_w; width = poly_h

        a_mm2 = 0
        for i in range(n_v):
            j = (i+1) % n_v
            a_mm2 += verts_m[i][0]*verts_m[j][1]; a_mm2 -= verts_m[j][0]*verts_m[i][1]
        poly_area = abs(a_mm2) / 2.0
        area = poly_area

        row_segments = []
        y_cur = min_ym
        while y_cur < max_ym - eff_w * 0.1:
            segs = polygon_row_segments(verts_m, y_cur + eff_w/2)
            for sx, ex in segs:
                sl = round(ex-sx, 3)
                if sl > 0.05: row_segments.append((y_cur, sx, ex, sl))
            y_cur = round(y_cur + eff_w, 4)
        if not row_segments:
            st.error("Не удалось разбить контур на ряды."); st.stop()

        row_lengths_arr = [rs[3] for rs in row_segments]
        if is_custom_length:
            layout_matrix, best_joints, main_board = get_custom_length_layout(row_lengths_arr, eff_w, collection_boards, mode=layout_mode)
        else:
            layout_matrix, best_joints, main_board = get_best_symmetric_layout(row_lengths_arr, eff_w, collection_boards, mode=layout_mode)
        M = main_board['length_m']

        main_pieces = [p for row in layout_matrix for p in row]
        if '_mixed_counts' in main_board and main_pieces:
            board_main_totals = {nm: {"qty": d['qty'], "sum": d['sum'], "unit": d['board']['unit'], "board": d['board']} for nm, d in main_board['_mixed_counts'].items()}
        else:
            board_main_totals = optimize_waste(main_pieces, main_board) if main_pieces else {}
        board_edge_totals = {}
        
        consolidate_history = {}
        if is_custom_length:
            board_main_totals, consolidate_history = consolidate_lengths(board_main_totals)

        extra_joists = len(best_joints) * 2
        joist_lines = math.ceil(poly_w / JOIST_STEP_M) + 1 + extra_joists
        j_m = math.ceil(joist_lines * poly_h)
        j_total = j_m * round(PIPES_JOIST[joist_choice] * METAL_MARGIN)

        pr = math.ceil(poly_w / PILE_STEP_M) + 1; pc = math.ceil(poly_h / PILE_STEP_M) + 1
        step_x_p = poly_w/(pr-1) if pr > 1 else poly_w; step_y_p = poly_h/(pc-1) if pc > 1 else poly_h
        pile_positions = []
        if "Грунт" in base_type:
            for i in range(pr):
                for j in range(pc):
                    px = min_xm + i*step_x_p; py = min_ym + j*step_y_p
                    if point_in_polygon(px, py, verts_m): pile_positions.append((px, py))
        piles = len(pile_positions)

        support_positions = []
        if use_adjustable_supports:
            ssx = 0.4; ssy = 0.4 if joist_support_type == "Лага ДПК" else 1.0
            sr = math.ceil(poly_w/ssx)+1; sc = math.ceil(poly_h/ssy)+1
            step_x_s = poly_w/(sr-1) if sr > 1 else poly_w; step_y_s = poly_h/(sc-1) if sc > 1 else poly_h
            for i in range(sr):
                for j in range(sc):
                    px = min_xm + i*step_x_s; py = min_ym + j*step_y_s
                    if point_in_polygon(px, py, verts_m): support_positions.append((px, py))
        supports_count = len(support_positions); supports_total = supports_count * 450

        f_m = math.ceil(pc * poly_w) if frame_choice and "Грунт" in base_type else 0
        f_total = f_m * round(PIPES_FRAME[frame_choice] * METAL_MARGIN) if frame_choice and "Грунт" in base_type else 0
        clips_packs = math.ceil((len(row_segments) * joist_lines) / 100); clips_total = clips_packs * 2200
        work_base = poly_area * 2400; work_steps = steps_m * 5200; work_piles = piles * 3600; work_supports = supports_count * 200

        mat_data = []
        for nm, dt in board_main_totals.items():
            mat_data.append({"Позиция": f"Доска рядовая: {nm}", "Кол-во": f"{dt['qty']} шт", "Сумма": dt['sum']})
        for nm, dt in board_edge_totals.items():
            mat_data.append({"Позиция": f"Доска торцевая: {nm}", "Кол-во": f"{dt['qty']} шт", "Сумма": dt['sum']})
        mat_data.extend([{"Позиция": f"Лага {joist_choice}", "Кол-во": f"{j_m} м.п.", "Сумма": j_total},
                         {"Позиция": "Кляймеры (уп. 100 шт)", "Кол-во": f"{clips_packs} уп.", "Сумма": clips_total}])
        if f_total > 0:
            bl = len(board_main_totals) + len(board_edge_totals)
            mat_data.insert(bl, {"Позиция": f"Каркас {frame_choice}", "Кол-во": f"{f_m} м.п.", "Сумма": f_total})
        if supports_count > 0:
            mat_data.append({"Позиция": f"Регулируемые опоры HILST LIFT (под {joist_support_type})", "Кол-во": f"{supports_count} шт.", "Сумма": supports_total})

        work_data = [{"Позиция": "Монтаж настила", "Сумма": work_base}]
        if steps_m > 0: work_data.append({"Позиция": "Монтаж ступеней", "Сумма": work_steps})
        if piles > 0: work_data.append({"Позиция": f"Монтаж свай ({piles} шт)", "Сумма": work_piles})
        if supports_count > 0: work_data.append({"Позиция": f"Монтаж регулируемых опор ({supports_count} шт)", "Сумма": work_supports})
        grand_total = sum(d['Сумма'] for d in mat_data) + sum(d['Сумма'] for d in work_data)

        def get_poly_plot(mode):
            fig, ax = plt.subplots(figsize=(10, 6))
            poly_patch = patches.Polygon(verts_m, closed=True, fill=False, edgecolor='#333', linewidth=2)
            ax.add_patch(poly_patch)
            if mode == "board":
                draw_w = eff_w * 0.85
                for idx, (y_pos, x_start, x_end, seg_len) in enumerate(row_segments):
                    if idx < len(layout_matrix):
                        x = x_start
                        for w in layout_matrix[idx]:
                            ax.add_patch(patches.Rectangle((x, y_pos), w, draw_w, color='#8d6e63', ec='black', lw=0.5)); x += w
                ax.text((min_xm+max_xm)/2, min_ym-0.5, f"Габариты: {int(poly_w*1000)} × {int(poly_h*1000)} мм | Площадь: {poly_area:.2f} м²", ha='center', fontweight='bold', fontsize=10)
            elif mode == "frame":
                abs_joints = set()
                for jx in best_joints: abs_joints.add(min_xm + jx)
                for i in range(math.ceil(poly_w/JOIST_STEP_M)+1):
                    cx = min_xm + min(i*JOIST_STEP_M, poly_w)
                    ax.plot([cx, cx], [min_ym, max_ym], color='blue', lw=1, alpha=0.3)
                for jx in abs_joints:
                    ax.plot([jx-0.02, jx-0.02], [min_ym, max_ym], color='c', lw=1.5, alpha=0.9)
                    ax.plot([jx+0.02, jx+0.02], [min_ym, max_ym], color='c', lw=1.5, alpha=0.9)
                if frame_choice and "Грунт" in base_type:
                    for j in range(pc):
                        cy = min_ym + j*step_y_p; ax.plot([min_xm, max_xm], [cy, cy], color='red', lw=3)
                ax.text((min_xm+max_xm)/2, min_ym-0.4, "Синим: Лаги | Голубым: Парные | Красным: Балки", color='blue', ha='center', fontsize=10)
            elif mode == "piles":
                if use_adjustable_supports:
                    for px, py in support_positions: ax.add_patch(patches.Circle((px, py), 0.08, color='orange', alpha=0.7))
                    if len(support_positions) >= 2: ax.text((min_xm+max_xm)/2, min_ym-0.4, f"Опор: {supports_count} шт", ha='center', fontsize=10, color='darkorange')
                else:
                    for px, py in pile_positions: ax.add_patch(patches.Circle((px, py), 0.12, color='black'))
                    if len(pile_positions) >= 2: ax.text((min_xm+max_xm)/2, min_ym-0.4, f"Свай: {piles} шт | Шаг: ~{int(step_x_p*1000)}×{int(step_y_p*1000)} мм", ha='center', fontsize=10)
            ax.set_xlim(min_xm-1.0, max_xm+1.0); ax.set_ylim(min_ym-1.2, max_ym+0.5); ax.set_aspect('equal'); plt.axis('off')
            buf = io.BytesIO(); plt.savefig(buf, format='png', bbox_inches='tight', dpi=150); plt.close(fig); buf.seek(0)
            return buf

        def create_poly_pdf():
            pdf = FPDF(); pdf.add_page(); pdf.set_font('Arial', '', 12)
            font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "DejaVuSans.ttf")
            try: pdf.add_font('DejaVu', '', font_path); pdf.set_font('DejaVu', '', 12)
            except: pass
            pdf.cell(200, 10, txt="Смета: нестандартная терраса", ln=True, align='C')
            pdf.cell(200, 10, txt=f"Клиент: {client_name} | Площадь: {poly_area:.2f} м²", ln=True, align='L')
            if manager_name or manager_phone: pdf.cell(200, 10, txt=f"Менеджер: {manager_name} {manager_phone}", ln=True, align='L')
            pdf.ln(5)
            pdf.set_fill_color(235, 235, 235)
            pdf.cell(110, 10, "Материалы", 1, 0, 'L', True); pdf.cell(30, 10, "Кол-во", 1, 0, 'C', True); pdf.cell(50, 10, "Сумма", 1, 1, 'C', True)
            for r in mat_data: pdf.cell(110, 10, str(r["Позиция"])[:45], 1); pdf.cell(30, 10, str(r["Кол-во"]), 1, 0, 'C'); pdf.cell(50, 10, f"{r['Сумма']:,.0f} р.", 1, 1, 'R')
            pdf.ln(5); pdf.cell(140, 10, "Работы", 1, 0, 'L', True); pdf.cell(50, 10, "Сумма", 1, 1, 'C', True)
            for r in work_data: pdf.cell(140, 10, str(r["Позиция"]), 1); pdf.cell(50, 10, f"{r['Сумма']:,.0f} р.", 1, 1, 'R')
            pdf.ln(5); pdf.set_font('DejaVu', '', 14); pdf.cell(190, 10, txt=f"ИТОГО: {grand_total:,.0f} руб.", ln=True, align='R')
            pdf.add_page(); pdf.set_font('DejaVu', '', 14); pdf.set_fill_color(0, 184, 148); pdf.set_text_color(255, 255, 255)
            pdf.cell(190, 12, 'Почему выбирают ООО «Дача 2000»:', ln=True, align='C', fill=True)
            pdf.set_text_color(0, 0, 0); pdf.set_font('DejaVu', '', 11); pdf.ln(8)
            for usp in ["- Террасы под ключ: полный цикл работ.", "- Гарантия 24 месяца.", "- Качественные материалы.", "- Нестандартные формы.", "- Профессиональные бригады.", "- Строгое соблюдение сроков.", "- Бесплатный выезд на замер."]:
                pdf.cell(190, 8, usp, ln=True)
            pdf.ln(10); pdf.set_font('DejaVu', '', 12); pdf.set_text_color(0, 184, 148)
            pdf.cell(190, 8, "Создаем идеальные террасы!", ln=True, align='C'); pdf.set_text_color(0, 0, 0)
            for m, t in [("board", "Настил"), ("frame", "Схема подсистемы"), ("piles", "Свайное поле")]:
                if m == "piles" and piles == 0: continue
                pdf.add_page(); pdf.cell(200, 10, t, ln=True, align='C'); pdf.image(get_poly_plot(m), x=15, y=30, w=180)
            return bytes(pdf.output())

        get_chart = get_poly_plot
        create_pdf_func = create_poly_pdf

    # ============================================================
    # РАСЧЁТ ДЛЯ ПРЯМОУГОЛЬНОЙ ТЕРРАСЫ
    # ============================================================
    else:
        length = st.session_state.get('ts_length', 9.0)
        width = st.session_state.get('ts_width', 4.0)
        area = length * width

        offset_front = eff_w if edge_front else 0
        offset_back = eff_w if edge_back else 0
        offset_left = eff_w if edge_left else 0
        offset_right = eff_w if edge_right else 0
        inner_X = round(length - offset_left - offset_right, 3)
        inner_Y = round(width - offset_front - offset_back, 3)
        if inner_X <= 0 or inner_Y <= 0:
            st.error("Размеры слишком малы для торцевой доски."); st.stop()

        row_lengths_arr = []
        if "Вдоль" in direction_choice:
            board_len_axis = inner_X; board_row_axis = inner_Y
            rows_count = math.ceil(board_row_axis / eff_w)
            for r in range(rows_count): row_lengths_arr.append(inner_X)
        else:
            board_len_axis = inner_Y; board_row_axis = inner_X
            rows_count = math.ceil(board_row_axis / eff_w)
            for r in range(rows_count): row_lengths_arr.append(inner_Y)

        if is_custom_length:
            layout_matrix, best_joints, main_board = get_custom_length_layout(row_lengths_arr, eff_w, collection_boards, mode=layout_mode)
        else:
            layout_matrix, best_joints, main_board = get_best_symmetric_layout(row_lengths_arr, eff_w, collection_boards, mode=layout_mode)
        M = main_board['length_m']

        edge_pieces = []
        if use_frame:
            if "Вдоль" in direction_choice:
                front_pieces = get_shifted_edge(layout_matrix, True, offset_left, offset_right) if edge_front else []
                back_pieces = get_shifted_edge(layout_matrix, False, offset_left, offset_right) if edge_back else []
                left_pieces = get_1d_symmetric_pieces(width, M) if edge_left else []
                right_pieces = get_1d_symmetric_pieces(width, M) if edge_right else []
            else:
                left_pieces = get_shifted_edge(layout_matrix, True, offset_front, offset_back) if edge_left else []
                right_pieces = get_shifted_edge(layout_matrix, False, offset_front, offset_back) if edge_right else []
                front_pieces = get_1d_symmetric_pieces(length, M) if edge_front else []
                back_pieces = get_1d_symmetric_pieces(length, M) if edge_back else []
            edge_pieces = front_pieces + back_pieces + left_pieces + right_pieces
        else:
            front_pieces = back_pieces = left_pieces = right_pieces = []

        main_pieces = [p for row in layout_matrix for p in row]
        if '_mixed_counts' in main_board and main_pieces:
            board_main_totals = {nm: {"qty": d['qty'], "sum": d['sum'], "unit": d['board']['unit'], "board": d['board']} for nm, d in main_board['_mixed_counts'].items()}
        else:
            board_main_totals = optimize_waste(main_pieces, main_board) if main_pieces else {}
            
        if is_custom_length and edge_pieces:
            board_edge_totals = {}
            for p in edge_pieces:
                brd = round_up_to_custom(p, collection_boards)
                nm = brd['name']
                if nm not in board_edge_totals:
                    board_edge_totals[nm] = {'qty': 0, 'sum': 0.0, 'unit': brd['unit'], 'board': brd}
                board_edge_totals[nm]['qty'] += 1
                board_edge_totals[nm]['sum'] += brd['board_cost']
        else:
            board_edge_totals = optimize_waste(edge_pieces, main_board) if edge_pieces else {}
            
        consolidate_history = {}
        if is_custom_length:
            combined_counts = {}
            for k, v in board_main_totals.items():
                if k not in combined_counts: combined_counts[k] = v.copy()
                else: 
                    combined_counts[k]['qty'] += v['qty']
                    combined_counts[k]['sum'] += v['sum']
            for k, v in board_edge_totals.items():
                if k not in combined_counts: combined_counts[k] = v.copy()
                else: 
                    combined_counts[k]['qty'] += v['qty']
                    combined_counts[k]['sum'] += v['sum']
            board_main_totals, consolidate_history = consolidate_lengths(combined_counts)
            board_edge_totals = {}

        extra_joists = len(best_joints) * 2
        joist_count_base = math.ceil(board_len_axis / JOIST_STEP_M) + 1
        joist_count_total = joist_count_base + extra_joists
        j_m = math.ceil((math.ceil(length/JOIST_STEP_M)+1+extra_joists)*width)
        j_total = j_m * round(PIPES_JOIST[joist_choice] * METAL_MARGIN)
        pr = math.ceil(length/PILE_STEP_M)+1; pc = math.ceil(width/PILE_STEP_M)+1
        piles = pr*pc if "Грунт" in base_type else 0

        supports_count = 0; supports_total = 0
        if use_adjustable_supports:
            ssx = 0.4; ssy = 0.4 if joist_support_type == "Лага ДПК" else 1.0
            sr = math.ceil(length/ssx)+1; sc_s = math.ceil(width/ssy)+1
            supports_count = sr * sc_s; supports_total = supports_count * 450

        f_m = math.ceil(pc*length) if "Вдоль" in direction_choice else math.ceil(pr*width)
        f_total = f_m * round(PIPES_FRAME[frame_choice]*METAL_MARGIN) if frame_choice and "Грунт" in base_type else 0
        clips_packs = math.ceil((math.ceil(width/eff_w)*joist_count_total)/100); clips_total = clips_packs * 2200
        work_base = area*2400; work_steps = steps_m*5200; work_piles = piles*3600; work_supports = supports_count*200

        mat_data = []
        for nm, dt in board_main_totals.items():
            mat_data.append({"Позиция": f"Доска рядовая: {nm}", "Кол-во": f"{dt['qty']} шт", "Сумма": dt['sum']})
        for nm, dt in board_edge_totals.items():
            mat_data.append({"Позиция": f"Доска торцевая: {nm}", "Кол-во": f"{dt['qty']} шт", "Сумма": dt['sum']})
        board_lines = len(board_main_totals) + len(board_edge_totals)
        mat_data.extend([{"Позиция": f"Лага {joist_choice} (вкл. парные)", "Кол-во": f"{j_m} м.п.", "Сумма": j_total},
                         {"Позиция": "Кляймеры (уп. 100 шт)", "Кол-во": f"{clips_packs} уп.", "Сумма": clips_total}])
        if frame_choice and "Грунт" in base_type: mat_data.insert(board_lines, {"Позиция": f"Каркас {frame_choice}", "Кол-во": f"{f_m} м.п.", "Сумма": f_total})
        if supports_count > 0: mat_data.append({"Позиция": f"Опоры HILST LIFT ({joist_support_type})", "Кол-во": f"{supports_count} шт.", "Сумма": supports_total})

        work_data = [{"Позиция": "Монтаж настила", "Сумма": work_base}]
        if steps_m > 0: work_data.append({"Позиция": "Монтаж ступеней", "Сумма": work_steps})
        if piles > 0: work_data.append({"Позиция": f"Монтаж свай ({piles} шт)", "Сумма": work_piles})
        if supports_count > 0: work_data.append({"Позиция": f"Монтаж опор ({supports_count} шт)", "Сумма": work_supports})
        grand_total = sum(d['Сумма'] for d in mat_data) + sum(d['Сумма'] for d in work_data)

        # Детализация по рядам
        detail_rows = []
        def format_row_data(row_name, pieces, standard_len):
            full_count = {}; cut_count = {}; total_len = 0.0
            for p in pieces:
                p_val = round(p, 3); total_len += p_val
                if abs(p_val - standard_len) <= 0.01: full_count[p_val] = full_count.get(p_val, 0) + 1
                else: cut_count[p_val] = cut_count.get(p_val, 0) + 1
            full_str = ", ".join([f"{l} м – {c} шт." for l, c in full_count.items()]) if full_count else "-"
            cut_str = ", ".join([f"{l} м – {c} шт." for l, c in cut_count.items()]) if cut_count else "-"
            return {"№ ряда / Элемент": row_name, "Целые доски": full_str, "Обрезанные доски": cut_str, "Суммарная длина": f"{round(total_len, 3)} м"}

        for i, row_pieces in enumerate(layout_matrix): detail_rows.append(format_row_data(f"Ряд {i+1}", row_pieces, M))
        if use_frame:
            if "Вдоль" in direction_choice:
                if edge_front: detail_rows.append(format_row_data("Торцевая: Спереди", front_pieces, M))
                if edge_back: detail_rows.append(format_row_data("Торцевая: Сзади", back_pieces, M))
                if edge_left: detail_rows.append(format_row_data("Торцевая: Слева", left_pieces, M))
                if edge_right: detail_rows.append(format_row_data("Торцевая: Справа", right_pieces, M))
            else:
                if edge_left: detail_rows.append(format_row_data("Торцевая: Слева", left_pieces, M))
                if edge_right: detail_rows.append(format_row_data("Торцевая: Справа", right_pieces, M))
                if edge_front: detail_rows.append(format_row_data("Торцевая: Спереди", front_pieces, M))
                if edge_back: detail_rows.append(format_row_data("Торцевая: Сзади", back_pieces, M))
        detail_df = pd.DataFrame(detail_rows)

        step_x = length/(pr-1) if pr > 1 else length; step_y = width/(pc-1) if pc > 1 else width

        def get_plot(mode):
            fig, ax = plt.subplots(figsize=(10, 6))
            if mode == "board":
                draw_w = eff_w * 0.8
                flags = {'F': edge_front, 'B': edge_back, 'L': edge_left, 'R': edge_right}
                if edge_front: draw_edge(ax, front_pieces, 'front', length, width, draw_w, flags)
                if edge_back: draw_edge(ax, back_pieces, 'back', length, width, draw_w, flags)
                if edge_left: draw_edge(ax, left_pieces, 'left', length, width, draw_w, flags)
                if edge_right: draw_edge(ax, right_pieces, 'right', length, width, draw_w, flags)
                if "Вдоль" in direction_choice:
                    for r, rp in enumerate(layout_matrix):
                        y, x = offset_front + r*eff_w, offset_left
                        for w in rp: ax.add_patch(patches.Rectangle((x, y), w, draw_w, color='#8d6e63', ec='black', lw=0.5)); x += w
                else:
                    for r, rp in enumerate(layout_matrix):
                        x, y = offset_left + r*eff_w, offset_front
                        for w in rp: ax.add_patch(patches.Rectangle((x, y), draw_w, w, color='#8d6e63', ec='black', lw=0.5)); y += w
                ax.text(length/2, -0.4, f"Длина: {int(length*1000)} мм", ha='center', fontweight='bold', fontsize=10)
                ax.text(-0.6, width/2, f"Глубина: {int(width*1000)} мм", va='center', rotation=90, fontweight='bold', fontsize=10)
            elif mode == "frame":
                abs_joints = set()
                if "Вдоль" in direction_choice:
                    for jx in best_joints: abs_joints.add(offset_left + jx)
                    for i in range(math.ceil(length/JOIST_STEP_M)+1):
                        cx = min(i*JOIST_STEP_M, length); ax.plot([cx, cx], [0, width], color='blue', lw=1, alpha=0.3)
                    for jx in abs_joints:
                        ax.plot([jx-0.02, jx-0.02], [0, width], color='c', lw=1.5, alpha=0.9); ax.plot([jx+0.02, jx+0.02], [0, width], color='c', lw=1.5, alpha=0.9)
                    if frame_choice and "Грунт" in base_type:
                        for j in range(pc): cy = j*step_y; ax.plot([0, length], [cy, cy], color='red', lw=3)
                else:
                    for jy in best_joints: abs_joints.add(offset_front + jy)
                    for i in range(math.ceil(width/JOIST_STEP_M)+1):
                        cy = min(i*JOIST_STEP_M, width); ax.plot([0, length], [cy, cy], color='blue', lw=1, alpha=0.3)
                    for jy in abs_joints:
                        ax.plot([0, length], [jy-0.02, jy-0.02], color='c', lw=1.5, alpha=0.9); ax.plot([0, length], [jy+0.02, jy+0.02], color='c', lw=1.5, alpha=0.9)
                    if frame_choice and "Грунт" in base_type:
                        for i in range(pr): cx = i*step_x; ax.plot([cx, cx], [0, width], color='red', lw=3)
                ax.text(length/2, -0.3, "Синим: Лаги | Голубым: Парные | Красным: Балки", color='blue', ha='center', fontsize=10)
            elif mode == "piles":
                if use_adjustable_supports:
                    ssx = 0.4; ssy = 0.4 if joist_support_type == "Лага ДПК" else 1.0
                    sr = math.ceil(length/ssx)+1; sc_s = math.ceil(width/ssy)+1
                    stx = length/(sr-1) if sr > 1 else length; sty = width/(sc_s-1) if sc_s > 1 else width
                    for i in range(sr):
                        for j in range(sc_s):
                            px, py = i*stx, j*sty; ax.add_patch(patches.Circle((px, py), 0.1, color='orange', alpha=0.7))
                else:
                    for i in range(pr):
                        for j in range(pc):
                            px, py = i*step_x, j*step_y; ax.add_patch(patches.Circle((px, py), 0.15, color='black'))
            ax.set_xlim(-1.0, length+1.0); ax.set_ylim(-1.2, width+0.5); ax.set_aspect('equal'); plt.axis('off')
            buf = io.BytesIO(); plt.savefig(buf, format='png', bbox_inches='tight', dpi=150); plt.close(fig); buf.seek(0)
            return buf

        def create_pdf():
            pdf = FPDF(); pdf.add_page(); pdf.set_font('Arial', '', 12)
            font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "DejaVuSans.ttf")
            try: pdf.add_font('DejaVu', '', font_path); pdf.set_font('DejaVu', '', 12)
            except: pass
            pdf.cell(200, 10, txt="Смета и чертежи на устройство террасы", ln=True, align='C')
            pdf.cell(200, 10, txt=f"Клиент: {client_name} | Габариты: {int(length*1000)}x{int(width*1000)} мм", ln=True, align='L')
            if manager_name or manager_phone: pdf.cell(200, 10, txt=f"Менеджер: {manager_name} {manager_phone}", ln=True, align='L')
            pdf.ln(5)
            pdf.set_fill_color(235, 235, 235); pdf.cell(110, 10, "Материалы", 1, 0, 'L', True); pdf.cell(30, 10, "Кол-во", 1, 0, 'C', True); pdf.cell(50, 10, "Сумма", 1, 1, 'C', True)
            for r in mat_data: pdf.cell(110, 10, str(r["Позиция"])[:45], 1); pdf.cell(30, 10, str(r["Кол-во"]), 1, 0, 'C'); pdf.cell(50, 10, f"{r['Сумма']:,.0f} р.".replace(",", " "), 1, 1, 'R')
            pdf.ln(5); pdf.cell(140, 10, "Работы", 1, 0, 'L', True); pdf.cell(50, 10, "Сумма", 1, 1, 'C', True)
            for r in work_data: pdf.cell(140, 10, str(r["Позиция"]), 1); pdf.cell(50, 10, f"{r['Сумма']:,.0f} р.".replace(",", " "), 1, 1, 'R')
            pdf.ln(5); pdf.set_font('DejaVu', '', 14); pdf.cell(190, 10, txt=f"ИТОГО: {grand_total:,.0f} руб.".replace(",", " "), ln=True, align='R')
            pdf.add_page(); pdf.set_font('DejaVu', '', 14); pdf.set_fill_color(0, 184, 148); pdf.set_text_color(255, 255, 255)
            pdf.cell(190, 12, 'Почему выбирают ООО «Дача 2000»:', ln=True, align='C', fill=True)
            pdf.set_text_color(0, 0, 0); pdf.set_font('DejaVu', '', 11); pdf.ln(8)
            for usp in ["- Террасы под ключ.", "- Гарантия 24 мес.", "- Качественные материалы.", "- Нестандартные формы.", "- Профбригады.", "- Сроки по договору.", "- Бесплатный выезд."]:
                pdf.cell(190, 8, usp, ln=True)
            pdf.ln(10); pdf.set_font('DejaVu', '', 12); pdf.set_text_color(0, 184, 148)
            pdf.cell(190, 8, "Создаем идеальные террасы!", ln=True, align='C'); pdf.set_text_color(0, 0, 0)
            for m, t in [("board", "Настил"), ("frame", "Подсистема"), ("piles", "Свайное поле")]:
                if m == "piles" and piles == 0: continue
                pdf.add_page(); pdf.cell(200, 10, t, ln=True, align='C'); pdf.image(get_plot(m), x=15, y=30, w=180)
            return bytes(pdf.output())

        get_chart = get_plot
        create_pdf_func = create_pdf

    # ============================================================
    # ВЫВОД РЕЗУЛЬТАТОВ (общий для обоих путей)
    # ============================================================
    # Крупная цена
    st.markdown(f"""<div style="text-align:center;padding:2rem;margin:1rem 0;background:{card_bg};border:2px solid #9fcb3d;border-radius:20px;box-shadow:0 8px 30px rgba(159,203,61,0.2);">
        <div style="font-size:0.9rem;color:{label_color};text-transform:uppercase;letter-spacing:2px;margin-bottom:0.5rem;">Итоговая стоимость</div>
        <div style="font-size:3.5rem;font-weight:900;background:linear-gradient(135deg,#f59e0b,#ea580c,#dc2626);-webkit-background-clip:text;-webkit-text-fill-color:transparent;line-height:1.1;">{grand_total:,.0f} ₽</div>
        <div style="font-size:0.85rem;color:{label_color};margin-top:0.5rem;">Материалы + Работы</div>
    </div>""", unsafe_allow_html=True)

    # Бейдж режима раскладки
    _mode_icon = "🎨" if layout_mode == 'symmetric' else "💰"
    _mode_name = "Симметричная раскладка" if layout_mode == 'symmetric' else "Экономичная раскладка"
    _mode_color = "#4caf50" if layout_mode == 'symmetric' else "#ff9800"
    st.markdown(f"""<div style="text-align:center;margin-bottom:1rem;">
        <span style="background:{_mode_color}22;color:{_mode_color};padding:6px 16px;border-radius:20px;font-size:0.85rem;font-weight:600;border:1px solid {_mode_color}44;">
            {_mode_icon} {_mode_name} · Доска: {M} м
        </span>
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    total_mat = sum(d['Сумма'] for d in mat_data); total_work = sum(d['Сумма'] for d in work_data)
    with m1: st.markdown(f'<div class="metric-card"><div class="label">Работы</div><div class="value blue">{total_work:,.0f} ₽</div></div>', unsafe_allow_html=True)
    with m2: st.markdown(f'<div class="metric-card"><div class="label">Материалы</div><div class="value orange">{total_mat:,.0f} ₽</div></div>', unsafe_allow_html=True)
    with m3: st.markdown(f'<div class="metric-card"><div class="label">Площадь</div><div class="value">{area:.1f} м²</div></div>', unsafe_allow_html=True)
    with m4: st.markdown(f'<div class="metric-card"><div class="label">Итого</div><div class="value total">{grand_total:,.0f} ₽</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if not is_complex:
        with st.expander(":material/bar_chart: Детализация по рядам", expanded=False):
            st.dataframe(detail_df, use_container_width=True, hide_index=True)
        st.markdown("<br>", unsafe_allow_html=True)

    colA, colB = st.columns(2)
    with colA:
        st.markdown("#### :material/inventory: Смета материалов")
        st.dataframe(mat_data, hide_index=True, use_container_width=True, 
                     column_config={"Сумма": st.column_config.NumberColumn(format="%.0f ₽")})
        if consolidate_history:
            with st.expander(":material/info: Служебная информация по раскрою"):
                st.markdown("**Укрупнение мелких партий (менее 10 шт):**")
                for new_name, old_names in consolidate_history.items():
                    if "дозаказ" in old_names[0]:
                        st.write(f"- **{old_names[0]}**")
                    else:
                        old_str = ', '.join([n.replace(collection_name, '').strip() for n in old_names if n != new_name])
                        if old_str:
                            st.write(f"- **{new_name}** (включает бывшие: {old_str})")
                        else:
                            st.write(f"- **{new_name}** (было объединение)")
    with colB:
        st.markdown("#### :material/construction: Смета работ")
        st.dataframe(work_data, hide_index=True, use_container_width=True,
                     column_config={"Сумма": st.column_config.NumberColumn(format="%.0f ₽")})

    col_dl1, col_dl2, col_dl3 = st.columns([1, 2, 1])
    with col_dl2:
        st.download_button(":material/download: СКАЧАТЬ ПРОЕКТ (PDF)", data=create_pdf_func(),
                           file_name=f"Terrasa_{client_name}.pdf", mime="application/pdf", use_container_width=True, type="primary")

    st.divider()
    st.subheader(":material/architecture: Технические схемы")
    t1, t2, t3 = st.tabs(["Вид настила", "Металлокаркас", "Свайное поле"])
    with t1: st.image(get_chart("board"), caption="Раскладка доски.")
    with t2: st.image(get_chart("frame"), caption="Парные лаги под стыки.")
    with t3:
        if piles > 0: st.image(get_chart("piles"))
        else: st.info("Основание — бетон, сваи не требуются.")

    # CRM
    st.markdown("---")
    st.markdown("### :material/work: Интеграции и Сохранение")
    export_params = {"client_name": client_name, "manager_name": manager_name, "manager_phone": manager_phone,
                     "shape_type": shape_type, "length": length, "width": width, "has_pool": has_pool,
                     "brand_choice": brand_choice, "collection_name": collection_name,
                     "direction_choice": direction_choice, "use_frame": use_frame,
                     "base_type": base_type, "steps_m": steps_m, "grand_total": grand_total}
    col_export, col_crm = st.columns(2)
    with col_export:
        st.info("Экспорт данных проекта.")
        st.download_button(":material/save: Сохранить проект (JSON)", data=json.dumps(export_params, ensure_ascii=False, indent=2),
                           file_name=f"project_terrace_{datetime.date.today()}.json", mime="application/json", use_container_width=True)
    with col_crm:
        st.info("Отправка заявки в CRM.")
        crm_webhook = st.text_input("Webhook URL CRM:", placeholder="https://your-crm.bitrix24.ru/rest/...", label_visibility="collapsed")
        if st.button(":material/rocket_launch: Отправить лид в CRM", use_container_width=True):
            if crm_webhook:
                try:
                    import requests
                    resp = requests.post(crm_webhook, json={"project_type": "terrace", "data": export_params, "total": grand_total})
                    if resp.status_code in [200, 201]: st.success(":material/check_circle: Заявка отправлена!")
                    else: st.error(f":material/cancel: Ошибка: статус {resp.status_code}")
                except Exception as e: st.error(f":material/cancel: Ошибка: {e}")
            else: st.warning(":material/warning: Введите URL Webhook")

    # Навигация назад
    st.markdown("---")
    col_back, _ = st.columns([1, 5])
    with col_back:
        if st.button("← Изменить параметры", use_container_width=True, key="back_5"):
            st.session_state.wizard_step = 4; st.rerun()
