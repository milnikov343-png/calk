import streamlit as st
import math
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import io
from fpdf import FPDF
import datetime

# --- 1. БАЗА ДАННЫХ И НАСТРОЙКИ ---
BOARDS = {
    "LikeWood Вельвет 140мм": {"price": 438, "unit": "м.п.", "width_mm": 140, "length_m": 4.0},
    "LikeWood 3D тиснение 140мм": {"price": 530, "unit": "м.п.", "width_mm": 140, "length_m": 4.0},
    "Woodvex Select 146мм 3м": {"price": 2054, "unit": "шт", "width_mm": 146, "length_m": 3.0},
    "Террапол СМАРТ 130мм 3м": {"price": 2019, "unit": "шт", "width_mm": 130, "length_m": 3.0},
}

PIPES_JOIST = {"Труба 60х40х2": 219, "Труба 60х40х3": 290}
PIPES_FRAME = {"Труба 80х80х2": 403, "Труба 80х80х3": 475}

METAL_MARGIN = 1.15
GAP_MM = 5
JOIST_STEP_M = 0.4
PILE_STEP_M = 2.0
PILE_PRICE = 3600

# --- 2. ИНТЕРФЕЙС ---
st.set_page_config(page_title="Дача 2000 | Единый стандарт ММ", layout="wide")
st.title("🏗️ Расчет террасы (Размеры в ММ)")

st.sidebar.header("Параметры")
client_name = st.sidebar.text_input("ФИО Клиента:", "Иван Иванович")
length = st.sidebar.number_input("Длина (м):", 1.0, 20.0, 6.0)
width = st.sidebar.number_input("Ширина (м):", 1.0, 20.0, 4.0)
base_type = st.sidebar.radio("Основание:", ["Грунт (Сваи)", "Бетон"])

board_choice = st.sidebar.selectbox("Доска:", list(BOARDS.keys()))
joist_choice = st.sidebar.selectbox("Лаги (60х40):", list(PIPES_JOIST.keys()))
frame_choice = st.sidebar.selectbox("Каркас (80х80):", list(PIPES_FRAME.keys())) if "Грунт" in base_type else None
steps_m = st.sidebar.number_input("Ступени (пог.м):", 0.0, 20.0, 3.0)

# --- 3. РАСЧЕТЫ ---
area = length * width
b_info = BOARDS[board_choice]
eff_w = (b_info["width_mm"] + GAP_MM) / 1000
rows = math.ceil(width / eff_w)
total_bm = rows * length
b_qty = math.ceil(total_bm) if b_info["unit"] == "м.п." else math.ceil(total_bm / b_info["length_m"])
b_total = b_qty * b_info["price"]

j_rows = math.ceil(length / JOIST_STEP_M) + 1
j_m = math.ceil(j_rows * width)
j_price = round(PIPES_JOIST[joist_choice] * METAL_MARGIN)
j_total = j_m * j_price

piles = 0
f_m = 0
f_total = 0
if "Грунт" in base_type:
    pr, pc = math.ceil(length/PILE_STEP_M)+1, math.ceil(width/PILE_STEP_M)+1
    piles = pr * pc
    f_m = math.ceil(pc * length)
    f_total = f_m * round(PIPES_FRAME[frame_choice] * METAL_MARGIN)

clips_packs = math.ceil((j_rows * rows) / 100)
clips_total = clips_packs * 2000

# Формируем таблицы для вывода на экран и в PDF
mat_table = [
    {"Наименование": board_choice, "Кол-во": f"{b_qty} {b_info['unit']}", "Сумма": b_total},
    {"Наименование": f"Лага {joist_choice}", "Кол-во": f"{j_m} м.п.", "Сумма": j_total},
    {"Наименование":
