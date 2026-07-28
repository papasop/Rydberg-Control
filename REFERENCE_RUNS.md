# Reference and Reproduction Runs

This file distinguishes the original manuscript-level reference evaluation
from independently regenerated public artifacts.

## Original CPython 3.12 Reference Evaluation

Status: internally frozen computational workflow; not externally timestamped.
The original CPython 3.12 byte-level output directories are not currently
included in this repository. Their reported hashes and numerical summaries are
documented from the original run.

### v2.0.1

- Protocol-content SHA-256:
  `2c05a45f5d534f581c0491a5215534ae657f3eae26e7362ea436850d51d909c4`
- Evaluated source/source-logic SHA-256:
  `620f8c43655498bfb1be67c4d72e799539508222f2bb0e84b6d545191e18e821`
- Reference ranking SHA-256:
  `5497773587b0b04626d49f6ccbc9f401a0e28bbb042f74deab24912649a5272b`
- Scientific verdict: FAIL because effect-size gates failed.

### v3.0.2

- Protocol-content SHA-256:
  `c9917d5119b520fa17e1e56f1d903403b3e2d963d5a24e32e3945fbd253ba39e`
- Evaluated source-logic SHA-256:
  `ae7dcfd733568901aa526ad2c2ad4e89a4da1f3378edcfe5b03035de8d026843`
- Reference ranking SHA-256:
  `610d54f7c73ef9f5d0b8b482001e4e450ace49926a0bb9ef2e7e69f801ccd947`
- Selected control: `v01_m_0.150`
- Scientific verdict: PASS.

## Public CPython 3.9.6 Rerun

Environment:

- CPython 3.9.6
- NumPy 2.0.2
- SciPy 1.13.1

### v2.0.1

- Public ranking SHA-256:
  `56e56671c4740a5f3165400ad4b0b311e4e5da5e10c972be7f26cb90610653e7`
- Selected control: `v00_m_0.030`
- Scientific verdict: FAIL because effect-size gates failed.

### v3.0.2

- Public ranking SHA-256:
  `a3f3b5a94999a78ff0442dc47e3911b92c6976426bc149a103e987aa7f47f3b9`
- Selected control: `v01_m_0.150`
- Scientific verdict: PASS.

## Interpretation

The public reruns reproduce the scientific selection and verdicts but do not
replace the byte-level identity of the original reference evaluation.
Protocol-content hashes are stable; source and ranking hashes can be
interpreter- or numerical-environment-sensitive.
