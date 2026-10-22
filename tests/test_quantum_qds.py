"""Comprehensive Unit & Security Verification Tests for Quantum QDS Framework.
Validates Teleportation, Pauli Projective Measurements, Non-AI Threat Detection,
Adversarial Attacks, and Blockchain Ledger Integrity.
"""

import pytest
import numpy as np
from quantum_qds.quantum_core import (
    create_qubit, quantum_teleport, measure_projective,
    BELL_PHI_PLUS, state_fidelity
)
from quantum_qds.qds_protocol import TeleportationQDS
from quantum_qds.threat_detector import QuantumThreatDetector
from quantum_qds.attack_simulator import QuantumAttackSimulator
from quantum_qds.quantum_blockchain import QuantumLedger, compute_merkle_root

# ==========================================
# 1. Quantum Teleportation & Fidelity Tests
# ==========================================

def test_noiseless_quantum_teleportation_fidelity():
    """Qubit state teleportation over an ideal channel must achieve exact fidelity F = 1.0."""
    # Test arbitrary states on the Bloch sphere
    for theta, phi in [(0.5, 0.2), (1.2, 0.8), (np.pi / 2, 0.0), (0.0, 0.0), (np.pi, 0.0)]:
        qubit = create_qubit(theta, phi)
        res = quantum_teleport(qubit, channel_noise=0.0)
        assert res["success"] is True
        assert res["fidelity"] == pytest.approx(1.0, rel=1e-5)
        assert res["bell_state"] in ["Phi+", "Phi-", "Psi+", "Psi-"]

def test_pauli_projective_measurements():
    """Measurements of eigenstates in their own basis must yield deterministic outcomes."""
    from quantum_qds.quantum_core import KET_0, KET_1, KET_PLUS, KET_MINUS
    
    # Measuring |0> in Z basis gives 0
    out0, _ = measure_projective(KET_0, basis="Z")
    assert out0 == 0
    # Measuring |1> in Z basis gives 1
    out1, _ = measure_projective(KET_1, basis="Z")
    assert out1 == 1
    # Measuring |+> in X basis gives 0
    out_plus, _ = measure_projective(KET_PLUS, basis="X")
    assert out_plus == 0
    # Measuring |-> in X basis gives 1
    out_minus, _ = measure_projective(KET_MINUS, basis="X")
    assert out_minus == 1

# ==========================================
# 2. QDS Protocol Legitimate Verification Tests
# ==========================================

def test_qds_legitimate_signature_acceptance():
    """Uncompromised signature must be accepted deterministically with QBER <= s_a."""
    qds = TeleportationQDS(key_length=32, channel_noise=0.0)
    qds.distribute_keys()
    
    sig = qds.sign_message("Official Government Clearance Document")
    res = qds.verify_signature(sig)
    
    assert res["overall_valid"] is True
    assert res["bob"]["decision"] == "ACCEPTED"
    assert res["charlie"]["decision"] == "ACCEPTED"
    assert res["bob"]["qber"] <= qds.s_a
    assert res["charlie"]["qber"] <= qds.s_a
    assert res["non_repudiation_passed"] is True

# ==========================================
# 3. Non-AI Cyber Threat Detection Tests
# ==========================================

def test_detect_signature_forgery():
    """Forged signature tokens must cause conjugate Pauli collapse and trigger Forgery detection."""
    sim = QuantumAttackSimulator()
    res = sim.run_simulation(message="Bank Transfer Authorization $10,000,000", attack_type="forgery")
    
    threat = res["threat_detection"]
    assert threat["threat_detected"] is True
    assert threat["threat_type"] == "DIGITAL_SIGNATURE_FORGERY"
    assert threat["decision"] == "REJECT"
    assert res["verification"]["overall_valid"] is False
    assert res["verification"]["bob"]["qber"] >= sim.qds.s_v or res["verification"]["charlie"]["qber"] >= sim.qds.s_v

def test_detect_impersonation_attack():
    """Impersonator lacking pre-shared entanglement must be detected."""
    sim = QuantumAttackSimulator()
    res = sim.run_simulation(message="Root Admin Authorization", attack_type="impersonation")
    
    threat = res["threat_detection"]
    assert threat["threat_detected"] is True
    assert threat["threat_type"] == "IMPERSONATION_ATTACK"
    assert threat["decision"] == "REJECT"

def test_detect_replay_attack():
    """Replaying old classical feed-forward bits on new states must be caught."""
    sim = QuantumAttackSimulator()
    res = sim.run_simulation(message="Replayed Transaction Token", attack_type="replay")
    
    threat = res["threat_detection"]
    assert threat["threat_detected"] is True
    assert threat["threat_type"] == "REPLAY_ATTACK"
    assert threat["decision"] == "REJECT"

def test_detect_channel_manipulation():
    """Eavesdropping / channel tampering exceeding s_a must raise a Channel Manipulation alert."""
    sim = QuantumAttackSimulator()
    res = sim.run_simulation(message="Confidential Dispatch", attack_type="channel_tap")
    
    threat = res["threat_detection"]
    assert threat["threat_detected"] is True
    assert threat["threat_type"] in ["QUANTUM_CHANNEL_MANIPULATION", "DIGITAL_SIGNATURE_FORGERY"]

def test_detect_repudiation_attack():
    """Alice sending mismatched keys to Bob and Charlie must violate non-repudiation."""
    sim = QuantumAttackSimulator()
    res = sim.run_simulation(message="Disputed Contract Agreement", attack_type="repudiation")
    
    threat = res["threat_detection"]
    assert threat["threat_detected"] is True
    assert threat["threat_type"] == "REPUDIATION_ATTEMPT"
    assert res["verification"]["non_repudiation_passed"] is False

# ==========================================
# 4. Quantum Blockchain Ledger Tests
# ==========================================

def test_quantum_blockchain_minting_and_integrity():
    """Blockchain audit ledger must record QDS events and pass full cryptographic verification."""
    ledger = QuantumLedger()
    assert len(ledger.chain) == 1  # Genesis block
    
    # Record events
    b1 = ledger.record_qds_event(
        message="Campus Patrol Checkpoint A",
        message_hash="abcd1234hash",
        decision="ACCEPTED",
        threat_type="NONE",
        qber_bob=0.02,
        qber_charlie=0.03
    )
    assert b1.index == 1
    assert b1.previous_hash == ledger.chain[0].hash
    
    b2 = ledger.record_qds_event(
        message="Fake Order Attempt",
        message_hash="bad9999hash",
        decision="REJECTED",
        threat_type="DIGITAL_SIGNATURE_FORGERY",
        qber_bob=0.38,
        qber_charlie=0.41
    )
    assert b2.index == 2
    assert b2.previous_hash == b1.hash
    assert b2.quantum_metadata["threat_flagged"] is True

    # Validate chain integrity
    integrity = ledger.verify_chain_integrity()
    assert integrity["valid"] is True
    assert integrity["block_count"] == 3

def test_merkle_root_computation():
    """Merkle root must be deterministic and sensitive to transaction alteration."""
    txs1 = [{"id": 1, "data": "alice"}, {"id": 2, "data": "bob"}]
    txs2 = [{"id": 1, "data": "alice"}, {"id": 2, "data": "charlie"}]
    
    root1 = compute_merkle_root(txs1)
    root2 = compute_merkle_root(txs2)
    
    assert root1 != root2
    assert compute_merkle_root(txs1) == root1
