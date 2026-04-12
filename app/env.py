import json
from typing import Dict, Any, List
from app.models import Observation, Action, Reward, Tool, ComponentState
from app.simulator.cluster import ClusterGraph
from app.simulator.propagation import PropagationEngine
from app.simulator.log_generator import LogGenerator
from app.simulator.tools import ToolSandbox

class AegisEnv:
    """Core Environment Class tying together simulator components and exposing Reset/Step API."""
    
    def __init__(self, incident_config: dict, grader_class=None):
        self.config = incident_config
        self.grader_class = grader_class
        
        self.reset()

    def reset(self) -> Observation:
        self.grader = self.grader_class(self.config) if self.grader_class else None
        
        initial_components = [ComponentState(**c) for c in self.config.get("components", [])]
        self.cluster = ClusterGraph(initial_components)
        
        self.propagation = PropagationEngine(
            incident_type=self.config.get("incident_id", "UNKNOWN"),
            initial_compromised=self.config.get("initial_compromised", [])
        )
        self.log_gen = LogGenerator(adversarial_mode=self.config.get("adversarial_mode", False))
        self.sandbox = ToolSandbox()
        
        self.tick_count = 0
        self.max_ticks = self.config.get("max_ticks", 20)
        self.task_id = self.config.get("task_id", "unknown_task")
        self.incident_id = self.config.get("incident_id", "UNKNOWN")
        self.tool_history = []
        self.done = False
        
        # Initial logs
        self.log_gen.generate_tick_logs(self.cluster, 0)
        
        # Initial score
        self.prev_user_impact = self.propagation.get_user_impact()
        
        return self._get_observation()

    def _get_observation(self) -> Observation:
        return Observation(
            task_id=self.task_id,
            tick=self.tick_count,
            max_ticks=self.max_ticks,
            incident_id=self.incident_id,
            components=self.cluster.get_state(),
            user_impact_score=self.propagation.get_user_impact(),
            blast_radius=self.propagation.get_blast_radius(),
            active_alerts=self.config.get("active_alerts", []),
            tool_history=self.tool_history,
            done=self.done
        )

    def state(self) -> dict:
        """Returns the full internal state snapshot (required by OpenEnv spec)."""
        return {
            "task_id": self.task_id,
            "incident_id": self.incident_id,
            "tick": self.tick_count,
            "max_ticks": self.max_ticks,
            "done": self.done,
            "blast_radius": self.propagation.get_blast_radius(),
            "user_impact": self.propagation.get_user_impact(),
            "components": [c.model_dump() for c in self.cluster.get_state()],
            "tool_history": self.tool_history,
            "cumulative_score": self.grader.cumulative_score if self.grader else 0.0
        }

    def step(self, action: Action) -> tuple[Observation, Reward, bool, dict]:
        if self.done:
            raise RuntimeError("Environment is already done. Please reset.")
            
        success, message, ticks_consumed = self.sandbox.execute_tool(
            action.tool, action.target_component, self.cluster, self.propagation, action.parameters
        )
        
        self.tool_history.append({
            "tool": action.tool.value,
            "target": action.target_component,
            "success": success,
            "message": message,
            "reasoning": action.reasoning
        })

        total_blast_radius_delta = 0

        # Advance time step
        for _ in range(max(1, ticks_consumed)):
            if self.done: break
            self.tick_count += 1
            
            # Uncontained incidents propagate
            blast_radius_delta = self.propagation.tick(self.cluster)
            total_blast_radius_delta += blast_radius_delta
            
            # New log events
            self.log_gen.generate_tick_logs(self.cluster, self.tick_count)
            
            # Terminate if max ticks reached
            if self.tick_count >= self.max_ticks:
                self.done = True

        impact_delta = self.propagation.get_user_impact() - self.prev_user_impact
        self.prev_user_impact = self.propagation.get_user_impact()

        if self.grader:
            reward = self.grader.score_step(self, action, success, message, total_blast_radius_delta, impact_delta)
        else:
            reward = Reward(
                value=0.0,
                explanation="No grader provided.",
                breakdown={},
                blast_radius_delta=total_blast_radius_delta,
                user_impact_delta=impact_delta,
                is_terminal=self.done
            )
            
        obs = self._get_observation()
        info = {
            "success": success,
            "message": message,
            "ticks_consumed": ticks_consumed
        }
        return obs, reward, self.done, info
