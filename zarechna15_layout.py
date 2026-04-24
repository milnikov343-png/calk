"""
Проект: Заречная 15, с. Луговое
Раскладка доски для террасы и крыльца.
Доска: 5800 мм × 145 мм, укладка поперёк дома, с торцевой доской.

Отдельная задача — НЕ привязана к калькулятору.
Запуск: streamlit run zarechna15_layout.py
"""
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import math

# ============================================================
# ПАРАМЕТРЫ ДОСКИ
# ============================================================
BOARD_LENGTH_MM = 5800       # длина доски (мм)
BOARD_WIDTH_MM  = 145        # ширина доски (мм)
GAP_MM          = 5          # зазор между досками (мм)
TRIM_WIDTH_MM   = 145        # ширина торцевой доски (мм)

BOARD_LENGTH_CM = BOARD_LENGTH_MM / 10
BOARD_WIDTH_CM  = BOARD_WIDTH_MM / 10
GAP_CM          = GAP_MM / 10
TRIM_WIDTH_CM   = TRIM_WIDTH_MM / 10
STEP_CM         = BOARD_WIDTH_CM + GAP_CM  # шаг раскладки

# ============================================================
# РАЗМЕРЫ ИЗ ЧЕРТЕЖА (см) — редактируемые
# ============================================================
# Терраса — основная площадка
TERRACE_WIDTH_CM  = 625.0    # вдоль дома
TERRACE_DEPTH_CM  = 305.0    # от дома

# Крыльцо — отдельная площадка
PORCH_WIDTH_CM    = 275.0    # вдоль дома
PORCH_DEPTH_CM    = 350.0    # от дома

# Ступени террасы (1 ступень, ширина 31 см)
TERRACE_STEPS     = 1
STEP_DEPTH_CM     = 31.0

# Ступени крыльца (2 ступени, ширина 31 см)
PORCH_STEPS       = 2

# Нижние ступени (6 ступеней, ширина 31 см)
BOTTOM_STEPS      = 6
BOTTOM_STEP_W_CM  = 400.0    # ширина нижних ступеней вдоль фасада


# ============================================================
# STREAMLIT UI
# ============================================================
st.set_page_config(page_title="Раскладка доски — Заречная 15", page_icon="📐", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
.stApp { background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 40%, #16213e 100%); }
html, body, [class*="css"], p, span, div, h1, h2, h3, h4, h5, h6, label, li {
    font-family: 'Inter', sans-serif; color: #f8f9fa !important;
}
[data-testid="collapsedControl"] { display: none; }
section[data-testid="stSidebar"] { display: none; }
.metric-card {
    background: linear-gradient(135deg, rgba(30,50,80,0.8), rgba(20,35,60,0.9));
    border: 1px solid rgba(0,184,148,0.3); border-radius: 16px;
    padding: 1.2rem 1.5rem; text-align: center;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}
.metric-card .label { color: #8899aa; font-size: 0.85rem; font-weight: 500;
    text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.4rem; }
.metric-card .value { font-size: 1.8rem; font-weight: 800;
    background: linear-gradient(135deg, #00b894, #00cec9);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.metric-card .value.orange {
    background: linear-gradient(135deg, #fdcb6e, #e17055);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
</style>
""", unsafe_allow_html=True)

st.markdown("## 📐 Раскладка доски — Проект «Заречная 15, с. Луговое»")
st.markdown("---")

# ---------- Ввод размеров ----------
with st.expander("🔧 РАЗМЕРЫ (из чертежа, можно скорректировать)", expanded=True):
    r1, r2, r3 = st.columns(3, gap="medium")
    with r1:
        st.markdown("#### Терраса")
        t_w = st.number_input("Ширина террасы вдоль дома (см):", 100.0, 2000.0, TERRACE_WIDTH_CM, step=5.0)
        t_d = st.number_input("Глубина террасы от дома (см):", 50.0, 1000.0, TERRACE_DEPTH_CM, step=5.0)
        t_steps = st.number_input("Кол-во ступеней террасы:", 0, 10, TERRACE_STEPS)
    with r2:
        st.markdown("#### Крыльцо")
        p_w = st.number_input("Ширина крыльца вдоль дома (см):", 100.0, 1000.0, PORCH_WIDTH_CM, step=5.0)
        p_d = st.number_input("Глубина крыльца от дома (см):", 50.0, 1000.0, PORCH_DEPTH_CM, step=5.0)
        p_steps = st.number_input("Кол-во ступеней крыльца:", 0, 10, PORCH_STEPS)
    with r3:
        st.markdown("#### Ступени и доска")
        step_depth = st.number_input("Глубина ступени (см):", 20.0, 50.0, STEP_DEPTH_CM, step=1.0)
        b_steps = st.number_input("Кол-во нижних ступеней:", 0, 10, BOTTOM_STEPS)
        b_step_w = st.number_input("Ширина нижних ступеней (см):", 100.0, 1000.0, BOTTOM_STEP_W_CM, step=5.0)
        board_len = st.number_input("Длина доски (мм):", 1000, 8000, BOARD_LENGTH_MM, step=100)
        board_w = st.number_input("Ширина доски (мм):", 50, 300, BOARD_WIDTH_MM, step=5)

# Пересчёт параметров
bl_cm = board_len / 10
bw_cm = board_w / 10
step_cm = bw_cm + GAP_CM

# ============================================================
# РАСЧЁТ КОЛИЧЕСТВА ДОСОК
# ============================================================

def calc_zone(width_cm, depth_cm, label):
    """Рассчитать кол-во досок для прямоугольной зоны."""
    # Доски поперёк дома → длина реза = depth_cm
    # Кол-во рядов вдоль дома: width_cm / step_cm
    # Торцевые доски: 2 боковые (depth_cm) + 1 передняя (width_cm)
    rows = math.ceil(width_cm / step_cm)
    cut_len = depth_cm  # длина каждой доски в ряду (см)
    # Сколько целых досок из одной заготовки
    pieces_per_board = int(bl_cm // cut_len)
    pieces_per_board = max(pieces_per_board, 1)
    boards_needed = math.ceil(rows / pieces_per_board)
    remainder_cm = bl_cm - cut_len  # остаток с каждой доски

    return {
        "label": label,
        "width": width_cm,
        "depth": depth_cm,
        "rows": rows,
        "cut_len": cut_len,
        "pieces_per_board": pieces_per_board,
        "boards_needed": boards_needed,
        "remainder_cm": remainder_cm,
        "area_m2": round(width_cm * depth_cm / 10000, 2),
    }


def calc_steps_zone(width_cm, num_steps, step_d, label):
    """Рассчитать доски для ступеней."""
    if num_steps == 0:
        return {"label": label, "boards_needed": 0, "rows": 0, "details": []}
    rows_per_step = math.ceil(step_d / step_cm)
    total_rows = rows_per_step * num_steps
    cut_len = width_cm
    pieces_per_board = int(bl_cm // cut_len) if cut_len <= bl_cm else 1
    pieces_per_board = max(pieces_per_board, 1)
    boards_needed = math.ceil(total_rows / pieces_per_board)
    return {
        "label": label,
        "boards_needed": boards_needed,
        "rows": total_rows,
        "rows_per_step": rows_per_step,
        "num_steps": num_steps,
        "cut_len": cut_len,
        "pieces_per_board": pieces_per_board,
        "width": width_cm,
    }


def calc_trim(zones_widths, zones_depths):
    """Торцевые доски — периметр каждой зоны (передняя + 2 боковые)."""
    total_trim_cm = 0
    for w in zones_widths:
        total_trim_cm += w  # передняя кромка
    for d in zones_depths:
        total_trim_cm += d * 2  # две боковые кромки
    trim_boards = math.ceil(total_trim_cm / bl_cm)
    return trim_boards, total_trim_cm


# --- Расчёт ---
terrace = calc_zone(t_w, t_d, "Терраса")
porch = calc_zone(p_w, p_d, "Крыльцо")

terrace_steps = calc_steps_zone(t_w, t_steps, step_depth, "Ступени террасы")
porch_steps = calc_steps_zone(p_w, p_steps, step_depth, "Ступени крыльца")
bottom_steps = calc_steps_zone(b_step_w, b_steps, step_depth, "Нижние ступени")

trim_boards, trim_total_cm = calc_trim(
    [t_w, p_w],
    [t_d, p_d],
)

total_boards = (
    terrace["boards_needed"]
    + porch["boards_needed"]
    + terrace_steps["boards_needed"]
    + porch_steps["boards_needed"]
    + bottom_steps["boards_needed"]
    + trim_boards
)

# ============================================================
# ВЫВОД РЕЗУЛЬТАТОВ
# ============================================================
st.markdown("---")

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f"""<div class="metric-card">
        <div class="label">Терраса (доски)</div>
        <div class="value">{terrace['boards_needed']} шт</div>
    </div>""", unsafe_allow_html=True)
with m2:
    st.markdown(f"""<div class="metric-card">
        <div class="label">Крыльцо (доски)</div>
        <div class="value">{porch['boards_needed']} шт</div>
    </div>""", unsafe_allow_html=True)
with m3:
    st.markdown(f"""<div class="metric-card">
        <div class="label">Ступени + торцевая</div>
        <div class="value">{terrace_steps['boards_needed'] + porch_steps['boards_needed'] + bottom_steps['boards_needed'] + trim_boards} шт</div>
    </div>""", unsafe_allow_html=True)
with m4:
    st.markdown(f"""<div class="metric-card">
        <div class="label orange">ИТОГО ДОСОК</div>
        <div class="value orange">{total_boards} шт</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ---------- Детальная таблица ----------
st.markdown("### 📋 Детальный расчёт")

details = []
for z in [terrace, porch]:
    details.append({
        "Зона": z["label"],
        "Размер (см)": f'{z["width"]:.0f} × {z["depth"]:.0f}',
        "Площадь (м²)": str(z["area_m2"]),
        "Рядов": str(z["rows"]),
        "Длина реза (см)": f'{z["cut_len"]:.0f}',
        "Кусков из доски": str(z["pieces_per_board"]),
        "Досок": str(z["boards_needed"]),
        "Остаток (см)": f'{z["remainder_cm"]:.0f}',
    })

for sz in [terrace_steps, porch_steps, bottom_steps]:
    if sz["boards_needed"] > 0:
        details.append({
            "Зона": sz["label"],
            "Размер (см)": f'{sz.get("width", 0):.0f} × {step_depth:.0f} × {sz.get("num_steps", 0)} ступ.',
            "Площадь (м²)": str(round(sz.get("width", 0) * step_depth * sz.get("num_steps", 0) / 10000, 2)),
            "Рядов": str(sz["rows"]),
            "Длина реза (см)": f'{sz.get("cut_len", 0):.0f}',
            "Кусков из доски": str(sz.get("pieces_per_board", 1)),
            "Досок": str(sz["boards_needed"]),
            "Остаток (см)": "—",
        })

details.append({
    "Зона": "Торцевая доска",
    "Размер (см)": f'{trim_total_cm:.0f} п.см',
    "Площадь (м²)": "—",
    "Рядов": "—",
    "Длина реза (см)": "периметр",
    "Кусков из доски": "—",
    "Досок": str(trim_boards),
    "Остаток (см)": "—",
})

st.dataframe(details, width="stretch", hide_index=True)

st.markdown(f"**ИТОГО досок {board_len}×{board_w} мм: {total_boards} шт.**")

# ============================================================
# ЧЕРТЁЖ
# ============================================================
st.markdown("---")
st.markdown("### 🏗️ Технический чертёж и раскладка доски")

fig, axes = plt.subplots(1, 2, figsize=(18, 10), facecolor="#1a1a2e")

# --- Левый график: план ---
ax1 = axes[0]
ax1.set_facecolor("#0f0f1a")
ax1.set_title("План террасы и крыльца", color="white", fontsize=14, fontweight="bold", pad=12)

# Масштаб — всё в сантиметрах
total_w = max(t_w, p_w, b_step_w) + 100
total_h = max(t_d, p_d) + t_steps * step_depth + p_steps * step_depth + b_steps * step_depth + 200

# Стена дома (верх)
house_w = t_w + p_w + 80  # чуть шире
ax1.add_patch(patches.Rectangle((-40, t_d + 20), house_w, 40, linewidth=2,
              edgecolor="#888", facecolor="#334455", zorder=5))
ax1.text(house_w / 2 - 40, t_d + 40, "СТЕНА ДОМА", ha="center", va="center",
         fontsize=10, color="white", fontweight="bold", zorder=6)

# Терраса
ax1.add_patch(patches.Rectangle((0, 0), t_w, t_d, linewidth=2,
              edgecolor="#00b894", facecolor="#1e3c50", alpha=0.7, zorder=3))
ax1.text(t_w / 2, t_d / 2, f"ТЕРРАСА\n{t_w:.0f}×{t_d:.0f} см", ha="center", va="center",
         fontsize=11, color="#00b894", fontweight="bold", zorder=4)

# Крыльцо (правее террасы)
porch_x = t_w + 40
ax1.add_patch(patches.Rectangle((porch_x, 0), p_w, p_d, linewidth=2,
              edgecolor="#fdcb6e", facecolor="#3d2c1e", alpha=0.7, zorder=3))
ax1.text(porch_x + p_w / 2, p_d / 2, f"КРЫЛЬЦО\n{p_w:.0f}×{p_d:.0f} см", ha="center", va="center",
         fontsize=11, color="#fdcb6e", fontweight="bold", zorder=4)

# Ступени террасы
for s in range(t_steps):
    y = -(s + 1) * step_depth
    ax1.add_patch(patches.Rectangle((0, y), t_w, step_depth, linewidth=1,
                  edgecolor="#00b894", facecolor="#123025", alpha=0.5, zorder=2))
    ax1.text(t_w / 2, y + step_depth / 2, f"Ступень {s+1}", ha="center", va="center",
             fontsize=8, color="#00b894", zorder=3)

# Ступени крыльца
for s in range(p_steps):
    y = -(s + 1) * step_depth
    ax1.add_patch(patches.Rectangle((porch_x, y), p_w, step_depth, linewidth=1,
                  edgecolor="#fdcb6e", facecolor="#2d2510", alpha=0.5, zorder=2))
    ax1.text(porch_x + p_w / 2, y + step_depth / 2, f"Ступень {s+1}", ha="center", va="center",
             fontsize=8, color="#fdcb6e", zorder=3)

# Нижние ступени (снизу по центру)
if b_steps > 0:
    bx = t_w / 2 - b_step_w / 2
    for s in range(b_steps):
        y = -(max(t_steps, p_steps) + s + 1) * step_depth - 20
        ax1.add_patch(patches.Rectangle((bx, y), b_step_w, step_depth, linewidth=1,
                      edgecolor="#74b9ff", facecolor="#102035", alpha=0.5, zorder=2))
        if s == 0 or s == b_steps - 1:
            ax1.text(bx + b_step_w / 2, y + step_depth / 2, f"Ступень {s+1}", ha="center", va="center",
                     fontsize=7, color="#74b9ff", zorder=3)

# Размерные линии
def dim_h(ax, x1, x2, y, text, color="#aaa"):
    ax.annotate("", xy=(x2, y), xytext=(x1, y),
                arrowprops=dict(arrowstyle="<->", color=color, lw=1.2))
    ax.text((x1 + x2) / 2, y + 8, text, ha="center", va="bottom", fontsize=9, color=color)

def dim_v(ax, y1, y2, x, text, color="#aaa"):
    ax.annotate("", xy=(x, y2), xytext=(x, y1),
                arrowprops=dict(arrowstyle="<->", color=color, lw=1.2))
    ax.text(x - 15, (y1 + y2) / 2, text, ha="right", va="center", fontsize=9, color=color, rotation=90)

dim_h(ax1, 0, t_w, t_d + 70, f"{t_w:.0f} см", "#00b894")
dim_h(ax1, porch_x, porch_x + p_w, p_d + 70, f"{p_w:.0f} см", "#fdcb6e")
dim_v(ax1, 0, t_d, -30, f"{t_d:.0f} см", "#00b894")
dim_v(ax1, 0, p_d, porch_x + p_w + 30, f"{p_d:.0f} см", "#fdcb6e")

ax1.set_xlim(-80, porch_x + p_w + 80)
bottom_y = -(max(t_steps, p_steps) + b_steps) * step_depth - 60
ax1.set_ylim(bottom_y, t_d + 120)
ax1.set_aspect("equal")
ax1.grid(True, alpha=0.1, color="white")
ax1.tick_params(colors="#555")
for spine in ax1.spines.values():
    spine.set_color("#333")

# --- Правый график: раскладка доски (терраса) ---
ax2 = axes[1]
ax2.set_facecolor("#0f0f1a")
ax2.set_title(f"Раскладка доски на террасе ({t_w:.0f}×{t_d:.0f} см)", color="white",
              fontsize=14, fontweight="bold", pad=12)

# Рисуем доски поперёк дома
colors_board = ["#1a5c45", "#1e6b50"]
for i in range(terrace["rows"]):
    x = i * step_cm
    c = colors_board[i % 2]
    ax2.add_patch(patches.Rectangle((x, 0), bw_cm, t_d, linewidth=0.5,
                  edgecolor="#00b894", facecolor=c, alpha=0.8))

# Торцевая доска — передняя
ax2.add_patch(patches.Rectangle((0, -bw_cm - GAP_CM), t_w, bw_cm, linewidth=1.5,
              edgecolor="#e17055", facecolor="#5a2d1e", alpha=0.8))
ax2.text(t_w / 2, -bw_cm / 2 - GAP_CM, "Торцевая доска", ha="center", va="center",
         fontsize=8, color="#e17055", fontweight="bold")

# Торцевые боковые
for side_x in [-(bw_cm + GAP_CM), t_w + GAP_CM]:
    ax2.add_patch(patches.Rectangle((side_x, 0), bw_cm, t_d, linewidth=1.5,
                  edgecolor="#e17055", facecolor="#5a2d1e", alpha=0.8))

# Стена дома (верх)
ax2.add_patch(patches.Rectangle((-20, t_d + GAP_CM), t_w + 40, 25, linewidth=2,
              edgecolor="#888", facecolor="#334455"))
ax2.text(t_w / 2, t_d + GAP_CM + 12.5, "СТЕНА ДОМА", ha="center", va="center",
         fontsize=9, color="white", fontweight="bold")

# Стрелка направления укладки
ax2.annotate("", xy=(t_w / 2, t_d - 20), xytext=(t_w / 2, 20),
             arrowprops=dict(arrowstyle="->", color="yellow", lw=2))
ax2.text(t_w / 2 + 15, t_d / 2, "Направление\nукладки", ha="left", va="center",
         fontsize=9, color="yellow", fontstyle="italic")

dim_h(ax2, 0, t_w, -bw_cm - 25, f"{t_w:.0f} см", "#aaa")
dim_v(ax2, 0, t_d, -bw_cm - 25, f"{t_d:.0f} см", "#aaa")

ax2.set_xlim(-50, t_w + 50)
ax2.set_ylim(-bw_cm - 50, t_d + 50)
ax2.set_aspect("equal")
ax2.grid(True, alpha=0.1, color="white")
ax2.tick_params(colors="#555")
for spine in ax2.spines.values():
    spine.set_color("#333")

plt.tight_layout()
st.pyplot(fig)

# ============================================================
# СВОДКА ПО НАРЕЗКЕ
# ============================================================
st.markdown("---")
st.markdown("### ✂️ Карта нарезки досок")

st.markdown(f"""
| Зона | Длина реза | Кусков из 1 доски ({bl_cm:.0f} см) | Остаток | Досок |
|------|-----------|-----------------------------------|---------|-------|
| **Терраса** | {t_d:.0f} см | {terrace['pieces_per_board']} | {terrace['remainder_cm']:.0f} см | **{terrace['boards_needed']}** |
| **Крыльцо** | {p_d:.0f} см | {porch['pieces_per_board']} | {porch['remainder_cm']:.0f} см | **{porch['boards_needed']}** |
| **Ступени террасы** ({t_steps} шт) | {t_w:.0f} см | {terrace_steps.get('pieces_per_board', '—')} | — | **{terrace_steps['boards_needed']}** |
| **Ступени крыльца** ({p_steps} шт) | {p_w:.0f} см | {porch_steps.get('pieces_per_board', '—')} | — | **{porch_steps['boards_needed']}** |
| **Нижние ступени** ({b_steps} шт) | {b_step_w:.0f} см | {bottom_steps.get('pieces_per_board', '—')} | — | **{bottom_steps['boards_needed']}** |
| **Торцевая доска** | периметр {trim_total_cm:.0f} см | — | — | **{trim_boards}** |
| | | | **ИТОГО** | **{total_boards}** |
""")

st.success(f"🎯 Для проекта «Заречная 15» необходимо **{total_boards} досок** размером {board_len}×{board_w} мм.")
