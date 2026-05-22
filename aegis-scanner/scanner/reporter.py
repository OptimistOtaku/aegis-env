import json
import os
import sys
from typing import List, Dict, Any

def safe_print(*args, **kwargs):
    try:
        import builtins
        builtins.print(*args, **kwargs)
    except UnicodeEncodeError:
        emoji_map = {
            "🔬": "[SCAN]",
            "🛡️": "[AEGIS]",
            "🚨": "[CRITICAL]",
            "⚠️": "[WARNING]",
            "🟨": "[MEDIUM]",
            "ℹ️": "[INFO]",
            "✨": "[SUCCESS]",
            "📂": "[DIR]",
            "🔴": "[CRITICAL]",
            "🟠": "[HIGH]",
            "🟡": "[MEDIUM]",
            "🔵": "[LOW]",
            "💡": "[FIX]"
        }
        translated_args = []
        for arg in args:
            arg_str = str(arg)
            for emoji, replacement in emoji_map.items():
                arg_str = arg_str.replace(emoji, replacement)
            encoding = sys.stdout.encoding or 'ascii'
            safe_str = arg_str.encode(encoding, errors='replace').decode(encoding)
            translated_args.append(safe_str)
        import builtins
        builtins.print(*translated_args, **kwargs)

# Override print globally in this module
print = safe_print

class SecurityReporter:
    def __init__(self, findings: Dict[str, List[Dict[str, Any]]]):
        """
        findings: Dict mapping file_path -> List of finding dictionaries
        """
        self.findings = findings
        self.total_critical = 0
        self.total_high = 0
        self.total_medium = 0
        self.total_low = 0
        self._calculate_totals()

    def _calculate_totals(self):
        for file, file_findings in self.findings.items():
            for f in file_findings:
                severity = f.get("severity", "LOW").upper()
                if severity == "CRITICAL":
                    self.total_critical += 1
                elif severity == "HIGH":
                    self.total_high += 1
                elif severity == "MEDIUM":
                    self.total_medium += 1
                else:
                    self.total_low += 1

    def print_terminal_dashboard(self):
        # ANSI Escape Codes for stunning terminal visuals
        RED = "\033[91m"
        ORANGE = "\033[33m"
        YELLOW = "\033[93m"
        BLUE = "\033[94m"
        BOLD = "\033[1m"
        UNDERLINE = "\033[4m"
        NC = "\033[0m" # No Color

        print(f"\n{BOLD}========================================================================{NC}")
        print(f"{BOLD}🛡️  AEGIS PRE-DEPLOYMENT SCAN REPORT{NC}")
        print(f"{BOLD}========================================================================{NC}")

        # Summary Header Bar
        if self.total_critical > 0:
            print(f"{RED}{BOLD}🚨 {self.total_critical} CRITICAL VULNERABILITIES FOUND{NC}")
        if self.total_high > 0:
            print(f"{ORANGE}{BOLD}⚠️  {self.total_high} HIGH-RISK SECURITY ISSUES FOUND{NC}")
        if self.total_medium > 0:
            print(f"{YELLOW}🟨  {self.total_medium} MEDIUM-RISK WARNINGS FOUND{NC}")
        if self.total_low > 0:
            print(f"{BLUE}ℹ️  {self.total_low} LOW-RISK ADVISORIES FOUND{NC}")

        if self.total_critical == 0 and self.total_high == 0 and self.total_medium == 0 and self.total_low == 0:
            print(f"\033[92m{BOLD}✨ SUCCESS: No security issues detected in this workspace! Good job.{NC}")
            print(f"{BOLD}========================================================================{NC}\n")
            return

        print(f"{BOLD}========================================================================{NC}\n")

        # Compile and group findings by file
        for file_path, file_findings in self.findings.items():
            if not file_findings:
                continue
            
            # Print file indicator
            relative_path = os.path.relpath(file_path)
            print(f"{BOLD}{UNDERLINE}File: {relative_path}{NC}")

            for f in file_findings:
                severity = f["severity"].upper()
                line = f["line"]
                line_str = f"Line {line}: " if line > 0 else ""
                
                # Assign severity tags and colors
                if severity == "CRITICAL":
                    sev_tag = f"{RED}[CRITICAL]{NC}"
                elif severity == "HIGH":
                    sev_tag = f"{ORANGE}[HIGH]{NC}"
                elif severity == "MEDIUM":
                    sev_tag = f"{YELLOW}[MEDIUM]{NC}"
                else:
                    sev_tag = f"{BLUE}[LOW]{NC}"

                # Print Finding Card
                print(f"  {sev_tag} {f['type']}")
                print(f"    Details: {f['message']}")
                if line > 0 or f.get("code"):
                    print(f"    {line_str}\033[90m{f['code']}\033[0m")
                
                # Actionable Remediation Hints
                suppression_tag = f['type'].lower().replace(" ", "-")
                print(f"    💡 Fix: Review configuration/code. Inline bypass: '# aegis-ignore: {suppression_tag}'")
                print()

        print(f"{BOLD}========================================================================{NC}")
        total_issues = self.total_critical + self.total_high + self.total_medium
        if total_issues > 0:
            print(f"{RED}{BOLD}Action Required: Scan failed due to unresolved high/critical risks.{NC}")
        else:
            print(f"\033[92m{BOLD}Scan passed with minor advisories.{NC}")
        print(f"{BOLD}========================================================================{NC}\n")

    def export_json(self) -> str:
        """Export raw structured JSON."""
        data = {
            "summary": {
                "critical": self.total_critical,
                "high": self.total_high,
                "medium": self.total_medium,
                "low": self.total_low,
                "total": self.total_critical + self.total_high + self.total_medium + self.total_low
            },
            "findings": self.findings
        }
        return json.dumps(data, indent=2)

    def export_markdown(self) -> str:
        """Export clean GitHub-flavored markdown report."""
        md = []
        md.append("# Aegis Pre-Deployment Security Audit Report\n")
        md.append("## Executive Summary\n")
        md.append("| Severity | Issue Count |")
        md.append("| --- | --- |")
        md.append(f"| 🔴 CRITICAL | {self.total_critical} |")
        md.append(f"| 🟠 HIGH | {self.total_high} |")
        md.append(f"| 🟡 MEDIUM | {self.total_medium} |")
        md.append(f"| 🔵 LOW | {self.total_low} |")
        md.append("\n---\n")

        for file_path, file_findings in self.findings.items():
            if not file_findings:
                continue
            relative_path = os.path.relpath(file_path)
            md.append(f"### 📂 `{relative_path}`\n")
            
            for f in file_findings:
                severity_emoji = "🔴" if f["severity"] == "CRITICAL" else "warning"
                if f["severity"] == "HIGH":
                    severity_emoji = "🟠"
                elif f["severity"] == "MEDIUM":
                    severity_emoji = "🟡"
                elif f["severity"] == "LOW":
                    severity_emoji = "🔵"

                md.append(f"#### {severity_emoji} {f['type']} (`{f['severity']}`)")
                md.append(f"* **Message:** {f['message']}")
                if f['line'] > 0:
                    md.append(f"* **Line {f['line']}:** `{f['code']}`")
                md.append("")
                
        return "\n".join(md)
