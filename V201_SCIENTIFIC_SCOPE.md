# v2.0.1 Scientific Scope

The v2.0.1 protocol is intentionally preserved as a frozen expected negative.
The strict verifier added later does not change its scientific protocol,
candidate family, manifest, or committed results.

For endpoint-equivalent candidates with `J(0)=0`, weak Markovian dephasing gives

```text
J(z, gamma) = j1(z) gamma + O(gamma^2).
```

Therefore, for sufficiently small `gamma`, close agreement between ordering by
`j1` and finite-noise ordering is a perturbative expectation rather than a
surprise by itself.

The main information in v2.0.1 is narrower:

- `j1` varies across a fixed endpoint-equivalent control family.
- The best candidate in the frozen family improves the task loss by only about
  0.48%.
- That improvement does not reach the predeclared practical-effect gates, so
  the protocol is an informative negative result.
