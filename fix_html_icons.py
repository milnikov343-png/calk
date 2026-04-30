import re
import os

def fix_file(filepath):
    with open(filepath, "r") as f:
        content = f.read()

    # 1. Ensure CSS import is in the file
    css_import = "@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0');\n"
    if "Material+Symbols+Outlined" not in content and "<style>" in content:
        content = content.replace("<style>\n", f"<style>\n{css_import}")

    # 2. Replace :material/icon: with <span> in specific HTML tags
    # For app.py, they are in <div class="card-title"> and <div class="card-image">
    content = re.sub(
        r':material/([a-z_]+):',
        r'<span class="material-symbols-outlined" style="vertical-align: bottom;">\1</span>',
        content
    )
    
    with open(filepath, "w") as f:
        f.write(content)

fix_file("app.py")
print("Done app.py")
