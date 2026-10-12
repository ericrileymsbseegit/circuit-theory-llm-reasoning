# Circuit-Theoretic Cognitive Bypass Detection

**Does an AI's declared reasoning actually produce its answer, or does it skip a step?**

This project tests whether a large language model follows the reasoning steps it says it follows. It borrows a tool from electrical engineering: build a problem where the correct path is known, then check whether the model's answers depend on each step in the right order or jump around one.

Kaggle / Google DeepMind 2026 submission · Eric Riley · MS Statistics, Texas A&M · BSEE, CU Boulder

---

## The short version

> I built a test to catch AI cheating. It caught me instead.

The first results looked like the model was skipping a step. The test was right that something was inconsistent, but the fault was in my own parser, which was reading the wrong number. After fixing it, the model followed the declared reasoning on about **100% of the hardest cases, up from roughly 25%** before the fix.

That is the point of the project: a confident number needs something to check it against. In a circuit, that check is physics.

---

## Why a circuit?

A circuit obeys conservation laws: what flows in must flow out. The right answer is fixed, so the test can be checked against a known truth. That makes the circuit the **control condition**:

1. Prove the method where the answer is known (the circuit).
2. Show it flags a real shortcut and that a clean result means something.
3. Only then ask the same question where the answer isn't known, such as marketing attribution.

## The circuit

```
           ┌──/\/\/──┐
           │   R1    │
VA ────────┤         ├──────●── VB
           │   R3    │      │
           └──/\/\/──┘      ⌇ R2
                            │
                          ground
```

The parallel resistors combine into one equivalent resistance, Rp. Rp and R2 then form a voltage divider, and VB is read where they meet. The picture shows two parallel resistors; the test circuits use 1 to 5 (N):

```
1/Rp = 1/R1 + 1/R3 + …          (two resistors: Rp = R1 × R3 / (R1 + R3))
VB   = VA × R2 / (Rp + R2)
```

- **VA**: input voltage
- **VB**: output voltage
- **R1, R3, …**: the resistors in parallel
- **R2**: the divider resistor to ground
- **Rp**: the equivalent resistance of the parallel resistors
- **N**: the number of parallel resistors in a circuit (1 to 5)

Getting VB right requires getting Rp right first. That ordering is what the test checks.

The **declared truth** is that VA reaches VB only *through* Rp. There is no direct VA → VB connection.

## How a skipped step is detected

The whole test is one question: **for any two steps, are they connected directly, or only through the step in between?**

```
Through the chain (good):     VA ──► Rp ──► VB      no direct VA–VB link
Back-channel (the alarm):     VA ──► Rp ──► VB
                               └──────────────┘     VA reaches VB directly; Rp was skipped
```

The readout is the **precision matrix**, the inverse of the covariance matrix:

```
Q = Σ⁻¹
```

- **Σ** (sigma): the covariance matrix of the model's step-by-step outputs across many problems
- **Q**: the precision matrix
- **Q[i, j]**: the cell for steps *i* and *j*. **Zero** means the two steps are not directly connected once the other steps are accounted for (conditionally independent). **Non-zero** means a direct link.

| Pair | Declared circuit says | Bypass would show |
|---|---|---|
| VA – Rp | connected (non-zero) | non-zero |
| Rp – VB | connected (non-zero) | non-zero |
| **VA – VB** | **zero** | **non-zero: shortcut** |

If the forbidden cells read zero, the model followed the declared path. If one flips to non-zero, the model took a shortcut. This is the same math as nodal analysis in circuits: the nodal admittance matrix plays the role of the precision matrix, and a missing wire shows up as a zero entry.

## The experiment: does a step-by-step rule help?

The same 100 circuits were given to Claude under two conditions:

- **Bare:** the circuit and the question only. Claude has to work out the formulas itself.
- **Explicit:** step-by-step instructions: compute Rp first, then VB.

Each circuit is solved under both conditions, so the results are **paired**. The question is whether the explicit rule changes the outcome:

- **H₀:** the rule does not help
- **Hₐ:** the rule does help

### Results (n = 100 paired circuits)

| Measure | Bare correct | Explicit correct | Fixed by the rule (b) | Broken by the rule (c) | Exact McNemar p |
|---|---|---|---|---|---|
| Rp correct | 93 | 100 | 7 | 0 | 0.0156 |
| VB correct | 93 | 100 | 7 | 0 | 0.0156 |
| Both correct | 91 | 100 | 9 | 0 | 0.0039 |

Accuracy by number of parallel resistors (20 circuits per N):

| N | Rp: bare | VB: bare | Both: bare | Explicit (all three) |
|---|---|---|---|---|
| 1 | 100% | 100% | 100% | 100% |
| 2 | 100% | 100% | 100% | 100% |
| 3 | 90% | 90% | 90% | 100% |
| 4 | 100% | 100% | 100% | 100% |
| 5 | 75% | 75% | 65% | 100% |

### Why McNemar's test

With paired results, only the circuits where the two conditions **disagree** carry information:

```
            Explicit right   Explicit wrong
Bare right       a                c
Bare wrong       b                d
```

- **a**: both right · **d**: both wrong (these say nothing about the rule)
- **b**: wrong without the rule, right with it ("fixed by the rule")
- **c**: right without the rule, wrong with it ("broken by the rule")

If the rule made no difference, a disagreement would be equally likely to fall in b or c, like a coin flip. With c = 0, the exact two-sided p-value is the chance that all b flips land the same way:

```
p = 2 × (½)^b        b = 7 → p = 0.0156      b = 9 → p = 0.0039
```

The rule never hurt (c = 0 in every case), and it fixed every bare error. The errors without it cluster in the largest circuits (N = 5), where there are more terms to combine. With 20 circuits per N, the per-N rates are rough; the paired test across all 100 is the main result.

## Repository contents

```
├── README.md
├── circuits_common.py              shared circuits, model call, parser and grading
├── run_bare.py                     bare condition: no instructions, Claude finds the formulas
├── run_explicit.py                 explicit condition: step-by-step instructions
├── compare.py                      paired comparison and McNemar test
├── circuits.csv                    the 100 test circuits (resistor and voltage values)
├── circuit_measurements_v6.json    circuits from the original Kaggle run
├── results_bare.csv                Claude's answers, bare condition
├── results_explicit.csv            Claude's answers, explicit condition
├── overview deck.pdf               full write-up with diagrams
└── results deck.pdf                McNemar results
```

## How to run

**Reproduce the results (no API key needed).** The model's answers are saved in `results_bare.csv` and `results_explicit.csv`, so the paired comparison runs on its own:

```bash
pip install -r requirements.txt
python compare.py
```

**Re-run the experiment from scratch (needs an Anthropic API key).** The runners call Claude, so set your key as an environment variable first. It is never stored in the code:

```bash
# Windows PowerShell:  setx ANTHROPIC_API_KEY "your-key"   (then reopen the terminal)
# macOS / Linux:       export ANTHROPIC_API_KEY="your-key"
python run_bare.py
python run_explicit.py
python compare.py
```

Settings shared by both conditions: model `claude-haiku-4-5-20251001`, temperature 0, 800 max tokens. An answer counts as correct if it is within 1% of the true value.

## The bigger lesson: discovered vs. invented

In a circuit, charge is conserved. Every valid method of analysis lands on the same number, and when two engineers disagree, one of them is wrong. The answer is **discovered**.

Marketing attribution has no such referee. First-touch, last-touch, linear, U-shaped and time-decay models, with 7-, 15- or 40-day windows, give different credit to the same campaigns from the same data. Nothing in the data says which is right. The answer is **invented** by the choice of rule.

What pins a number down, from strongest to weakest:

| Evidence | Example | Can it be proven wrong? |
|---|---|---|
| Conserved law | the circuit (charge) | yes, self-enforcing |
| Experiment | randomized incrementality test | yes |
| Quasi-experiment | difference-in-differences, synthetic control | partly |
| Convention | first / last / multi-touch attribution | no |

An AI's reasoning can be verified where there is an invariant and can only be taken on faith where there isn't. The way forward is not better conventions or an AI oracle. It's invariants: a structural model first, then an experiment that supplies a real check.

> A number you can't prove wrong isn't a measurement. It's a choice wearing a costume.

## License

MIT
