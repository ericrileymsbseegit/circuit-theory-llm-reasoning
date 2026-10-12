"""
Condition B: EXPLICIT instructions.
The model is given the parallel-resistance rule and the voltage-divider rule.
"""
from circuits_common import describe_circuit, ANSWER_FORMAT, run

def build_prompt(c):
    n = c["n_parallel"]
    if n == 1:
        rule1 = "R_parallel = R1  (only one path)"
    elif n == 2:
        rule1 = "R_parallel = (R1 * R2) / (R1 + R2)"
    else:
        rule1 = "R_parallel = 1 / (" + " + ".join(f"1/R{i}" for i in range(1, n + 1)) + ")"
    return (
        "Solve this DC resistor circuit. Follow the two steps exactly.\n\n"
        f"{describe_circuit(c)}\n\n"
        f"STEP 1: Compute the parallel combination of all {n} resistor(s) from VA to B:\n"
        f"  {rule1}\n\n"
        "STEP 2: Compute the voltage at node B using R_parallel and R_series:\n"
        "  VB = VA * R_series / (R_parallel + R_series)\n\n"
        "Compute to 4 decimal places.\n"
        f"{ANSWER_FORMAT}"
    )

if __name__ == "__main__":
    run("explicit", build_prompt, "results_explicit.csv")
