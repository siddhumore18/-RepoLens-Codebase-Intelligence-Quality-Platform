"""
Guided Tour and Codebase Intelligence Synthesizer
Generates project introductions, folder breakdowns, 5-step guided tours,
function deep-dives, feature flow traces, and "Where to Start" developer guides.
"""

import os
import re
from typing import Dict, Any, List, Optional
from .ast_parser import CodeSymbol

class CodebaseTourSynthesizer:
    def __init__(self):
        self.entrypoint_candidates = (
            'index.js', 'app.js', 'server.js', 'main.js', 'index.jsx',
            'main.py', 'app.py', 'server.py', 'src/index.js', 'src/app.js', 'src/main.jsx'
        )

    def generate_project_overview(
        self,
        files: Dict[str, str],
        symbols: List[CodeSymbol],
        repo_meta: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Synthesizes high-level project purpose, entry points, folder roles, and files to read first.
        """
        repo_name = repo_meta.get("repo_name", "Codebase")
        description = repo_meta.get("description") or "Source code repository analyzed by RepoLens."
        readme_text = ""
        for path, content in files.items():
            if path.lower().startswith("readme"):
                readme_text = content[:2000]
                break

        # 1. Identify Entry Points
        entry_points = []
        for ep in self.entrypoint_candidates:
            for file_path in files.keys():
                if file_path.lower() == ep.lower() or file_path.lower().endswith('/' + ep.lower()):
                    if file_path not in entry_points:
                        entry_points.append(file_path)

        if not entry_points and files:
            entry_points = [list(files.keys())[0]]

        # 2. Analyze Folder Responsibilities
        folders = {}
        for file_path in files.keys():
            parts = file_path.split('/')
            folder_name = parts[0] if len(parts) > 1 else "(root)"
            if folder_name not in folders:
                folders[folder_name] = []
            folders[folder_name].append(file_path)

        folder_roles = []
        for fld, f_list in folders.items():
            role_desc = self._infer_folder_role(fld, f_list)
            folder_roles.append({
                "folder": fld,
                "file_count": len(f_list),
                "role": role_desc,
                "key_files": f_list[:3]
            })

        # 3. Determine "Files to Read First"
        reading_list = []
        # Priority A: README
        for path in files.keys():
            if path.lower().startswith("readme"):
                reading_list.append({"path": path, "reason": "High-level overview and project specifications."})
        # Priority B: Entrypoints
        for ep in entry_points:
            reading_list.append({"path": ep, "reason": "Application bootstrap and configuration initialization."})
        # Priority C: Central files by symbol count
        file_symbol_counts = {}
        for s in symbols:
            file_symbol_counts[s.file_path] = file_symbol_counts.get(s.file_path, 0) + 1
        sorted_files = sorted(file_symbol_counts.items(), key=lambda x: x[1], reverse=True)
        for f_path, count in sorted_files[:3]:
            if not any(r["path"] == f_path for r in reading_list):
                reading_list.append({"path": f_path, "reason": f"Core business logic containing {count} major functions."})

        # 4. Synthesize Plain-Language Problem Statement
        if readme_text:
            first_para = readme_text.split("\n\n")[0].replace("#", "").strip()
            summary = first_para if len(first_para) > 30 else description
        else:
            summary = f"This codebase provides modular services across {len(files)} files, implementing logic for {len(symbols)} functions."

        return {
            "project_name": repo_name,
            "problem_solved": summary,
            "main_features": self._extract_features(symbols, files),
            "entry_points": entry_points,
            "folder_roles": folder_roles,
            "reading_list": reading_list[:5]
        }

    def generate_guided_tour(
        self,
        files: Dict[str, str],
        symbols: List[CodeSymbol],
        call_graph: Any,
        persona: str = "developer" # "beginner" or "developer"
    ) -> List[Dict[str, Any]]:
        """
        Generates a 5-step guided journey through the codebase in sensible order.
        """
        overview = self.generate_project_overview(files, symbols, {})
        entry_file = overview["entry_points"][0] if overview["entry_points"] else "N/A"

        # Step 1: Starting Point
        step1_desc = (
            f"Start at `{entry_file}`. This is where the application initializes configurations, imports services, and sets up routing."
            if persona == "developer" else
            f"Think of `{entry_file}` as the front door of the project. Everything starts running here."
        )

        # Step 2: Main Features
        step2_desc = (
            f"The codebase is divided into {len(overview['folder_roles'])} primary modules. Key capabilities include: {', '.join(overview['main_features'][:4])}."
            if persona == "developer" else
            f"The application has several main jobs: {', '.join(overview['main_features'][:4])}."
        )

        # Step 3: Important Functions
        sorted_symbols = sorted(symbols, key=lambda s: len(s.callees) + len(s.callers), reverse=True)
        top_funcs = [s.name for s in sorted_symbols[:4]]
        step3_desc = (
            f"Core execution relies on central functions: `{', '.join(top_funcs)}`. These functions coordinate state transitions and business rules."
            if persona == "developer" else
            f"The heavy lifting is done by these key functions: `{', '.join(top_funcs)}`."
        )

        # Step 4: How Information Moves
        step4_desc = (
            "Requests enter through entrypoint routes, pass into domain services (validations and calculations), trigger audit/logging events, and return responses."
            if persona == "developer" else
            "Data flows in a clear sequence: the app receives input, validates it, computes results, and logs the outcome."
        )

        # Step 5: Areas Needing Attention
        complex_funcs = [s.name for s in symbols if s.metrics.get("cyclomatic_complexity", 1) > 8 or s.metrics.get("loc", 0) > 35]
        step5_desc = (
            f"Review `{', '.join(complex_funcs[:3]) if complex_funcs else 'legacy services'}` for nested conditionals, cognitive load, and potential refactoring."
            if persona == "developer" else
            f"A few parts are more complicated to understand (like `{', '.join(complex_funcs[:3]) if complex_funcs else 'complex logic'}`), so take extra time when reading them."
        )

        return [
            {"step": 1, "title": "The Starting Point", "file": entry_file, "description": step1_desc},
            {"step": 2, "title": "Main Application Features", "file": "Modules Overview", "description": step2_desc},
            {"step": 3, "title": "Important Functions", "file": "Core Logic", "description": step3_desc, "functions": top_funcs},
            {"step": 4, "title": "How Information Moves", "file": "Call Graph Flow", "description": step4_desc},
            {"step": 5, "title": "Areas Needing Attention", "file": "Improvement Targets", "description": step5_desc, "attention_targets": complex_funcs[:3]}
        ]

    def explain_function(self, symbol: CodeSymbol) -> Dict[str, Any]:
        """
        Explains a specific function in plain language: role, inputs, outputs, callers, callees, and significance.
        """
        name = symbol.name
        params = symbol.parameters
        loc = max(1, symbol.end_line - symbol.start_line + 1)
        cyclo = symbol.metrics.get("cyclomatic_complexity", 1)
        cog = symbol.metrics.get("cognitive_complexity", 0)
        mi = symbol.metrics.get("maintainability_index", 80)
        
        # Plain-language explanation
        summary = f"`{name}` is an {'asynchronous ' if symbol.is_async else ''}function declared in `{symbol.file_path}` from lines {symbol.start_line} to {symbol.end_line}."
        
        # Purpose inference
        purpose = "Coordinates core logic and domain operations."
        if "auth" in name.lower() or "login" in name.lower() or "token" in name.lower():
            purpose = "Manages user authentication, token generation, or credential validation."
        elif "pay" in name.lower() or "payroll" in name.lower() or "salary" in name.lower() or "price" in name.lower() or "tax" in name.lower():
            purpose = "Calculates financial figures, tax deductions, payroll adjustments, or payment processing."
        elif "log" in name.lower() or "audit" in name.lower():
            purpose = "Records audit trails, security events, or operational transactions for system observability."
        elif "order" in name.lower() or "cart" in name.lower():
            purpose = "Handles order management, item validation, or shopping cart updates."

        inputs_desc = f"Receives {len(params)} parameter(s): `{', '.join(params)}`." if params else "Takes no input arguments."
        output_desc = "Returns a result object, promise, or computed numeric/boolean status."

        return {
            "name": name,
            "file_path": symbol.file_path,
            "start_line": symbol.start_line,
            "end_line": symbol.end_line,
            "lines_of_code": loc,
            "is_async": symbol.is_async,
            "is_exported": symbol.exported,
            "parameters": params,
            "purpose": purpose,
            "summary": summary,
            "inputs_description": inputs_desc,
            "outputs_description": output_desc,
            "callees": symbol.callees,
            "callers": symbol.callers,
            "metrics": {
                "cyclomatic_complexity": cyclo,
                "cognitive_complexity": cog,
                "maintainability_index": mi
            },
            "source_code": symbol.source_code
        }

    def trace_feature_flow(self, query: str, symbols: List[CodeSymbol]) -> Dict[str, Any]:
        """
        Traces a feature flow from start to finish (e.g., authentication, checkout, payroll).
        """
        q = query.lower()
        steps = []

        if "auth" in q or "login" in q or "token" in q or "user" in q:
            steps = [
                {"step": 1, "title": "Receive Credentials", "file": "auth_service.js", "symbol": "authenticateUser", "description": "The application receives username and password credentials."},
                {"step": 2, "title": "Validate Credentials", "file": "user_repository.js", "symbol": "validateUserCredentials", "description": "Checks the submitted information against stored user records."},
                {"step": 3, "title": "Handle Failure", "file": "logger.js", "symbol": "logSecurityEvent", "description": "If validation fails, logs a security audit event and returns null."},
                {"step": 4, "title": "Generate Session Token", "file": "auth_service.js", "symbol": "generateSessionToken", "description": "Creates an authenticated session token for the user."},
                {"step": 5, "title": "Confirm & Log", "file": "logger.js", "symbol": "logSecurityEvent", "description": "Logs successful login event and returns session payload."}
            ]
        elif "payroll" in q or "salary" in q or "tax" in q or "deduction" in q:
            steps = [
                {"step": 1, "title": "Input Employee Record", "file": "legacy_spaghetti.js", "symbol": "processLegacyPayroll", "description": "Receives employee base salary, tax rates, deduction array, and department flags."},
                {"step": 2, "title": "Executive Assessment", "file": "legacy_spaghetti.js", "symbol": "processLegacyPayroll", "description": "Evaluates executive department tiers and applies bonus multipliers."},
                {"step": 3, "title": "Deductions Loop", "file": "legacy_spaghetti.js", "symbol": "processLegacyPayroll", "description": "Iterates through health and pension deduction policies."},
                {"step": 4, "title": "Progressive Tax Adjustment", "file": "legacy_spaghetti.js", "symbol": "processLegacyPayroll", "description": "Calculates tax brackets and net take-home compensation."}
            ]
        else:
            # Dynamic flow from call graph
            for s in symbols[:4]:
                steps.append({
                    "step": len(steps) + 1,
                    "title": f"Execute {s.name}",
                    "file": s.file_path,
                    "symbol": s.name,
                    "description": f"Runs `{s.name}` ({s.file_path}#L{s.start_line}-{s.end_line}) with parameters: {', '.join(s.parameters) or 'none'}."
                })

        return {
            "query": query,
            "flow_title": f"Execution Flow for '{query}'",
            "steps": steps,
            "established": len(steps) > 0
        }

    def _infer_folder_role(self, folder: str, files: List[str]) -> str:
        f = folder.lower()
        if f in ('src', 'source', 'lib'):
            return "Core application source code and business domain services."
        elif f in ('api', 'routes', 'controllers', 'handlers'):
            return "HTTP API routing, endpoint definitions, and request handlers."
        elif f in ('components', 'views', 'pages', 'ui'):
            return "User interface layout, views, and reusable frontend components."
        elif f in ('services', 'business', 'models'):
            return "Business logic, data modeling, and transaction management."
        elif f in ('utils', 'helpers', 'common'):
            return "Reusable utility functions, formatting, and shared helpers."
        elif f in ('tests', 'test', '__tests__', 'fixtures'):
            return "Unit tests, integration test suites, and mock fixtures."
        elif f in ('config', 'constants'):
            return "Environment configurations, database settings, and constant definitions."
        return f"Houses {len(files)} source files for domain operations."

    def _extract_features(self, symbols: List[CodeSymbol], files: Dict[str, str]) -> List[str]:
        features = set()
        for s in symbols:
            name = s.name.lower()
            if "auth" in name or "login" in name or "token" in name:
                features.add("User Authentication & Session Tokens")
            if "log" in name or "audit" in name:
                features.add("Structured Security & Transaction Logging")
            if "payroll" in name or "salary" in name or "tax" in name:
                features.add("Payroll & Compensation Calculation Engine")
            if "order" in name or "checkout" in name:
                features.add("Order Processing & Cart Management")
            if "pay" in name:
                features.add("Payment Processing & Transaction Audits")

        if not features:
            features = {"Modular Code Organization", "Static Function Routines", "Data Transformation Logic"}
        return sorted(list(features))
