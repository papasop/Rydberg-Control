# Known Limitations

This repository is intended to make the frozen simulated protocols reproducible
and auditable. It does not turn the historical scripts into a newly hardened
protocol.

- Historical `source_hash` fields were based on a code-object inventory, not a
  complete file-byte hash. The new wrapper records real byte SHA-256 values for
  every external-run artifact.
- Some module constants and dataclass defaults in the historical scripts were
  not fully bound into the protocol manifest. The published manifest now records
  the main physical constants, but a future hardened protocol should instantiate
  the model entirely from the manifest.
- SVD nullspace bases are not canonical across all LAPACK implementations. This
  can affect candidate byte identities even when the subspace is numerically the
  same. A future version should canonicalize the basis or generate candidates
  from subspace-projection invariants.
- The ranking certificate is process-ordered before held-out evaluation, but it
  is not witnessed by a third-party timestamp. Use Git commit history and
  artifact mtimes as audit evidence, not as cryptographic external attestation.
- The v3 quasi-static-detuning result is local to the tested small-noise
  `sigma^2` expansion regime. Larger-noise scans are needed to locate where the
  ranking visibly breaks.
- The artifacts are exact-model simulations. They are not PASQAL production
  compilation, cloud execution, hardware/QPU measurements, bandwidth/slew-aware
  compiled controls, or production-control evidence.
- Historical one-click helpers remain for provenance, but the external
  reproduction entry point is `reproduce.py`. It avoids relying on the old
  one-click exit-code behavior and independently classifies v2 as the expected
  predeclared negative.
- The legacy v2 one-click entry point now delegates to
  `verify_v201_strict_v1.py`. Historical source identities are reported, not
  re-established, and are not a whitelist for current strict verification.
