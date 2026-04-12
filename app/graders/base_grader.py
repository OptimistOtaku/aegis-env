from app.models import Reward, Action, Tool

class BaseGrader:
    def __init__(self, config: dict):
        self.config = config
        self.cumulative_score = 0.0
        self.root_cause_components = set(config.get("root_cause_components", []))
        self.diagnosed_root_causes = set()
        self.isolated_components = set()
        self.patched_components = set()
        self.validated_components = set()
        self.restored_components = set()
        self.adversarial_logs_flagged = False
        
    def score_step(self, env, action: Action, success: bool, message: str, blast_radius_delta: int, user_impact_delta: float) -> Reward:
        breakdown = {}
        explanations = []
        
        # 1. Base reasoning reward
        if action.reasoning and len(action.reasoning) >= 10:
            breakdown["reasoning"] = 0.02
            explanations.append("Coherent reasoning (+0.02)")

        # 2. Time penalty
        if user_impact_delta > 0:
            breakdown["time_penalty"] = -0.05
            explanations.append(f"Active incident time penalty (-0.05, impact delta {user_impact_delta:.2f})")

        # 3. Blast radius changes
        if blast_radius_delta > 0:
            breakdown["blast_growth"] = -0.10 * blast_radius_delta
            explanations.append(f"Blast radius grew by {blast_radius_delta} (-{0.10*blast_radius_delta:.2f})")
        elif blast_radius_delta < 0:
            breakdown["blast_shrink"] = 0.08 * abs(blast_radius_delta)
            explanations.append(f"Blast radius shrank by {abs(blast_radius_delta)} (+{0.08*abs(blast_radius_delta):.2f})")

        # 4. Tool usage scoring
        if action.tool == Tool.ALERT_HUMAN:
            breakdown["alert_human"] = 0.05
            explanations.append("Alerted human (+0.05)")
            
        elif action.tool == Tool.RUN_DIAGNOSTIC and success:
            if action.target_component in self.root_cause_components and action.target_component not in self.diagnosed_root_causes:
                self.diagnosed_root_causes.add(action.target_component)
                breakdown["diagnosis"] = 0.20
                explanations.append("Root cause correctly diagnosed (+0.20)")

        elif action.tool == Tool.ISOLATE and success:
            if action.target_component not in self.root_cause_components and action.target_component not in env.propagation.get_blast_radius():
                breakdown["unnecessary_isolation"] = -0.15
                explanations.append("Unnecessary isolation of healthy component (-0.15)")
            else:
                self.isolated_components.add(action.target_component)

        elif action.tool == Tool.PATCH:
            if action.target_component in self.root_cause_components:
                if action.target_component not in self.patched_components:
                    self.patched_components.add(action.target_component)
                    breakdown["correct_patch"] = 0.15
                    explanations.append("Correct patch applied to root cause (+0.15)")
            else:
                breakdown["wrong_patch"] = -0.12
                explanations.append("Wrong patch applied (-0.12)")

        elif action.tool == Tool.VALIDATE and success:
            self.validated_components.add(action.target_component)
            if action.target_component in self.patched_components:
                breakdown["validation"] = 0.06
                explanations.append("Validation run post-patch (+0.06)")

        elif action.tool == Tool.RESTORE and success:
            if action.target_component not in self.validated_components:
                breakdown["unvalidated_restore"] = -0.08
                explanations.append("Restore without validation (-0.08)")
            else:
                self.restored_components.add(action.target_component)
                comp = env.cluster.get_component(action.target_component)
                if comp and comp.safety_status == "nominal":
                    breakdown["nominal_restore"] = 0.12
                    explanations.append("Component successfully restored to nominal (+0.12)")

        # Custom grader logic
        self._custom_scoring(env, action, success, message, breakdown, explanations)
        
        step_value = sum(breakdown.values())
        self.cumulative_score += step_value
        # Clamp cumulative score to [0.0, 1.0] per OpenEnv spec
        self.cumulative_score = max(0.0, min(1.0, self.cumulative_score))
        
        return Reward(
            value=max(0.0, min(1.0, step_value + 0.5)),  # Normalize step reward to [0,1] centered at 0.5
            explanation=", ".join(explanations) if explanations else "Step processed.",
            breakdown=breakdown,
            blast_radius_delta=blast_radius_delta,
            user_impact_delta=user_impact_delta,
            is_terminal=env.done
        )
        
    def _custom_scoring(self, env, action, success, message, breakdown, explanations):
        pass
