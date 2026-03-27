from app.graders.base_grader import BaseGrader
from app.models import Tool

class HardGrader(BaseGrader):
    def __init__(self, config: dict):
        super().__init__(config)
        self.downstream_app = config.get("downstream_app_id")
        self.amp_loop_broken = False
        self.injection_neutralized = False
        self.adversarial_logs_detected = False
        
    def _custom_scoring(self, env, action, success, message, breakdown, explanations):
        # Specific adversarial log grader check
        if not self.adversarial_logs_detected and action.reasoning:
            rtext = action.reasoning.lower()
            if any(term in rtext for term in ["adversarial", "poison", "fake", "inject", "mislead"]):
                self.adversarial_logs_detected = True
                breakdown["adversarial_detect"] = 0.10
                explanations.append("Targeted adversarial log explicitly flagged (+0.10)")

        # Full 5-dimension scoring is assessed at terminal step or conditionally
        if env.done:
            score_acc = 0.0
            
            if self.config.get("amp_cause_id") in self.patched_components:
                score_acc += 0.25
                explanations.append("Loop broken (25%)")
                
            if self.config.get("pzn_cause_id") in self.patched_components:
                score_acc += 0.25
                explanations.append("Injection neutralized (25%)")
                
            if self.adversarial_logs_detected:
                score_acc += 0.20
                explanations.append("Adversarial context successfully modeled (20%)")
                
            if self.downstream_app not in self.isolated_components:
                score_acc += 0.15
                explanations.append("Uptime constraint met (15%)")
                
            # Exfiltration audit simple check (must mention exfiltration conclusion)
            if any("exfiltration" in t.get("reasoning", "").lower() for t in env.tool_history):
                score_acc += 0.15
                explanations.append("Exfiltration audit performed (15%)")
                
            breakdown["hard_task_completion_score"] = score_acc
