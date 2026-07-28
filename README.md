# K(z)-Guided Prospective Task-Loss Ranking — Reproduction Package

Frozen, falsifiable evaluation of whether an **ideal-path** control descriptor
can rank **finite-noise task losses** — computed *before* any noisy outcome —
for controls that share the same complete ideal unitary.

Two pre-registered protocols are included:

| Protocol | Noise model | Predictor | Verdict |
|---|---|---|---|
| v2.0.1 (`2c05a45f…`) | Weak local Markovian dephasing | First-order slope `j1(z) = −Re Tr[ρ_target G_z(ρ₀₀)]`, `G_z = dE_z/dγ` at γ = 0 | **FAIL** — ranking perfect (Spearman 1.0) but task improvement 0.48% < 1% predeclared minimum |
| v3.0.2 (`c9917d51…`) | Zero-mean common quasi-static detuning offset ξ ~ N(0, σ²) | Variance susceptibility `q2(z) = ½ d²J/dξ²` at ξ = 0 | **PASS (14/14 gates)** — predicted improvement 20.56%, measured 20.3–20.6%, prediction error ≤ 0.96% |

The v2.0.1 failure is reported as registered. It is part of the evidence:
the same predictor architecture yields a real, falsifiable negative under one
noise model and a positive under another.

---

## 1. Repository contents

```
├── pasqal_kz_quasistatic_ranking_v3_0_2.py   # v3.0.2 main script (quasi-static detuning)
├── pasqal_kqs_v302_one_click.py              # v3.0.2 standalone verifier/packager
├── pasqal_kz_task_ranking_prospective_v2_0_1.py  # v2.0.1 main script (Markovian dephasing)
├── pasqal_kz_v201_one_click.py               # v2.0.1 standalone verifier/packager
├── manifests/
│   ├── v2.0.1/prospective_protocol.json      # frozen protocol, protocol_sha256 = 2c05a45f…
│   └── v3.0.2/prospective_protocol.json      # frozen protocol, protocol_sha256 = c9917d51…
├── results/
│   ├── v2.0.1/summary.json                   # our reference outputs (FAIL)
│   └── v3.0.2/summary.json                   # our reference outputs (PASS)
├── requirements.txt
└── README.md
```

> The historical v2 "Colab-stable recommit" notebook cell (which redefined
> `source_hash`, re-committed, and evaluated in one cell) is **not** shipped:
> it documents the one-time 2026-07-27 hash-repair recorded in the commitment
> history, and its stable-hash logic now lives in the v2.0.1 main script
> itself. Publishing it would invite confusion about the pre-registration
> trail.

Each main script is self-contained and implements the full two-stage
workflow: **commit** (freeze protocol, compute nothing) → **evaluate**
(generate candidates, freeze predicted ranking, only then compute held-out
noisy losses).

---

## 2. Environment

- Python **3.12.x** (developed on 3.12.13)
- Dependencies: `pip install -r requirements.txt`

```
numpy==2.0.2
scipy>=1.11
```

> **Python-version caveat.** The `source_sha256` commitment hashes a
> normalized inventory of *compiled bytecode* (a deliberate defence against
> notebook-namespace tampering). It therefore matches only under the same
> CPython version (3.12.x). On other Python versions the source-hash gate
> will fail even for a byte-identical file; in that case verify the
> **protocol hash** and the **ranking certificate hash** instead — the
> scientific outputs are pure NumPy/SciPy numerics and are
> version-insensitive to within floating-point reproducibility.

---

## 3. Reproduce v3.0.2 (quasi-static detuning — PASS)

Two-stage (recommended — mirrors the original pre-registration):

```bash
# Stage 1 — freeze the protocol (computes NO physics)
python pasqal_kz_quasistatic_ranking_v3_0_2.py
# → prints protocol_sha256 = c9917d5119b520fa17e1e56f1d903403b3e2d963d5a24e32e3945fbd253ba39e
# → writes pasqal_kz_commit_c9917d5119b5/prospective_protocol.json

# Stage 2 — frozen held-out evaluation
python pasqal_kz_quasistatic_ranking_v3_0_2.py \
    --evaluate --expected-hash c9917d5119b520fa17e1e56f1d903403b3e2d963d5a24e32e3945fbd253ba39e
```

Or in one invocation:

```bash
python pasqal_kz_quasistatic_ranking_v3_0_2.py --one-click
```

Run in a **clean, empty directory** (the evaluator refuses to overwrite an
existing output directory).

### Expected outputs

`pasqal_kqs_v302_eval_c9917d5119b5/` containing:

- `predicted_ranking_frozen_before_heldout.json` — the frozen prediction
- `candidate_ranking_results.csv`, `heldout_results.csv`
- `candidate_predictor_audit.json`, `reference_control.csv`, `selected_control.csv`
- `summary.json` — the verdict

### Hashes to check

| Artifact | Expected SHA-256 |
|---|---|
| Protocol | `c9917d5119b520fa17e1e56f1d903403b3e2d963d5a24e32e3945fbd253ba39e` |
| Source as evaluated 2026-07-27 (Python 3.12 only) | `ae7dcfd733568901aa526ad2c2ad4e89a4da1f3378edcfe5b03035de8d026843` |
| Source as shipped in this repo (docstring-only cleanup, Python 3.12 only) | `7ed2c8fe92355629bedd7b8ce057712c94845fe27821e8aa0871a774ca667874` |
| Frozen ranking (reference run, NumPy 2.0.2) | `610d54f7c73ef9f5d0b8b482001e4e450ace49926a0bb9ef2e7e69f801ccd947` |

> The shipped v3.0.2 script differs from the evaluated one **only in the
> module docstring** (a stale stage-2 filename and noise-model sentence were
> corrected). The frozen `PROTOCOL` — hence the protocol hash — is
> untouched, and the one-click verifier accepts both source hashes.
> The ranking-hash value is NumPy-version sensitive at the ~1e-6 relative
> level: under other NumPy versions the JSON bytes (hence the hash) differ
> slightly, while all rank statistics reproduce exactly (verified on
> NumPy 2.2.5: identical Spearman values to all printed digits,
> `all_gates_pass: true`).

### Headline numbers (should match `results/v3.0.2/summary.json`)

- 80/80 endpoint-valid candidates; selected `v01_m_0.150`
- Predicted relative improvement **20.557%**; measured **20.32–20.55%** at
  σ ∈ {0.03, 0.06, 0.12, 0.24} rad/µs
- Prediction relative error **≤ 0.96%** (0.015% at σ = 0.03)
- Spearman ρ ≥ 0.99986, pairwise concordance ≥ 0.9984 (3160 pairs),
  top-16 overlap = 1.0; selected candidate actual rank **1/80** at every σ

---

## 4. Reproduce v2.0.1 (Markovian dephasing — registered FAIL)

```bash
python pasqal_kz_task_ranking_prospective_v2_0_1.py
python pasqal_kz_task_ranking_prospective_v2_0_1.py \
    --evaluate --expected-hash 2c05a45f5d534f581c0491a5215534ae657f3eae26e7362ea436850d51d909c4
```

Expected: perfect ranking (Spearman 1.0, 1770 pairs), prediction error
≤ 1.03%, but relative improvement **0.48%**, failing the predeclared 1%
minimum → `all_gates_pass: false`,
`scientific_status: PROSPECTIVE_KZ_RANKING_AND_TASK_IMPROVEMENT_NOT_SUPPORTED`.

A standalone verifier/packager mirroring the v3 one also exists:

```bash
python pasqal_kz_v201_one_click.py
```

It verifies the commitment against the known v2.0.1 source hashes, runs the
held-out evaluation if needed, checks artifacts, and writes the result ZIP
plus certificate.

| Artifact | Expected SHA-256 |
|---|---|
| Protocol | `2c05a45f5d534f581c0491a5215534ae657f3eae26e7362ea436850d51d909c4` |
| Source as evaluated 2026-07-27 (Python 3.12 only) | `620f8c43655498bfb1be67c4d72e799539508222f2bb0e84b6d545191e18e821` |
| Source as shipped in this repo (Python 3.12 only) | `8442f0282845be197446299692af57ebd99a45cb5877674bc3d9abb79ebd518b` |
| Frozen ranking (reference run, NumPy 2.0.2) | `5497773587b0b04626d49f6ccbc9f401a0e28bbb042f74deab24912649a5272b` |

> The v2.0.1 source hash exists in several legitimate flavors because the
> hash *definition* was repaired once on 2026-07-27 (notebook-global →
> stable inventory; see section 5). The shipped script carries the frozen
> protocol byte-identical; its stable-inventory hash under Python 3.12 is
> `8442f028…`. The one-click verifier accepts all known hashes. As with
> v3, the ranking hash is NumPy-version sensitive at the ~1e-6 relative
> level while all rank statistics reproduce exactly (verified on
> NumPy 2.2.5: Spearman = 1.0 at every γ, both improvement gates failing
> as registered).

---

## 5. Commitment history (full disclosure)

All protocol/source hashes ever issued, in order. No evaluation was run
under any superseded commitment; superseded entries were replaced *before*
any outcome was computed.

| # | Protocol hash (prefix) | UTC | Status |
|---|---|---|---|
| 1 | `1370a7ec…` (v2.0) | 2026-07-27 22:16 | Superseded — evaluation-script fix before any computation |
| 2 | `2c05a45f…` (v2.0.1) | 2026-07-27 22:28 | **Evaluated → FAIL** (source `620f8c43…`, Colab-stabilized) |
| 3 | `80080d0a…` (v3.0) | 2026-07-27 23:11 | Superseded — revision before any computation |
| 4 | `c9917d51…` (v3.0.2) | 2026-07-27 | **Evaluated → PASS (14/14)** (source `ae7dcfd7…`) |

Result ZIP certificates:

- v2.0.1: `3eb9bd524685a11112ac6af34b860ea5342e3b723724fa84f1f615e837f62380`
- v3.0.2: `fac3a2066cc4d93f57eafdf3b84b3c2fcda37816255bac7569537bc4e14b88aa`

---

## 6. What the scripts do (pipeline)

1. **Commit**: serialize the protocol, hash it, timestamp it, write the
   manifest. No Hamiltonian, K(z), candidate, or noisy outcome is computed.
2. **Candidate generation**: deterministic right-null singular vectors of
   the endpoint Jacobian at the reference control `z₀`, ± directions ×
   fixed tangent amplitudes; each candidate is nonlinearly corrected back
   onto the full-unitary endpoint fibre (infidelity ≤ 1e-11).
3. **Frozen prediction**: rank all valid candidates by the ideal-path
   predictor only (`q2` for v3, `j1` for v2). The complete ranking and all
   controls are written to disk *before* any noisy simulation.
4. **Held-out evaluation**: exact quasi-static averaging (Gauss–Hermite
   order 15; v3) or exact Lindblad channels (v2) at held-out noise strengths
   never used by the selector.
5. **Gates**: rank correlation, pairwise concordance, top-k recovery,
   beats-reference, minimum improvement, prediction sign and first-order
   error — all predeclared in the frozen manifest.

## 7. Scope and claim boundary

A PASS supports the prospective claim that an ideal-path-derived score ranks
finite-noise state-transfer losses **in this frozen exact two-atom,
six-segment model**. The held-out losses are simulated outcomes, not
measurements. This is **not** PASQAL production compilation, hardware/cloud
evidence, a universal path-cost principle, or physics beyond standard
Lindblad/quantum mechanics.

## 8. Reference

Paper (archived, DOI):

- *Same Ideal Gate, Predictably Different Noise in Rydberg Control*,
  Zenodo, published 2026-07-27:
  https://zenodo.org/records/21629515

The v1 path-response construction (CW/CCW/ALT lifts, K_z first-order closure
to 1.1%) is described in the accompanying paper and reproduced by
`path1.41.py`:

- Immutable source (pinned commit `a67fe1b885f6`):
  https://github.com/papasop/quantum/blob/a67fe1b885f6d70ceb391057b35a122359d64dd5/path1.41.py
- SHA-256 of the source file at that revision:
  `97956e3c3354b0ad16a85c83368fcc4355ca18a8f6fd087133a69cb175975b21`

### Note on the one-click packager

`pasqal_kqs_v302_one_click.py` and `pasqal_kz_v201_one_click.py` are
standalone verifier/packagers: each imports the frozen protocol machinery
from its main script (no Colab dependency), re-checks the commitment, runs
the held-out evaluation if needed, and writes the result ZIP plus
certificate. Run them after stage 1 has produced the manifest directory,
from the folder containing both `.py` files of the same version.
