"""
Security and Compliance Vulnerability Scanner
Static Analysis & Heuristic Engine for detecting security anti-patterns,
secret leaks, injection risks, and unhandled async rejections.
"""

import re
from typing import List, Dict, Any

class SecurityScanner:
    def __init__(self):
        self.secret_patterns = [
            (r'(?i)(api[_-]?key|secret|token|password|auth_token)\s*[:=]\s*["\']([a-zA-Z0-9_\-\.]{8,})["\']', "HARDCODED_SECRET", "HIGH", "Hardcoded credentials or API key detected in source code. Secrets should be loaded from environment variables."),
            (r'ghp_[a-zA-Z0-9]{36}', "GITHUB_PERSONAL_ACCESS_TOKEN", "CRITICAL", "Live GitHub Personal Access Token pattern exposed."),
            (r'xox[baprs]-[0-9a-zA-Z]{10,48}', "SLACK_TOKEN_LEAK", "CRITICAL", "Exposed Slack API bot or user token."),
            (r'AIza[0-9A-Za-z-_]{35}', "GOOGLE_API_KEY", "CRITICAL", "Exposed Google Cloud API Key.")
        ]
        
        self.vuln_patterns = [
            (r'\beval\s*\(', "INSECURE_EVAL_EXECUTION", "CRITICAL", "CWE-95: Use of `eval()` allows dynamic code injection from untrusted inputs.", "Replace with structured JSON parser or domain-specific expression engine."),
            (r'new\s+Function\s*\(', "DYNAMIC_FUNCTION_CONSTRUCTOR", "HIGH", "CWE-95: Function constructor can be exploited for arbitrary JavaScript execution.", "Refactor into static handler functions."),
            (r'child_process\.exec\s*\(', "COMMAND_INJECTION_RISK", "CRITICAL", "CWE-78: Passing unsanitized strings to `exec()` risks remote OS command injection.", "Use `execFile()` or `spawn()` with array arguments without a shell."),
            (r'dangerouslySetInnerHTML', "UNSAFE_DOM_INJECTION", "HIGH", "CWE-79: Unsanitized HTML rendering allows Cross-Site Scripting (XSS).", "Sanitize with DOMPurify or use standard JSX text bindings."),
            (r'\.innerHTML\s*=', "RAW_INNERHTML_ASSIGNMENT", "MEDIUM", "CWE-79: Direct innerHTML assignment can introduce DOM-based XSS.", "Use `textContent` or sanitized template elements.")
        ]

    def scan_codebase(self, files: Dict[str, str]) -> List[Dict[str, Any]]:
        findings = []

        for file_path, content in files.items():
            lines = content.splitlines()
            for line_idx, line in enumerate(lines, start=1):
                # 1. Check Secrets
                for pat, rule_id, severity, desc in self.secret_patterns:
                    match = re.search(pat, line)
                    if match:
                        findings.append({
                            "rule_id": rule_id,
                            "file_path": file_path,
                            "line_number": line_idx,
                            "severity": severity,
                            "category": "SECRETS_AND_CREDENTIALS",
                            "title": "Exposed Hardcoded Secret",
                            "description": desc,
                            "code_snippet": line.strip()[:100],
                            "remediation": "Move secrets to `.env` or secret manager (e.g. AWS Secrets Manager, Vault)."
                        })

                # 2. Check Code Vulnerabilities
                for pat, rule_id, severity, title, rem in self.vuln_patterns:
                    if re.search(pat, line):
                        findings.append({
                            "rule_id": rule_id,
                            "file_path": file_path,
                            "line_number": line_idx,
                            "severity": severity,
                            "category": "SECURITY_VULNERABILITY",
                            "title": title,
                            "description": title,
                            "code_snippet": line.strip()[:100],
                            "remediation": rem
                        })

            # 3. Check Unhandled Async Rejections (Functions with async but no try/catch)
            if "async " in content and "try " not in content and "catch" not in content and "then" not in content:
                findings.append({
                    "rule_id": "UNHANDLED_ASYNC_EXCEPTIONS",
                    "file_path": file_path,
                    "line_number": 1,
                    "severity": "MEDIUM",
                    "category": "ROBUSTNESS_AND_RELIABILITY",
                    "title": "Missing Async Error Boundaries",
                    "description": "File declares asynchronous operations without explicit `try/catch` or promise error handling, which may cause unhandled process termination.",
                    "code_snippet": lines[0].strip() if lines else "",
                    "remediation": "Wrap asynchronous I/O calls in `try/catch` blocks or use global promise rejection handlers."
                })

        return findings
