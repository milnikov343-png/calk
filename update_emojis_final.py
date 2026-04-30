import os
import re

emoji_map = {
    '⚠️': ':material/warning:',
    '↔️': ':material/swap_horiz:',
    '📥': ':material/download:',
    '💼': ':material/work:',
    '✨': ':material/auto_awesome:',
    '📋': ':material/list_alt:',
    '🏗️': ':material/construction:',
    '📏': ':material/straighten:',
    '⬜': ':material/rectangle:',
    '✅': ':material/check_circle:',
    '🏊': ':material/pool:',
    '📐': ':material/architecture:',
    '💾': ':material/save:',
    '🚀': ':material/rocket_launch:',
    '🤖': ':material/smart_toy:',
    '🖱️': ':material/mouse:',
    '⏺️': ':material/circle:',
    '🔳': ':material/crop_din:',
    '📊': ':material/bar_chart:',
    '✏️': ':material/edit:',
    '🛠️': ':material/build:',
    '❌': ':material/cancel:',
    '👆': ':material/touch_app:',
    '🔲': ':material/crop_square:',
    '🧱': ':material/inventory_2:',
    '🪵': ':material/forest:',
    '⛓️': ':material/link:',
    '🚪': ':material/sensor_door:',
    '📦': ':material/package:',
    '🚚': ':material/local_shipping:',
    '⚒️': ':material/construction:',
    '🛡️': ':material/shield:',
    '🏡': ':material/home:',
    '🌙': ':material/dark_mode:',
    '☀️': ':material/light_mode:',
    '⬅': ':material/arrow_back:',
    '📝': ':material/description:',
    '🔄': ':material/refresh:',
    '🚧': ':material/vertical_split:',
    '⚙️': ':material/settings:'
}

def replace_emojis(match):
    return emoji_map.get(match.group(0), match.group(0))

pattern = re.compile('|'.join(re.escape(key) for key in emoji_map.keys()))

for file in ["app.py", "pages/fence_calculator.py", "pages/terrace_calculator.py", "pages/fence_prices.py"]:
    if not os.path.exists(file): continue
    with open(file, "r") as f:
        content = f.read()
    
    # We want to keep page_icon="emoji" intact.
    # We'll temporarily mask them.
    content = re.sub(r'page_icon="([^"]+)"', r'page_icon="[[[\1]]]"', content)
    
    # Replace all matching emojis
    content = pattern.sub(replace_emojis, content)
    
    # Unmask page_icon
    content = re.sub(r'page_icon="\[\[\[(.*?)\]\]\]"', r'page_icon="\1"', content)

    # Some icons might have ended up as ":material/settings: " where there was a space. Clean up double spaces if any.
    content = content.replace(':material/settings:  ', ':material/settings: ')
    
    with open(file, "w") as f:
        f.write(content)

print("Done")
