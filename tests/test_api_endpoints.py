import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_root_index_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "Spatial Navigator" in response.text
    assert "campusBlueprintSection" in response.text

def test_api_campus_graph():
    response = client.get("/api/campus/graph")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert "rooms" in data
    assert "costModel" in data
    assert len(data["nodes"]) >= 80

def test_api_campus_route():
    payload = {
        "source": "GATE",
        "destination": "T3",
        "algorithm": "dijkstra",
        "avoid_stairs": False,
        "stairs_penalty": 4.0,
        "accessible_only": False,
        "prefer_indoor": False,
        "outdoor_penalty": 2.5,
        "k_alternatives": 2
    }
    response = client.post("/api/campus/route", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "primary" in data
    assert data["primary"]["path"][0] == "GATE"
    assert data["primary"]["path"][-1] == "T3"
    assert "directions" in data
    assert len(data["directions"]) > 0
    assert "comparison" in data
    assert len(data["comparison"]) in (4, 5)  # Dijkstra, A*, ALT, Bidirectional, BFS
    assert "alternatives" in data
    assert len(data["alternatives"]) >= 1

def test_api_campus_route_accessible():
    payload = {
        "source": "GATE",
        "destination": "T3",
        "algorithm": "dijkstra",
        "accessible_only": True
    }
    response = client.post("/api/campus/route", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Path must use elevator 'LIFT_C' and 'LIFT_F0', never stairs
    for edge in data["primary"]["edges"]:
        assert edge["type"] != "s", "Accessible route must not use stairs"

def test_api_campus_multi_stop():
    payload = {
        "origin": "GATE",
        "stops": ["CANT", "T3", "LIB"],
        "avoid_stairs": False
    }
    response = client.post("/api/campus/multi-stop", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "visit_sequence" in data
    assert "full_path" in data
    assert data["full_path"][0] == "GATE"

def test_api_campus_shortcuts():
    response = client.get("/api/campus/shortcuts?node_id=GATE")
    assert response.status_code == 200
    data = response.json()
    assert "nearest_entrance" in data
    assert "nearest_stairs" in data
    assert "nearest_lift" in data

def test_existing_retail_preset_endpoint():
    # Verify we did not break existing features
    response = client.post("/api/graph/preset", json={"preset": "vidyalankar"})
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data

# ==========================================
# Quantum Cyber Defense (QDS) API Tests
# ==========================================

def test_api_qds_status():
    response = client.get("/api/qds/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OPERATIONAL"
    assert data["ai_ml_free"] is True
    assert "Teleportation" in data["protocol"]

def test_api_qds_simulate_attack_forgery():
    payload = {
        "message": "High-Value Transfer Payload",
        "attack_type": "forgery"
    }
    response = client.post("/api/qds/simulate-attack", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["threat_detection"]["threat_detected"] is True
    assert data["threat_detection"]["threat_type"] == "DIGITAL_SIGNATURE_FORGERY"
    assert "blockchain_receipt" in data
    assert data["blockchain_receipt"]["block_index"] >= 1

def test_api_qds_simulate_attack_legitimate():
    payload = {
        "message": "Legitimate Campus Clearance",
        "attack_type": "none"
    }
    response = client.post("/api/qds/simulate-attack", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["threat_detection"]["threat_detected"] is False
    assert data["verification"]["overall_valid"] is True
    assert "blockchain_receipt" in data

def test_api_qds_ledger():
    response = client.get("/api/qds/ledger")
    assert response.status_code == 200
    data = response.json()
    assert "integrity" in data
    assert data["integrity"]["valid"] is True
    assert "chain" in data
    assert len(data["chain"]) >= 1

def test_api_qds_benchmarks():
    response = client.get("/api/qds/benchmarks")
    assert response.status_code == 200
    data = response.json()
    assert "current" in data
    assert "curves" in data
    assert len(data["curves"]) >= 5
