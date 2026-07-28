# Corrigenda and Frozen-Source Notes

The v2.0.1 and v3.0.2 evaluator scripts are retained as frozen computational
artifacts. Historical wording in their module docstrings or frozen protocol
metadata should be read subject to the following clarifications.

1. The protocols were programmatically frozen inside the computational
   workflow; they were not externally timestamped or registered with a third
   party.
2. The v3 predictor `q2(z)` is a task-relative local detuning susceptibility
   evaluated from the predeclared probes `xi = {-h,0,+h}`. It does not use
   held-out finite-`sigma` averaged losses, but it should not be described as
   being computed from the strictly unperturbed ideal trajectory alone.
3. Every reported task loss and improvement is simulated in the declared exact
   local model. "Measured" does not mean laboratory measurement.
4. `protocol_sha256` hashes canonical protocol content. It is distinct from a
   byte hash of the complete manifest file, a source hash, and a ranking
   certificate hash.
5. The frozen scripts are not modified to update this terminology because doing
   so would generate additional source-hash variants. Scientific logic changes,
   if any, should be released under a new version identifier.
