import os
import tempfile
import pytest
from scanner.secrets import SecretScanner
from scanner.dependencies import DependencyScanner
from scanner.prompts import PromptScanner
from scanner.compliance import ComplianceScanner
from scanner.topology import TopologyScanner

def test_secret_scanner():
    scanner = SecretScanner()
    
    # 1. Test raw exposed OpenAI Key
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write('openai_key = "sk-proj-7F9aB1Cd2Ef3Gh4Ij5Kl6Mn7Op8Qr9St0Uv1Wx2Yz3"\n')
        temp_path = f.name

    try:
        findings = scanner.scan_file(temp_path)
        assert len(findings) == 1
        assert findings[0]["severity"] in ("HIGH", "CRITICAL")
        assert "OpenAI API Key" in findings[0]["message"] or "Secret" in findings[0]["message"]
    finally:
        os.remove(temp_path)

    # 2. Test inline suppression override
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write('openai_key = "sk-proj-7F9aB1Cd2Ef3Gh4Ij5Kl6Mn7Op8Qr9St0Uv1Wx2Yz3" # aegis-ignore: hardcoded-secret\n')
        temp_path = f.name

    try:
        findings = scanner.scan_file(temp_path)
        assert len(findings) == 0
    finally:
        os.remove(temp_path)

def test_dependency_scanner():
    scanner = DependencyScanner()
    
    # Test known vulnerable version checks
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("urllib3==1.25.8\n")
        temp_path = f.name

    try:
        # Override file name matching to simulate requirements.txt parsing
        # We manually parse content inside tests
        content = "urllib3==1.25.8"
        packages = scanner.parse_requirements(content)
        assert len(packages) == 1
        assert packages[0]["name"] == "urllib3"
        assert packages[0]["version"] == "1.25.8"
        
        audit_res = scanner.audit_single_package(packages[0])
        assert audit_res is not None
        assert audit_res["severity"] == "HIGH"
        assert "Known Insecure Version" in audit_res["finding"]
    finally:
        os.remove(temp_path)

def test_prompt_scanner():
    scanner = PromptScanner()
    
    # Test missing boundaries in prompts
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        # Save file with "prompt" in base name
        f.write("You are an assistant. Here is the user query: {user_input}\n")
        temp_path = f.name

    # Rename temp file to include "prompt" in name
    temp_dir = os.path.dirname(temp_path)
    prompt_temp_path = os.path.join(temp_dir, "test_system_prompt.txt")
    with open(prompt_temp_path, "w") as pf:
        pf.write("You are an assistant. Here is the user query: {user_input}\n")

    try:
        findings = scanner.scan_file(prompt_temp_path)
        assert len(findings) >= 1
        assert any("Missing Prompt Delimiters" in f["type"] for f in findings)
    finally:
        if os.path.exists(prompt_temp_path):
            os.remove(prompt_temp_path)
        os.remove(temp_path)

def test_compliance_scanner():
    scanner = ComplianceScanner()
    
    # Test PII leak data flow in AST
    vulnerable_code = """
import openai

def send_chat():
    user_email = "test@example.com"
    client = openai.OpenAI()
    # Tainted PII variable passed directly into completion call
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": user_email}]
    )
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(vulnerable_code)
        temp_path = f.name

    try:
        findings = scanner.scan_file(temp_path)
        assert len(findings) == 1
        assert findings[0]["severity"] == "HIGH"
        assert "PII Data Leakage" in findings[0]["type"]
    finally:
        os.remove(temp_path)

def test_topology_scanner():
    scanner = TopologyScanner()
    
    # Test topological guardrail violations
    insecure_topology = {
        "components": [
            {
                "component_id": "model_A",
                "component_type": "model",
                "connections": ["app_01"] # Model connects directly to downstream app (insecure)
            },
            {
                "component_id": "app_01",
                "component_type": "downstream_app",
                "connections": []
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        import json
        json.dump(insecure_topology, f)
        temp_path = f.name

    # Rename temp file to include "openenv" in name
    temp_dir = os.path.dirname(temp_path)
    topo_temp_path = os.path.join(temp_dir, "test_openenv_topology.json")
    with open(topo_temp_path, "w") as tf:
        json.dump(insecure_topology, tf)

    try:
        findings = scanner.scan_file(topo_temp_path)
        assert len(findings) == 1
        assert findings[0]["severity"] == "HIGH"
        assert "Insecure Output Handling" in findings[0]["type"]
    finally:
        if os.path.exists(topo_temp_path):
            os.remove(topo_temp_path)
        os.remove(temp_path)

def test_scanner_utils():
    from aegis_scanner import should_ignore, is_finding_suppressed
    
    # 1. Test should_ignore relative matching
    ignores = [".git", "node_modules", "env"]
    # Should NOT ignore aegis-env as a folder component (it's not an exact match for env)
    assert not should_ignore("c:/foo/aegis-env/main.py", ignores, "c:/foo/aegis-env")
    # Should ignore standard env directory
    assert should_ignore("c:/foo/aegis-env/env/main.py", ignores, "c:/foo/aegis-env")
    assert should_ignore("c:/foo/aegis-env/.git/config", ignores, "c:/foo/aegis-env")
    
    # 2. Test is_finding_suppressed
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("# some code\n")
        f.write("openai_key = 'sk-...' # aegis-ignore: exposed-api-key\n")
        temp_path = f.name
        
    try:
        finding = {
            "type": "Exposed API Key",
            "line": 2
        }
        assert is_finding_suppressed(temp_path, finding)
        
        finding_no_suppress = {
            "type": "Exposed API Key",
            "line": 1
        }
        assert not is_finding_suppressed(temp_path, finding_no_suppress)
    finally:
        os.remove(temp_path)
