#!/usr/bin/env python3
import os
import sys
import argparse
from typing import List, Dict, Any

# Ensure stdout supports UTF-8 on Windows and other platforms where possible
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

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

# Import modular scanners
from scanner.secrets import SecretScanner
from scanner.dependencies import DependencyScanner
from scanner.prompts import PromptScanner
from scanner.compliance import ComplianceScanner
from scanner.topology import TopologyScanner
from scanner.reporter import SecurityReporter

def load_ignore_patterns(target_dir: str) -> List[str]:
    """Loads exclusion glob patterns from .aegisignore or defaults."""
    default_ignores = [
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "env",
        "dist",
        "build",
        "tests",
        ".dockerignore",
        ".gitignore",
        "uv.lock",
        "poetry.lock"
    ]
    ignore_path = os.path.join(target_dir, ".aegisignore")
    if os.path.exists(ignore_path):
        try:
            with open(ignore_path, "r") as f:
                patterns = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
                return default_ignores + patterns
        except Exception:
            pass
    return default_ignores

def should_ignore(path: str, ignore_patterns: List[str], target_dir: str = None) -> bool:
    """Checks if a file path matches any exclusion list pattern."""
    if target_dir:
        try:
            rel_path = os.path.relpath(path, target_dir)
        except Exception:
            rel_path = path
    else:
        rel_path = path

    normalized_path = rel_path.replace("\\", "/")
    parts = normalized_path.split("/")
    
    for p in ignore_patterns:
        # Match exact folder names, exact file names, or exact endings
        if p in parts or normalized_path.endswith(p) or os.path.basename(path) == p:
            return True
        # Simple glob-like wildcard support if pattern contains '*'
        if "*" in p:
            import fnmatch
            if fnmatch.fnmatch(normalized_path, p) or fnmatch.fnmatch(os.path.basename(path), p):
                return True
    return False

def is_finding_suppressed(file_path: str, finding: Dict[str, Any]) -> bool:
    """Checks if a finding is suppressed via inline comments in the file."""
    line_num = finding.get("line", 0)
    finding_type = finding.get("type", "")
    slug = finding_type.lower().replace(" ", "-")

    if not os.path.exists(file_path):
        return False

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception:
        return False

    # Case 1: Line-specific suppression check
    if line_num > 0 and line_num <= len(lines):
        line_content = lines[line_num - 1]
        if "aegis-ignore" in line_content:
            # Match specific slug or generic ignore in comments
            if f"aegis-ignore: {slug}" in line_content or "aegis-ignore" in line_content.split("#")[-1] or "aegis-ignore" in line_content.split("//")[-1]:
                return True

    # Case 2: Global/metadata check (checks first 20 lines for file-wide overrides)
    for l_content in lines[:20]:
        if "aegis-ignore: global" in l_content:
            if f"aegis-ignore: global-{slug}" in l_content or "aegis-ignore: global" in l_content:
                return True

    return False

def main():
    parser = argparse.ArgumentParser(
        description="Aegis Pre-Deployment Scanner - Enterprise Security for AI-led Projects."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to the directory to scan (default: current folder)."
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="Report export format (default: text dashboard)."
    )
    parser.add_argument(
        "--output",
        default=None,
        help="File path to write the scan findings report."
    )
    parser.add_argument(
        "--validate-keys",
        action="store_true",
        help="Perform safe live dry-run checks to verify if exposed keys are active."
    )
    parser.add_argument(
        "--run-fuzzing",
        action="store_true",
        help="Execute safe, low-cost dynamic prompt red-teaming checks using local OpenAI keys."
    )
    parser.add_argument(
        "--fail-on",
        choices=["CRITICAL", "HIGH", "MEDIUM", "LOW"],
        default="HIGH",
        help="Minimum severity threshold to trigger a non-zero exit code (default: HIGH)."
    )

    args = parser.parse_args()
    target_dir = os.path.abspath(args.path)

    if not os.path.exists(target_dir):
        print(f"Error: Target directory '{target_dir}' does not exist.")
        sys.exit(1)

    print(f"🔬 Aegis scanning workspace: {target_dir} ...")

    # Load ignore rules
    ignores = load_ignore_patterns(target_dir)

    # Initialize modular scanning layers
    secret_scanner = SecretScanner(validate_keys=args.validate_keys)
    dep_scanner = DependencyScanner()
    prompt_scanner = PromptScanner(run_fuzzing=args.run_fuzzing)
    compliance_scanner = ComplianceScanner()
    topo_scanner = TopologyScanner()

    all_findings: Dict[str, List[Dict[str, Any]]] = {}

    # Recursively traverse directory tree
    for root, dirs, files in os.walk(target_dir):
        # Filter directories in-place to respect ignored folders
        dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d), ignores, target_dir)]

        for file in files:
            file_path = os.path.join(root, file)
            if should_ignore(file_path, ignores, target_dir):
                continue

            file_findings = []

            # 1. Secret scanning runs on all readable code assets
            if not file.endswith((".png", ".jpg", ".jpeg", ".pdf", ".pyc", ".db", ".zip", ".tar.gz")):
                file_findings.extend(secret_scanner.scan_file(file_path))

            # 2. Dependency scanning
            if file in ("requirements.txt", "package.json"):
                file_findings.extend(dep_scanner.scan_file(file_path))

            # 3. Prompt audits
            # Checks prompt yaml, prompt text files, or files with prompt assignments
            base_name_lower = file.lower()
            if "prompt" in base_name_lower or file.endswith((".txt", ".yaml", ".json", ".py", ".js")):
                file_findings.extend(prompt_scanner.scan_file(file_path))

            # 4. AST Compliance taint scanning (Python specific)
            if file.endswith(".py"):
                file_findings.extend(compliance_scanner.scan_file(file_path))

            # 5. Architecture Topology audits
            if "openenv" in base_name_lower or "topology" in base_name_lower:
                file_findings.extend(topo_scanner.scan_file(file_path))

            if file_findings:
                all_findings[file_path] = file_findings

    # Filter out any findings that are suppressed via inline comments
    filtered_findings: Dict[str, List[Dict[str, Any]]] = {}
    for file_path, file_findings in all_findings.items():
        active_findings = []
        for f in file_findings:
            if not is_finding_suppressed(file_path, f):
                active_findings.append(f)
        if active_findings:
            filtered_findings[file_path] = active_findings
            
    all_findings = filtered_findings

    # Process and compile security findings
    reporter = SecurityReporter(all_findings)

    # Output reports
    if args.format == "text":
        reporter.print_terminal_dashboard()
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as out_file:
                    out_file.write(reporter.export_markdown())
                print(f"Report successfully saved in markdown format to {args.output}")
            except Exception as e:
                print(f"Error saving file: {e}")
    elif args.format == "json":
        json_output = reporter.export_json()
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as out_file:
                    out_file.write(json_output)
                print(f"Report successfully saved in JSON format to {args.output}")
            except Exception as e:
                print(f"Error saving file: {e}")
        else:
            print(json_output)
    elif args.format == "markdown":
        md_output = reporter.export_markdown()
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as out_file:
                    out_file.write(md_output)
                print(f"Report successfully saved in Markdown format to {args.output}")
            except Exception as e:
                print(f"Error saving file: {e}")
        else:
            print(md_output)

    # Trigger exit-code controls to block unsafe commits/deploys in CI/CD pipeline
    fail_threshold = args.fail_on.upper()
    severity_order = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    threshold_idx = severity_order.index(fail_threshold)

    fail_build = False
    for file_path, file_findings in all_findings.items():
        for f in file_findings:
            f_severity = f["severity"].upper()
            f_idx = severity_order.index(f_severity)
            if f_idx >= threshold_idx:
                fail_build = True
                break
        if fail_build:
            break

    if fail_build:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
