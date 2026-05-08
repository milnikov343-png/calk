with open('pages/terrace_calculator.py', 'r') as f:
    lines = f.readlines()

terrace_py_lines = []
terrace_py_lines.extend(lines[8:16]) # Imports
terrace_py_lines.append("\n")
terrace_py_lines.extend(lines[43:255]) # Math functions

with open('calculators/terrace.py', 'w') as f:
    f.writelines(terrace_py_lines)

terrace_calc_lines = []
terrace_calc_lines.extend(lines[0:43])
terrace_calc_lines.append("from calculators.terrace import get_row_patterns, get_1d_symmetric_pieces, get_best_symmetric_layout, optimize_waste, get_shifted_edge, draw_edge, point_in_polygon, polygon_row_segments\n")
terrace_calc_lines.extend(lines[255:])

with open('pages/terrace_calculator.py', 'w') as f:
    f.writelines(terrace_calc_lines)

print("Split terrace helpers.")
