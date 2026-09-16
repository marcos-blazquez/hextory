# Next pulse focus (sticky)

1. DES-0001/0002 **Approved**; FileCheckpointer + GraphRunner/optional LangGraph landed. R-0009 **59.4** (Δ+2.5 vs R-0008) — not flat.
2. Ceiling to ≥90: **hosted git + live Actions + branch protection** (aspects 7, 10) when Marcos lifts git-init deferral. Until then, keep local `python3 scripts/ci_design_gates.py` + pytest green every pulse (expect skips if langgraph extra missing).
3. Capability lenses: code-review avoidance as one capability; open graphs proven (registry + LangGraph compiles from definition); testing layer `tests/{unit,behavior,adapters}` (not Cucumber).
4. Hygiene: scrub leftover “Draft” / “may change in review” in Approved DES-0002; Status cells stay bare.
5. Product track (outside pulse): harden interceptors (idempotency/quota) then LLM beyond NullLlm. Watch: DES-0003 Draft scope creep; do not score dual runtime as multi-target.
6. Always report; ≥90 self-pause unchanged. Do not draft new SDDs or implement product features during pulse. Do not `git init` until Marcos says so.
