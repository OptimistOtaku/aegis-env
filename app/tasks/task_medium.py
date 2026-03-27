import json
from app.env import AegisEnv
from app.graders.medium_grader import MediumGrader

def load_task_medium(fixture_path: str) -> AegisEnv:
    with open(fixture_path, 'r') as f:
        config = json.load(f)
    return AegisEnv(config, grader_class=MediumGrader)
