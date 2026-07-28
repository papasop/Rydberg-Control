# Scientific Hardening Roadmap

This repository contains frozen v2.0.1/v3.0.2 reproduction artifacts. The items
below are the required hardening steps for the next protocol version rather
than silent edits to those archived scripts.

## Layer 1: Immediate Credibility Repairs

The next evaluator version should implement all of the following before any
held-out noisy loss is computed:

- Use real file-byte SHA-256 for source commitments.
- Put `C6`, segment duration, atom spacing, Hilbert/control dimensions,
  Jacobian finite-difference step, rank cut, endpoint tolerances, and stability
  thresholds directly in `PROTOCOL`.
- Instantiate the physical model exclusively from the frozen `PROTOCOL`.
- Record Python implementation/version, NumPy, SciPy, platform, and
  BLAS/LAPACK configuration in every manifest.
- Canonicalize the endpoint nullspace basis, or generate candidates from
  subspace-projection invariants rather than basis-vector identities.
- Fix recovery-manifest path handling and make one-click runs idempotent.
- Use relative pairwise tie tolerances and report comparable-pair fractions.
- Return real CLI exit codes via `raise SystemExit(main())`.
- Remove v3 quasi-static dead code inherited from the Lindblad evaluator and
  repair stale naming.
- Commit the frozen protocol manifest and frozen ranking certificate to Git
  before any held-out computation, using an external Git commit as the witness.

The current `audit_repository.py` script provides repository-level checks for
real file-byte hashes, environment reporting, protocol-content hashes, verdicts,
and comparable-pair fractions without mutating frozen artifacts.

## Layer 2: More Falsifiable Scientific Tests

Priority order for the next scientific extension:

1. Scan detuning noise scale `sigma` until ranking visibly breaks and report
   the empirical breakdown scale `sigma*`.
2. Freeze on a new candidate family or new reference control, then extrapolate
   to held-out losses.
3. Add time-dependent, correlated, or non-Gaussian detuning noise.
4. Re-evaluate after PASQAL-style compilation, smoothing, bandwidth limits, and
   slew-rate constraints.
5. Only then consider relaxing endpoint equivalence, because doing so changes
   the core fixed-unitary-fibre question.
