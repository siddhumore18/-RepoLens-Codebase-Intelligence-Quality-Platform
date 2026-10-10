"""
AI_Model Interactive CLI
Command-line interface for running AST code analysis, ML anomaly detection,
evaluating RAG retrieval, and asking codebase questions.
"""

import sys
import os
import argparse
import json

# Ensure AI_Model is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from AI_Model.ast_parser import ASTCodeParser
from AI_Model.feature_extractor import FeatureExtractor
from AI_Model.anomaly_detector import AnomalyDetector
from AI_Model.quality_classifier import CodeQualityClassifier
from AI_Model.embeddings import CodeEmbeddingEngine
from AI_Model.rag_engine import HybridGraphRAGEngine
from AI_Model.evaluator import CodeRetrievalEvaluator
from AI_Model.github_fetcher import GitHubRepositoryFetcher

def main():
    parser_cli = argparse.ArgumentParser(description="RepoLens ML/AI Codebase Intelligence CLI")
    parser_cli.add_argument("--dir", default=None, help="Directory path of repository/fixtures to analyze")
    parser_cli.add_argument("--github", type=str, default=None, help="Public GitHub repository URL (e.g. https://github.com/expressjs/express)")
    parser_cli.add_argument("--token", type=str, default=None, help="Optional GitHub Personal Access Token")
    parser_cli.add_argument("--analyze", action="store_true", help="Run AST & ML Anomaly Detection Analysis")
    parser_cli.add_argument("--evaluate", action="store_true", help="Run RAG retrieval benchmark")
    parser_cli.add_argument("--ask", type=str, help="Ask a question about the codebase with source citations")
    parser_cli.add_argument("--mode", type=str, default="hybrid_graph", choices=["bm25", "semantic", "hybrid", "hybrid_graph"])

    args = parser_cli.parse_args()

    print(f"\n" + "="*70)
    print(f"   REPOLENS: AI_MODEL MACHINE LEARNING PIPELINE")
    print(f"="*70)

    files = {}
    if args.github:
        print(f"[*] Ingesting live GitHub repository: {args.github} ...")
        fetcher = GitHubRepositoryFetcher(token=args.token)
        repo_data = fetcher.fetch_repository(args.github)
        files = repo_data["files"]
        print(f"[*] Successfully fetched {repo_data['file_count']} files at commit {repo_data['commit_sha'][:8]}")
    else:
        target_dir = args.dir or os.path.join(os.path.dirname(__file__), "fixtures")
        if not os.path.exists(target_dir):
            print(f"[!] Error: Directory '{target_dir}' does not exist.")
            sys.exit(1)
        print(f"[*] Ingesting local directory: {target_dir}")
        for root, _, filenames in os.walk(target_dir):
            for fn in filenames:
                if fn.endswith(('.js', '.jsx', '.mjs', '.cjs', '.py')):
                    full_p = os.path.join(root, fn)
                    rel_p = os.path.relpath(full_p, start=target_dir).replace("\\", "/")
                    with open(full_p, 'r', encoding='utf-8') as f:
                        files[rel_p] = f.read()

    print(f"[*] Loaded {len(files)} source files for AST parsing.")

    ast_parser = ASTCodeParser()
    symbols = []
    for path, content in files.items():
        extracted = ast_parser.parse_file(path, content)
        symbols.extend(extracted)
    print(f"[*] Extracted {len(symbols)} function and method symbols.")

    feature_extractor = FeatureExtractor()
    call_graph = feature_extractor.build_call_graph(symbols)
    features = feature_extractor.extract_features(symbols, call_graph)
    print(f"[*] Built Directed Call Graph: {len(call_graph.nodes)} nodes, {len(call_graph.edges)} edges.")

    anomaly_detector = AnomalyDetector()
    enriched = anomaly_detector.detect_anomalies(features)

    classifier = CodeQualityClassifier()
    risks = classifier.predict_risk(enriched)

    rag = HybridGraphRAGEngine()
    rag.index_repository(files, symbols, call_graph)

    if args.analyze or (not args.evaluate and not args.ask):
        print(f"\n[+] ML ANOMALY DETECTION & CODE QUALITY RANKINGS:")
        print(f"-"*70)
        print(f"{'Function Name':<24} | {'LOC':<5} | {'Cyclo':<5} | {'Cognitive':<9} | {'Priority':<10} | {'Anomaly Prob':<12}")
        print(f"-"*70)
        for item in enriched:
            print(f"{item['name']:<24} | {item['loc']:<5} | {item['cyclomatic_complexity']:<5} | {item['cognitive_complexity']:<9} | {item.get('review_priority', 'LOW'):<10} | {item.get('ml_anomaly_probability', 0.0):<12.3f}")
        print(f"-"*70)

    if args.evaluate:
        print(f"\n[+] RUNNING RAG RETRIEVAL ABLATION BENCHMARKS:")
        evaluator = CodeRetrievalEvaluator(rag)
        benchmarks = [
            {"query": "Where are user credentials validated and session tokens created?", "target_symbols": ["authenticateUser", "generateSessionToken"]},
            {"query": "How is audit and transaction logging handled?", "target_symbols": ["logSecurityEvent", "logTransaction"]},
            {"query": "Where is legacy payroll and executive deduction calculated?", "target_symbols": ["processLegacyPayroll"]}
        ]
        results = evaluator.run_benchmark(benchmarks)
        print(json.dumps(results, indent=2))

    if args.ask:
        print(f"\n[?] Question: '{args.ask}' (Mode: {args.mode})")
        ans = rag.answer_question(args.ask, mode=args.mode)
        print(f"\n[+] Answer:\n{ans['answer']}\n")
        print(f"[+] Verified Citations ({len(ans['citations'])}):")
        for c in ans['citations']:
            print(f"    - {c['file_path']}#L{c['start_line']}-L{c['end_line']} (Symbol: `{c['symbol_name']}`)")

    print(f"\n" + "="*70 + "\n")

if __name__ == "__main__":
    main()
