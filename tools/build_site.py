import sys
t = open("template.html").read()
d = open("schedule_plan.json").read()
html = t.replace("__PLAN__", d).replace("__UPDATED__", sys.argv[1] if len(sys.argv) > 1 else "7 Oct 2026")
open("site/index.html", "w").write(html)
# artifact version: no document wrapper; theme tokens guarded for the viewer's toggle
a = html[html.index("<title>"):html.index("</head>")] + html[html.index("<body>") + 6:html.index("</body>")]
start = a.index("@media (prefers-color-scheme: dark){:root{")
end = a.index("color-scheme:dark }}", start) + len("color-scheme:dark }}")
vals = a[start + len("@media (prefers-color-scheme: dark){:root{"):end - 2]
a = a[:start] + '@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){' + vals + '}}\n:root[data-theme="dark"]{' + vals + '}' + a[end:]
open("rrb-it-plan.html", "w").write(a)
print("built", len(html), len(a))
