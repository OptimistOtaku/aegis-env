from app.graders.base_grader import BaseGrader
from app.models import Tool

class MediumGrader(BaseGrader):
    def __init__(self, config: dict):
        super().__init__(config)
        self.false_positive_component = config.get("false_positive_component")
        self.symptom_components = set(config.get("symptom_components", []))
        
    def _custom_scoring(self, env, action, success, message, breakdown, explanations):
        if action.tool == Tool.ISOLATE and success:
            if action.target_component == self.false_positive_component:
                breakdown["false_positive_penalty"] = -0.20
                explanations.append("Unnecessarily isolated healthy false positive (-0.20)")
                
        if action.tool == Tool.PATCH and success:
            if action.target_component in self.symptom_components:
                breakdown["patch_symptom"] = -0.15
                explanations.append("Patched individual model instead of root cause (-0.15)")
                
        if env.done and env.tick_count <= 12 and len(env.propagation.get_blast_radius()) == 0:
            breakdown["speed_bonus"] = 0.10
            explanations.append("Completed task within 12 ticks bonus (+0.10)")
