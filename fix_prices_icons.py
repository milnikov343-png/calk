import re

with open("pages/fence_prices.py", "r") as f:
    content = f.read()

# Add CSS if missing
css_import = "@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0');\n"
if "Material+Symbols+Outlined" not in content and "<style>" in content:
    content = content.replace("<style>\n", f"<style>\n{css_import}")

# Regex to find <div class="price-section-title ...">:material/xxx: and replace with <span>
content = re.sub(
    r'(<div class="price-section-title [^>]+>):material/([a-z_]+):',
    r'\1<span class="material-symbols-outlined" style="vertical-align: bottom;">\2</span>',
    content
)

with open("pages/fence_prices.py", "w") as f:
    f.write(content)

print("Done")
