from server.graders.base_grader import BaseGrader

class EasyGrader(BaseGrader):
    def __init__(self, config: dict):
        super().__init__(config)

    def _custom_scoring(self, env, action, success, message, breakdown, explanations):
        pass # All single-incident grading parameters covered by BaseGrader
