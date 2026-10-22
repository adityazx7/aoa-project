"""Quantum Core Module: State simulation, Bell-state entanglement,
Pauli operators, projective measurements, and Quantum Teleportation.
"""

import numpy as np
from typing import Tuple, Dict, Any, List

# --- Basis States ---
KET_0 = np.array([[1.0], [0.0]], dtype=complex)
KET_1 = np.array([[0.0], [1.0]], dtype=complex)

KET_PLUS = (KET_0 + KET_1) / np.sqrt(2.0)
KET_MINUS = (KET_0 - KET_1) / np.sqrt(2.0)

KET_PLUS_I = (KET_0 + 1j * KET_1) / np.sqrt(2.0)
KET_MINUS_I = (KET_0 - 1j * KET_1) / np.sqrt(2.0)

# --- Pauli Matrices ---
PAULI_I = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=complex)
PAULI_X = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=complex)
PAULI_Y = np.array([[0.0, -1j], [1j, 0.0]], dtype=complex)
PAULI_Z = np.array([[1.0, 0.0], [0.0, -1.0]], dtype=complex)

PAULI_DICT = {"I": PAULI_I, "X": PAULI_X, "Y": PAULI_Y, "Z": PAULI_Z}

# --- Bell States (2-Qubit Maximally Entangled Basis) ---
# |Phi+> = (|00> + |11>) / sqrt(2)
BELL_PHI_PLUS = (np.kron(KET_0, KET_0) + np.kron(KET_1, KET_1)) / np.sqrt(2.0)
# |Phi-> = (|00> - |11>) / sqrt(2)
BELL_PHI_MINUS = (np.kron(KET_0, KET_0) - np.kron(KET_1, KET_1)) / np.sqrt(2.0)
# |Psi+> = (|01> + |10>) / sqrt(2)
BELL_PSI_PLUS = (np.kron(KET_0, KET_1) + np.kron(KET_1, KET_0)) / np.sqrt(2.0)
# |Psi-> = (|01> - |10>) / sqrt(2)
BELL_PSI_MINUS = (np.kron(KET_0, KET_1) - np.kron(KET_1, KET_0)) / np.sqrt(2.0)

BELL_BASIS = [BELL_PHI_PLUS, BELL_PHI_MINUS, BELL_PSI_PLUS, BELL_PSI_MINUS]
BELL_LABELS = ["Phi+", "Phi-", "Psi+", "Psi-"]

# Projectors for Bell-State Measurement (BSM)
BELL_PROJECTORS = [state @ state.conj().T for state in BELL_BASIS]

# --- Projective Measurement Operators in Pauli Bases ---
PROJECTORS_Z = {
    0: KET_0 @ KET_0.conj().T,
    1: KET_1 @ KET_1.conj().T
}
PROJECTORS_X = {
    0: KET_PLUS @ KET_PLUS.conj().T,
    1: KET_MINUS @ KET_MINUS.conj().T
}
PROJECTORS_Y = {
    0: KET_PLUS_I @ KET_PLUS_I.conj().T,
    1: KET_MINUS_I @ KET_MINUS_I.conj().T
}

PROJECTORS = {"Z": PROJECTORS_Z, "X": PROJECTORS_X, "Y": PROJECTORS_Y}


def create_qubit(theta: float, phi: float) -> np.ndarray:
    """Create a pure single-qubit state on the Bloch Sphere:
    |psi> = cos(theta/2)|0> + e^(i*phi)*sin(theta/2)|1>
    """
    alpha = np.cos(theta / 2.0)
    beta = np.exp(1j * phi) * np.sin(theta / 2.0)
    state = np.array([[alpha], [beta]], dtype=complex)
    # Normalize
    norm = np.linalg.norm(state)
    return state / norm


def create_density_matrix(state: np.ndarray) -> np.ndarray:
    """Convert pure state ket to density matrix rho = |psi><psi|."""
    return state @ state.conj().T


def state_fidelity(rho: np.ndarray, sigma: np.ndarray) -> float:
    """Calculate quantum state fidelity between two density matrices F(rho, sigma).
    For pure states, F = |<psi|phi>|^2.
    """
    if rho.shape == (2, 1) and sigma.shape == (2, 1):
        inner = np.vdot(rho, sigma)
        return float(np.abs(inner) ** 2)
    # General trace fidelity
    from scipy.linalg import sqrtm
    sqrt_rho = sqrtm(rho)
    m = sqrt_rho @ sigma @ sqrt_rho
    sqrt_m = sqrtm(m)
    f = np.real(np.trace(sqrt_m)) ** 2
    return float(np.clip(f, 0.0, 1.0))


def measure_projective(state: np.ndarray, basis: str = "Z") -> Tuple[int, np.ndarray]:
    """Perform a projective von Neumann measurement in basis ('Z', 'X', or 'Y').
    Returns (outcome_bit: 0 or 1, collapsed_state).
    """
    basis = basis.upper()
    proj = PROJECTORS.get(basis, PROJECTORS_Z)
    
    # Probabilities P(outcome) = <psi| P |psi>
    p0 = float(np.real(state.conj().T @ proj[0] @ state)[0, 0])
    p0 = np.clip(p0, 0.0, 1.0)
    p1 = 1.0 - p0

    outcome = int(np.random.choice([0, 1], p=[p0, p1]))
    
    # Wave function collapse
    collapsed = proj[outcome] @ state
    norm = np.linalg.norm(collapsed)
    if norm > 1e-12:
        collapsed = collapsed / norm
    else:
        collapsed = KET_0 if outcome == 0 else KET_1

    return outcome, collapsed


def bell_state_measurement(two_qubit_state: np.ndarray) -> Tuple[int, str]:
    """Perform a 2-qubit Bell-State Measurement (BSM).
    Returns (bell_index: 0..3, label: 'Phi+', 'Phi-', 'Psi+', 'Psi-').
    """
    probs = []
    for proj in BELL_PROJECTORS:
        prob = float(np.real(two_qubit_state.conj().T @ proj @ two_qubit_state)[0, 0])
        probs.append(max(0.0, prob))
    
    probs = np.array(probs)
    total_p = np.sum(probs)
    if total_p > 1e-9:
        probs = probs / total_p
    else:
        probs = np.array([0.25, 0.25, 0.25, 0.25])
        
    outcome_idx = int(np.random.choice([0, 1, 2, 3], p=probs))
    return outcome_idx, BELL_LABELS[outcome_idx]


def quantum_teleport(
    input_qubit: np.ndarray,
    channel_noise: float = 0.0
) -> Dict[str, Any]:
    """Simulates quantum teleportation of an input qubit from Alice to Bob.
    
    1. Pre-shared entanglement: Alice has Qubit A, Bob has Qubit B in |Phi+>_AB.
    2. Combined state of Qubit In (Alice), Qubit A (Alice), Qubit B (Bob):
       |Psi_total> = |input> (x) |Phi+>_AB
    3. Alice performs Bell-State Measurement on (Input, Qubit A).
    4. Alice transmits 2 classical bits (m1, m2) to Bob.
    5. Bob applies Pauli correction: sigma_x^m2 * sigma_z^m1 to Qubit B.
    6. Bob's reconstructed qubit is compared to input qubit.
    
    Args:
        input_qubit: 2x1 complex vector.
        channel_noise: Depolarizing noise probability (0.0 = ideal, >0 = channel degradation).
    """
    # 1. Total 3-qubit state: |input> (x) |Phi+>
    total_state = np.kron(input_qubit, BELL_PHI_PLUS)
    
    # 2. BSM Projectors on Qubits 1 & 2 (with Identity on Qubit 3)
    bsm_probs = []
    for proj_bell in BELL_PROJECTORS:
        proj_3q = np.kron(proj_bell, PAULI_I)
        prob = float(np.real(total_state.conj().T @ proj_3q @ total_state)[0, 0])
        bsm_probs.append(max(0.0, prob))
        
    bsm_probs = np.array(bsm_probs) / sum(bsm_probs)
    bsm_idx = int(np.random.choice([0, 1, 2, 3], p=bsm_probs))
    
    # Classical feed-forward bits
    # 0 -> Phi+ : (m1=0, m2=0) -> I
    # 1 -> Phi- : (m1=1, m2=0) -> Z
    # 2 -> Psi+ : (m1=0, m2=1) -> X
    # 3 -> Psi- : (m1=1, m2=1) -> X*Z = -iY
    m1 = 1 if bsm_idx in (1, 3) else 0
    m2 = 1 if bsm_idx in (2, 3) else 0
    
    # Collapsed 3-qubit state
    proj_chosen = np.kron(BELL_PROJECTORS[bsm_idx], PAULI_I)
    collapsed_3q = proj_chosen @ total_state
    collapsed_3q = collapsed_3q / np.linalg.norm(collapsed_3q)
    
    # Project onto Alice's measured Bell state <Bell_k| (x) I_3 to get Bob's state
    inner_proj = np.kron(BELL_BASIS[bsm_idx].conj().T, PAULI_I)
    bob_raw = inner_proj @ collapsed_3q
    norm_b = np.linalg.norm(bob_raw)
    if norm_b > 1e-12:
        bob_raw = bob_raw / norm_b

    # 3. Bob applies Pauli Correction: U_corr = (X^m2) * (Z^m1)
    u_corr = np.linalg.matrix_power(PAULI_X, m2) @ np.linalg.matrix_power(PAULI_Z, m1)
    bob_corrected = u_corr @ bob_raw
    bob_corrected = bob_corrected / np.linalg.norm(bob_corrected)
    
    # 4. Optional Channel Noise Simulation (Depolarizing / Phase perturbation)
    if channel_noise > 0.0:
        noise_type = np.random.choice(["none", "X", "Y", "Z"], p=[
            1.0 - channel_noise,
            channel_noise / 3.0,
            channel_noise / 3.0,
            channel_noise / 3.0
        ])
        if noise_type != "none":
            bob_corrected = PAULI_DICT[noise_type] @ bob_corrected
            bob_corrected = bob_corrected / np.linalg.norm(bob_corrected)

    # 5. Measure Fidelity with original input state
    fid = state_fidelity(input_qubit, bob_corrected)
    
    return {
        "bsm_index": bsm_idx,
        "bell_state": BELL_LABELS[bsm_idx],
        "classical_bits": (m1, m2),
        "pauli_correction": f"X^{m2} Z^{m1}",
        "fidelity": float(fid),
        "bob_state": [
            {"re": float(bob_corrected[0, 0].real), "im": float(bob_corrected[0, 0].imag)},
            {"re": float(bob_corrected[1, 0].real), "im": float(bob_corrected[1, 0].imag)}
        ],
        "success": fid > 0.95
    }
