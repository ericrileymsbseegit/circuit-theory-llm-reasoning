"""
Shared pieces for the explicit-vs-bare A/B test:
circuit generation, exact answers, the API call, parsing and scoring.
Both runners import this file, so they test the SAME circuits with the
SAME model, settings, parser and grading. Only the prompt differs.
"""
import csv, json, os, random, re, time
import anthropic

MODEL       = "claude-haiku-4-5-20251001"   # same model as the Kaggle runs
TEMPERATURE = 0.0
MAX_TOKENS  = 800
TOLERANCE   = 0.01                          # correct if within 1% of the true value
CIRCUITS_CSV = "circuits.csv"
KAGGLE_JSON  = "circuit_measurements_v6.json"   # Kaggle v6 run (500 circuits)
MAX_CIRCUITS = None                             # e.g. 100 for a quick trial; None = all

E12 = [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2]

# Output format both conditions must follow (format only, no physics rules)
ANSWER_FORMAT = (
    "End your response with exactly these two lines:\n"
    "R_parallel = <number in ohms>\n"
    "VB = <number in volts>\n"
)

# ── Circuits ───────────────────────────────────────────────────────────────
def _resistor(rng):
    nominal = rng.choice(E12) * rng.choice([10, 100, 1000])
    return round(nominal * rng.uniform(0.9, 1.1), 1)          # E12 with ±10% tolerance

def generate_circuits(n_per_level=20, levels=(1, 2, 3, 4, 5), seed=2026):
    rng = random.Random(seed)
    circuits, cid = [], 0
    for n in levels:
        for _ in range(n_per_level):
            cid += 1
            circuits.append({
                "id": cid,
                "n_parallel": n,
                "r_parallel": [_resistor(rng) for _ in range(n)],
                "r_series": _resistor(rng),
                "va": rng.choice([3.3, 5.0, 9.0, 12.0, 15.0, 24.0]),
            })
    return circuits

def save_circuits(circuits, path=CIRCUITS_CSV):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "n_parallel", "r_parallel", "r_series", "va"])
        for c in circuits:
            w.writerow([c["id"], c["n_parallel"],
                        ";".join(str(r) for r in c["r_parallel"]),
                        c["r_series"], c["va"]])

def circuits_from_kaggle_json(json_path=KAGGLE_JSON):
    """
    Kaggle v6 topology: R1 and R3 in parallel from VA to B, R2 in series from B to GND.
    Here they become r_parallel = [R1, R3] and r_series = R2.
    """
    with open(json_path) as f:
        records = json.load(f)["records"]
    return [{"id": r["id"], "n_parallel": 2, "r_parallel": [r["r1"], r["r3"]],
             "r_series": r["r2"], "va": r["va"]} for r in records]

def load_circuits(path=CIRCUITS_CSV):
    """
    Priority: circuits.csv if it exists; else build it from the Kaggle JSON;
    else generate a fresh seeded set. Both runners then read the same circuits.csv.
    """
    if not os.path.exists(path):
        if os.path.exists(KAGGLE_JSON):
            save_circuits(circuits_from_kaggle_json(), path)
            print(f"Created {path} from {KAGGLE_JSON} (your Kaggle circuits).")
        else:
            save_circuits(generate_circuits(), path)
            print(f"Created {path} with a fresh, seeded circuit set.")
    out = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            out.append({
                "id": int(row["id"]),
                "n_parallel": int(row["n_parallel"]),
                "r_parallel": [float(x) for x in row["r_parallel"].split(";")],
                "r_series": float(row["r_series"]),
                "va": float(row["va"]),
            })
    return out[:MAX_CIRCUITS] if MAX_CIRCUITS else out

def true_answers(c):
    rp = 1.0 / sum(1.0 / r for r in c["r_parallel"])
    vb = c["va"] * c["r_series"] / (rp + c["r_series"])
    return rp, vb

# ── Circuit description shared by both prompts ─────────────────────────────
def describe_circuit(c):
    n = c["n_parallel"]
    lines = ["Circuit:", "  VA ---[R1]--- B ---[R_series]--- GND"]
    for i in range(2, n + 1):
        lines += ["   |             |", f"   +---[R{i}]----+"]
    if n == 1:
        lines.append("  (R1 is the only path from VA to node B)")
    else:
        names = ", ".join(f"R{i}" for i in range(1, n + 1))
        lines.append(f"  ({names} all connect in parallel from VA to node B)")
    lines.append("")
    lines.append("Component values:")
    for i, r in enumerate(c["r_parallel"], 1):
        lines.append(f"  R{i} = {r} ohms")
    lines.append(f"  R_series = {c['r_series']} ohms  (from B to GND)")
    lines.append(f"  VA = {c['va']} V")
    lines.append("  GND = 0 V")
    return "\n".join(lines)

# ── Model call ─────────────────────────────────────────────────────────────
_client = None
def ask(prompt, retries=3):
    global _client
    if _client is None:
        _client = _client = anthropic.Anthropic() # Removed API key argument to use environment variable
    for attempt in range(retries):
        try:
            msg = _client.messages.create(
                model=MODEL, max_tokens=MAX_TOKENS, temperature=TEMPERATURE,
                messages=[{"role": "user", "content": prompt}])
            return "".join(b.text for b in msg.content if b.type == "text")
        except Exception as e:
            if attempt == retries - 1:
                return f"ERROR: {e}"
            time.sleep(2 ** attempt)

# ── Parsing and scoring ────────────────────────────────────────────────────
_NUM = r"(-?\d[\d,]*\.?\d*(?:[eE]-?\d+)?)"
_RP  = re.compile(r"R_parallel\s*[=≈]\s*" + _NUM)
_VB  = re.compile(r"\bVB\s*[=≈]\s*" + _NUM)

def _last(pattern, text):
    hits = pattern.findall(text)
    return float(hits[-1].replace(",", "")) if hits else None

def parse(text):
    """Take the LAST 'R_parallel =' and 'VB =' in the reply (the final answer lines)."""
    return _last(_RP, text), _last(_VB, text)

def close(got, truth):
    return got is not None and abs(got - truth) <= TOLERANCE * abs(truth)

# ── Shared run loop ────────────────────────────────────────────────────────
def run(condition, build_prompt, out_csv):
    circuits = load_circuits()
    fields = ["id", "n_parallel", "condition", "rp_true", "vb_true",
              "rp_model", "vb_model", "rp_correct", "vb_correct", "both_correct", "response"]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for k, c in enumerate(circuits, 1):
            rp_t, vb_t = true_answers(c)
            text = ask(build_prompt(c))
            rp_m, vb_m = parse(text)
            rp_ok, vb_ok = close(rp_m, rp_t), close(vb_m, vb_t)
            w.writerow({"id": c["id"], "n_parallel": c["n_parallel"], "condition": condition,
                        "rp_true": round(rp_t, 4), "vb_true": round(vb_t, 4),
                        "rp_model": rp_m, "vb_model": vb_m,
                        "rp_correct": int(rp_ok), "vb_correct": int(vb_ok),
                        "both_correct": int(rp_ok and vb_ok), "response": text})
            print(f"[{condition}] {k}/{len(circuits)}  N={c['n_parallel']}  "
                  f"Rp {'ok ' if rp_ok else 'MISS'}  VB {'ok' if vb_ok else 'MISS'}")
    print(f"Saved {out_csv}")
