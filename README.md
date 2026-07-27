# K(z)-Guided Prospective Task-Loss Ranking — Reproduction Package

Frozen, falsifiable evaluation of whether an ideal-path control descriptor can
rank finite-noise task losses, computed before any noisy outcome, for controls
that share the same complete ideal unitary.

Two pre-registered protocols are included:

| Protocol | Noise model | Predictor | Verdict |
| --- | --- | --- | --- |
| v2.0.1 (`2c05a45f...`) | Weak local Markovian dephasing | First-order slope `j1(z) = -Re Tr[rho_target G_z(rho_00)]`, `G_z = dE_z/dgamma` at `gamma = 0` | FAIL — ranking perfect, Spearman `1.0`, but task improvement `0.48%` < `1%` predeclared minimum |
| v3.0.2 (`c9917d51...`) | Zero-mean common quasi-static detuning offset `xi ~ N(0, sigma^2)` | Variance susceptibility `q2(z) = 1/2 d^2J/dxi^2` at `xi = 0` | PASS, `14/14` gates — predicted improvement `20.56%`, measured `20.3–20.6%`, prediction error <= `0.96%` |

The v2.0.1 failure is reported as registered. It is part of the evidence: the
same predictor architecture yields a real, falsifiable negative under one noise
model and a positive under another.

## 1. Repository Contents

```text
├── pasqal_kz_quasistatic_ranking_v3_0_2.py       # v3.0.2 main script, quasi-static detuning
├── pasqal_kqs_v302_one_click.py                  # v3.0.2 verification, evaluation, and result packaging
├── pasqal_kz_task_ranking_prospective_v2_0_1.py  # v2.0.1 main script, Markovian dephasing
├── manifests/
│   ├── v2.0.1/prospective_protocol.json          # frozen protocol, protocol_sha256 = 2c05a45f...
│   └── v3.0.2/prospective_protocol.json          # frozen protocol, protocol_sha256 = c9917d51...
├── results/
│   ├── v2.0.1/summary.json                       # reference outputs, FAIL
│   └── v3.0.2/summary.json                       # reference outputs, PASS
├── requirements.txt
└── README.md
```

Each main script is self-contained and implements the full two-stage workflow:
commit, freeze protocol and compute nothing; then evaluate, generate candidates,
freeze predicted ranking, and only then compute held-out noisy losses.

## 2. Environment

Python 3.12.x, developed on Python 3.12.13.

Install dependencies:

```bash
pip install -r requirements.txt
```

Expected dependency set:

```text
numpy==2.0.2
scipy>=1.11
```

**Python-version caveat.** The `source_sha256` commitment hashes a normalized
inventory of compiled bytecode, a deliberate defense against notebook-namespace
tampering. It therefore matches only under the same CPython version, `3.12.x`.
On other Python versions, the source-hash gate will fail even for a
byte-identical file. In that case, verify the protocol hash and the ranking
certificate hash instead. The scientific outputs are pure NumPy/SciPy numerics
and are version-insensitive to within floating-point reproducibility.

## 3. Reproduce v3.0.2: Quasi-Static Detuning, PASS

Two-stage execution is recommended because it mirrors the original
pre-registration.

Stage 1 freezes the protocol and computes no physics:

```bash
python pasqal_kz_quasistatic_ranking_v3_0_2.py
```

Expected:

```text
protocol_sha256 = c9917d5119b520fa17e1e56f1d903403b3e2d963d5a24e32e3945fbd253ba39e
writes pasqal_kz_commit_c9917d5119b5/prospective_protocol.json
```

Stage 2 performs the frozen held-out evaluation:

```bash
python pasqal_kz_quasistatic_ranking_v3_0_2.py \
    --evaluate \
    --expected-hash c9917d5119b520fa17e1e56f1d903403b3e2d963d5a24e32e3945fbd253ba39e
```

Or run both stages in one invocation:

```bash
python pasqal_kz_quasistatic_ranking_v3_0_2.py --one-click
```

The main evaluator's default output directory is
`pasqal_kz_eval_c9917d5119b5/`.

To verify the frozen v3.0.2 commitment, run evaluation, check artifacts, and
package the result ZIP plus certificate:

```bash
python pasqal_kqs_v302_one_click.py
```

Run in a clean, empty directory. The evaluator refuses to overwrite an existing
output directory. The packaging script writes:

Expected packaged-output directory:

```text
pasqal_kqs_v302_eval_c9917d5119b5/
├── predicted_ranking_frozen_before_heldout.json
├── candidate_ranking_results.csv
├── heldout_results.csv
├── candidate_predictor_audit.json
├── reference_control.csv
├── selected_control.csv
└── summary.json
```

Hashes to check:

| Artifact | Expected SHA-256 |
| --- | --- |
| Protocol | `c9917d5119b520fa17e1e56f1d903403b3e2d963d5a24e32e3945fbd253ba39e` |
| Source, Python 3.12 only | `ae7dcfd733568901aa526ad2c2ad4e89a4da1f3378edcfe5b03035de8d026843` |
| Frozen ranking | `610d54f7c73ef9f5d0b8b482001e4e450ace49926a0bb9ef2e7e69f801ccd947` |

Headline numbers, matching `results/v3.0.2/summary.json`:

- `80/80` endpoint-valid candidates; selected `v01_m_0.150`
- predicted relative improvement `20.557%`
- measured improvement `20.32–20.55%` at `sigma in {0.03, 0.06, 0.12, 0.24}` rad/µs
- prediction relative error <= `0.96%`, with `0.015%` at `sigma = 0.03`
- Spearman rho >= `0.99986`
- pairwise concordance >= `0.9984`, `3160` pairs
- top-16 overlap = `1.0`
- selected candidate actual rank `1/80` at every sigma

## 4. Reproduce v2.0.1: Markovian Dephasing, Registered FAIL

```bash
python pasqal_kz_task_ranking_prospective_v2_0_1.py

python pasqal_kz_task_ranking_prospective_v2_0_1.py \
    --evaluate \
    --expected-hash 2c05a45f5d534f581c0491a5215534ae657f3eae26e7362ea436850d51d909c4
```

Expected: perfect ranking, Spearman `1.0` over `1770` pairs, prediction error
<= `1.03%`, but relative improvement `0.48%`, failing the predeclared `1%`
minimum.

Expected verdict:

```text
all_gates_pass: false
scientific_status: PROSPECTIVE_KZ_RANKING_AND_TASK_IMPROVEMENT_NOT_SUPPORTED
```

Hashes to check:

| Artifact | Expected SHA-256 |
| --- | --- |
| Protocol | `2c05a45f5d534f581c0491a5215534ae657f3eae26e7362ea436850d51d909c4` |
| Source, Python 3.12 only | `620f8c43655498bfb1be67c4d72e799539508222f2bb0e84b6d545191e18e821` |
| Frozen ranking | `5497773587b0b04626d49f6ccbc9f401a0e28bbb042f74deab24912649a5272b` |

## 5. Commitment History

Full disclosure: all protocol and source hashes ever issued, in order. No
evaluation was run under any superseded commitment; superseded entries were
replaced before any outcome was computed.

| # | Protocol hash | UTC | Status |
| --- | --- | --- | --- |
| 1 | `1370a7ec...` v2.0 | 2026-07-27 22:16 | Superseded — evaluation-script fix before any computation |
| 2 | `2c05a45f...` v2.0.1 | 2026-07-27 22:28 | Evaluated -> FAIL, source `620f8c43...`, Colab-stabilized |
| 3 | `80080d0a...` v3.0 | 2026-07-27 23:11 | Superseded — revision before any computation |
| 4 | `c9917d51...` v3.0.2 | 2026-07-27 | Evaluated -> PASS, `14/14`, source `ae7dcfd7...` |

Result ZIP certificates:

| Version | SHA-256 |
| --- | --- |
| v2.0.1 | `3eb9bd524685a11112ac6af34b860ea5342e3b723724fa84f1f615e837f62380` |
| v3.0.2 | `fac3a2066cc4d93f57eafdf3b84b3c2fcda37816255bac7569537bc4e14b88aa` |

## 6. What the Scripts Do

The pipeline has five stages:

1. **Commit**: serialize the protocol, hash it, timestamp it, and write the
   manifest. No Hamiltonian, `K(z)`, candidate, or noisy outcome is computed.
2. **Candidate generation**: compute deterministic right-null singular vectors
   of the endpoint Jacobian at the reference control `z0`, use ± directions and
   fixed tangent amplitudes, and nonlinearly correct each candidate back onto the
   full-unitary endpoint fibre with infidelity <= `1e-11`.
3. **Frozen prediction**: rank all valid candidates by the ideal-path predictor
   only, `q2` for v3 and `j1` for v2. The complete ranking and all controls are
   written to disk before any noisy simulation.
4. **Held-out evaluation**: compute exact quasi-static averaging,
   Gauss-Hermite order 15 for v3, or exact Lindblad channels for v2, at held-out
   noise strengths never used by the selector.
5. **Gates**: apply predeclared rank correlation, pairwise concordance,
   top-k recovery, beats-reference, minimum improvement, prediction sign, and
   first-order error checks.

## 7. Scope and Claim Boundary

A PASS supports the prospective claim that an ideal-path-derived score ranks
finite-noise state-transfer losses in this frozen exact two-atom, six-segment
model. The held-out losses are simulated outcomes, not measurements.

This is not PASQAL production compilation, hardware/cloud evidence, a universal
path-cost principle, or physics beyond standard Lindblad/quantum mechanics.

## 8. Reference

The v1 path-response construction, including CW/CCW/ALT lifts and `K_z`
first-order closure to `1.1%`, is described in the accompanying paper and
reproduced by `path1.41.py`, commit `a67fe1b885f6`, SHA-256:

```text
97956e3c3354b0ad16a85c83368fcc4355ca18a8f6fd087133a69cb175975b21
```
