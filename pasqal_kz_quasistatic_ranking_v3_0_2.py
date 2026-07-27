#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K_qs(z)-GUIDED QUASI-STATIC DETUNING OPTIMIZATION v3.0.2

Two-stage, falsifiable local-model protocol.

Stage 1 (default): write and hash a frozen protocol.  No Hamiltonian,
K(z), candidate, or noisy-channel outcome is computed.

Stage 2:
    python pasqal_kz_quasistatic_ranking_v3_0_2.py \
        --evaluate --expected-hash <HASH_FROM_STAGE_1>

The evaluator:
  1. constructs a deterministic finite set of full-unitary-equivalent
     two-atom, six-segment Rydberg controls;
  2. ranks every valid candidate using only its zero-noise, ideal-path
     quasi-static variance susceptibility K_qs(z);
  3. freezes the complete predicted ranking and every control to disk;
  4. only then evaluates exact finite-noise quasi-static detuning task losses;
  5. tests rank correlation, pairwise ordering, top-k recovery, and whether
     the predicted winner improves on the reference.

The scalar task is state-transfer infidelity for input |00> relative to the
common ideal output U0|00>.  The noise model is a zero-mean common quasi-static
detuning offset.  This is an exact local model, not Pulser production
compilation, cloud execution, QPU evidence, or a universal robustness claim.

Dependencies: NumPy, SciPy.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import marshal
import platform
import sys
import types
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from scipy.linalg import expm, expm_frechet
from scipy.optimize import least_squares
from scipy.stats import kendalltau, spearmanr


SCRIPT_ID = "KQS-PROSPECTIVE-DETUNING-RANKING-v3.0.2"
C6 = 5_420_158.53  # rad um^6 / us
FLOOR = 1e-14


PROTOCOL: dict[str, Any] = {
    "script_id": SCRIPT_ID,
    "seed": 20260728,
    "scope": "exact local two-atom Rydberg model; no cloud, QPU, or measurement",
    "system": {
        "atoms": 2,
        "segments": 6,
        "segment_duration_us": 0.120,
        "spacing_um": 6.0,
        "control_dimension": 18,
    },
    "endpoint": {
        "equivalence": "complete ideal unitary up to global phase",
        "jacobian_fd": 0.001,
        "rank_relative_cut": 1e-6,
        "candidate_tangent_amplitudes": [0.030, 0.060, 0.100, 0.150],
        "candidate_directions":
            "plus/minus each deterministic right-null singular vector",
        "endpoint_infidelity_tol": 1e-11,
        "endpoint_residual_tol": 2e-8,
        "minimum_control_separation": 1e-5,
    },
    "noise": {
        "model": "zero-mean common quasi-static detuning offset",
        "offset_units": "rad/us",
        "predictor_step_rad_per_us": 0.002,
        "heldout_sigma_rad_per_us": [0.03, 0.06, 0.12, 0.24],
        "gauss_hermite_order": 15,
        "selection_uses_heldout_sigma_or_averaged_losses": False,
    },
    "task": {
        "input_state": "|00>",
        "ideal_target": "U0|00>",
        "loss":
            "Jbar(z,sigma)=E_xi[1-|<psi_target|U_z(xi)|00>|^2], "
            "xi~Normal(0,sigma^2)",
        "predictor":
            "q2(z)=0.5*d^2 J(z,xi)/dxi^2 at xi=0; "
            "for zero-mean quasi-static noise, E[J]=J0+q2*sigma^2+O(sigma^4)",
    },
    "ranking": {
        "population": "all endpoint-valid non-reference candidates",
        "rule":
            "ascending q2(z), with deterministic candidate_id tie-break",
        "frozen_artifact":
            "predicted_ranking_frozen_before_heldout.json",
        "top_fraction": 0.20,
        "pairwise_tie_tolerance": 1e-13,
    },
    "selection": {
        "rule":
            "among endpoint-valid candidates choose the smallest predicted "
            "quasi-static variance susceptibility q2; candidate_id tie-break",
        "reference_not_used_as_candidate": True,
        "minimum_predicted_relative_improvement": 0.01,
    },
    "heldout_gates": {
        "all_losses_finite": True,
        "minimum_spearman_rho_each_gamma": 0.80,
        "minimum_kendall_tau_each_gamma": 0.65,
        "minimum_pairwise_concordance_each_gamma": 0.80,
        "minimum_top_k_overlap_each_gamma": 0.60,
        "selected_beats_reference_at_every_gamma": True,
        "minimum_relative_improvement_each_gamma": 0.005,
        "selected_rank_fraction_max_each_gamma": 0.20,
        "prediction_sign_correct_at_every_gamma": True,
        "maximum_first_order_relative_error": 0.20,
    },
    "negative_controls": {
        "unselected_candidates_are_evaluated": True,
        "selection_must_not_be_worst_at_any_gamma": True,
    },
    "claim_boundary": (
        "A PASS supports the prospective claim that an ideal-path K_qs(z) "
        "variance susceptibility ranks finite quasi-static-detuning "
        "state-transfer losses in this frozen exact two-atom, six-segment "
        "model. The held-out "
        "losses are simulated outcomes, not measurements. It is not PASQAL "
        "production compilation, hardware/cloud evidence, a universal "
        "path-cost, or physics beyond standard Lindblad quantum mechanics."
    ),
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def protocol_hash() -> str:
    return hashlib.sha256(canonical_bytes(PROTOCOL)).hexdigest()


def program_name() -> str:
    return Path(
        globals().get(
            "__file__", "pasqal_kz_quasistatic_ranking_v3_0_2.py"
        )
    ).name


def source_hash() -> str:
    """
    Hash the exact .py file when one exists.

    The prospective protocol must therefore be run from a saved file.  The
    marshal fallback exists only for diagnostics in an interactive namespace;
    a commitment made through the supported file workflow always stores the
    byte-for-byte SHA-256 of this script.
    """
    # Deliberately do not inspect __file__. IPython mutates/removes it after
    # %run, while pasted cells have no stable source path. The explicit logic
    # inventory below is invariant to unrelated notebook variables.
    def normalized_constant(value: Any) -> Any:
        if isinstance(value, types.CodeType):
            return {"code": normalized_code(value)}
        if isinstance(value, tuple):
            return {"tuple": [normalized_constant(v) for v in value]}
        if isinstance(value, frozenset):
            items = [normalized_constant(v) for v in value]
            return {"frozenset": sorted(
                items, key=lambda item: canonical_bytes(item)
            )}
        if isinstance(value, bytes):
            return {"bytes_hex": value.hex()}
        if value is None or isinstance(
            value, (str, int, float, complex, bool)
        ):
            return {
                "type": type(value).__name__,
                "value": repr(value),
            }
        return {
            "type": type(value).__qualname__,
            "repr": repr(value),
        }

    def normalized_code(code: types.CodeType) -> dict[str, Any]:
        return {
            "argcount": code.co_argcount,
            "posonlyargcount": code.co_posonlyargcount,
            "kwonlyargcount": code.co_kwonlyargcount,
            "nlocals": code.co_nlocals,
            "flags": code.co_flags,
            "bytecode_hex": code.co_code.hex(),
            "names": list(code.co_names),
            "varnames": list(code.co_varnames),
            "freevars": list(code.co_freevars),
            "cellvars": list(code.co_cellvars),
            "constants": [
                normalized_constant(v) for v in code.co_consts
            ],
        }

    inventory: dict[str, Any] = {"protocol": PROTOCOL, "functions": {}}
    function_names = [
        "canonical_bytes", "protocol_hash", "program_name", "source_hash",
        "clean", "write_json", "vec", "unvec", "endpoint_jacobian",
        "endpoint_geometry", "corrected_candidate", "generate_candidates",
        "pairwise_concordance", "evaluate", "commit", "parse_args", "main",
    ]
    for name in function_names:
        code = getattr(globals().get(name), "__code__", None)
        if code is None:
            raise RuntimeError(f"cannot hash required function: {name}")
        inventory["functions"][f"function:{name}"] = normalized_code(code)
    for method_name, method in sorted(vars(Model).items()):
        method_code = getattr(method, "__code__", None)
        if method_code is not None:
            inventory["functions"][
                f"class:Model.{method_name}"
            ] = normalized_code(method_code)
    return hashlib.sha256(canonical_bytes(inventory)).hexdigest()


def clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, np.ndarray):
        return clean(value.tolist())
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(clean(value), indent=2, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def vec(matrix: np.ndarray) -> np.ndarray:
    return np.asarray(matrix, complex).reshape(-1, order="F")


def unvec(vector: np.ndarray, d: int) -> np.ndarray:
    return np.asarray(vector, complex).reshape((d, d), order="F")


@dataclass
class Model:
    segment_duration_us: float = 0.120
    spacing_um: float = 6.0

    def __post_init__(self) -> None:
        self.d = 4
        self.p = 18
        i2 = np.eye(2, dtype=complex)
        x = np.array([[0, 1], [1, 0]], dtype=complex)
        y = np.array([[0, -1j], [1j, 0]], dtype=complex)
        n = np.array([[0, 0], [0, 1]], dtype=complex)

        def embed(op: np.ndarray, site: int) -> np.ndarray:
            return np.kron(op, i2) if site == 0 else np.kron(i2, op)

        self.I = np.eye(self.d, dtype=complex)
        self.IL = np.eye(self.d**2, dtype=complex)
        self.X = embed(x, 0) + embed(x, 1)
        self.Y = embed(y, 0) + embed(y, 1)
        self.ns = [embed(n, 0), embed(n, 1)]
        self.N = self.ns[0] + self.ns[1]
        self.V = C6 / self.spacing_um**6 * (self.ns[0] @ self.ns[1])
        self.omega0 = 2 * np.pi * np.array([2.0, 1.7, 2.3, 1.5, 2.1, 1.8])
        self.delta0 = 2 * np.pi * np.array(
            [-2.3, -1.2, 0.4, 1.4, 2.0, 0.8]
        )
        self.phase0 = np.array([0.0, 0.4, 1.1, 2.0, 2.7, -2.4])
        self.z0 = np.zeros(self.p)
        self.D = np.zeros((self.d**2, self.d**2), dtype=complex)
        for op in self.ns:
            ada = op.conj().T @ op
            self.D += np.kron(op.conj(), op)
            self.D -= 0.5 * np.kron(self.I, ada)
            self.D -= 0.5 * np.kron(ada.T, self.I)
        self.U0 = self.unitary(self.z0)
        self.S0 = np.kron(self.U0.conj(), self.U0)
        ket00 = np.array([1, 0, 0, 0], dtype=complex)
        self.rho_in = np.outer(ket00, ket00.conj())
        psi_target = self.U0 @ ket00
        self.rho_target = np.outer(psi_target, psi_target.conj())

    def hamiltonian(
        self, z: np.ndarray, j: int, detuning_offset: float = 0.0
    ) -> np.ndarray:
        omega = self.omega0[j] * (1.0 + z[3 * j])
        if omega <= 0:
            raise ValueError("candidate has non-positive Rabi amplitude")
        delta = (
            self.delta0[j] + 2 * np.pi * z[3 * j + 1]
            + float(detuning_offset)
        )
        phase = self.phase0[j] + z[3 * j + 2]
        return (
            0.5 * omega
            * (math.cos(phase) * self.X + math.sin(phase) * self.Y)
            - delta * self.N
            + self.V
        )

    def unitary(
        self, z: np.ndarray, detuning_offset: float = 0.0
    ) -> np.ndarray:
        u = self.I.copy()
        for j in range(6):
            u = expm(-1j * self.hamiltonian(z, j, detuning_offset)
                     * self.segment_duration_us) @ u
        return u

    def aligned_residual(self, z: np.ndarray) -> np.ndarray:
        u = self.unitary(z)
        u *= np.exp(-1j * np.angle(np.vdot(self.U0, u)))
        delta = u - self.U0
        return np.r_[delta.real.ravel(), delta.imag.ravel()]

    def endpoint_infidelity(self, z: np.ndarray) -> float:
        overlap = np.trace(self.U0.conj().T @ self.unitary(z))
        return float(max(0.0, 1.0 - min(1.0, abs(overlap) ** 2 / self.d**2)))

    def coherent_liouvillian(self, h: np.ndarray) -> np.ndarray:
        return -1j * (np.kron(self.I, h) - np.kron(h.T, self.I))

    def channel_and_derivative(
        self, z: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        channel = self.IL.copy()
        derivative = np.zeros_like(channel)
        dt = self.segment_duration_us
        for j in range(6):
            a = self.coherent_liouvillian(self.hamiltonian(z, j)) * dt
            propagator, dprop = expm_frechet(
                a, self.D * dt, compute_expm=True
            )
            derivative = dprop @ channel + propagator @ derivative
            channel = propagator @ channel
        k_response = np.linalg.solve(channel, derivative)
        return channel, derivative, k_response

    def noisy_channel(self, z: np.ndarray, gamma: float) -> np.ndarray:
        channel = self.IL.copy()
        dt = self.segment_duration_us
        for j in range(6):
            generator = (
                self.coherent_liouvillian(self.hamiltonian(z, j))
                + gamma * self.D
            )
            channel = expm(generator * dt) @ channel
        return channel

    def task_loss_from_channel(self, channel: np.ndarray) -> float:
        rho = unvec(channel @ vec(self.rho_in), self.d)
        fidelity = float(np.real(np.trace(self.rho_target @ rho)))
        return float(max(0.0, 1.0 - fidelity))

    def predicted_slope(self, derivative: np.ndarray) -> float:
        drho = unvec(derivative @ vec(self.rho_in), self.d)
        return float(-np.real(np.trace(self.rho_target @ drho)))

    def coherent_task_loss(
        self, z: np.ndarray, detuning_offset: float
    ) -> float:
        psi = self.unitary(z, detuning_offset) @ np.array(
            [1, 0, 0, 0], dtype=complex
        )
        fidelity = float(np.real(np.vdot(
            psi, self.rho_target @ psi
        )))
        return float(max(0.0, 1.0 - min(1.0, fidelity)))

    def quasistatic_susceptibility(self, z: np.ndarray) -> float:
        h = float(PROTOCOL["noise"]["predictor_step_rad_per_us"])
        jp = self.coherent_task_loss(z, +h)
        j0 = self.coherent_task_loss(z, 0.0)
        jm = self.coherent_task_loss(z, -h)
        return float((jp - 2.0 * j0 + jm) / (2.0 * h * h))

    def averaged_quasistatic_loss(
        self, z: np.ndarray, sigma: float
    ) -> float:
        order = int(PROTOCOL["noise"]["gauss_hermite_order"])
        nodes, weights = np.polynomial.hermite.hermgauss(order)
        losses = [
            self.coherent_task_loss(
                z, math.sqrt(2.0) * float(sigma) * float(node)
            )
            for node in nodes
        ]
        return float(np.dot(weights, losses) / math.sqrt(math.pi))


def endpoint_jacobian(model: Model, z: np.ndarray, h: float) -> np.ndarray:
    columns = []
    for k in range(model.p):
        dz = np.zeros(model.p)
        dz[k] = h
        columns.append(
            (model.aligned_residual(z + dz)
             - model.aligned_residual(z - dz)) / (2 * h)
        )
    return np.column_stack(columns)


def endpoint_geometry(model: Model) -> dict[str, Any]:
    h = float(PROTOCOL["endpoint"]["jacobian_fd"])
    q1 = endpoint_jacobian(model, model.z0, h)
    q2 = endpoint_jacobian(model, model.z0, h / 2)
    _, s, vh = np.linalg.svd(q2, full_matrices=True)
    cut = float(PROTOCOL["endpoint"]["rank_relative_cut"]) * s[0]
    rank = int(np.count_nonzero(s > cut))
    vertical = vh[rank:].T
    normal = vh[:rank].T
    p1 = vertical @ vertical.T
    _, s1, vh1 = np.linalg.svd(q1, full_matrices=True)
    rank1 = int(np.count_nonzero(s1 > float(
        PROTOCOL["endpoint"]["rank_relative_cut"]) * s1[0]))
    v1 = vh1[rank1:].T
    projector_change = float(np.linalg.norm(p1 - v1 @ v1.T, 2))
    return {
        "q": q2,
        "rank": rank,
        "nullity": model.p - rank,
        "singular_values": s,
        "vertical": vertical,
        "normal": normal,
        "projector_change": projector_change,
        "stable": bool(rank == rank1 and projector_change < 0.02),
    }


def corrected_candidate(
    model: Model,
    tangent: np.ndarray,
    amplitude: float,
    normal: np.ndarray,
) -> tuple[np.ndarray, dict[str, Any]]:
    predictor = model.z0 + amplitude * tangent
    fit = least_squares(
        lambda a: model.aligned_residual(predictor + normal @ a),
        np.zeros(normal.shape[1]),
        ftol=1e-13,
        xtol=1e-13,
        gtol=1e-13,
        max_nfev=200,
    )
    z = predictor + normal @ fit.x
    residual = float(np.linalg.norm(model.aligned_residual(z)))
    return z, {
        "optimizer_success": bool(fit.success),
        "endpoint_residual": residual,
        "endpoint_infidelity": model.endpoint_infidelity(z),
        "control_separation": float(np.linalg.norm(z - model.z0)),
        "correction_norm": float(np.linalg.norm(normal @ fit.x)),
    }


def generate_candidates(
    model: Model, geometry: dict[str, Any]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    vertical = geometry["vertical"]
    normal = geometry["normal"]
    amplitudes = PROTOCOL["endpoint"]["candidate_tangent_amplitudes"]
    for direction_index in range(vertical.shape[1]):
        tangent = vertical[:, direction_index]
        # Fix the otherwise arbitrary SVD sign deterministically.
        pivot = int(np.argmax(np.abs(tangent)))
        if tangent[pivot] < 0:
            tangent = -tangent
        for sign in (-1, 1):
            for amplitude in amplitudes:
                signed = float(sign * amplitude)
                candidate_id = (
                    f"v{direction_index:02d}_"
                    f"{'p' if sign > 0 else 'm'}_{amplitude:.3f}"
                )
                try:
                    z, diagnostic = corrected_candidate(
                        model, tangent, signed, normal
                    )
                    slope = model.quasistatic_susceptibility(z)
                    valid = bool(
                        diagnostic["optimizer_success"]
                        and diagnostic["endpoint_infidelity"]
                        <= PROTOCOL["endpoint"]["endpoint_infidelity_tol"]
                        and diagnostic["endpoint_residual"]
                        <= PROTOCOL["endpoint"]["endpoint_residual_tol"]
                        and diagnostic["control_separation"]
                        >= PROTOCOL["endpoint"]["minimum_control_separation"]
                    )
                    rows.append({
                        "candidate_id": candidate_id,
                        "direction_index": direction_index,
                        "signed_amplitude": signed,
                        "z": z,
                        "predicted_slope": slope,
                        "predictor_kind":
                            "quasi-static variance susceptibility",
                        "valid": valid,
                        **diagnostic,
                    })
                except Exception as exc:
                    rows.append({
                        "candidate_id": candidate_id,
                        "direction_index": direction_index,
                        "signed_amplitude": signed,
                        "valid": False,
                        "reason": f"{type(exc).__name__}: {exc}",
                    })
    return rows


def pairwise_concordance(
    predicted: np.ndarray, observed: np.ndarray, tolerance: float
) -> tuple[float, int]:
    """Fraction of non-tied pairs whose predicted and observed order agrees."""
    concordant = 0
    comparable = 0
    for i in range(len(predicted)):
        for j in range(i + 1, len(predicted)):
            dp = float(predicted[i] - predicted[j])
            do = float(observed[i] - observed[j])
            if abs(dp) <= tolerance or abs(do) <= tolerance:
                continue
            comparable += 1
            concordant += int(dp * do > 0)
    value = float(concordant / comparable) if comparable else float("nan")
    return value, comparable


def evaluate(args: argparse.Namespace) -> int:
    expected = protocol_hash()
    if args.expected_hash != expected:
        raise RuntimeError(
            "Commitment mismatch. Expected exactly: "
            f"{expected}; received: {args.expected_hash!r}"
        )
    manifest = Path(args.manifest) if args.manifest else (
        Path(f"pasqal_kz_commit_{expected[:12]}") / "prospective_protocol.json"
    )
    if not manifest.exists():
        raise FileNotFoundError(
            f"Frozen manifest not found: {manifest}. Run commitment stage first."
        )
    frozen = json.loads(manifest.read_text(encoding="utf-8"))
    if frozen.get("protocol_sha256") != expected:
        raise RuntimeError("Manifest hash field does not match expected hash.")
    if hashlib.sha256(canonical_bytes(frozen["protocol"])).hexdigest() != expected:
        raise RuntimeError("Manifest protocol content failed SHA-256 verification.")
    if frozen.get("source_sha256") != source_hash():
        raise RuntimeError(
            "Evaluator source differs from the source frozen at commitment."
        )

    out = Path(args.outdir or f"pasqal_kz_eval_{expected[:12]}")
    if out.exists():
        raise FileExistsError(
            f"Output directory already exists: {out}. Choose --outdir."
        )
    out.mkdir(parents=True)

    model = Model()
    geometry = endpoint_geometry(model)
    if not geometry["stable"] or geometry["nullity"] <= 0:
        result = {
            "scientific_status": "FAILED_ENDPOINT_GEOMETRY",
            "protocol_sha256": expected,
            "rank": geometry["rank"],
            "nullity": geometry["nullity"],
            "projector_change": geometry["projector_change"],
        }
        write_json(out / "summary.json", result)
        print(json.dumps(clean(result), indent=2))
        return 2

    reference_slope = model.quasistatic_susceptibility(model.z0)
    candidates = generate_candidates(model, geometry)
    valid = [row for row in candidates if row.get("valid", False)]
    if not valid:
        result = {
            "scientific_status": "NO_VALID_ENDPOINT_EQUIVALENT_CANDIDATE",
            "protocol_sha256": expected,
        }
        write_json(out / "summary.json", result)
        print(json.dumps(result, indent=2))
        return 2

    predicted_order = sorted(
        valid, key=lambda row: (row["predicted_slope"], row["candidate_id"])
    )
    for predicted_rank, row in enumerate(predicted_order, start=1):
        row["predicted_rank"] = predicted_rank
    selected = predicted_order[0]
    predicted_relative_improvement = (
        (reference_slope - selected["predicted_slope"])
        / max(abs(reference_slope), FLOOR)
    )
    selection_gate = bool(
        predicted_relative_improvement
        >= PROTOCOL["selection"]["minimum_predicted_relative_improvement"]
    )

    # Ordering barrier: no finite-sigma averaged loss has been computed above.
    ranking_certificate = {
        "protocol_sha256": expected,
        "ranking_rule": PROTOCOL["ranking"]["rule"],
        "number_ranked": len(predicted_order),
        "ranking": [
            {
                "predicted_rank": row["predicted_rank"],
                "candidate_id": row["candidate_id"],
                "predicted_slope": row["predicted_slope"],
                "control": row["z"],
                "endpoint_infidelity": row["endpoint_infidelity"],
                "endpoint_residual": row["endpoint_residual"],
            }
            for row in predicted_order
        ],
        "selected_candidate_id": selected["candidate_id"],
        "reference_predicted_slope": reference_slope,
        "predicted_relative_improvement": predicted_relative_improvement,
        "selection_gate": selection_gate,
        "heldout_outcomes_computed": False,
        "frozen_utc": datetime.now(timezone.utc).isoformat(),
    }
    ranking_path = out / PROTOCOL["ranking"]["frozen_artifact"]
    write_json(ranking_path, ranking_certificate)
    ranking_sha = hashlib.sha256(ranking_path.read_bytes()).hexdigest()

    gamma_rows: list[dict[str, Any]] = []
    candidate_loss_rows: list[dict[str, Any]] = []
    z_selected = selected["z"]
    all_eval = [("reference", model.z0)] + [
        (row["candidate_id"], row["z"]) for row in valid
    ]
    losses_by_gamma: dict[float, list[tuple[str, float]]] = {}
    for gamma in PROTOCOL["noise"]["heldout_sigma_rad_per_us"]:
        values = []
        for candidate_id, z in all_eval:
            loss = model.averaged_quasistatic_loss(z, float(gamma))
            values.append((candidate_id, loss))
        losses_by_gamma[float(gamma)] = values
        lookup = dict(values)
        loss0 = lookup["reference"]
        loss1 = lookup[selected["candidate_id"]]
        relative_improvement = (loss0 - loss1) / max(loss0, FLOOR)
        predicted_difference = float(gamma) ** 2 * (
            selected["predicted_slope"] - reference_slope
        )
        exact_difference = loss1 - loss0
        prediction_error = abs(exact_difference - predicted_difference)
        prediction_relative_error = prediction_error / max(
            abs(exact_difference), FLOOR
        )
        candidate_values = [
            (row["candidate_id"], lookup[row["candidate_id"]])
            for row in predicted_order
        ]
        actual_order = sorted(
            candidate_values, key=lambda item: (item[1], item[0])
        )
        actual_rank = {
            candidate_id: rank
            for rank, (candidate_id, _) in enumerate(actual_order, start=1)
        }
        predicted_scores = np.asarray(
            [row["predicted_slope"] for row in predicted_order], float
        )
        actual_scores = np.asarray(
            [lookup[row["candidate_id"]] for row in predicted_order], float
        )
        spearman = float(spearmanr(
            predicted_scores, actual_scores
        ).statistic)
        kendall = float(kendalltau(
            predicted_scores, actual_scores
        ).statistic)
        concordance, comparable_pairs = pairwise_concordance(
            predicted_scores,
            actual_scores,
            float(PROTOCOL["ranking"]["pairwise_tie_tolerance"]),
        )
        top_k = max(
            1,
            int(math.ceil(
                float(PROTOCOL["ranking"]["top_fraction"]) * len(valid)
            )),
        )
        predicted_top = {
            row["candidate_id"] for row in predicted_order[:top_k]
        }
        actual_top = {
            candidate_id for candidate_id, _ in actual_order[:top_k]
        }
        top_k_overlap = len(predicted_top & actual_top) / top_k
        selected_rank = actual_rank[selected["candidate_id"]]
        for row in predicted_order:
            candidate_loss_rows.append({
                "sigma_detuning_rad_per_us": float(gamma),
                "candidate_id": row["candidate_id"],
                "predicted_slope": row["predicted_slope"],
                "predicted_rank": row["predicted_rank"],
                "heldout_task_loss": lookup[row["candidate_id"]],
                "actual_rank": actual_rank[row["candidate_id"]],
            })
        gamma_rows.append({
            "sigma_detuning_rad_per_us": float(gamma),
            "reference_loss": loss0,
            "selected_loss": loss1,
            "exact_loss_difference": exact_difference,
            "predicted_loss_difference": predicted_difference,
            "relative_improvement": relative_improvement,
            "prediction_relative_error": prediction_relative_error,
            "spearman_rho": spearman,
            "kendall_tau_b": kendall,
            "pairwise_concordance": concordance,
            "comparable_pairs": comparable_pairs,
            "top_k": top_k,
            "top_k_overlap": top_k_overlap,
            "selected_actual_rank": selected_rank,
            "number_ranked_candidates": len(valid),
        })

    max_rank_fraction = max(
        row["selected_actual_rank"] / row["number_ranked_candidates"]
        for row in gamma_rows
    )
    gates = {
        "endpoint_geometry_stable": bool(geometry["stable"]),
        "valid_candidate_exists": bool(valid),
        "predicted_improvement_predeclared_minimum": selection_gate,
        "all_losses_finite": all(
            math.isfinite(row["heldout_task_loss"])
            for row in candidate_loss_rows
        ),
        "spearman_ranking_each_gamma": all(
            row["spearman_rho"] >= PROTOCOL["heldout_gates"][
                "minimum_spearman_rho_each_gamma"
            ] for row in gamma_rows
        ),
        "kendall_ranking_each_gamma": all(
            row["kendall_tau_b"] >= PROTOCOL["heldout_gates"][
                "minimum_kendall_tau_each_gamma"
            ] for row in gamma_rows
        ),
        "pairwise_ordering_each_gamma": all(
            row["pairwise_concordance"] >= PROTOCOL["heldout_gates"][
                "minimum_pairwise_concordance_each_gamma"
            ] for row in gamma_rows
        ),
        "top_k_recovery_each_gamma": all(
            row["top_k_overlap"] >= PROTOCOL["heldout_gates"][
                "minimum_top_k_overlap_each_gamma"
            ] for row in gamma_rows
        ),
        "selected_beats_reference_at_every_gamma": all(
            row["selected_loss"] < row["reference_loss"]
            for row in gamma_rows
        ),
        "minimum_relative_improvement_each_gamma": all(
            row["relative_improvement"]
            >= PROTOCOL["heldout_gates"][
                "minimum_relative_improvement_each_gamma"
            ]
            for row in gamma_rows
        ),
        "selected_rank_fraction_each_gamma": all(
            row["selected_actual_rank"] / row["number_ranked_candidates"]
            <= PROTOCOL["heldout_gates"][
                "selected_rank_fraction_max_each_gamma"
            ] for row in gamma_rows
        ),
        "selection_not_worst_at_any_gamma": all(
            row["selected_actual_rank"] < row["number_ranked_candidates"]
            for row in gamma_rows
        ),
        "prediction_sign_correct_at_every_gamma": all(
            row["exact_loss_difference"]
            * row["predicted_loss_difference"] > 0
            for row in gamma_rows
        ),
        "maximum_first_order_relative_error": all(
            row["prediction_relative_error"]
            <= PROTOCOL["heldout_gates"][
                "maximum_first_order_relative_error"
            ]
            for row in gamma_rows
        ),
    }
    all_pass = all(gates.values())
    summary = {
        "scientific_status": (
            "PROSPECTIVE_KZ_RANKING_AND_TASK_IMPROVEMENT_SUPPORTED"
            if all_pass else
            "PROSPECTIVE_KZ_RANKING_AND_TASK_IMPROVEMENT_NOT_SUPPORTED"
        ),
        "all_gates_pass": all_pass,
        "protocol_sha256": expected,
        "ranking_certificate_sha256": ranking_sha,
        "support_type":
            "exact local model; prospective frozen simulated evaluation",
        "endpoint_geometry": {
            "rank": geometry["rank"],
            "nullity": geometry["nullity"],
            "projector_change": geometry["projector_change"],
        },
        "candidate_audit": {
            "attempted": len(candidates),
            "valid": len(valid),
            "selected_candidate_id": selected["candidate_id"],
            "reference_predicted_slope": reference_slope,
            "selected_predicted_slope": selected["predicted_slope"],
            "predicted_relative_improvement": predicted_relative_improvement,
            "predictor_difference":
                selected["predicted_slope"] - reference_slope,
        },
        "heldout_rows": gamma_rows,
        "worst_selected_rank_fraction": max_rank_fraction,
        "gates": gates,
        "claim_boundary": PROTOCOL["claim_boundary"],
    }

    # Artifact tables.  Controls are stored only after selection was frozen.
    with (out / "heldout_results.csv").open(
        "w", newline="", encoding="utf-8"
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=list(gamma_rows[0]))
        writer.writeheader()
        writer.writerows(gamma_rows)
    with (out / "candidate_ranking_results.csv").open(
        "w", newline="", encoding="utf-8"
    ) as stream:
        writer = csv.DictWriter(
            stream, fieldnames=list(candidate_loss_rows[0])
        )
        writer.writeheader()
        writer.writerows(candidate_loss_rows)
    np.savetxt(out / "reference_control.csv", model.z0, delimiter=",")
    np.savetxt(out / "selected_control.csv", z_selected, delimiter=",")
    write_json(out / "summary.json", summary)
    write_json(out / "candidate_predictor_audit.json", [
        {k: v for k, v in row.items() if k != "z"} for row in candidates
    ])

    print("=" * 96)
    print("K_qs(z)-GUIDED QUASI-STATIC DETUNING OPTIMIZATION v3.0.2")
    print("=" * 96)
    print(json.dumps(clean(summary), indent=2, ensure_ascii=False))
    print(f"outputs={out}")
    return 0 if all_pass else 1


def commit(args: argparse.Namespace) -> int:
    digest = protocol_hash()
    out = Path(args.outdir or f"pasqal_kz_commit_{digest[:12]}")
    if out.exists():
        manifest_path = out / "prospective_protocol.json"
        if not manifest_path.exists():
            existing_is_reusable = False
            recovery_reason = "existing directory has no manifest"
        else:
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
            protocol_ok = bool(
                existing.get("protocol_sha256") == digest
                and hashlib.sha256(
                    canonical_bytes(existing.get("protocol"))
                ).hexdigest() == digest
            )
            source_ok = bool(existing.get("source_sha256") == source_hash())
            existing_is_reusable = bool(protocol_ok and source_ok)
            recovery_reason = "existing manifest belongs to older/different source"

        if existing_is_reusable:
            print("=" * 96)
            print("EXISTING IDENTICAL COMMITMENT REUSED — NO OUTCOME COMPUTED")
            print("=" * 96)
            print(f"protocol_sha256={digest}")
            print(f"source_sha256={source_hash()}")
            print(f"manifest={manifest_path}")
            print("\nEvaluation command:")
            print(
                f"python {program_name()} --evaluate "
                f"--expected-hash {digest}"
            )
            return 0

        if args.outdir:
            raise FileExistsError(
                f"Explicit --outdir cannot be reused because {recovery_reason}: "
                f"{out}. Existing files will not be overwritten."
            )

        base = Path(f"pasqal_kz_commit_{digest[:12]}")
        recovery_index = 1
        while True:
            candidate = Path(
                f"{base.name}_recovery_{recovery_index:03d}"
            )
            if not candidate.exists():
                print(
                    f"[recovery] {recovery_reason}: {out}; "
                    f"using new directory {candidate}"
                )
                out = candidate
                break
            recovery_index += 1
    out.mkdir(parents=True)
    manifest = {
        "protocol": PROTOCOL,
        "protocol_sha256": digest,
        "source_sha256": source_hash(),
        "frozen_utc": datetime.now(timezone.utc).isoformat(),
        "outcomes_computed": False,
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
    }
    write_json(out / "prospective_protocol.json", manifest)
    print("=" * 96)
    print("K_qs(z)-GUIDED QUASI-STATIC OPTIMIZATION — COMMITMENT")
    print("=" * 96)
    print(json.dumps(clean(manifest), indent=2, ensure_ascii=False))
    print("\nNO HAMILTONIAN, K(z), CANDIDATE, OR NOISY OUTCOME WAS COMPUTED.")
    print(f"protocol_sha256={digest}")
    print(f"manifest={out / 'prospective_protocol.json'}")
    print("\nEvaluation command:")
    print(
        f"python {program_name()} --evaluate "
        f"--expected-hash {digest}"
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluate", action="store_true")
    parser.add_argument(
        "--one-click",
        action="store_true",
        help="freeze the protocol, then evaluate it in the same invocation",
    )
    parser.add_argument("--expected-hash", default=None)
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--outdir", default=None)
    args, unknown = parser.parse_known_args()
    if unknown:
        print(f"[notebook] ignored kernel arguments: {unknown}")
    if args.evaluate and args.one_click:
        parser.error("choose either --evaluate or --one-click")
    if args.evaluate and not args.expected_hash:
        parser.error("--evaluate requires --expected-hash")
    return args


def main() -> None:
    args = parse_args()
    if args.one_click:
        digest = protocol_hash()
        commit_args = argparse.Namespace(
            evaluate=False,
            one_click=False,
            expected_hash=None,
            manifest=None,
            outdir=None,
        )
        commit(commit_args)
        evaluate_args = argparse.Namespace(
            evaluate=True,
            one_click=False,
            expected_hash=digest,
            manifest=str(
                Path(f"pasqal_kz_commit_{digest[:12]}")
                / "prospective_protocol.json"
            ),
            outdir=None,
        )
        code = evaluate(evaluate_args)
    else:
        code = evaluate(args) if args.evaluate else commit(args)
    # Avoid sys.exit() in notebooks; the printed verdict and summary file carry
    # the scientific status.  Shell callers can inspect failed gates in JSON.
    if code:
        print(f"[scientific gate status] nonzero={code}")


if __name__ == "__main__":
    main()
