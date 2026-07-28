# Fix Notes (2026-07-28, r2)

v3 fixes (carried over from r1):

1. `pasqal_kqs_v302_one_click.py` made standalone (imports protocol
   machinery from the main v3.0.2 script; accepts both the as-evaluated
   source hash `ae7dcfd7...` and the shipped docstring-cleaned hash
   `7ed2c8fe...`).
2. v3.0.2 main-script docstring cleanup (stale v2 filename + noise-model
   sentence). Docstring-only: protocol hash `c9917d51...` unchanged.
3. README: immutable path1.41.py link, one-click usage, dual source hashes,
   NumPy-version caveat for the ranking hash.

v2 additions (r2):

4. `pasqal_kz_v201_one_click.py` made standalone (same import pattern).
   The verifier accepts all four known v2.0.1 source hashes from the
   2026-07-27 hash-definition repair trail (`42de3826`, `7e882872`,
   `620f8c43`, and the shipped-script stable-inventory hash `8442f028`);
   the frozen protocol hash `2c05a45f...` is unchanged across all of them.
   The certificate now records the runtime source hash.
5. The historical v2 "Colab-stable recommit" cell is deliberately NOT
   shipped: it documents the one-time hash repair (already disclosed in
   README section 5) and its stable-hash logic lives in the v2.0.1 main
   script itself.
6. README: v2 one-click usage, v2 dual source-hash table, note explaining
   the multiple legitimate v2 source hashes, removal of the stale
   "no v2 packager" note.

End-to-end verification of this exact package (Python 3.12.12, NumPy 2.2.5):

- v3: stage-1 commit reproduces `c9917d51...`; one-click passes all six
  commitment checks; evaluation returns `all_gates_pass: true` with
  Spearman values identical to the reference run at all printed digits.
- v2: stage-1 commit reproduces `2c05a45f...`; one-click verifies against
  the known-hash set; evaluation reproduces the registered FAIL
  (`all_gates_pass: false`, only the two predeclared-improvement gates
  failing), Spearman = 1.0 at every gamma, prediction errors matching the
  reference run at all printed digits.

Note: ranking-certificate hashes under NumPy 2.2.5 differ at the byte level
from the reference NumPy 2.0.2 runs (~1e-6 relative float drift); all rank
statistics and gate verdicts reproduce exactly.
