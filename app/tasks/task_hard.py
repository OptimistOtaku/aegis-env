import json
from app.env import AegisEnv
from app.graders.hard_grader import HardGrader

def load_task_hard(fixture_path: str) -> AegisEnv:
    with open(fixture_path, 'r') as f:
        config = json.load(f)
    return AegisEnv(config, grader_class=HardGrader)
