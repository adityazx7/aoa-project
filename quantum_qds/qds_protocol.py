"""3-Party Teleportation-Based Quantum Digital Signature (QDS) Protocol Engine.
Implements Key Distribution via Bell Entanglement, Symmetrization, Signature Generation,
and Dual-Verifier Non-Repudiation Verification.
"""

import numpy as np
import hashlib
from typing import Dict, Any, List, Tuple
from quantum_qds.quantum_core import (
    KET_0, KET_1, KET_PLUS, KET_MINUS,
    measure_projective, quantum_teleport, state_fidelity
)

class TeleportationQDS:
    """Teleportation-Based Quantum Digital Signature Protocol (Alice, Bob, Charlie)."""

    def __init__(
        self,
        key_length: int = 32,
        s_a: float = 0.08,  # Acceptance error threshold
        s_v: float = 0.22,  # Verification / Forgery rejection threshold
        s_k: float = 0.14,  # Non-repudiation discrepancy threshold
        channel_noise: float = 0.01  # Natural quantum channel decoherence
    ):
        self.key_length = key_length
        self.s_a = s_a
        self.s_v = s_v
        self.s_k = s_k
        self.channel_noise = channel_noise

        # Alice's private key store
        # For each message bit b in {0, 1}, Alice prepares key_length qubits
        self.alice_private_keys: Dict[int, List[Dict[str, Any]]] = {0: [], 1: []}

        # Bob and Charlie's received quantum keys (density matrices or state vectors)
        self.bob_keys: Dict[int, List[np.ndarray]] = {0: [], 1: []}
        self.charlie_keys: Dict[int, List[np.ndarray]] = {0: [], 1: []}
        
        self.is_distributed = False

    def distribute_keys(self) -> Dict[str, Any]:
        """Phase 1: Quantum Public Key Distribution via Entanglement & Teleportation.
        Alice generates states in randomly chosen conjugate Pauli bases (Z or X),
        and teleports copies to Bob and Charlie.
        """
        self.alice_private_keys = {0: [], 1: []}
        self.bob_keys = {0: [], 1: []}
        self.charlie_keys = {0: [], 1: []}
        teleport_stats = []

        for b in (0, 1):
            for i in range(self.key_length):
                # Alice chooses random basis: 'Z' or 'X'
                basis = str(np.random.choice(["Z", "X"]))
                bit = int(np.random.choice([0, 1]))

                # Prepare qubit
                if basis == "Z":
                    qubit = KET_0 if bit == 0 else KET_1
                else:
                    qubit = KET_PLUS if bit == 0 else KET_MINUS

                self.alice_private_keys[b].append({
                    "index": i,
                    "basis": basis,
                    "bit": bit,
                    "state": qubit
                })

                # Teleport to Bob
                res_bob = quantum_teleport(qubit, channel_noise=self.channel_noise)
                # Reconstruct state from teleported components
                q_bob = np.array([
                    [res_bob["bob_state"][0]["re"] + 1j * res_bob["bob_state"][0]["im"]],
                    [res_bob["bob_state"][1]["re"] + 1j * res_bob["bob_state"][1]["im"]]
                ], dtype=complex)
                self.bob_keys[b].append(q_bob)

                # Teleport to Charlie
                res_charlie = quantum_teleport(qubit, channel_noise=self.channel_noise)
                q_charlie = np.array([
                    [res_charlie["bob_state"][0]["re"] + 1j * res_charlie["bob_state"][0]["im"]],
                    [res_charlie["bob_state"][1]["re"] + 1j * res_charlie["bob_state"][1]["im"]]
                ], dtype=complex)
                self.charlie_keys[b].append(q_charlie)

                if i < 4:
                    teleport_stats.append({
                        "bit_index": i,
                        "msg_target": b,
                        "basis": basis,
                        "declared_bit": bit,
                        "bob_fidelity": res_bob["fidelity"],
                        "charlie_fidelity": res_charlie["fidelity"],
                        "bsm_bell_state": res_bob["bell_state"]
                    })

        self.is_distributed = True
        return {
            "key_length": self.key_length,
            "total_qubits_teleported": self.key_length * 2 * 2,  # 2 msg bits * 2 verifiers
            "channel_noise": self.channel_noise,
            "sample_telemetry": teleport_stats
        }

    def sign_message(self, message: str) -> Dict[str, Any]:
        """Phase 2: Signature Generation by Alice.
        Message hash is mapped to a bit sequence; Alice reveals classical preparation
        indices (basis and bit) for the matching key set.
        """
        if not self.is_distributed:
            self.distribute_keys()

        # Compute deterministic 1-bit or multi-bit hash of message
        digest = hashlib.sha256(message.encode("utf-8")).hexdigest()
        # Take parity of first byte as message bit m in {0, 1}
        m_bit = int(digest[0], 16) % 2

        # Reveal signature sequence for message bit m_bit
        signature_tokens = []
        for k in self.alice_private_keys[m_bit]:
            signature_tokens.append({
                "index": k["index"],
                "basis": k["basis"],
                "bit": k["bit"]
            })

        return {
            "message": message,
            "hash": digest,
            "m_bit": m_bit,
            "signature_tokens": signature_tokens
        }

    def verify_signature(
        self,
        signature_package: Dict[str, Any],
        tampered_tokens: List[Dict[str, Any]] = None,
        tamper_bob_keys: bool = False
    ) -> Dict[str, Any]:
        """Phase 3: Verification & Threat Assessment by Bob and Charlie.
        Bob and Charlie perform projective measurements on their stored quantum keys
        using the basis declared in the signature package.
        """
        m_bit = signature_package["m_bit"]
        tokens = tampered_tokens if tampered_tokens is not None else signature_package["signature_tokens"]

        bob_errors = 0
        charlie_errors = 0
        total_checks = min(len(tokens), self.key_length)

        bob_measurements = []
        charlie_measurements = []

        for i in range(total_checks):
            token = tokens[i]
            declared_basis = token["basis"]
            expected_bit = token["bit"]

            # 1. Bob measures his stored qubit
            q_b = self.bob_keys[m_bit][i]
            if tamper_bob_keys:
                # Eavesdropper or channel noise disturbance
                noise_x = np.random.choice([0, 1], p=[0.2, 0.8])
                if noise_x:
                    q_b = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=complex) @ q_b

            out_b, _ = measure_projective(q_b, basis=declared_basis)
            is_err_b = (out_b != expected_bit)
            if is_err_b:
                bob_errors += 1

            # 2. Charlie measures his stored qubit
            q_c = self.charlie_keys[m_bit][i]
            out_c, _ = measure_projective(q_c, basis=declared_basis)
            is_err_c = (out_c != expected_bit)
            if is_err_c:
                charlie_errors += 1

            if i < 8:
                bob_measurements.append({
                    "index": i,
                    "basis": declared_basis,
                    "expected": expected_bit,
                    "outcome": out_b,
                    "match": not is_err_b
                })
                charlie_measurements.append({
                    "index": i,
                    "basis": declared_basis,
                    "expected": expected_bit,
                    "outcome": out_c,
                    "match": not is_err_c
                })

        qber_bob = bob_errors / total_checks if total_checks > 0 else 0.0
        qber_charlie = charlie_errors / total_checks if total_checks > 0 else 0.0
        discrepancy = abs(qber_bob - qber_charlie)

        # Decision rules based strictly on Quantum Thresholds
        # 1. Bob decision
        if qber_bob <= self.s_a:
            decision_bob = "ACCEPTED"
        elif qber_bob < self.s_v:
            decision_bob = "SUSPICIOUS_CHANNEL_MANIPULATION"
        else:
            decision_bob = "REJECTED_FORGERY"

        # 2. Charlie decision
        if qber_charlie <= self.s_a:
            decision_charlie = "ACCEPTED"
        elif qber_charlie < self.s_v:
            decision_charlie = "SUSPICIOUS_CHANNEL_MANIPULATION"
        else:
            decision_charlie = "REJECTED_FORGERY"

        # 3. Non-repudiation cross-check
        non_repudiation_passed = (discrepancy <= self.s_k)

        # Overall security verdict
        overall_valid = (
            decision_bob == "ACCEPTED" and
            decision_charlie == "ACCEPTED" and
            non_repudiation_passed
        )

        return {
            "total_checks": total_checks,
            "thresholds": {
                "s_a_acceptance": self.s_a,
                "s_v_rejection": self.s_v,
                "s_k_discrepancy": self.s_k
            },
            "bob": {
                "errors": bob_errors,
                "qber": round(qber_bob, 4),
                "decision": decision_bob,
                "sample_measurements": bob_measurements
            },
            "charlie": {
                "errors": charlie_errors,
                "qber": round(qber_charlie, 4),
                "decision": decision_charlie,
                "sample_measurements": charlie_measurements
            },
            "discrepancy": round(discrepancy, 4),
            "non_repudiation_passed": non_repudiation_passed,
            "overall_valid": overall_valid
        }
