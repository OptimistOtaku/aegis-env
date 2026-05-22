# 🛡️ Aegis Pre-Deployment Scanner

> **The startup-ready pre-deployment scanner for AI-infused software systems.** Detect prompt injections, exposed secrets, toxic/hallucinated dependencies, compliance taint flows, and architectural vulnerabilities in a single command.

---

## 🚀 Quickstart

Run it instantly in any node repository without installing:
```bash
npx @optimistotaku/aegis-scan
```

### Or install it globally:
```bash
npm install -g @optimistotaku/aegis-scan
```

Once installed globally, scan any directory:
```bash
aegis-scan .
```

---

## 🛠️ Key Security Modules

Aegis is specifically built to address the unique threat vectors of **AI-driven development and web frameworks**:

1. **🔬 Secrets Auditor**: 
   * Scans files for exposed API keys (OpenAI, Anthropic, HuggingFace, AWS, etc.) using high-fidelity regex + AST scanning.
   * Leverages Shannon entropy metrics to detect high-entropy keys.
   * *Feature*: Run with `--validate-keys` to perform dry-run safe authentication checks to confirm if keys are active!

2. **📦 Dependency Hallucination Guard**:
   * Evaluates your `requirements.txt` or `package.json` manifest.
   * Asynchronously cross-references the online NPM/PyPI registries to detect **hallucinated libraries** (made up by AI vibe-coding assistants) or package-squatting vectors (packages registered < 30 days ago).

3. **🧬 Prompt Injection & Fuzzer**:
   * Audits prompts and system boundaries.
   * Run with `--run-fuzzing` to red-team prompts using simulated sandboxed payloads against your configured endpoint.

4. **⚖️ PII Compliance Taint Tracker**:
   * Statically traces variables containing sensitive PII fields (e.g. `user_email`, `phone_number`) flowing directly into model completion APIs without tokenization or mask functions.

5. **🥅 Topology Gatekeeper**:
   * Audits configuration maps to verify the presence of active Moderation Filters (e.g., LlamaGuard) and prevent infinite agentic loop topologies.

---

## 🎯 Fine-Tuning & Line Suppressions

Aegis supports clean, granular developer-centric suppression rules to maintain a zero-noise workspace. 

### Line Bypassing
If a finding is a known safe-exception, simply append `# aegis-ignore: <vulnerability-slug>` on that specific line:
```python
# aegis-ignore: exposed-api-key-/-secret
SK_KEY = "sk-proj-7F9aB1Cd2Ef3Gh4Ij5Kl6Mn7Op8Qr9St0Uv1Wx2Yz3" 
```

### File-Level Bypassing
Add `# aegis-ignore: global` or `# aegis-ignore: global-<vulnerability-slug>` inside the first 20 lines of any file to suppress scanning completely:
```python
# aegis-ignore: global
# This entire file is excluded from all Aegis scanner checks
...
```

### Global Ignore File (`.aegisignore`)
Create an `.aegisignore` file in the root of your workspace to exclude entire directories or file patterns (e.g. `/tests`, `/dist`, `*.log`).

---

## 🤖 CI/CD Integration & Command Configuration

Aegis is engineered to seamlessly fit into GitHub Actions, GitLab CI, or local `pre-commit` hooks.

```bash
# Set severity thresholds to fail builds
aegis-scan . --fail-on HIGH

# Export professional markdown reports
aegis-scan . --format markdown --output aegis-report.md
```

### Complete CLI Command Flags:
* `--fail-on [CRITICAL|HIGH|MEDIUM|LOW]`: Exit with code 1 if findings meet or exceed this threshold.
* `--format [terminal|markdown|json]`: Specify reporting output formats.
* `--output <filename>`: Write scan reports directly to a file.
* `--validate-keys`: Perform safe, lightweight live validation on discovered tokens.
* `--run-fuzzing`: Enable online red-team fuzzing arrays.
* `--ignore-dependencies`: Skip parsing package manifests.

---

## ⚖️ License

Licensed under the Apache-2.0 License.
