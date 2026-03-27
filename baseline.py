import os
import json
import random
from typing import Dict, Any
from app.models import Tool, Action
from app.tasks.task_easy import load_task_easy
from app.tasks.task_medium import load_task_medium
from app.tasks.task_hard import load_task_hard

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

class BaselineAgent:
    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock or OpenAI is None
        self.client = None
        if not self.use_mock:
            self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def decide_action(self, obs: Dict[str, Any]) -> Action:
        if self.use_mock:
            return self._mock_action(obs)
            
        system_prompt = """You are a senior AI safety incident responder.
You must stabilize the AI cluster by selecting one tool per turn.
Respond ONLY with a JSON object containing:
{"tool": "<tool_name>", "target_component": "<component_id>", "parameters": {}, "reasoning": "rationale"}
Available tools: read_logs, run_diagnostic, isolate, patch, rollback, scale_down, reroute_traffic, alert_human, validate, restore.
You must parse logs and isolate root causes to maximize reward.
"""
        obs_json = json.dumps(obs, indent=2)
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Current Observation:\n{obs_json}\nWhat is your next action?"}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            content = response.choices[0].message.content
            action_dict = json.loads(content)
            return Action(
                tool=Tool(action_dict["tool"]),
                target_component=action_dict["target_component"],
                parameters=action_dict.get("parameters", {}),
                reasoning=action_dict.get("reasoning", "No reasoning provided.")
            )
        except Exception as e:
            print(f"Agent error: {e}")
            return Action(tool=Tool.ALERT_HUMAN, target_component="lb_01", parameters={}, reasoning=f"Error: {str(e)}")

    def _mock_action(self, obs: Dict[str, Any]) -> Action:
        # Simple heuristic to test plumbing
        target = random.choice(obs["components"])["component_id"]
        reasoning = "Mocking action for baseline plumbing test."
        if random.random() < 0.5:
            tool = Tool.RUN_DIAGNOSTIC
        else:
            tool = Tool.PATCH
        return Action(tool=tool, target_component=target, parameters={}, reasoning=reasoning)

def run_evaluation(use_mock: bool = False):
    tasks = {
        "task_easy": ("data/incidents/jbk_single_01.json", load_task_easy),
        "task_medium": ("data/incidents/dft_cascade_01.json", load_task_medium),
        "task_hard": ("data/incidents/amp_pzn_adversarial_01.json", load_task_hard)
    }
    
    agent = BaselineAgent(use_mock=use_mock)
    results = {}
    
    for task_name, (fixture, loader) in tasks.items():
        if not os.path.exists(fixture):
            print(f"Skipping {task_name}, fixture not found: {fixture}")
            continue
            
        print(f"Running baseline for {task_name}...")
        env = loader(fixture)
        obs = env.reset()
        
        step_count = 0
        while not obs.done and step_count < 20:
            action = agent.decide_action(obs.model_dump())
            obs, reward = env.step(action)
            step_count += 1
            
        final_score = env.grader.cumulative_score if env.grader else 0.0
        results[task_name] = final_score
        print(f"  Finished {task_name} in {step_count} steps. Score: {final_score:.2f}")

    if results:
        results["average"] = sum(results.values()) / len(results)
    else:
        results["average"] = 0.0
        
    with open("baseline_results.json", "w") as f:
        json.dump(results, f, indent=2)
        
    print(f"\nFinal Baseline Results:\n{json.dumps(results, indent=2)}")

if __name__ == "__main__":
    has_key = "OPENAI_API_KEY" in os.environ
    print(f"Running evaluation with gpt-4o-mini={has_key} mock={not has_key}")
    run_evaluation(use_mock=not has_key)
