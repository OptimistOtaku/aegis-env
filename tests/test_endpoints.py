from fastapi.testclient import TestClient
from app.main import app

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
        "target_component": "api_01",
        "parameters": {},
        "reasoning": "Test step logic"
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
    
    # 4. Observation endpoint
    response = client.get("/observation")
    assert response.status_code == 200
    obs_data = response.json()
    assert obs_data["tick"] == 1
