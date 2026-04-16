import json
import math

from app import get_best_symmetric_layout, PARSED_BOARDS

collection_boards = PARSED_BOARDS["LikeWood"]["LikeWood Вельвет 140x22 (Венге/Антрацит/Махагон)"]
for b in collection_boards:
    print("Board available:", b)

direction_choice = "Вдоль"
length = 9.0
width = 4.0
eff_w = (140 + 5) / 1000
offset_front = eff_w
offset_back = 0
offset_left = eff_w
offset_right = eff_w

inner_X = round(length - offset_left - offset_right, 3)
inner_Y = round(width - offset_front - offset_back, 3)

row_lengths_arr = []
rows_count = math.ceil(inner_Y / eff_w)
for r in range(rows_count):
    row_lengths_arr.append(inner_X)

layout_matrix, best_joints, main_board = get_best_symmetric_layout(row_lengths_arr, eff_w, collection_boards)

print("Main board selected:", main_board['length_m'])
print("Layout rows (first 4):")
for r in layout_matrix[:4]:
    print(r)

