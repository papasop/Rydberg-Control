# Strict Audit of v2.0.1 and v3.0.2

This audit records issues found before further public posting. The archived
v2.0.1 and v3.0.2 scientific scripts, protocol manifests, and result artifacts
remain archival. Fixes that change scientific protocol semantics belong in new
protocol versions such as v2.1 or v3.1.

## Current Archival Status

- v2.0.1 remains an expected negative: ranking gates pass, practical-effect
  gates fail, and the reported improvement is about 0.48%.
- v3.0.2 remains an expected pass inside the frozen exact quasi-static-detuning
  model, with about 20% model-internal improvement over the reference control.
- The old one-click files are now legacy shims. Current verification is through
  `verify_v201_strict_v1.py` and `verify_v302_strict_v1.py`.

## Findings

- The historical main scripts record key constants in `PROTOCOL`, but the model
  is not fully instantiated from a parsed protocol object. `C6`, basis
  construction, atom symmetry, model class defaults, and some naming choices
  still live in code. This is archival for v2.0.1/v3.0.2; v2.1/v3.1 should make
  protocol-to-model instantiation explicit.
- Historical `source_hash` values are source-logic/code-object records, not a
  universal file-byte identity scheme. The strict external verifiers use real
  SHA-256 file bytes for fresh freeze/evaluate pairing and report historical
  manifest source hashes only as records.
- Candidate generation still depends on a 10-dimensional SVD nullspace basis.
  The sign of singular vectors is handled historically, but general rotations
  within near-degenerate subspaces are not canonicalized. A future protocol
  should either canonicalize the subspace basis or freeze candidate control
  files and their hashes before held-out evaluation.
- On the local CPython 3.9.6 environment used for this audit, v3.0.2 fresh
  evaluation spent several minutes in candidate correction
  (`generate_candidates -> least_squares -> expm`) before interruption. The
  strict verifiers now include per-subprocess timeouts; future protocols should
  make runtime expectations explicit and consider freezing the prospective
  candidate controls as first-class pre-held-out artifacts.
- The strict verifiers now recompute ranking-certificate file SHA-256, compare
  it to `summary["ranking_certificate_sha256"]`, cross-check the selected
  candidate, verify CSV row counts, reject non-finite numerics, and forbid
  unverified cache packaging.
- v2.0.1 is classified as `REPRODUCED_EXPECTED_NEGATIVE` with shell exit code 0
  when its expected negative result is reproduced. Endpoint failures, missing
  artifacts, source/ranking identity failures, schema errors, and unexpected
  scientific outcomes remain nonzero.
- Pairwise statistics still use the frozen absolute tie tolerance. Future
  protocols should use relative tie tolerances and report comparable-pair
  fractions directly in summary output.
- The exact two-atom model has atom-permutation symmetry and an effective
  `3+1` block structure. The observed endpoint rank 8 should not be described
  as representative of a general fully controllable two-qubit setting.
- v3.0.2 is a quasi-static unitary-noise path. Historical code and summary text
  retain inherited names such as `gamma_rows` and `maximum_first_order_relative_error`,
  and some prose still mentions Lindblad/quantum mechanics generically. These
  are archival wording issues; v3.1 should remove Markovian dead code and use
  quasi-static-specific names.
- The v3.0.2 result primarily validates the small-noise `sigma^2` Taylor window
  tested in the frozen protocol. Larger-noise scans, new candidate families,
  compiled controls, and hardware/cloud evaluations must be new protocols, not
  retroactive minor repairs.

## Release Gate Before Posting

- Clean-environment reproduction of both archival results through strict
  verifiers.
- Tamper tests for source bytes, manifest protocol content, ranking certificate,
  selected candidate, CSV row counts, and non-finite numerics.
- Manuscript wording that lowers the surprise level of Taylor-order ranking and
  separates model-internal evidence from hardware or universal claims.
- Any PASQAL-facing note should only claim task-relevant susceptibility
  differences on a fixed endpoint fibre and about 20% improvement in the
  declared exact model.

## Evidence Outside the Current Repository

The current repository contains the v2.0.1/v3.0.2 scripts, manifests, results,
strict verifiers, and repository audit code. It does not contain the following
evidence-chain files mentioned in broader PASQAL-facing discussions:

- `path1.41.py`
- equal-`A2` six-permutation scripts and outputs
- BB1 32-case Cloud EMU scripts, job IDs, and CSV outputs

Those files must be supplied and audited before public text relies on their
specific numerical claims. Until then, PASQAL-facing language should omit the
path-response, equal-`A2`, and BB1 Cloud EMU numbers or label them as
unreviewed exploratory context outside this repository.
