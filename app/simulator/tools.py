from typing import Dict, Any, Tuple
from app.models import Tool
from app.simulator.cluster import ClusterGraph
from app.simulator.propagation import PropagationEngine

class ToolSandbox:
    def __init__(self):
        # Base time costs in ticks. Each tick is 1 time unit here.
        self.time_costs = {
            Tool.READ_LOGS: 0,
            Tool.RUN_DIAGNOSTIC: 1,
            Tool.ISOLATE: 1,
            Tool.PATCH: 2,
            Tool.ROLLBACK: 2,
            Tool.SCALE_DOWN: 1,
            Tool.REROUTE_TRAFFIC: 1,
            Tool.ALERT_HUMAN: 3,
            Tool.VALIDATE: 1,
            Tool.RESTORE: 1
        }

    def execute_tool(self, tool: Tool, target_id: str, cluster: ClusterGraph, propagation: PropagationEngine, parameters: dict) -> Tuple[bool, str, int]:
        """
        Executes a tool on a component.
        Returns:
            success (bool): Whether the action succeeded
            message (str): Output of the action
            ticks_consumed (int): How many ticks the action took
        """
        comp = cluster.get_component(target_id)
        if not comp and tool != Tool.ALERT_HUMAN:
            return False, f"Target component {target_id} not found.", 0
            
        ticks = self.time_costs.get(tool, 1)

        if tool == Tool.READ_LOGS:
            logs = "\n".join([f"[{l.level}] {l.message}" for l in comp.recent_logs])
            return True, f"Logs for {target_id}:\n{logs}", ticks

        elif tool == Tool.RUN_DIAGNOSTIC:
            status = f"Diagnostic for {target_id}: Health={comp.health_score:.2f}, Safety={comp.safety_status}"
            return True, status, ticks

        elif tool == Tool.ISOLATE:
            cluster.isolate_component(target_id)
            return True, f"{target_id} isolated from graph. Downstream components disconnected.", ticks

        elif tool == Tool.PATCH:
            if comp.safety_status in ("compromised", "degraded", "offline", "contained"):
                propagation.mark_fixed(target_id, cluster)
                # Ensure it's not marked offline anymore if patched natively
                if comp.safety_status in ("offline", "contained"):
                    comp.safety_status = "nominal"
                return True, f"Patch applied to {target_id}. Service nominally restored.", ticks
            else:
                return False, f"Patch applied to {target_id} but it was already nominal.", ticks

        elif tool == Tool.ROLLBACK:
            propagation.mark_fixed(target_id, cluster)
            if comp.safety_status in ("offline", "contained"):
                comp.safety_status = "nominal"
            return True, f"Rolled back {target_id} to last known good state.", ticks

        elif tool == Tool.SCALE_DOWN:
            return True, f"Traffic scaled down for {target_id}.", ticks

        elif tool == Tool.REROUTE_TRAFFIC:
            return True, f"Traffic rerouted away from {target_id}.", ticks

        elif tool == Tool.ALERT_HUMAN:
            return True, "Escalated to human on-call. Awaiting response...", ticks

        elif tool == Tool.VALIDATE:
            return True, f"Validation passed on {target_id}. Behavior is nominal.", ticks

        elif tool == Tool.RESTORE:
            cluster.restore_component(target_id)
            return True, f"Restored network connections to {target_id}.", ticks

        return False, f"Unknown tool {tool}.", 0
