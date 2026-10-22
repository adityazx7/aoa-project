"""Cyber Attack Simulator for Teleportation-Based Quantum Digital Signatures.
Injects Forgery, Impersonation, Replay, Quantum Channel Tap, and Repudiation Attacks.
"""

import copy
import numpy as np
from typing import Dict, Any, List
from quantum_qds.qds_protocol import TeleportationQDS
from quantum_qds.threat_detector import QuantumThreatDetector

class QuantumAttackSimulator:
    """Simulates real-world adversarial attacks on QDS channels and signatures."""

    def __init__(self, qds: TeleportationQDS = None, detector: QuantumThreatDetector = None):
        self.qds = qds if qds is not None else TeleportationQDS(key_length=32)
        self.detector = detector if detector is not None else QuantumThreatDetector()

    def run_simulation(
        self,
        message: str = "Authorized Executive Order #2026-ALPHA",
        attack_type: str = "none"
    ) -> Dict[str, Any]:
        """Executes a full QDS cycle with optional adversarial attack injection.
        
        Args:
            message: Plain-text string to sign.
            attack_type: 'none', 'forgery', 'impersonation', 'replay', 'channel_tap', 'repudiation'.
        """
        # Ensure keys are distributed
        if not self.qds.is_distributed:
            self.qds.distribute_keys()

        # Step 1: Sign legitimate message
        sig_pkg = self.qds.sign_message(message)
        tampered_tokens = None
        tamper_bob = False
        attack_hint = None

        # Step 2: Inject Adversarial Attack
        attack_details = {
            "attack_type": attack_type,
            "description": "No attack injected. Baseline legitimate quantum transmission.",
            "manipulation_rate": 0.0
        }

        if attack_type == "forgery":
            # Attacker creates forged tokens by guessing states without entangled keys
            attack_hint = "forgery"
            tampered_tokens = copy.deepcopy(sig_pkg["signature_tokens"])
            for token in tampered_tokens:
                # Adversary flips basis and bit (wave-function conjugate collapse)
                token["basis"] = "X" if token["basis"] == "Z" else "Z"
                token["bit"] = 1 - token["bit"]
            attack_details["description"] = "Adversary Eve forged signature tokens without possessing Alice's quantum private keys."
            attack_details["manipulation_rate"] = 1.0

        elif attack_type == "impersonation":
            attack_hint = "impersonation"
            tampered_tokens = copy.deepcopy(sig_pkg["signature_tokens"])
            for token in tampered_tokens:
                # Attacker guesses bases completely at random
                token["basis"] = str(np.random.choice(["Z", "X"]))
                token["bit"] = int(np.random.choice([0, 1]))
            attack_details["description"] = "Rogue node claimed Alice's identity without pre-shared Bell-state entanglement."
            attack_details["manipulation_rate"] = 1.0

        elif attack_type == "replay":
            attack_hint = "replay"
            # Use signature tokens from the opposite message bit (stale previous signature)
            alt_bit = 1 - sig_pkg["m_bit"]
            tampered_tokens = []
            for k in self.qds.alice_private_keys[alt_bit]:
                tampered_tokens.append({"index": k["index"], "basis": k["basis"], "bit": k["bit"]})
            attack_details["description"] = "Adversary replayed captured quantum measurements from a previously transmitted signature."
            attack_details["manipulation_rate"] = 1.0

        elif attack_type == "channel_tap":
            attack_hint = "channel_tap"
            # Eavesdropper taps quantum channel: measures and disrupts Bob's qubits
            tamper_bob = True
            attack_details["description"] = "Man-in-the-Middle intercept-resend probe / partial beam-splitter tap applied to fiber channel."
            attack_details["manipulation_rate"] = 0.8

        elif attack_type == "repudiation":
            attack_hint = "repudiation"
            # Alice maliciously altered Charlie's keys during key distribution to repudiate later
            for i in range(len(self.qds.charlie_keys[sig_pkg["m_bit"]])):
                # Flip Charlie's quantum states to orthogonal state
                q_c = self.qds.charlie_keys[sig_pkg["m_bit"]][i]
                self.qds.charlie_keys[sig_pkg["m_bit"]][i] = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=complex) @ q_c
            attack_details["description"] = "Dishonest signer Alice sent discrepant quantum states to Bob and Charlie to enable repudiation."
            attack_details["manipulation_rate"] = 1.0

        # Step 3: Run Verification
        verif_res = self.qds.verify_signature(
            sig_pkg,
            tampered_tokens=tampered_tokens,
            tamper_bob_keys=tamper_bob
        )

        # Step 4: Run Physics-Based Non-AI Threat Detection
        threat_analysis = self.detector.analyze_signature(verif_res, attack_hint=attack_hint)

        return {
            "message": message,
            "hash": sig_pkg["hash"],
            "attack_simulation": attack_details,
            "verification": verif_res,
            "threat_detection": threat_analysis
        }
