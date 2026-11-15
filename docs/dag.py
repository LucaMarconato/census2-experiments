#!/usr/bin/env python3
"""The pixi task graph (`pixi task list --json`, depends-on) as docs/tasks.svg, via Graphviz.

Tasks without dependencies either way (dag, floci-stop) are utilities and left out.
"""

import json
import subprocess
import textwrap
from pathlib import Path

envs = json.loads(subprocess.run(["pixi", "task", "list", "--json"], capture_output=True, text=True, check=True).stdout)
tasks = {}
for env in envs:
    for feature in env["features"]:
        for t in feature["tasks"]:
            tasks.setdefault(t["name"], (t, env["environment"]))

linked = {t for t, _ in tasks.values() for d in t.get("depends_on") or [] for t in (t["name"], d["task_name"])}
dot = ['digraph tasks {', 'rankdir=LR; bgcolor="#FFFFFF"; nodesep=0.3; ranksep=0.5;',
       'node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=12, color="#4A5568", fillcolor="#FFFFFF"];',
       'edge [color="#718096", arrowsize=0.7];']
for name, (t, env) in sorted(tasks.items()):
    if name not in linked:
        continue
    desc = "\\n".join(textwrap.wrap(t.get("description") or "", 34))
    fill = "#FDF1E4" if env == "spike" else "#E8F0FB" if name == "all" else "#FFFFFF"
    dot.append(f'"{name}" [fillcolor="{fill}", label="{name}\\n{desc}"];')
    for d in t.get("depends_on") or []:
        dot.append(f'"{d["task_name"]}" -> "{name}";')
dot.append("}")
out = Path(__file__).with_name("tasks.svg")
r = subprocess.run(["dot", "-Tsvg"], input="\n".join(dot).encode(), capture_output=True)
if r.returncode:
    raise SystemExit(r.stderr.decode() + "\n".join(dot))
out.write_bytes(r.stdout)
print(out)
