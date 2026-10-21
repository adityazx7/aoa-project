"""
Cost model and routing profiles for Spatial Navigator v2.
All internal routing costs are unified in SECONDS.
Physical distances are tracked in METRES.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any

WALK_SPEED_MPS = 1.3  # Base walking speed: 1.3 m/s (~4.7 km/h)

@dataclass
class CostConfig:
    walk_speed: float = WALK_SPEED_MPS
    stairs_time_s: float = 12.0         # 12s per flight transition
    stairs_up_time_s: float = 12.0      # Symmetric undirected default
    stairs_down_time_s: float = 12.0    # Symmetric undirected default
    lift_wait_time_s: float = 8.0       # 8s lift transition
    lift_ride_time_s: float = 8.0       # 8s ride per floor transition
    door_time_s: float = 4.0            # 4s door threshold
    outdoor_penalty_mult: float = 1.3   # 30% time penalty if prefer_indoor
    stairs_avoid_mult: float = 4.0      # 4x time penalty if avoid_stairs

@dataclass
class RoutingProfile:
    avoid_stairs: bool = False
    stairs_penalty: float = 4.0
    wheelchair: bool = False            # True = stairs strictly forbidden
    accessible_only: bool = False       # Alias for wheelchair
    prefer_indoor: bool = False
    outdoor_penalty: float = 1.3
    quiet_route: bool = False
    k_alternatives: int = 1

    def __post_init__(self):
        if self.accessible_only:
            self.wheelchair = True

def compute_edge_metrics(
    edge_type: str,
    distance_m: float,
    outdoor: bool,
    config: CostConfig = CostConfig(),
    is_downward: bool = False
) -> Dict[str, float]:
    """
    Computes time (seconds) and distance (metres) for a given edge.
    Symmetric for undirected graph consistency.
    """
    if edge_type == "s":
        # Stairs: 12.0s
        t = config.stairs_time_s
        d = max(distance_m, 6.0)
        return {"time_s": t, "distance_m": d}
    elif edge_type == "l":
        # Lift: 8.0s
        t = config.lift_ride_time_s
        d = max(distance_m, 4.5)
        return {"time_s": t, "distance_m": d}
    elif edge_type == "d":
        # Door transition: 4.0s
        t = config.door_time_s
        d = max(distance_m, 1.0)
        return {"time_s": t, "distance_m": d}
    else:
        # Standard walk / corridor / bridge
        t = distance_m / config.walk_speed if config.walk_speed > 0 else distance_m
        return {"time_s": t, "distance_m": distance_m}
