from pages.fence_calculator import calculate_fence, load_prices
import os
import sys
# fake streamlit execution context might be needed if load_prices depends on it, but load_prices is probably just json load
prices, proflist, shtaket = load_prices()
params = {
    "calc_mode": "express",
    "fence_length": 30,
    "fence_height": 2.0,
    "material_type": "Профнастил",
    "material_name": "С8 Односторонний окрас 0.45",
    "gap": 0.04,
    "fastener": "Саморез кровельный в цвет",
    "color_ral": "RAL 8017",
    "has_kalitka": True,
    "kalitka_count": 1,
    "has_otkatnye": True,
    "otkatnye_count": 1,
    "has_raspashnye": False,
    "raspashnye_count": 0,
    "has_avtomatika": True,
    "stolb_type": "60х60х2мм",
    "lag_rows": 2,
    "distance_km": 50,
    "post_pitch": 3.0,
    "hole_depth": 1.5,
    "ground_distance": 0.05,
    "has_fundament": False,
    "fund_length": 0,
    "fund_width": 0,
    "fund_height": 0,
    "address": "Test",
    "contact": "Test",
    "manager_name": "test",
    "manager_phone": "123"
}
result = calculate_fence(params, prices, proflist, shtaket)
print(result["total_works"], result["total_materials"], result["grand_total"])
