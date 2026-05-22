import yaml
import os
import json
from typing import List, Dict, Any

class TopologyScanner:
    def __init__(self):
        pass

    def scan_file(self, file_path: str) -> List[Dict[str, Any]]:
        findings = []
        if not os.path.isfile(file_path):
            return findings

        base_name = os.path.basename(file_path).lower()
        is_yaml = base_name.endswith(".yaml") or base_name.endswith(".yml")
        is_json = base_name.endswith(".json")

        if not (is_yaml or is_json) or "topology" not in base_name and "openenv" not in base_name:
            return findings

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                if is_yaml:
                    # Safe load YAML config
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
        except Exception:
            return findings

        if not isinstance(data, dict):
            return findings

        components = data.get("components", [])
        if not isinstance(components, list):
            return findings

        # Map topology
        adj_list = {}
        comp_types = {}
        for comp in components:
            if not isinstance(comp, dict):
                continue
            comp_id = comp.get("component_id")
            comp_type = comp.get("component_type")
            conns = comp.get("connections", [])
            
            if comp_id:
                adj_list[comp_id] = conns
                comp_types[comp_id] = comp_type

        # Audit rule 1: Missing Output Guardrail (OWASP LLM02: Insecure Output Handling)
        # Any edge flowing from a model directly to a downstream app or load balancer
        # without being intercepted by a safety filter/guardrail component.
        for node, conns in adj_list.items():
            if comp_types.get(node) == "model":
                for target in conns:
                    target_type = comp_types.get(target, "")
                    if target_type in ("downstream_app", "load_balancer"):
                        findings.append({
                            "type": "Insecure Output Handling (OWASP LLM02)",
                            "severity": "HIGH",
                            "message": f"Edge maps 'model' component '{node}' directly to '{target}' ({target_type}) without a mediating 'safety_filter' component. Susceptible to unmoderated jailbreak outputs.",
                            "line": 1,
                            "code": f"Topology Link: {node} -> {target}"
                        })

        # Audit rule 2: Cyclic Feedback / Amplification Loops (OWASP LLM04: Model DoS)
        # We trace standard cycles (size 2 or more) that could self-amplify inputs endlessly.
        visited = set()
        path = []

        def dfs_detect_cycles(curr_node) -> List[List[str]]:
            cycles = []
            if curr_node in path:
                # Found cycle! Return path from the node onwards
                cycle_start_idx = path.index(curr_node)
                cycles.append(path[cycle_start_idx:] + [curr_node])
                return cycles

            if curr_node in visited:
                return cycles

            visited.add(curr_node)
            path.append(curr_node)

            for neighbor in adj_list.get(curr_node, []):
                # Ensure neighbor exists in topology to prevent trace faults
                if neighbor in adj_list:
                    cycles.extend(dfs_detect_cycles(neighbor))

            path.pop()
            return cycles

        all_cycles = []
        for node in adj_list:
            if node not in visited:
                all_cycles.extend(dfs_detect_cycles(node))

        for cycle in all_cycles:
            # We flag loops that involve model and app components
            cycle_str = " -> ".join(cycle)
            has_model = any(comp_types.get(node) == "model" for node in cycle)
            has_app = any(comp_types.get(node) in ("downstream_app", "inference_api") for node in cycle)
            
            if has_model and has_app:
                findings.append({
                    "type": "Self-Amplification Cycle (OWASP LLM04)",
                    "severity": "HIGH",
                    "message": f"Cyclic output loop detected: '{cycle_str}'. AI agent outputs feed directly back into system inputs, carrying risk of self-amplifying Prompt Injection or denial of service loops.",
                    "line": 1,
                    "code": f"Cycle: {cycle_str}"
                })

        return findings
