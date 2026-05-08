import sys

with open('pages/fence_calculator.py', 'r') as f:
    lines = f.readlines()

fence_py_lines = []
fence_calc_lines = []

# lines 0-6 (1-7) are page config
fence_calc_lines.extend(lines[0:7])

# imports needed in fence_calculator.py
fence_calc_lines.append("import json\n")
fence_calc_lines.append("import datetime\n")
fence_calc_lines.append("from data_loader import get_fence_prices\n")
fence_calc_lines.append("from calculators.fence import calculate_fence, create_fence_pdf\n\n")

# fence.py lines 7 to 1159 (0-indexed: 7 to 1159)
fence_py_lines.extend(lines[7:1159])

# the rest goes to fence_calculator.py
fence_calc_lines.extend(lines[1159:])

with open('calculators/fence.py', 'w') as f:
    f.writelines(fence_py_lines)

with open('pages/fence_calculator.py', 'w') as f:
    f.writelines(fence_calc_lines)

print("Split completed.")
