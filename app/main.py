from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import glob
import random

from app.models import Observation, Action, Reward, Tool
from app.tasks.task_easy import load_task_easy
from app.tasks.task_medium import load_task_medium
from app.tasks.task_hard import load_task_hard

app = FastAPI(title="aegis-env", description="OpenEnv AI Safety Incident Response Environment")

# Holds the active environment session for a single connected agent
current_env = None

class ResetRequest(BaseModel):
    task_id: str
    fixture_id: Optional[str] = None

class StepResponse(BaseModel):
    observation: Observation
    reward: Reward

@app.get("/")
def get_info():
    """Endpoint 1/6: Environment Status"""
    return {
        "name": "aegis-env",
        "description": "AI Safety Incident Response OpenEnv",
        "version": "1.0.0",
        "active_session": current_env is not None
    }

@app.get("/tools")
def get_tools():
    """Endpoint 2/6: Available tools enumeration"""
    return {t.name: t.value for t in Tool}

@app.post("/reset", response_model=Observation)
def reset_env(req: ResetRequest):
    """Endpoint 3/6: Reset environment"""
    global current_env
    task_map = {
        "task_easy": load_task_easy,
        "task_medium": load_task_medium,
        "task_hard": load_task_hard
    }
    
    if req.task_id not in task_map:
        raise HTTPException(status_code=400, detail=f"Unknown task {req.task_id}")
        
    fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "data", "incidents")
    
    if req.fixture_id:
        target = os.path.join(fixtures_dir, req.fixture_id)
        if os.path.exists(target):
            current_env = task_map[req.task_id](target)
        else:
            raise HTTPException(status_code=404, detail=f"Fixture not found: {req.fixture_id}")
    else:
        # Auto-resolve a fixture based on task
        prefix_map = {
            "task_easy": "jbk_",
            "task_medium": "dft_",
            "task_hard": "amp_"
        }
        prefix = prefix_map[req.task_id]
        pattern = os.path.join(fixtures_dir, f"{prefix}*.json")
        fixture_files = glob.glob(pattern)
        
        if not fixture_files:
            raise HTTPException(status_code=404, detail=f"No fixtures found for {req.task_id} in data/incidents/")
            
        chosen = random.choice(fixture_files)
        current_env = task_map[req.task_id](chosen)
    
    return current_env.reset()

@app.post("/step", response_model=StepResponse)
def step_env(action: Action):
    """Endpoint 4/6: Agent steps the environment"""
    global current_env
    if not current_env:
        raise HTTPException(status_code=400, detail="Environment not initialized. Call /reset first.")
    
    if current_env.done:
        raise HTTPException(status_code=400, detail="Environment is terminated. Call /reset.")
        
    obs, reward, done, info = current_env.step(action)
    return StepResponse(observation=obs, reward=reward)

@app.get("/observation", response_model=Observation)
def get_observation():
    """Endpoint 5/6: Observe environment state without advancing time"""
    if not current_env:
        raise HTTPException(status_code=400, detail="Environment not initialized.")
    return current_env._get_observation()

@app.get("/state")
def get_state():
    """Full internal state snapshot (OpenEnv spec)"""
    if not current_env:
        raise HTTPException(status_code=400, detail="Environment not initialized.")
    return current_env.state()

@app.get("/score")
def get_score():
    """Endpoint 6/6: Retrieves cumulative live score and state"""
    if not current_env:
        raise HTTPException(status_code=400, detail="Environment not initialized.")
    if not current_env.grader:
        return {"cumulative_score": 0.0}
        
    return {
        "cumulative_score": current_env.grader.cumulative_score,
        "diagnosed_root_causes": list(current_env.grader.diagnosed_root_causes),
        "patched_components": list(current_env.grader.patched_components),
        "isolated_components": list(current_env.grader.isolated_components),
        "validated_components": list(current_env.grader.validated_components)
    }
