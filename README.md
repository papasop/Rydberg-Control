# K(z)-Guided Prospective Task-Loss Ranking — Reproduction Package

This repository contains two programmatically frozen prospective protocols for
testing whether a task-relative local susceptibility can rank held-out
finite-noise task losses among controls that are numerically equivalent at the
complete ideal-unitary endpoint.

The protocols were frozen inside the computational workflow. They were not
externally timestamped or certified by a third party.

| Protocol | Noise model | Frozen predictor | Verdict |
|---|---|---|---|
| v2.0.1 (`2c05a45f…`) | Weak local Markovian dephasing | First-order task slope `j1(z)` at `gamma = 0` | **FAIL** — ranking succeeded, but the predicted 0.484% and held-out simulated 0.482% improvements failed the predeclared effect-size gates |
| v3.0.2 (`c9917d51…`) | Zero-mean common quasi-static detuning | Local variance susceptibility `q2(z) = 0.5 d²J/dxi²` evaluated from the predeclared probes `xi = {-h,0,+h}` | **PASS** — predicted improvement 20.557%; held-out simulated improvement 20.319–20.554% |

For v3, the selector uses the local probes `xi = {-h,0,+h}` but does not use
any held-out finite-`sigma` Gaussian-averaged loss. The full ranking is written
to a certificate before those held-out losses are evaluated.

These are exact-model simulated outcomes. They are not PASQAL production
compilation, cloud execution, physical-QPU measurements, a universal path cost,
or evidence beyond standard quantum mechanics.

## One-command external reproduction

For a fresh clone, install the direct dependencies and run the wrapper:

```bash
python -m pip install -r requirements-lock-python312.txt
python reproduce.py --preflight
python reproduce.py
```

Shell and Windows entry points are also provided:

```bash
./reproduce.sh
pwsh ./reproduce.ps1
```

The default command is equivalent to `python reproduce.py --protocol all`.
Protocol-specific runs are available with `--protocol v2` or `--protocol v3`.
Each run writes a unique, never-overwritten directory under
`external_runs/YYYYMMDDTHHMMSSZ_<short-id>/` containing environment metadata,
two-stage commitment/evaluation outputs, wrapper verdicts, a full log,
`reproduction_summary.json`, and real file-byte checksums.

Use CPython 3.12 for strict external reproduction:

```bash
python reproduce.py --protocol all --strict-environment
```

Non-3.12 runs are allowed by default but warn that strict source/ranking byte
identity is not guaranteed. The wrapper reports strict byte identity separately
from numerical reproduction and scientific status.

The wrapper deliberately does **not** call the historical `--one-click` paths.
For each protocol it runs a commitment subprocess, reads the actual
`prospective_protocol.json`, then runs held-out evaluation with that manifest
and independently classifies the result. The v2.0.1 outcome is an expected
predeclared negative:
`REPRODUCED_EXPECTED_NEGATIVE`, not a reproduction error. The v3.0.2 outcome is
`REPRODUCED_EXPECTED_PASS`.

Docker reproduction:

```bash
docker build -t fixed-unitary-noise-robust-control .
docker run --rm -v "$PWD/external_runs:/app/external_runs" fixed-unitary-noise-robust-control
```

No Pulser, Qiskit, PASQAL SDK, GPU, or Jupyter runtime is required. See
`KNOWN_LIMITATIONS.md` for the remaining historical limitations and why the new
wrapper documents rather than rewrites them.

The v2.0.1 failure is reported as part of the frozen evaluation trail:
the same predictor architecture yields a real, falsifiable negative under one
noise model and a positive under another.

---

## 1. Repository contents

```
├── pasqal_kz_quasistatic_ranking_v3_0_2.py   # v3.0.2 main script (quasi-static detuning)
├── pasqal_kqs_v302_one_click.py              # v3.0.2 standalone verifier/packager
├── pasqal_kz_task_ranking_prospective_v2_0_1.py  # v2.0.1 main script (Markovian dephasing)
├── pasqal_kz_v201_one_click.py               # v2.0.1 standalone verifier/packager
├── CORRIGENDA.md
├── CITATION.cff
├── ARTIFACTS.sha256
├── REFERENCE_RUNS.md
├── SCIENTIFIC_HARDENING.md
├── audit_repository.py
├── manifests/
│   ├── v2.0.1/prospective_protocol.json      # frozen protocol, protocol_sha256 = 2c05a45f…
│   └── v3.0.2/prospective_protocol.json      # frozen protocol, protocol_sha256 = c9917d51…
├── results/
│   ├── v2.0.1/summary.json                   # independent CPython 3.9.6 rerun (FAIL)
│   └── v3.0.2/summary.json                   # independent CPython 3.9.6 rerun (PASS)
├── requirements.txt
└── README.md
```

> The historical v2 "Colab-stable recommit" notebook cell (which redefined
> `source_hash`, re-committed, and evaluated in one cell) is **not** shipped:
> it documents the one-time 2026-07-27 hash-repair recorded in the commitment
> history, and its stable-hash logic now lives in the v2.0.1 main script
> itself. Publishing it would invite confusion about the frozen workflow trail.

Each main script is self-contained and implements the full two-stage
workflow: **commit** (freeze protocol, compute nothing) → **evaluate**
(generate candidates, freeze predicted ranking, only then compute held-out
noisy losses).

---

## 2. Environment

- CPython **3.12.x**; the original development environment used Python 3.12.13.
- Direct runtime dependencies are listed in `requirements.txt`.

```
numpy==2.0.2
scipy>=1.11,<2.0
```

The scientific protocol hash identifies canonical protocol content. Source
hashes and ranking-certificate hashes are separate artifacts. Some historical
source-hash implementations and ranking JSON byte hashes are interpreter- or
NumPy-version sensitive; therefore scientific reproduction should report both
the strict byte-hash checks and the numerical gate results.

Run the repository-level audit with:

```bash
python3 audit_repository.py
```

The audit computes real file-byte SHA-256 values, records Python/NumPy/SciPy
and BLAS/LAPACK configuration, recomputes protocol-content hashes, verifies the
public rerun verdicts, and reports comparable-pair fractions. See
`SCIENTIFIC_HARDENING.md` for the required next-version hardening steps and
additional falsification tests.

---

## 3. Data provenance

The manuscript reports the original CPython 3.12 evaluation and its reference
hashes. The committed artifacts under `manifests/` and `results/` were
independently regenerated on CPython 3.9.6 with NumPy 2.0.2 from the published
scripts. They reproduce the protocol-content hashes, selected controls,
scientific verdicts, gate outcomes, and reported effect sizes. Some
floating-point values, source identities, and ranking-certificate byte hashes
differ from the original CPython 3.12 run.

The public rerun artifacts must therefore not be interpreted as the original
byte-level reference artifacts. If the original CPython 3.12 files are later
recovered, they will be archived under a separate immutable directory rather
than replacing the public reruns. See `REFERENCE_RUNS.md` for the side-by-side
reference and public-rerun hash record.

---

## 4. Reproduce v3.0.2 (quasi-static detuning — PASS)

Two-stage (recommended — mirrors the original programmatically frozen workflow):

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
> untouched. The source hashes above are historical/reference identities,
> separate from protocol-content and numerical-verdict reproduction.
> The ranking-hash value is NumPy-version sensitive at the ~1e-6 relative
> level: under other NumPy versions the JSON bytes (hence the hash) differ
> slightly, while all rank statistics reproduce exactly (verified on
> NumPy 2.2.5: identical Spearman values to all printed digits,
> `all_gates_pass: true`).

### Reference CPython 3.12 headline numbers reported in the manuscript

The numbers below are from the original CPython 3.12 reference evaluation. The
committed `results/v3.0.2/summary.json` is an independent CPython 3.9.6 rerun.
It reproduces the selected control, scientific verdict, gate outcomes, and
effect size, but is not byte-identical to the reference output.

- 80/80 endpoint-valid candidates; selected `v01_m_0.150`
- Predicted relative improvement **20.557%**; held-out simulated improvement
  **20.32–20.55%** at
  σ ∈ {0.03, 0.06, 0.12, 0.24} rad/µs
- Prediction relative error **≤ 0.96%** (0.015% at σ = 0.03)
- Spearman ρ ≥ 0.99986, pairwise concordance ≥ 0.9984 (3160 pairs),
  top-16 overlap = 1.0; selected candidate actual rank **1/80** at every σ

---

## 5. Reproduce v2.0.1 (Markovian dephasing — predeclared FAIL)

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
python verify_v201_strict_v1.py
```

It performs a fresh two-stage external reproduction in a unique
`external_runs/v201/YYYYMMDDTHHMMSSZ_<short-id>/` directory, verifies real
file-byte source identity within that fresh run, recomputes the ranking
certificate byte hash, classifies the expected negative result, stages a
self-contained bundle, and writes a ZIP plus certificate. The verifier is
self-identifying by its own file-byte SHA-256; this is not third-party
timestamping or certification.

The older `pasqal_kz_v201_one_click.py` entry point is now only a legacy
compatibility shim that delegates to `verify_v201_strict_v1.py`. Historical
source hashes are documented in `REFERENCE_RUNS.md` and
`historical_source_identities.json`; they are not used as a whitelist for
current PASS decisions.

| Artifact | Expected SHA-256 |
|---|---|
| Protocol | `2c05a45f5d534f581c0491a5215534ae657f3eae26e7362ea436850d51d909c4` |
| Source as evaluated 2026-07-27 (Python 3.12 only) | `620f8c43655498bfb1be67c4d72e799539508222f2bb0e84b6d545191e18e821` |
| Source as shipped in this repo (Python 3.12 only) | `8442f0282845be197446299692af57ebd99a45cb5877674bc3d9abb79ebd518b` |
| Frozen ranking (reference run, NumPy 2.0.2) | `5497773587b0b04626d49f6ccbc9f401a0e28bbb042f74deab24912649a5272b` |

> The v2.0.1 source hash exists in several legitimate flavors because the
> hash *definition* was repaired once on 2026-07-27 (notebook-global →
> stable inventory; see section 6). The shipped script carries the frozen
> protocol byte-identical; its stable-inventory hash under Python 3.12 is
> `8442f028…`. These values are retained as historical records only; the
> strict verifier does not accept a source-hash whitelist for PASS. As with
> v3, the ranking hash is NumPy-version sensitive at the ~1e-6 relative
> level while all rank statistics reproduce exactly (verified on
> NumPy 2.2.5: Spearman = 1.0 at every γ, both improvement gates failing as
> recorded under the frozen protocol).

---

## 6. Commitment history (full disclosure)

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

## 7. What the scripts do (pipeline)

1. **Commit**: serialize the protocol, hash it, timestamp it, write the
   manifest. No Hamiltonian, K(z), candidate, or noisy outcome is computed.
2. **Candidate generation**: deterministic right-null singular vectors of
   the endpoint Jacobian at the reference control `z₀`, ± directions ×
   fixed tangent amplitudes; each candidate is nonlinearly corrected back
   onto the full-unitary endpoint fibre (infidelity ≤ 1e-11).
3. **Frozen prediction**
   - v2 ranks endpoint-valid candidates by the zero-noise Markovian task
     derivative `j1(z)`;
   - v3 ranks endpoint-valid candidates by `q2(z)`, evaluated from the
     predeclared infinitesimal probes `xi = {-h,0,+h}`.

   The complete candidate ranking and controls are written to disk before any
   held-out finite-noise loss is evaluated.
4. **Held-out evaluation**: exact quasi-static averaging (Gauss–Hermite
   order 15; v3) or exact Lindblad channels (v2) at held-out noise strengths
   never used by the selector.
5. **Gates**: rank correlation, pairwise concordance, top-k recovery,
   beats-reference, minimum improvement, prediction sign and first-order
   error — all predeclared in the frozen manifest.

## 8. Scope and claim boundary

A PASS supports the prospective claim that a task-relative locally evaluated
score ranks finite-noise state-transfer losses **in this frozen exact two-atom,
six-segment model**. The held-out losses are simulated outcomes, not
measurements. This is **not** PASQAL production compilation, hardware/cloud
evidence, a universal path-cost principle, or physics beyond standard
Lindblad/quantum mechanics.

## 9. Reference

### Preliminary computational record

An earlier computational record was archived under the title:

- *Prospective Noise-Robust Control on a Fixed-Unitary Fibre*,
  Zenodo, 2026-07-27:
  https://doi.org/10.5281/zenodo.21634625

The current manuscript, *Prospective Noise-Robust Control within a
Fixed-Unitary Fibre*, narrows and strengthens that earlier motivation into a
task-relative prospective ranking and control-selection study. The earlier DOI
must not be interpreted as the DOI of the current manuscript.

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
