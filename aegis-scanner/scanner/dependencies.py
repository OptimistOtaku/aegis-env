import os
import re
import json
import requests
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import List, Dict, Any

class DependencyScanner:
    def __init__(self):
        # A lightweight blocklist of deprecated or vulnerable package versions
        self.vulnerable_blocklist = {
            "urllib3": "<1.26.15",
            "requests": "<2.31.0",
            "cryptography": "<41.0.0",
            "aiohttp": "<3.8.6",
            "jinja2": "<3.1.3"
        }

    def parse_requirements(self, content: str) -> List[Dict[str, str]]:
        """Parses python requirements.txt dependencies."""
        packages = []
        pattern = re.compile(r"^\s*([a-zA-Z0-9_\-\[\]]+)(?:\s*(==|>=|<=|>|<)\s*([a-zA-Z0-9_\-\.]+))?")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            
            # Remove inline comments
            line = line.split("#")[0].strip()
            match = pattern.match(line)
            if match:
                name = match.group(1).lower()
                op = match.group(2) or "=="
                version = match.group(3) or "latest"
                packages.append({"name": name, "version": version, "op": op, "type": "pypi"})
        return packages

    def parse_package_json(self, content: str) -> List[Dict[str, str]]:
        """Parses javascript package.json dependencies."""
        packages = []
        try:
            data = json.loads(content)
            deps = data.get("dependencies", {})
            dev_deps = data.get("devDependencies", {})
            for name, version in {**deps, **dev_deps}.items():
                # Strip semantic version symbols (^, ~, *, etc.)
                clean_version = re.sub(r"[^\d\.]", "", version) or "latest"
                packages.append({"name": name.lower(), "version": clean_version, "op": "==", "type": "npm"})
        except Exception:
            pass
        return packages

    def check_registry_pypi(self, pkg_name: str) -> Dict[str, Any]:
        """Queries PyPI API to audit package metadata."""
        url = f"https://pypi.org/pypi/{pkg_name}/json"
        try:
            resp = requests.get(url, timeout=3)
            if resp.status_code == 404:
                return {"exists": False, "created_at": None, "hallucinated": True}
            
            if resp.status_code == 200:
                data = resp.json()
                releases = data.get("releases", {})
                info = data.get("info", {})
                
                # Retrieve registration/creation time of package
                created_at = None
                if releases:
                    # Find oldest release timestamp
                    times = []
                    for rel_version, uploads in releases.items():
                        for upload in uploads:
                            upload_time = upload.get("upload_time")
                            if upload_time:
                                try:
                                    times.append(datetime.fromisoformat(upload_time.replace("Z", "+00:00")))
                                except Exception:
                                    pass
                    if times:
                        created_at = min(times)
                
                # Check age
                is_recent = False
                if created_at:
                    age_days = (datetime.now(timezone.utc) - created_at.astimezone(timezone.utc)).days
                    # Flag packages created in last 30 days as high risk of hallucination hijacking targets
                    is_recent = age_days < 30
                
                return {"exists": True, "created_at": created_at, "hallucinated": is_recent}
        except Exception:
            pass
        return {"exists": True, "created_at": None, "hallucinated": False}

    def check_registry_npm(self, pkg_name: str) -> Dict[str, Any]:
        """Queries NPM registry API to audit package metadata."""
        # Clean scope if scoped npm package
        clean_name = pkg_name.replace("/", "%2F")
        url = f"https://registry.npmjs.org/{clean_name}"
        try:
            resp = requests.get(url, timeout=3)
            if resp.status_code == 404:
                return {"exists": False, "created_at": None, "hallucinated": True}
            
            if resp.status_code == 200:
                data = resp.json()
                time_data = data.get("time", {})
                created_str = time_data.get("created")
                
                created_at = None
                is_recent = False
                if created_str:
                    try:
                        created_at = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                        age_days = (datetime.now(timezone.utc) - created_at.astimezone(timezone.utc)).days
                        is_recent = age_days < 30
                    except Exception:
                        pass
                
                return {"exists": True, "created_at": created_at, "hallucinated": is_recent}
        except Exception:
            pass
        return {"exists": True, "created_at": None, "hallucinated": False}

    def audit_single_package(self, pkg: Dict[str, str]) -> Dict[str, Any]:
        name = pkg["name"]
        pkg_type = pkg["type"]
        
        # 1. Run local CVE blocklist check
        if name in self.vulnerable_blocklist:
            expected = self.vulnerable_blocklist[name]
            return {
                "package": name,
                "type": pkg_type,
                "finding": "Known Insecure Version",
                "severity": "HIGH",
                "message": f"Dependency '{name}' matches a known high-severity vulnerability pattern ({expected}). Update recommended."
            }

        # 2. Run online hallucination registry validation
        if pkg_type == "pypi":
            status = self.check_registry_pypi(name)
        else:
            status = self.check_registry_npm(name)

        if not status["exists"]:
            return {
                "package": name,
                "type": pkg_type,
                "finding": "Hallucinated Package Risk",
                "severity": "CRITICAL",
                "message": f"Package '{name}' DOES NOT exist on public registries! Crucial risk of AI Package Hallucination Hijacking if registered by third-parties."
            }
        
        if status["hallucinated"]:
            return {
                "package": name,
                "type": pkg_type,
                "finding": "Suspect Newly-Registered Package",
                "severity": "HIGH",
                "message": f"Package '{name}' was registered within the last 30 days. Verify its legitimacy to prevent typosquatting/malicious payload injections."
            }
            
        return None

    def scan_file(self, file_path: str) -> List[Dict[str, Any]]:
        findings = []
        if not os.path.isfile(file_path):
            return findings

        base_name = os.path.basename(file_path)
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return findings

        # Detect parser type
        packages = []
        if base_name == "requirements.txt":
            packages = self.parse_requirements(content)
        elif base_name == "package.json":
            packages = self.parse_package_json(content)
        else:
            return findings

        if not packages:
            return findings

        # Execute concurrent threat audits asynchronously using a thread pool
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(self.audit_single_package, packages))

        for res in results:
            if res:
                findings.append({
                    "type": res["finding"],
                    "severity": res["severity"],
                    "message": res["message"],
                    "line": 0,
                    "code": f"Import Target: {res['package']} ({res['type']})"
                })

        return findings
