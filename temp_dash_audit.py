"""Dashboard HTML audit"""
import re
from pathlib import Path

dash = Path(r"C:\Users\Never\.openclaw\workspace\docs\dashboardV14PM.html")
content = dash.read_text(encoding="utf-8")

print("### DASHBOARD AUDIT ###")
print("Size: %d bytes, %d lines" % (len(content), content.count("\n")))

# Check for hardcoded URLs/paths
urls = re.findall(r'https?://[^\s"<>]+', content)
print("\nExternal URLs: %d" % len(set(urls)))
for u in sorted(set(urls)):
    print("  %s" % u[:120])

# Check for division by zero in JS
print("\nJS division risks:")
lines = content.splitlines()
for i, line in enumerate(lines, 1):
    stripped = line.strip()
    # Look for / followed by a variable name (potential zero)
    if re.search(r'/\s*[a-zA-Z_]\w*\b', stripped) and not stripped.startswith("//") and not stripped.startswith("*"):
        # Skip CSS, comments, URLs
        if "url(" in stripped or "http" in stripped or "font" in stripped:
            continue
        if "color" in stripped or "border" in stripped or "background" in stripped:
            continue
        if "//" in stripped and stripped.index("//") < stripped.index("/"):
            continue
        # Only show actual division operations
        if re.search(r'[=+\-*(,]\s*[^/]*/\s*[a-zA-Z_]\w*', stripped):
            print("  line %d: %s" % (i, stripped[:120]))

# Check status.json fields used by dashboard
print("\nStatus fields accessed (S.xxx):")
fields = sorted(set(re.findall(r'S\.(\w+)', content)))
print("  %d unique fields: %s" % (len(fields), ", ".join(fields)))

# Check coin fields accessed (c.xxx)
coin_fields = sorted(set(re.findall(r'\bc\.(\w+)', content)))
print("\nCoin fields accessed (c.xxx):")
print("  %d unique fields: %s" % (len(coin_fields), ", ".join(coin_fields)))
