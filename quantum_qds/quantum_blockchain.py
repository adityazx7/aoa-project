"""Quantum-Secured Blockchain Ledger Module.
Provides an immutable cryptographic audit ledger for QDS transactions,
teleportation verification records, and threat detection alerts.
"""

import hashlib
import json
import time
from typing import List, Dict, Any, Optional

def compute_sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def compute_merkle_root(items: List[Dict[str, Any]]) -> str:
    """Computes SHA-256 Merkle Root of an array of transaction dicts."""
    if not items:
        return compute_sha256("EMPTY_TREE")
    
    current_level = [
        compute_sha256(json.dumps(item, sort_keys=True))
        for item in items
    ]
    
    while len(current_level) > 1:
        next_level = []
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            right = current_level[i + 1] if i + 1 < len(current_level) else left
            next_level.append(compute_sha256(left + right))
        current_level = next_level

    return current_level[0]

class QuantumBlock:
    """An immutable block recording QDS events, threat alerts, and telemetry."""

    def __init__(
        self,
        index: int,
        timestamp: float,
        transactions: List[Dict[str, Any]],
        previous_hash: str,
        quantum_metadata: Dict[str, Any],
        nonce: int = 0
    ):
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.quantum_metadata = quantum_metadata
        self.merkle_root = compute_merkle_root(transactions)
        self.nonce = nonce
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        payload = f"{self.index}{self.timestamp}{self.previous_hash}{self.merkle_root}{json.dumps(self.quantum_metadata, sort_keys=True)}{self.nonce}"
        return compute_sha256(payload)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "iso_time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.timestamp)),
            "previous_hash": self.previous_hash,
            "merkle_root": self.merkle_root,
            "hash": self.hash,
            "nonce": self.nonce,
            "transactions_count": len(self.transactions),
            "transactions": self.transactions,
            "quantum_metadata": self.quantum_metadata
        }

class QuantumLedger:
    """Blockchain Audit Trail for Quantum Digital Signatures."""

    def __init__(self):
        self.chain: List[QuantumBlock] = []
        self.pending_transactions: List[Dict[str, Any]] = []
        # Create Genesis Block
        self.create_genesis_block()

    def create_genesis_block(self):
        genesis_meta = {
            "protocol": "Teleportation-Based Quantum Digital Signature (QDS)",
            "standard": "SIH 2026 Problem Statement 26141",
            "security_type": "Information-Theoretic Security (No-Cloning Theorem)",
            "genesis_status": "ENTANGLEMENT_INITIALIZED"
        }
        genesis_tx = [{
            "type": "GENESIS_INITIALIZATION",
            "signer": "ALICE_ROOT_CA",
            "verifiers": ["BOB_VERIFIER_1", "CHARLIE_VERIFIER_2"],
            "bell_state": "Phi+"
        }]
        genesis_block = QuantumBlock(
            index=0,
            timestamp=time.time(),
            transactions=genesis_tx,
            previous_hash="0" * 64,
            quantum_metadata=genesis_meta,
            nonce=26141
        )
        self.chain.append(genesis_block)

    @property
    def latest_block(self) -> QuantumBlock:
        return self.chain[-1]

    def record_qds_event(
        self,
        message: str,
        message_hash: str,
        decision: str,
        threat_type: str,
        qber_bob: float,
        qber_charlie: float,
        fidelity: float = 1.0,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> QuantumBlock:
        """Mints a new block recording a verified or rejected QDS transaction."""
        tx = {
            "message": message,
            "hash": message_hash,
            "decision": decision,
            "threat_type": threat_type,
            "qber_bob": qber_bob,
            "qber_charlie": qber_charlie,
            "fidelity": fidelity,
            "timestamp": time.time(),
            "extra": extra_data or {}
        }
        
        meta = {
            "avg_qber": round((qber_bob + qber_charlie) / 2.0, 4),
            "threat_flagged": (threat_type != "NONE"),
            "threat_type": threat_type,
            "fidelity": fidelity
        }

        new_block = QuantumBlock(
            index=len(self.chain),
            timestamp=time.time(),
            transactions=[tx],
            previous_hash=self.latest_block.hash,
            quantum_metadata=meta,
            nonce=len(self.chain) * 137
        )
        self.chain.append(new_block)
        return new_block

    def verify_chain_integrity(self) -> Dict[str, Any]:
        """Validates that no block hash, previous hash, or Merkle root has been tampered with."""
        for i in range(1, len(self.chain)):
            curr = self.chain[i]
            prev = self.chain[i - 1]

            if curr.previous_hash != prev.hash:
                return {
                    "valid": False,
                    "error": f"Hash link broken between block {prev.index} and {curr.index}"
                }
            if curr.calculate_hash() != curr.hash:
                return {
                    "valid": False,
                    "error": f"Block {curr.index} payload tampered! Hash mismatch."
                }
            if compute_merkle_root(curr.transactions) != curr.merkle_root:
                return {
                    "valid": False,
                    "error": f"Block {curr.index} Merkle root mismatch! Transactions modified."
                }

        return {
            "valid": True,
            "block_count": len(self.chain),
            "latest_hash": self.latest_block.hash
        }

    def get_chain_dict(self) -> List[Dict[str, Any]]:
        return [b.to_dict() for b in self.chain]

# Global singleton instance
quantum_ledger_instance = QuantumLedger()
