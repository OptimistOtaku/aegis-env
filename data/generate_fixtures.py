import json
import os
import random

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
    # Vary which model is compromised based on index
    targets = ["model_A", "model_B", "model_C"]
    compromised_model = targets[(idx - 1) % len(targets)]
    
    for comp in c:
        if comp["component_id"] == "api_01":
            comp["connections"] = [compromised_model]  # simplify topology
        # Set initial compromised component to compromised state
        if comp["component_id"] == compromised_model:
            comp["safety_status"] = "compromised"
            comp["health_score"] = 0.6
    
    # Vary max_ticks slightly across fixtures
    max_ticks = 8 + (idx % 3)  # 8, 9, 10 cycle
    
    return {
        "task_id": "task_easy",
        "incident_id": "JBK",
        "max_ticks": max_ticks,
        "initial_compromised": [compromised_model],
        "root_cause_components": [compromised_model],
        "components": c,
        "active_alerts": [f"ALERT: Anomalous payload detected on endpoint /generate — source: {compromised_model}"]
    }

def gen_medium(idx):
    c = get_base_components()
    # Vary which models are symptoms vs false positive
    symptom_sets = [
        (["model_A", "model_B"], "model_C"),
        (["model_B", "model_C"], "model_A"),
        (["model_A", "model_C"], "model_B"),
    ]
    symptoms, false_pos = symptom_sets[(idx - 1) % len(symptom_sets)]
    
    # Set initial compromised states
    for comp in c:
        if comp["component_id"] == "filter_01":
            comp["safety_status"] = "compromised"
            comp["health_score"] = 0.4
        if comp["component_id"] in symptoms:
            comp["safety_status"] = "degraded"
            comp["health_score"] = 0.7
    
    max_ticks = 15 + (idx % 3)  # 15, 16, 17 cycle
    
    return {
        "task_id": "task_medium",
        "incident_id": "DFT",
        "max_ticks": max_ticks,
        "initial_compromised": ["filter_01"] + symptoms,
        "root_cause_components": ["filter_01"],
        "false_positive_component": false_pos,
        "symptom_components": symptoms,
        "components": c,
        "active_alerts": ["WARNING: Output distribution shift detected across fleet."]
    }

def gen_hard(idx):
    c = get_base_components()
    # Add cyclical amplification connection app_01 -> api_01
    for comp in c:
        if comp["component_id"] == "app_01":
            comp["connections"] = ["api_01"]
            comp["safety_status"] = "compromised"
            comp["health_score"] = 0.3
        if comp["component_id"] == "data_pipe_01":
            comp["safety_status"] = "compromised"
            comp["health_score"] = 0.4
        if comp["component_id"] == "api_01":
            comp["safety_status"] = "degraded"
            comp["health_score"] = 0.6
        if comp["component_id"] == "filter_01":
            comp["safety_status"] = "degraded"
            comp["health_score"] = 0.7
            
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
