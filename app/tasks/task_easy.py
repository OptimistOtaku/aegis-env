import json
from app.env import AegisEnv
from app.graders.easy_grader import EasyGrader

def load_task_easy(fixture_path: str) -> AegisEnv:
    with open(fixture_path, 'r') as f:
        config = json.load(f)
    return AegisEnv(config, grader_class=EasyGrader)
