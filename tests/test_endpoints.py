from fastapi.testclient import TestClient
from server.app import app

client = TestClient(app)

def test_info_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "aegis-env"

def test_tools_endpoint():
    response = client.get("/tools")
    assert response.status_code == 200
    tools = response.json()
    assert "READ_LOGS" in tools
    assert tools["READ_LOGS"] == "read_logs"

def test_reset_and_step_easy():
    # 1. Reset
    response = client.post("/reset", json={"task_id": "task_easy"})
    assert response.status_code == 200
    obs = response.json()
    assert obs["task_id"] == "task_easy"
    assert obs["tick"] == 0

    # 2. Step
    action_payload = {
        "tool": "run_diagnostic",
        "target_component": "model_A",
        "parameters": {},
        "reasoning": "Running diagnostic on the compromised model."
    }
    response = client.post("/step", json=action_payload)
    assert response.status_code == 200
    res = response.json()
    assert "observation" in res
    assert "reward" in res
    assert res["observation"]["tick"] == 1
    
    # 3. Score endpoint
    response = client.get("/score")
    assert response.status_code == 200
    score_data = response.json()
    assert "cumulative_score" in score_data
    assert 0.0 <= score_data["cumulative_score"] <= 1.0
    
    # 4. Observation endpoint
    response = client.get("/observation")
    assert response.status_code == 200
    obs_data = response.json()
    assert obs_data["tick"] == 1

    # 5. State endpoint (OpenEnv spec)
    response = client.get("/state")
    assert response.status_code == 200
    state_data = response.json()
    assert "tick" in state_data
    assert "done" in state_data
    assert "blast_radius" in state_data
    assert "components" in state_data

def test_reset_and_step_medium():
    response = client.post("/reset", json={"task_id": "task_medium"})
    assert response.status_code == 200
    obs = response.json()
    assert obs["task_id"] == "task_medium"
    assert obs["tick"] == 0
    assert len(obs["blast_radius"]) > 0  # Should start compromised

    action_payload = {
        "tool": "run_diagnostic",
        "target_component": "filter_01",
        "parameters": {},
        "reasoning": "Diagnosing the safety filter which is the likely root cause."
    }
    response = client.post("/step", json=action_payload)
    assert response.status_code == 200
    res = response.json()
    assert res["observation"]["tick"] == 1

def test_reset_and_step_hard():
    response = client.post("/reset", json={"task_id": "task_hard"})
    assert response.status_code == 200
    obs = response.json()
    assert obs["task_id"] == "task_hard"
    assert obs["tick"] == 0
    assert len(obs["blast_radius"]) > 0
    
    action_payload = {
        "tool": "read_logs",
        "target_component": "data_pipe_01",
        "parameters": {},
        "reasoning": "Reading logs from data pipeline — checking for adversarial injection patterns."
    }
    response = client.post("/step", json=action_payload)
    assert response.status_code == 200
    res = response.json()
    # READ_LOGS costs 0 ticks but env always advances at least 1 tick
    assert res["observation"]["tick"] == 1

def test_reward_bounded():
    """Verify that cumulative scores remain within [0.0, 1.0]."""
    response = client.post("/reset", json={"task_id": "task_easy"})
    assert response.status_code == 200
    
    # Run several steps and verify score stays in range
    for i in range(5):
        action_payload = {
            "tool": "patch",
            "target_component": "lb_01",
            "parameters": {},
            "reasoning": "Patch attempt."
        }
        response = client.post("/step", json=action_payload)
        if response.status_code != 200:
            break
    
    response = client.get("/score")
    assert response.status_code == 200
    score = response.json()["cumulative_score"]
    assert 0.0 <= score <= 1.0, f"Score {score} out of [0, 1] range"

def test_invalid_task():
    response = client.post("/reset", json={"task_id": "task_impossible"})
    assert response.status_code == 400

def test_step_without_reset():
    # Ensure fresh state by checking if env is none
    import server.app as main_module
    main_module.current_env = None
    
    action_payload = {
        "tool": "read_logs",
        "target_component": "lb_01",
        "parameters": {},
        "reasoning": "Test."
    }
    response = client.post("/step", json=action_payload)
    assert response.status_code == 400
