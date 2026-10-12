"""
Condition A: BARE instructions.
Same circuits, same two steps, same answer format, but NO formulas.
The model has to know (or work out) the rules on its own.
"""
from circuits_common import describe_circuit, ANSWER_FORMAT, run

def build_prompt(c):
    n = c["n_parallel"]
    return (
        "Solve this DC resistor circuit in two steps.\n\n"
        f"{describe_circuit(c)}\n\n"
        f"STEP 1: Find R_parallel, the equivalent resistance of the {n} resistor(s) from VA to B.\n\n"
        "STEP 2: Find VB, the voltage at node B.\n\n"
        "Compute to 4 decimal places.\n"
        f"{ANSWER_FORMAT}"
    )

if __name__ == "__main__":
    run("bare", build_prompt, "results_bare.csv")
