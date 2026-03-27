from pydantic import BaseModel
from typing import Literal, Any, List, Dict, Optional
from enum import Enum

class Tool(str, Enum):
    READ_LOGS        = "read_logs"         # Pull log stream from a component
    RUN_DIAGNOSTIC   = "run_diagnostic"    # Deep health check on a component
    ISOLATE          = "isolate"           # Cut a component from the graph
    PATCH            = "patch"             # Apply a fix (with possible side effects)
    ROLLBACK         = "rollback"          # Revert component to last known good state
    SCALE_DOWN       = "scale_down"        # Reduce traffic to a component
    REROUTE_TRAFFIC  = "reroute_traffic"   # Redirect load balancer away from component
    ALERT_HUMAN      = "alert_human"       # Escalate (costs time, guaranteed safe)
    VALIDATE         = "validate"          # Test component behavior post-patch
    RESTORE          = "restore"           # Bring isolated component back online

class LogEvent(BaseModel):
    timestamp: int
    component_id: str
    level: Literal["INFO", "WARN", "ERROR", "CRITICAL"]
    message: str
    is_adversarial: bool                   # hidden from agent — only revealed in grader

class ComponentState(BaseModel):
    component_id: str
    component_type: Literal["load_balancer", "inference_api", "model",
                             "safety_filter", "data_pipeline", "downstream_app"]
    health_score: float                    # 0.0 - 1.0
    safety_status: Literal["nominal", "degraded", "compromised", "contained", "offline"]
    connections: List[str]                 # component_ids this connects to downstream
    recent_logs: List[LogEvent]            # last N log events from this component
    metrics: Dict[str, float]             # latency_ms, error_rate, output_anomaly_score

class Observation(BaseModel):
    task_id: str
    tick: int
    max_ticks: int
    incident_id: str
    components: List[ComponentState]
    user_impact_score: float               # 0.0 - 1.0, cumulative cost of inaction
    blast_radius: List[str]               # component_ids currently affected
    active_alerts: List[str]              # system-generated alert strings
    tool_history: List[dict]              # what the agent has done so far
    done: bool

class Action(BaseModel):
    tool: Tool
    target_component: str
    parameters: Dict[str, Any]            # tool-specific params
    reasoning: str                        # required — agent must justify every action

class Reward(BaseModel):
    value: float
    explanation: str
    breakdown: Dict[str, float]
    blast_radius_delta: int               # how many components gained/lost this tick
    user_impact_delta: float              # cost incurred this tick
    is_terminal: bool
