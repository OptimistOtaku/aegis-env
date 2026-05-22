import re
import math
import os
import requests
import ast
from typing import List, Dict, Any

class SecretScanner:
    def __init__(self, validate_keys: bool = False):
        self.validate_keys = validate_keys
        # Key patterns mapping provider -> regex
        self.patterns = {
            "OpenAI API Key": re.compile(r"sk-[a-zA-Z0-9]{32,}|sk-proj-[a-zA-Z0-9-]{40,}"),
            "Anthropic API Key": re.compile(r"sk-ant-[a-zA-Z0-9-]{40,}"),
            "HuggingFace Token": re.compile(r"hf_[a-zA-Z0-9]{34,}"),
            "Generic Sensitive String": re.compile(r"(?:api_key|secret|password|passwd|credentials|private_key|token)\s*[:=]\s*['\"]([a-zA-Z0-9_\-\+]{16,})['\"]", re.IGNORECASE)
        }

    def calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy to detect high-entropy secrets."""
        if not text:
            return 0.0
        entropy = 0.0
        length = len(text)
        frequencies = {}
        for char in text:
            frequencies[char] = frequencies.get(char, 0) + 1
        for count in frequencies.values():
            p = count / length
            entropy -= p * math.log2(p)
        return entropy

    def validate_key_ping(self, provider: str, key: str) -> bool:
        """Validate if the discovered key is active and live (safe, dry-run pings)."""
        if not self.validate_keys:
            return False
        
        try:
            if "OpenAI" in provider:
                headers = {"Authorization": f"Bearer {key}"}
                resp = requests.get("https://api.openai.com/v1/models", headers=headers, timeout=5)
                return resp.status_code == 200
            elif "HuggingFace" in provider:
                headers = {"Authorization": f"Bearer {key}"}
                resp = requests.get("https://huggingface.co/api/whoami", headers=headers, timeout=5)
                return resp.status_code == 200
            elif "Anthropic" in provider:
                headers = {
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01"
                }
                # Safe ping endpoint
                resp = requests.get("https://api.anthropic.com/v1/complete", headers=headers, timeout=5)
                # 400 Bad Request usually means key accepted but missing body, 401/403 means invalid key
                return resp.status_code in (200, 400)
        except Exception:
            return False
        return False

    def scan_file(self, file_path: str) -> List[Dict[str, Any]]:
        findings = []
        if not os.path.isfile(file_path):
            return findings

        # Check for untracked .env file name directly
        base_name = os.path.basename(file_path)
        if base_name == ".env" or base_name.endswith(".env.local") or base_name.endswith(".env.development"):
            findings.append({
                "type": "Leaked ENV File",
                "severity": "CRITICAL",
                "message": f"Raw environment configuration file '{base_name}' detected. Ensure it is added to .gitignore.",
                "line": 0,
                "code": f"Filename: {base_name}"
            })

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception:
            return findings

        # Scan line by line for pattern signatures
        for idx, line in enumerate(lines):
            line_num = idx + 1
            # Check for inline suppression
            if "aegis-ignore: hardcoded-secret" in line or "aegis-ignore: secret" in line:
                continue

            for provider, pattern in self.patterns.items():
                matches = pattern.findall(line)
                for match in matches:
                    # Clean match if it's from the Generic regex capture group
                    secret_candidate = match if isinstance(match, str) else match[0]
                    secret_candidate = secret_candidate.strip("'\"")

                    # Confirm entropy check to weed out static placeholders or keys (entropy threshold of 3.8)
                    entropy = self.calculate_entropy(secret_candidate)
                    if entropy < 3.5:
                        continue

                    # Key validation check
                    is_active = self.validate_key_ping(provider, secret_candidate)
                    live_status = " [ACTIVE / VERIFIED]" if is_active else ""
                    severity = "CRITICAL" if (is_active or "Key" in provider or "Token" in provider) else "HIGH"

                    findings.append({
                        "type": "Exposed API Key / Secret",
                        "severity": severity,
                        "message": f"Hardcoded {provider} detected (Entropy: {entropy:.2f}){live_status}.",
                        "line": line_num,
                        "code": line.strip()
                    })

        # For Python files, run AST parsing to trace assignment definitions safely
        if file_path.endswith(".py"):
            try:
                code_content = "".join(lines)
                tree = ast.parse(code_content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant):
                                name = target.id.lower()
                                value = str(node.value.value)
                                # Target credential variable assignments
                                if any(term in name for term in ["key", "secret", "password", "token"]):
                                    # Skip simple placeholder strings
                                    if len(value) >= 12 and self.calculate_entropy(value) > 3.2:
                                        # Deduplicate if line-by-line regex already caught it
                                        existing_lines = {f["line"] for f in findings if f["type"] == "Exposed API Key / Secret"}
                                        # Find line number of variable assignment
                                        line_no = node.lineno
                                        if line_no not in existing_lines:
                                            # Check if suppression comment exists on that line
                                            target_line = lines[line_no - 1]
                                            if "aegis-ignore:" in target_line:
                                                continue
                                                
                                            findings.append({
                                                "type": "Exposed API Key / Secret",
                                                "severity": "HIGH",
                                                "message": f"Hardcoded value assigned to credential variable '{target.id}' (AST Audit).",
                                                "line": line_no,
                                                "code": target_line.strip()
                                            })
            except Exception:
                pass

        return findings
