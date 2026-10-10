"""
AI Model Microservice Server
Exposes all Machine Learning, Anomaly Detection, AST Parsing, and Hybrid RAG endpoints.
"""

import sys
import os
import time
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from AI_Model.ast_parser import ASTCodeParser, CodeSymbol
from AI_Model.feature_extractor import FeatureExtractor
from AI_Model.anomaly_detector import AnomalyDetector
from AI_Model.quality_classifier import CodeQualityClassifier
from AI_Model.embeddings import CodeEmbeddingEngine
from AI_Model.rag_engine import HybridGraphRAGEngine
from AI_Model.evaluator import CodeRetrievalEvaluator
from AI_Model.github_fetcher import GitHubRepositoryFetcher
from AI_Model.security_scanner import SecurityScanner
from AI_Model.refactoring_engine import RefactoringEngine

app = FastAPI(
    title="RepoLens AI Model Service",
    description="Python ML & AI Engine for Code Intelligence, Anomaly Detection & Hybrid RAG",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

parser = ASTCodeParser()
feature_extractor = FeatureExtractor()
anomaly_detector = AnomalyDetector()
quality_classifier = CodeQualityClassifier()
rag_engine = HybridGraphRAGEngine()
security_scanner = SecurityScanner()
refactoring_engine = RefactoringEngine()

indexed_files: Dict[str, str] = {}
indexed_symbols: List[CodeSymbol] = []
indexed_features: List[Dict[str, Any]] = []
call_graph = None
current_snapshot = {}

class AnalyzePayload(BaseModel):
    files: Dict[str, str]
    repo_meta: Optional[Dict[str, Any]] = None

class GitHubImportPayload(BaseModel):
    url: str
    branch: Optional[str] = None
    token: Optional[str] = None

class ChatPayload(BaseModel):
    question: str
    mode: Optional[str] = "hybrid_graph"

@app.get("/health")
def health():
    return {"status": "ok", "service": "RepoLens AI_Model Service"}

@app.post("/api/ai/github-import")
def import_github(payload: GitHubImportPayload):
    global indexed_files, indexed_symbols, indexed_features, call_graph, current_snapshot
    fetcher = GitHubRepositoryFetcher(token=payload.token)
    repo_data = fetcher.fetch_repository(payload.url, branch=payload.branch)
    
    return analyze_repo(AnalyzePayload(
        files=repo_data["files"],
        repo_meta={
            "owner": repo_data["owner"],
            "repo": repo_data["repo"],
            "repo_name": repo_data["repo_name"],
            "description": repo_data["description"],
            "stars": repo_data["stars"],
            "commit_sha": repo_data["commit_sha"],
            "branch": repo_data["branch"]
        }
    ))

@app.post("/api/ai/analyze")
def analyze_repo(payload: AnalyzePayload):
    global indexed_files, indexed_symbols, indexed_features, call_graph, current_snapshot
    indexed_files = payload.files
    current_snapshot = payload.repo_meta or {
        "repo_name": "Custom Codebase",
        "commit_sha": "live_commit_sha",
        "branch": "main"
    }

    symbols: List[CodeSymbol] = []
    for path, content in indexed_files.items():
        if path.endswith(('.js', '.jsx', '.mjs', '.cjs', '.py')):
            extracted = parser.parse_file(path, content)
            symbols.extend(extracted)

    indexed_symbols = symbols
    call_graph = feature_extractor.build_call_graph(symbols)
    features = feature_extractor.extract_features(symbols, call_graph)
    
    anomaly_results = anomaly_detector.detect_anomalies(features)
    risk_results = quality_classifier.predict_risk(anomaly_results)

    risk_map = {r["symbol_id"]: r for r in risk_results}
    for item in anomaly_results:
        s_id = item.get("symbol_id")
        if s_id in risk_map:
            item["refactoring_urgency"] = risk_map[s_id]["refactoring_urgency"]
            item["primary_risk_driver"] = risk_map[s_id]["primary_risk_driver"]

    indexed_features = anomaly_results
    rag_engine.index_repository(indexed_files, indexed_symbols, call_graph)

    return {
        "status": "success",
        "snapshot": current_snapshot,
        "files_count": len(indexed_files),
        "symbols_count": len(symbols),
        "graph_nodes": len(call_graph.nodes),
        "graph_edges": len(call_graph.edges),
        "features": indexed_features
    }

@app.get("/api/ai/graph")
def get_graph():
    global call_graph, indexed_features
    if not call_graph:
        return {"nodes": [], "edges": []}

    priority_map = {f["name"]: f.get("review_priority", "LOW") for f in indexed_features}
    nodes = [{"id": n, "label": n, "priority": priority_map.get(n, "LOW")} for n in call_graph.nodes]
    edges = [{"source": u, "target": v} for u, v in call_graph.edges]
    return {"nodes": nodes, "edges": edges}

from AI_Model.guided_tour import CodebaseTourSynthesizer

tour_synthesizer = CodebaseTourSynthesizer()

@app.get("/api/ai/project-overview")
def get_project_overview():
    global indexed_files, indexed_symbols, current_snapshot
    return tour_synthesizer.generate_project_overview(indexed_files, indexed_symbols, current_snapshot)

@app.get("/api/ai/guided-tour")
def get_guided_tour(persona: str = "developer"):
    global indexed_files, indexed_symbols, call_graph
    return tour_synthesizer.generate_guided_tour(indexed_files, indexed_symbols, call_graph, persona=persona)

@app.get("/api/ai/function-details")
def get_function_details(symbol_name: str):
    global indexed_symbols
    for s in indexed_symbols:
        if s.name == symbol_name:
            return tour_synthesizer.explain_function(s)
    raise HTTPException(status_code=404, detail=f"Symbol '{symbol_name}' not found.")

@app.get("/api/ai/feature-flow")
def trace_feature_flow(query: str):
    global indexed_symbols
    return tour_synthesizer.trace_feature_flow(query, indexed_symbols)

@app.get("/api/ai/where-to-start")
def get_where_to_start():
    global indexed_files, indexed_symbols, indexed_features, current_snapshot
    overview = tour_synthesizer.generate_project_overview(indexed_files, indexed_symbols, current_snapshot)
    
    # Central functions by PageRank / callers
    sorted_central = sorted(indexed_features, key=lambda f: f.get("pagerank", 0) + len(f.get("callers", [])), reverse=True)
    
    # Top improvement candidates
    improvement_candidates = [f for f in indexed_features if f.get("review_priority") in ("CRITICAL", "HIGH")]

    return {
        "files_to_read_first": overview.get("reading_list", []),
        "central_functions": sorted_central[:4],
        "top_improvement_candidates": improvement_candidates[:4],
        "suggested_questions": [
            "Where is user authentication and session token validation handled?",
            "How is structured security and transaction logging implemented?",
            "Where is payroll and progressive tax deduction calculated?",
            "What happens when payment processing fails?",
            "Where should I start if I want to add order cancellation?"
        ],
        "analysis_notes": {
            "supported_languages": [".js", ".jsx", ".mjs", ".cjs", ".py"],
            "dynamic_dispatch_notice": "Dynamic computed member calls are recorded explicitly as unresolved to prevent false caller assumptions."
        }
    }

@app.get("/api/ai/impact")
def get_change_impact(symbol: str, depth: int = 3):
    global call_graph
    if not call_graph or symbol not in call_graph:
        return {
            "target_symbol": symbol,
            "direct_callers": [],
            "transitive_callers": [],
            "blast_radius_score": 0.0,
            "risk_assessment": "Symbol has no known internal callers or is an entrypoint."
        }

    visited = set()
    queue = [(symbol, 0)]
    paths = []

    while queue:
        curr, d = queue.pop(0)
        if d >= depth:
            continue
        for caller in call_graph.predecessors(curr):
            if caller not in visited:
                visited.add(caller)
                queue.append((caller, d + 1))
                paths.append({"caller": caller, "distance": d + 1, "via": curr})

    direct = list(call_graph.predecessors(symbol))
    blast_radius = len(visited) * 15.0 + len(direct) * 25.0

    return {
        "target_symbol": symbol,
        "direct_callers": direct,
        "transitive_callers": list(visited),
        "impact_paths": paths,
        "blast_radius_score": round(min(100.0, blast_radius), 1),
        "risk_level": "CRITICAL" if blast_radius > 60 else "HIGH" if blast_radius > 30 else "MODERATE"
    }

@app.get("/api/ai/findings")
def get_findings():
    global indexed_features
    findings = []
    for f in indexed_features:
        if f.get("cognitive_complexity", 0) > 15:
            findings.append({
                "rule_id": "HIGH_COGNITIVE_OVERLOAD",
                "symbol_name": f["name"],
                "file_path": f["file_path"],
                "severity": "CRITICAL",
                "message": f"Cognitive complexity ({f['cognitive_complexity']}) exceeds threshold. Deeply nested conditionals make this function difficult to follow.",
                "suggestion": "Decompose into smaller helper functions with early return guards."
            })
        if f.get("loc", 0) > 40:
            findings.append({
                "rule_id": "LONG_METHOD_SMELL",
                "symbol_name": f["name"],
                "file_path": f["file_path"],
                "severity": "HIGH",
                "message": f"Function has {f['loc']} lines of code and handles multiple responsibilities.",
                "suggestion": "Split business validation, calculation, and persistence into separate modules."
            })
        if f.get("param_count", 0) >= 5:
            findings.append({
                "rule_id": "EXCESSIVE_PARAMETERS",
                "symbol_name": f["name"],
                "file_path": f["file_path"],
                "severity": "MEDIUM",
                "message": f"Takes {f['param_count']} parameters. Long argument lists increase coupling and make testing fragile.",
                "suggestion": "Bundle parameters into a structured configuration object."
            })
    return {"findings": findings, "total": len(findings)}

@app.post("/api/ai/chat")
def chat(payload: ChatPayload):
    global rag_engine
    if not rag_engine.chunks:
        raise HTTPException(status_code=400, detail="No indexed repository.")
    t0 = time.perf_counter()
    res = rag_engine.answer_question(payload.question, mode=payload.mode or "hybrid_graph")
    res["latency_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)
    return res

@app.get("/api/ai/security-scan")
def get_security_scan():
    global indexed_files
    findings = security_scanner.scan_codebase(indexed_files)
    critical_count = sum(1 for f in findings if f["severity"] == "CRITICAL")
    high_count = sum(1 for f in findings if f["severity"] == "HIGH")
    medium_count = sum(1 for f in findings if f["severity"] == "MEDIUM")
    
    score = max(0, 100 - (critical_count * 25 + high_count * 12 + medium_count * 5))
    grade = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D" if score >= 40 else "F"

    return {
        "security_score": score,
        "compliance_grade": grade,
        "total_findings": len(findings),
        "critical_count": critical_count,
        "high_count": high_count,
        "medium_count": medium_count,
        "findings": findings
    }

@app.get("/api/ai/refactor")
def get_refactored_code(symbol_name: str):
    global indexed_symbols, indexed_features
    for s in indexed_symbols:
        if s.name == symbol_name:
            feat = next((f for f in indexed_features if f.get("name") == symbol_name), None)
            return refactoring_engine.generate_refactoring(s, feat)
    raise HTTPException(status_code=404, detail=f"Symbol '{symbol_name}' not found for refactoring.")

@app.get("/api/ai/evaluate")
def evaluate():
    global rag_engine
    if not rag_engine.chunks:
        _load_default_fixtures()
    evaluator = CodeRetrievalEvaluator(rag_engine)
    return evaluator.run_benchmark()

def _load_default_fixtures():
    global indexed_files, indexed_symbols, indexed_features, call_graph, current_snapshot
    fixture_dir = os.path.join(os.path.dirname(__file__), "fixtures")
    files_payload = {}
    if os.path.exists(fixture_dir):
        for f in os.listdir(fixture_dir):
            p = os.path.join(fixture_dir, f)
            if os.path.isfile(p):
                with open(p, "r", encoding="utf-8") as file_obj:
                    files_payload[f] = file_obj.read()
    
    if files_payload:
        analyze_repo(AnalyzePayload(
            files=files_payload,
            repo_meta={
                "repo_name": "Sample Codebase",
                "commit_sha": "7f8b92c4",
                "branch": "main",
                "description": "A modular backend codebase providing authentication, structured security logging, and payroll calculations."
            }
        ))

# Initialize on import/startup
_load_default_fixtures()

if __name__ == "__main__":
    print("Launching AI Model Server on port 5000...")
    uvicorn.run(app, host="127.0.0.1", port=5000)

