import os, re
f = "pages/terrace_calculator.py"
content = open(f).read()
emojis = re.findall(r'[^\x00-\x7Fа-яА-ЯёЁ₽©«»\s\w\d\.\,\;\:\!\?\-\(\)\/\"\'\=\+\[\]\{\}\<\>\|\\\_]+', content)
print(set(emojis))
