"""List Freqtrade strategy classes in a folder by reading source (no execution)."""
import ast, json, sys, pathlib
out = []
for p in sorted(pathlib.Path(sys.argv[1]).rglob("*.py")):
    try:
        tree = ast.parse(p.read_text(errors="ignore"))
    except SyntaxError:
        continue
    for n in tree.body:
        if isinstance(n, ast.ClassDef) and n.bases:
            src = ast.get_source_segment(p.read_text(errors="ignore"), n) or ""
            if "populate_" not in src:
                continue
            info = {"file": str(p), "class": n.name, "bases": [ast.unparse(b) for b in n.bases]}
            for st in n.body:
                if isinstance(st, (ast.Assign, ast.AnnAssign)):
                    tg = st.targets[0] if isinstance(st, ast.Assign) else st.target
                    if isinstance(tg, ast.Name) and tg.id in ("timeframe", "can_short", "INTERFACE_VERSION"):
                        try: info[tg.id] = ast.literal_eval(st.value)
                        except Exception: info[tg.id] = ast.unparse(st.value)
            info["informative"] = "informative_pairs" in src and "BTC" in src
            out.append(info)
json.dump(out, sys.stdout, indent=0)
