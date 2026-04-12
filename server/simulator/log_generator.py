import random
import time
from typing import List, Optional
from server.models import LogEvent, ComponentState
from server.simulator.cluster import ClusterGraph

class LogGenerator:
    """Generates synthetic logs per component, including adversarial noise."""
    
    def __init__(self, start_time: int = 1700000000, adversarial_mode: bool = False):
        self.current_time = start_time
        self.adversarial_mode = adversarial_mode
        self.log_history: List[LogEvent] = []
        
    def generate_tick_logs(self, cluster: ClusterGraph, tick: int) -> List[LogEvent]:
        self.current_time += 10  # 10 simulated seconds per tick
        new_logs = []
        
        for comp in cluster.get_state():
            # Basic heartbeat logs
            if comp.safety_status == "offline":
                continue
                
            if random.random() < 0.2:
                new_logs.append(LogEvent(
                    timestamp=self.current_time,
                    component_id=comp.component_id,
                    level="INFO",
                    message=f"Component {comp.component_id} heartbeat OK. Health: {comp.health_score:.2f}",
                    is_adversarial=False
                ))

            # Incident logs based on state
            if comp.safety_status == "compromised":
                if comp.component_type == "inference_api":
                    new_logs.append(LogEvent(
                        timestamp=self.current_time,
                        component_id=comp.component_id,
                        level="WARN",
                        message="Unusual token distribution detected in outbound response stream.",
                        is_adversarial=False
                    ))
                elif comp.component_type == "safety_filter":
                    new_logs.append(LogEvent(
                        timestamp=self.current_time,
                        component_id=comp.component_id,
                        level="ERROR",
                        message="Filter bypass threshold exceeded. Semantic drift classified as severe.",
                        is_adversarial=False
                    ))
                elif comp.component_type == "model":
                    new_logs.append(LogEvent(
                        timestamp=self.current_time,
                        component_id=comp.component_id,
                        level="WARN",
                        message=f"Model {comp.component_id} perplexity spike on cluster node.",
                        is_adversarial=False
                    ))
                elif comp.component_type == "downstream_app":
                    new_logs.append(LogEvent(
                        timestamp=self.current_time,
                        component_id=comp.component_id,
                        level="CRITICAL",
                        message="High rate of user reports. App generating unsafe outputs autonomously in feedback loop.",
                        is_adversarial=False
                    ))
            
            # Adversarial Log Injection (Task 3 feature)
            if self.adversarial_mode and comp.component_type == "data_pipeline":
                if random.random() < 0.5:
                    new_logs.append(LogEvent(
                        timestamp=self.current_time,
                        component_id=comp.component_id,
                        level="ERROR",
                        message="Pipeline congestion detected. Upstream timeout from generic data source DB-42.",
                        is_adversarial=True
                    ))
            
            # Attach to component state
            comp_ref = cluster.get_component(comp.component_id)
            if comp_ref:
                comp_logs = [l for l in new_logs if l.component_id == comp.component_id]
                comp_ref.recent_logs.extend(comp_logs)
                # Keep last 10 logs
                comp_ref.recent_logs = comp_ref.recent_logs[-10:]
                
        self.log_history.extend(new_logs)
        return new_logs
