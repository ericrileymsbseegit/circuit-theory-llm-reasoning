"""
Paired comparison of bare vs explicit on the same circuits (McNemar test).
Run after run_bare.py and run_explicit.py.
"""
import csv, os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
from math import comb

def load(path):
    with open(path, newline="", encoding="utf-8") as f:
        return {int(r["id"]): r for r in csv.DictReader(f)}

def mcnemar_exact(b, c):
    """Two-sided exact McNemar p-value: binomial test on the discordant pairs."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p)

def compare(metric, bare, expl):
    ids = sorted(set(bare) & set(expl))
    both = b = c = neither = 0
    for i in ids:
        a_ok, e_ok = int(bare[i][metric]), int(expl[i][metric])
        if a_ok and e_ok: both += 1
        elif e_ok:        b += 1          # fixed by giving the rule
        elif a_ok:        c += 1          # broken by giving the rule
        else:             neither += 1
    n = len(ids)
    print(f"\n=== {metric} (n = {n} paired circuits) ===")
    print(f"  Bare correct:      {both + c:>4} / {n}  ({(both + c) / n:.1%})")
    print(f"  Explicit correct:  {both + b:>4} / {n}  ({(both + b) / n:.1%})")
    print(f"  Both right {both}, both wrong {neither}")
    print(f"  Fixed by the rule (b) = {b},  broken by the rule (c) = {c}")
    print(f"  Exact McNemar p = {mcnemar_exact(b, c):.4g}")

def by_level(metric, bare, expl):
    print(f"\n  {metric} accuracy by number of parallel resistors:")
    print("   N   bare   explicit")
    for n in sorted({int(r["n_parallel"]) for r in bare.values()}):
        ids = [i for i, r in bare.items() if int(r["n_parallel"]) == n and i in expl]
        ab = sum(int(bare[i][metric]) for i in ids) / len(ids)
        ex = sum(int(expl[i][metric]) for i in ids) / len(ids)
        print(f"   {n}   {ab:5.0%}   {ex:6.0%}")

if __name__ == "__main__":
    bare = load(os.path.join(BASE_DIR, "results_bare.csv"))
    expl = load(os.path.join(BASE_DIR, "results_explicit.csv"))
    for m in ["rp_correct", "vb_correct", "both_correct"]:
        compare(m, bare, expl)
        by_level(m, bare, expl)
