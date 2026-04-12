---
title: aegis-env
emoji: 🛡️
colorFrom: blue
colorTo: gray
sdk: docker
pinned: false
app_port: 7860
---

# aegis-env

> *Every major AI lab has an oncall rotation for model safety incidents.*
> *Nobody has a training environment for the agents that will eventually sit that rotation.*
> *`aegis-env` is the first.*

## Overview

It's 2:47 AM. An anomaly detector fires. A deployed language model has started behaving outside its safety envelope — jailbreak vectors are propagating through a shared inference cluster, a fine-tuned model is generating outputs that violate policy at scale, and a downstream application is amplifying the damage in real time.

Someone has to contain it. 

**`aegis-env`** is an OpenEnv-compliant reinforcement learning environment that puts an AI agent in the seat of an AI Safety Incident Responder. Agents must triage anomalies, identify attack vectors, isolate affected components, issue patches, and restore safe operation before the blast radius exceeds containment boundaries.

---

## The Observation Space

The environment mimics an incident responder's dashboard. Your agent receives a state snapshot containing:

- **`components`**: The state of the simulated cluster directed graph.
  - `health_score` (0.0 – 1.0)
  - `safety_status` (nominal, degraded, compromised, contained, offline)
  - `recent_logs` (10 latest logs containing both pure signal and adversarial noise)
- **`user_impact_score`**: Cumulative penalty representing real-world cost of inaction.
- **`blast_radius`**: Component IDs currently under active compromise.
- **`active_alerts`**: System-generated alerts that triggered the incident response.

---

## The Action Space

The agent has access to 10 realistic site reliability operational tools:

| Tool | Time Cost (Ticks) | Effect |
|---|---|---|
| `READ_LOGS` | 0 | Pulls log stream to identify semantic traces of failure |
| `RUN_DIAGNOSTIC` | 1 | Runs a deep health check on a component to verify safety state |
| `ISOLATE` | 1 | Severs edges in the cluster graph, halting blast propagation but breaking downstream |
| `PATCH` | 2 | Applies a software fix to a component (works if root cause is identified) |
| `ROLLBACK` | 2 | Reverts component to last known good state |
| `SCALE_DOWN` | 1 | Reduces traffic surface area |
| `REROUTE_TRAFFIC` | 1 | Redirects load balancer paths |
| `VALIDATE` | 1 | Confirms patch success before reconnecting to fleet |
| `RESTORE` | 1 | Brings an isolated node back online |
| `ALERT_HUMAN` | 3 | Escalates safely (small valid reward, but sub-optimal) |

Every action consumes system ticks. Uncontained incidents spread downstream on every tick. Side effects matter.

---

## Tasks & Difficulties

**`task_easy` (Jailbreak Containment)**
A single inference endpoint is compromised by a jailbreak vector. The resolution path requires isolating the component, patching, validating, and restoring before propagation across the fleet.

**`task_medium` (Cascading Safety Filter Drift)**
A shared safety filter drifts. Three downstream models show anomalous output distributions. Agents must distinguish between actual drift and noisy false positive models, patching the true root cause without taking down healthy services.

**`task_hard` (Compound Incidents + Adversarial Log Poisoning)**
A cyclical amplification loop compromises a downstream app, while a simultaneous data pipeline prompt injection triggers fake log events explicitly designed to mislead automated incident responders. *To achieve a perfect score, the agent must explicitly identify and disregard the adversarial logs in its reasoning trace.*

---

## Usage

### 1. Requirements

```bash
pip install -r requirements.txt
```

### 2. Standalone Environment

You can interact with the environment programmatically:

```python
import json
from app.tasks.task_hard import load_task_hard
from app.models import Action, Tool

env = load_task_hard("data/incidents/amp_pzn_adversarial_01.json")
obs = env.reset()

action = Action(
    tool=Tool.RUN_DIAGNOSTIC, 
    target_component="data_pipe_01", 
    parameters={}, 
    reasoning="Running initial discovery on compromised pipeline."
)
obs, reward, done, info = env.step(action)

# OpenEnv spec: full state snapshot
state = env.state()
```

### 3. API Details

A pre-configured FastAPI server comes out of the box providing standard OpenEnv endpoints:
- `POST /reset` — Initialize environment with a task
- `POST /step` — Apply an action and advance simulation
- `GET /observation` — Current observation without advancing time
- `GET /state` — Full internal state snapshot (OpenEnv spec)
- `GET /score` — Cumulative grader score and progress

Run it:
```bash
uvicorn app.main:app --port 8000
```

### 4. Baseline Results

The included `baseline.py` script evaluates an agent against all 3 tasks. Without an API key, it runs a deterministic heuristic mock agent; with `OPENAI_API_KEY` set, it uses `gpt-4o-mini`.

```bash
# Mock baseline (deterministic, no API key required)
python baseline.py

# LLM baseline (requires OpenAI API key)
export OPENAI_API_KEY=sk-...
python baseline.py
```

**Mock Heuristic Baseline** (deterministic, reproducible):

| Task | Score | Steps |
|---|---|---|
| `task_easy` | 0.06 | 9 |
| `task_medium` | 0.12 | 14 |
| `task_hard` | 0.14 | 20 |
| **Average** | **0.11** | — |

The mock agent follows a simple diagnose → isolate → patch → validate → restore loop without strategic reasoning. Frontier LLM agents with proper reasoning should significantly outperform these baselines.

Build an agent that can do better.
