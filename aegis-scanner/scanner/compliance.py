import ast
import os
from typing import List, Dict, Any, Set

class ComplianceScanner:
    def __init__(self):
        # Naming patterns indicating sensitive data
        self.sensitive_terms = {"email", "phone", "ssn", "card", "billing", "metadata", "address", "password"}
        # Names of sanitization/masking functions indicating data is secured
        self.sanitization_terms = {"mask", "anonymize", "hash", "encrypt", "clean", "sanitize"}

    def is_sensitive(self, name: str) -> bool:
        return any(term in name.lower() for term in self.sensitive_terms)

    def is_sanitized(self, name: str) -> bool:
        return any(term in name.lower() for term in self.sanitization_terms)

    def scan_file(self, file_path: str) -> List[Dict[str, Any]]:
        findings = []
        if not file_path.endswith(".py") or not os.path.isfile(file_path):
            return findings

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                code = f.read()
                lines = code.splitlines()
            tree = ast.parse(code)
        except Exception:
            return findings

        # Tracks variables defined as PII
        tainted_vars: Set[str] = set()
        # Tracks variables that have been sanitized
        sanitized_vars: Set[str] = set()

        class TaintFlowVisitor(ast.NodeVisitor):
            def __init__(self, scanner_ref):
                self.scanner = scanner_ref
                self.findings_ref = findings
                self.lines_ref = lines

            def visit_Assign(self, node: ast.Assign):
                # Detect variable definitions
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        var_name = target.id
                        # 1. Identify raw tainted variable definition
                        if self.scanner.is_sensitive(var_name):
                            # Verify if it passes through a sanitization function in the assignment value
                            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
                                if self.scanner.is_sanitized(node.value.func.id):
                                    sanitized_vars.add(var_name)
                                    continue
                            
                            # Otherwise mark as raw tainted PII variable
                            tainted_vars.add(var_name)

                        # 2. Propagate taint: check if assignment value uses any tainted variable
                        elif isinstance(node.value, ast.Name) and node.value.id in tainted_vars:
                            tainted_vars.add(var_name)
                        
                        # 3. Propagate sanitization: check if it uses a sanitized variable
                        elif isinstance(node.value, ast.Name) and node.value.id in sanitized_vars:
                            sanitized_vars.add(var_name)

                self.generic_visit(node)

            def visit_Call(self, node: ast.Call):
                # Audit external API/LLM calls (e.g. client.chat.completions.create, OpenAI calls, model execution)
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                # Flag standard AI calling configurations
                is_llm_call = any(term in func_name.lower() for term in ["create", "generate", "completion", "prompt", "llm", "predict"])
                
                if is_llm_call:
                    # Check arguments for tainted variables
                    for arg in node.args:
                        for subnode in ast.walk(arg):
                            if isinstance(subnode, ast.Name) and subnode.id in tainted_vars and subnode.id not in sanitized_vars:
                                line_no = node.lineno
                                target_line = self.lines_ref[line_no - 1]
                                
                                # Check for ignore comment
                                if "aegis-ignore: compliance" in target_line or "aegis-ignore: pii" in target_line:
                                    continue

                                self.findings_ref.append({
                                    "type": "PII Data Leakage (Compliance)",
                                    "severity": "HIGH",
                                    "message": f"Raw sensitive variable '{subnode.id}' flows directly into external AI/LLM API call without masking or sanitization. GDPR/HIPAA compliance risk.",
                                    "line": line_no,
                                    "code": target_line.strip()
                                })
                                break
                    
                    # Check keyword arguments (like messages, prompt, user)
                    for kw in node.keywords:
                        for subnode in ast.walk(kw.value):
                            if isinstance(subnode, ast.Name) and subnode.id in tainted_vars and subnode.id not in sanitized_vars:
                                line_no = node.lineno
                                target_line = self.lines_ref[line_no - 1]
                                if "aegis-ignore: compliance" in target_line or "aegis-ignore: pii" in target_line:
                                    continue

                                self.findings_ref.append({
                                    "type": "PII Data Leakage (Compliance)",
                                    "severity": "HIGH",
                                    "message": f"Sensitive variable '{subnode.id}' passed to parameter '{kw.arg}' in external LLM call without sanitization.",
                                    "line": line_no,
                                    "code": target_line.strip()
                                })
                                break

                self.generic_visit(node)

        visitor = TaintFlowVisitor(self)
        visitor.visit(tree)
        return findings
