import os, re
for f in ["app.py", "pages/fence_calculator.py", "pages/terrace_calculator.py", "pages/fence_prices.py"]:
    if not os.path.exists(f): continue
    content = open(f).read()
    # Simple regex to find emojis
    emojis = re.findall(r'[^\x00-\x7Fа-яА-ЯёЁ₽©«»\s\w\d\p{P}]+', content)
    emojis = [e for e in emojis if len(e.strip()) > 0 and e not in ['$', '_', '-', '*']]
    # Print distinct emojis
    print(f, list(set(emojis)))
