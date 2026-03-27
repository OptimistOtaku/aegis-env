import json
import os

def get_base_components():
    return [
        {"component_id": "lb_01", "component_type": "load_balancer", "health_score": 1.0, "safety_status": "nominal", "connections": ["api_01"], "recent_logs": [], "metrics": {}},
        {"component_id": "api_01", "component_type": "inference_api", "health_score": 1.0, "safety_status": "nominal", "connections": ["model_A", "model_B", "model_C"], "recent_logs": [], "metrics": {}},
        {"component_id": "model_A", "component_type": "model", "health_score": 1.0, "safety_status": "nominal", "connections": ["filter_01"], "recent_logs": [], "metrics": {}},
        {"component_id": "model_B", "component_type": "model", "health_score": 1.0, "safety_status": "nominal", "connections": ["filter_01"], "recent_logs": [], "metrics": {}},
        {"component_id": "model_C", "component_type": "model", "health_score": 1.0, "safety_status": "nominal", "connections": ["filter_01"], "recent_logs": [], "metrics": {}},
        {"component_id": "filter_01", "component_type": "safety_filter", "health_score": 1.0, "safety_status": "nominal", "connections": ["app_01"], "recent_logs": [], "metrics": {}},
        {"component_id": "app_01", "component_type": "downstream_app", "health_score": 1.0, "safety_status": "nominal", "connections": [], "recent_logs": [], "metrics": {}},
        {"component_id": "data_pipe_01", "component_type": "data_pipeline", "health_score": 1.0, "safety_status": "nominal", "connections": ["api_01"], "recent_logs": [], "metrics": {}}
    ]

def gen_easy(idx):
    c = get_base_components()
    for comp in c:
        if comp["component_id"] == "api_01": comp["connections"] = ["model_A"] # simplify topology
    
    return {
        "task_id": "task_easy",
        "incident_id": "JBK",
        "max_ticks": 8,
        "initial_compromised": ["model_A"],
        "root_cause_components": ["model_A"],
        "components": c,
        "active_alerts": ["ALERT: Anomalous payload detected on endpoint /generate"]
    }

def gen_medium(idx):
    c = get_base_components()
    return {
        "task_id": "task_medium",
        "incident_id": "DFT",
        "max_ticks": 15,
        "initial_compromised": ["filter_01", "model_A", "model_B"],
        "root_cause_components": ["filter_01"],
        "false_positive_component": "model_C",
        "symptom_components": ["model_A", "model_B"],
        "components": c,
        "active_alerts": ["WARNING: Output distribution shift detected across fleet."]
    }

def gen_hard(idx):
    c = get_base_components()
    # Add cyclical amplification connection app_01 -> api_01
    for comp in c:
        if comp["component_id"] == "app_01":
            comp["connections"] = ["api_01"]
        if comp["component_id"] == "data_pipe_01":
            comp["safety_status"] = "compromised"
            
    return {
        "task_id": "task_hard",
        "incident_id": "AMP_PZN",
        "max_ticks": 20,
        "adversarial_mode": True,
        "initial_compromised": ["app_01", "data_pipe_01", "api_01", "filter_01"],
        "root_cause_components": ["app_01", "data_pipe_01"],
        "amp_cause_id": "app_01",
        "pzn_cause_id": "data_pipe_01",
        "downstream_app_id": "app_01",
        "components": c,
        "active_alerts": ["CRITICAL: Service degradation.", "ERROR: Pipeline desync."]
    }

def generate_all():
    os.makedirs('data/incidents', exist_ok=True)
    for i in range(1, 8):
        with open(f'data/incidents/jbk_single_{i:02d}.json', 'w') as f:
            json.dump(gen_easy(i), f, indent=2)
    for i in range(1, 8):
        with open(f'data/incidents/dft_cascade_{i:02d}.json', 'w') as f:
            json.dump(gen_medium(i), f, indent=2)
    for i in range(1, 7): # 7+7+6 = 20
        with open(f'data/incidents/amp_pzn_adversarial_{i:02d}.json', 'w') as f:
            json.dump(gen_hard(i), f, indent=2)
            
if __name__ == '__main__':
    generate_all()
    print("Generated 20 fixtures.")
