# Prospective Noise-Robust Control within a Fixed-Unitary Fibre
### Reproduction Package

Can a locally computed, task-relative susceptibility select a more
noise-robust control before any held-out finite-noise loss is evaluated, among
controls that are numerically identical at the complete ideal-unitary endpoint?
This repository contains two programmatically frozen prospective protocols
that answer this question in a frozen exact two-atom Rydberg model:

- **v3.0.2 (quasi-static detuning) — PASS**: the frozen `q2` ranking selects
  `v01_m_0.150`, with 20.6% lower leading susceptibility and 20.3%–20.6%
  lower held-out simulated loss across σ = 0.03–0.24 rad/µs (prediction error
  ≤ 0.96%, Spearman ≥ 0.99986, actual rank 1/80).
- **v2.0.1 (Markovian dephasing) — expected negative**: ranking succeeds
  (Spearman = 1.0), but the ≈0.48% improvement fails the predeclared
  practical-improvement gates.

The protocols were frozen inside the computational workflow. They were not
externally timestamped or certified by a third party. These are exact-model
simulated outcomes, not PASQAL production compilation, cloud execution,
physical-QPU measurements, a universal path cost, or evidence beyond standard
quantum mechanics.

## Conceptual provenance: a path-dependent realization layer

This repository was motivated by a broader structural idea developed in the
author's work on information time, Principle R, and the K=1 framework:
physical change may possess a realization-cost layer that is not determined
by the endpoint alone. In that framework, a path-dependent cost is written
schematically as

\[
E[\gamma]=\int_\gamma F(\gamma,\dot{\gamma})\,d\lambda .
\]

The present quantum-control study does not assume or test that framework.
It investigates a finite-dimensional operational analogue. Controls can have
the same complete ideal-unitary endpoint while following different
time-dependent Hamiltonian trajectories. Under a specified task and noise
model, those trajectories can therefore have different local susceptibilities
and different finite-noise losses.

The correspondence is structural rather than deductive:

| General cost-layer idea | Operational object in this repository |
|---|---|
| Endpoint equivalence does not determine realization cost | Equal complete ideal unitary does not determine finite-noise task loss |
| Cost depends on the executed path | `j1(z)` and `q2(z)` depend on the control trajectory and declared noise model |
| A limiting or ordering statement need not imply practical realization | Accurate ranking need not pass a predeclared utility threshold |
| Structural claims require falsifiable gates | v2 is an expected negative; v3 is a positive under separately declared gates |

For the quasi-static protocol, `q2(z)` is evaluated locally from the
predeclared probes `xi = {-h,0,+h}`. It is used to freeze the candidate
ranking before any held-out finite-`sigma` Gaussian-averaged loss is
evaluated. For sufficiently weak noise,

\[
\overline J(z,\sigma)
=J(z,0)+q_2(z)\sigma^2+O(\sigma^4).
\]

Because the endpoint-equivalent candidates share the same `J(z,0)` within
the declared numerical tolerance, `q2(z)` determines their leading
weak-noise ordering. The substantive numerical result is the
candidate-dependent susceptibility reduction and the finite declared window
over which the selected advantage persists.

The endpoint-equivalent controls form a locally resolved family whose endpoint
Jacobian has rank 8 and right-nullity 10 in the declared 18-dimensional
control parameterisation. This local Jacobian statement should not be read as
a global claim that the entire endpoint fibre is everywhere a smooth
ten-dimensional manifold.

These results are not evidence for a universal information-time functional,
Principle R, or the K=1 framework. They provide a task- and noise-relative
quantum-control realization of the more general distinction between endpoint
description and path-dependent implementation.

| Protocol | Noise model | Frozen predictor | Verdict |
|---|---|---|---|
| v2.0.1 (`2c05a45f…`) | Weak local Markovian dephasing | First-order task slope `j1(z)` at `gamma = 0` | **Expected negative** — ranking succeeded (Spearman 1.0), but the predicted 0.484% and held-out 0.482% improvements failed the predeclared effect-size gates |
| v3.0.2 (`c9917d51…`) | Zero-mean common quasi-static detuning | Local variance susceptibility `q2(z) = 0.5 d²J/dxi²` evaluated from the predeclared probes `xi = {-h,0,+h}` | **PASS** — predicted improvement 20.557%; held-out simulated improvement 20.319–20.554% |

For v3, the selector uses the local probes `xi = {-h,0,+h}` but does not use
any held-out finite-`sigma` Gaussian-averaged loss. The full ranking is written
to a certificate before those held-out losses are evaluated.

## One-command external reproduction

For a fresh clone, install the locked direct dependencies and run the strict
wrapper:

```bash
python -m pip install -r requirements-lock-python312.txt
python reproduce.py --protocol all --strict-environment
```

This command verifies the checked-out Git commit reported in
`environment.json` and printed by `--preflight`. It performs fresh two-stage
v2.0.1/v3.0.2 reproduction, then runs `verify_v201_strict_v1.py`,
`verify_v302_strict_v1.py`, `audit_repository.py`, and the tamper-test suite.
The overall status is `REPRODUCED_EXPECTED_RESULTS` only if all of those checks
pass. v2.0.1 is an expected scientific negative
(`REPRODUCED_EXPECTED_NEGATIVE`); v3.0.2 is an expected scientific positive
(`REPRODUCED_EXPECTED_PASS`).

Shell and Windows entry points are also provided; pass strict mode explicitly:

```bash
./reproduce.sh --strict-environment
pwsh ./reproduce.ps1 --strict-environment
```

Protocol-specific diagnostic runs are available with `--protocol v2` or
`--protocol v3`. Each run writes a unique, never-overwritten directory under
`external_runs/YYYYMMDDTHHMMSSZ_<short-id>/` containing environment metadata,
two-stage commitment/evaluation outputs, wrapper verdicts, a full log,
`reproduction_summary.json`, and real file-byte checksums.

Use CPython 3.12 for strict external reproduction. Non-3.12 runs are allowed
only for local diagnostics and warn that strict source/ranking byte identity is
not guaranteed. The wrapper reports strict byte identity separately from
numerical reproduction and scientific status.

The wrapper deliberately does **not** call the historical `--one-click` paths.
For each protocol it runs a commitment subprocess, reads the actual
`prospective_protocol.json`, then runs held-out evaluation with that manifest
and independently classifies the result. The internal ordering barrier is a
programmatic workflow barrier, not external preregistration.

The legacy `pasqal_kqs_v302_one_click.py` and `pasqal_kz_v201_one_click.py`
entry points are compatibility shims that delegate to the strict verifiers.

Docker reproduction:

```bash
docker build -t fixed-unitary-noise-robust-control .
docker run --rm -v "$PWD/external_runs:/app/external_runs" fixed-unitary-noise-robust-control
```

Docker is the recommended route when a local CPython 3.12 environment is not
already available.

No Pulser, Qiskit, PASQAL SDK, GPU, or Jupyter runtime is required. See
`KNOWN_LIMITATIONS.md` for the remaining historical limitations and why the new
wrapper documents rather than rewrites them.

The v2.0.1 failure is reported as part of the frozen evaluation trail:
the same predictor architecture yields a real, falsifiable negative under one
noise model and a positive under another.

---

## 1. Repository contents

```
├── reproduce.py / reproduce.sh / reproduce.ps1   # one-command strict external reproduction
├── environment-reference.json                 # expected reference environment record
├── requirements-lock-python312.txt            # locked deps for strict reproduction
├── Dockerfile                                 # container reproduction
├── pasqal_kz_quasistatic_ranking_v3_0_2.py    # v3.0.2 main script
├── verify_v302_strict_v1.py                   # v3.0.2 strict verifier
├── pasqal_kz_task_ranking_prospective_v2_0_1.py  # v2.0.1 main script (Markovian dephasing)
├── verify_v201_strict_v1.py                   # v2.0.1 strict verifier
├── pasqal_kqs_v302_one_click.py               # legacy shim -> strict verifier
├── pasqal_kz_v201_one_click.py                # legacy shim -> strict verifier
├── audit_repository.py                        # repository-level audit
├── manifests/                                 # frozen protocols (2c05a45f…, c9917d51…)
├── results/                                   # independent CPython 3.9.6 reruns
├── external_runs/                             # never-overwritten reproduction records
├── REFERENCE_RUNS.md                          # reference vs public-rerun hash record
├── ARTIFACTS.sha256                           # repository file-byte checksums
├── STRICT_AUDIT_201_302.md                    # strict audit specification
├── SCIENTIFIC_HARDENING.md                    # next-version hardening steps
├── CORRIGENDA.md / KNOWN_LIMITATIONS.md / CITATION.cff
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

## 4. External verification record

Independent clean-clone runs of the one-command workflow (`external_runs/`)
have reported:

- `REPRODUCED_EXPECTED_RESULTS` (overall)
- v2.0.1: `REPRODUCED_EXPECTED_NEGATIVE`; v3.0.2:
  `REPRODUCED_EXPECTED_PASS`
- `STRICT_AUDIT_PASS` for both strict verifiers and the repository audit
- `TAMPER_TESTS_PASS` for the adversarial tamper suite

"Strict verifier" denotes an independent code path within this repository,
not an independent research team. These mechanisms establish reproducibility,
internal consistency, and tamper sensitivity; they do not provide an external
timestamp or third-party preregistration.

---

## 5. Reproduce v3.0.2 (quasi-static detuning — PASS)

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
python verify_v302_strict_v1.py
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

The older `pasqal_kqs_v302_one_click.py` entry point is now only a legacy
compatibility shim that delegates to `verify_v302_strict_v1.py`. Historical
source hashes are records, not a whitelist for current PASS decisions.

---

## 6. Reproduce v2.0.1 (Markovian dephasing — expected negative)

```bash
python pasqal_kz_task_ranking_prospective_v2_0_1.py
python pasqal_kz_task_ranking_prospective_v2_0_1.py \
    --evaluate --expected-hash 2c05a45f5d534f581c0491a5215534ae657f3eae26e7362ea436850d51d909c4
```

Expected: perfect ranking (Spearman 1.0, 1770 pairs), prediction error
≤ 1.03%, but relative improvement **0.48%**, failing the predeclared 1%
minimum → `all_gates_pass: false`,
`scientific_status: PROSPECTIVE_KZ_RANKING_AND_TASK_IMPROVEMENT_NOT_SUPPORTED`.

A strict standalone verifier/packager also exists:

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
> stable inventory; see section 7). The shipped script carries the frozen
> protocol byte-identical; its stable-inventory hash under Python 3.12 is
> `8442f028…`. These values are retained as historical records only; the
> strict verifier does not accept a source-hash whitelist for PASS. As with
> v3, the ranking hash is NumPy-version sensitive at the ~1e-6 relative
> level while all rank statistics reproduce exactly (verified on
> NumPy 2.2.5: Spearman = 1.0 at every γ, both improvement gates failing as
> recorded under the frozen protocol).

---

## 7. Commitment history (full disclosure)

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

## 8. What the scripts do (pipeline)

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

## 9. Scope and claim boundary

A PASS supports the prospective claim that a task-relative locally evaluated
score ranks finite-noise state-transfer losses **in this frozen exact two-atom,
six-segment model**. The held-out losses are simulated outcomes, not
measurements. This is **not** PASQAL production compilation, hardware/cloud
evidence, a universal path-cost principle, or physics beyond standard
Lindblad/quantum mechanics.

## 10. Reference

### Archived computational record

The current computational record is archived under the title:

- *Prospective Noise-Robust Control on a Fixed-Unitary Fibre*,
  Zenodo, 2026-07-28:
  https://doi.org/10.5281/zenodo.21638025

The Zenodo record is archived under the earlier preposition variant ("on");
the repository title uses the current manuscript wording ("within").

This DOI identifies the archived computational record for the current
fixed-unitary fibre reproduction package. It should still be read with the
scope boundary above: exact local simulation, not PASQAL production
compilation, cloud execution, or hardware evidence.

The companion manuscript reports the original CPython 3.12 reference
evaluation; this repository hosts the protocols, hashes, independent reruns,
and verification machinery. See `REFERENCE_RUNS.md` for the exact
relationship.

The v1 path-response construction (CW/CCW/ALT lifts, K_z first-order closure
to 1.1%) is described in the accompanying paper and reproduced by
`path1.41.py`:

- Immutable source (pinned commit `a67fe1b885f6`):
  https://github.com/papasop/quantum/blob/a67fe1b885f6d70ceb391057b35a122359d64dd5/path1.41.py
- SHA-256 of the source file at that revision:
  `97956e3c3354b0ad16a85c83368fcc4355ca18a8f6fd087133a69cb175975b21`

### Note on the one-click packager

`pasqal_kqs_v302_one_click.py` and `pasqal_kz_v201_one_click.py` are
legacy compatibility shims. Use `verify_v302_strict_v1.py` and
`verify_v201_strict_v1.py` for current external verification and packaging.
The strict verifiers run fresh two-stage reproductions in unique directories,
record real file-byte hashes of the main script and verifier, verify summary
and ranking-certificate consistency, classify the expected scientific outcome,
and stage self-contained bundles.
