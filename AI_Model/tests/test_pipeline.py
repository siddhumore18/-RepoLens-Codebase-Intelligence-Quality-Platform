"""
Unit tests for AI_Model
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from AI_Model.ast_parser import ASTCodeParser
from AI_Model.feature_extractor import FeatureExtractor
from AI_Model.anomaly_detector import AnomalyDetector
from AI_Model.quality_classifier import CodeQualityClassifier
from AI_Model.embeddings import CodeEmbeddingEngine
from AI_Model.rag_engine import HybridGraphRAGEngine
from AI_Model.github_fetcher import GitHubRepositoryFetcher

SAMPLE_CODE = """
import { logSecurityEvent } from './logger.js';

export async function processPayment(userId, amount, currency, isExpress) {
    if (amount <= 0) {
        throw new Error('Invalid amount');
    }
    if (isExpress) {
        logSecurityEvent('EXPRESS_PAYMENT', { userId, amount });
    }
    return { success: true, txId: 'tx_123' };
}
"""

def test_github_fetcher_url():
    fetcher = GitHubRepositoryFetcher()
    owner, repo = fetcher.parse_repo_url("https://github.com/expressjs/express")
    assert owner == "expressjs"
    assert repo == "express"

def test_ast_parser():
    parser = ASTCodeParser()
    symbols = parser.parse_file("payment.js", SAMPLE_CODE)
    assert len(symbols) == 1
    sym = symbols[0]
    assert sym.name == "processPayment"
    assert sym.is_async is True
    assert "logSecurityEvent" in sym.callees

def test_feature_extractor():
    parser = ASTCodeParser()
    symbols = parser.parse_file("payment.js", SAMPLE_CODE)
    fe = FeatureExtractor()
    graph = fe.build_call_graph(symbols)
    features = fe.extract_features(symbols, graph)
    assert len(features) == 1
    assert features[0]["cyclomatic_complexity"] >= 2

def test_anomaly_detector():
    detector = AnomalyDetector()
    mock_features = [
        {"symbol_id": "s1", "name": "f1", "loc": 10, "cyclomatic_complexity": 2, "cognitive_complexity": 1, "max_nesting": 1, "param_count": 2, "halstead_volume": 100, "halstead_difficulty": 5, "out_degree": 1},
        {"symbol_id": "s2", "name": "f2", "loc": 12, "cyclomatic_complexity": 2, "cognitive_complexity": 2, "max_nesting": 1, "param_count": 1, "halstead_volume": 120, "halstead_difficulty": 6, "out_degree": 1},
        {"symbol_id": "s3", "name": "f3", "loc": 15, "cyclomatic_complexity": 3, "cognitive_complexity": 2, "max_nesting": 2, "param_count": 2, "halstead_volume": 150, "halstead_difficulty": 7, "out_degree": 2},
        {"symbol_id": "s4", "name": "f4", "loc": 11, "cyclomatic_complexity": 2, "cognitive_complexity": 1, "max_nesting": 1, "param_count": 2, "halstead_volume": 110, "halstead_difficulty": 5, "out_degree": 1},
        {"symbol_id": "s5", "name": "anomaly_god_fn", "loc": 150, "cyclomatic_complexity": 25, "cognitive_complexity": 40, "max_nesting": 6, "param_count": 8, "halstead_volume": 3500, "halstead_difficulty": 35, "out_degree": 12}
    ]
    results = detector.detect_anomalies(mock_features)
    assert results[0]["name"] == "anomaly_god_fn"
    assert results[0]["review_priority"] in ("CRITICAL", "HIGH")

def test_rag_retrieval():
    parser = ASTCodeParser()
    symbols = parser.parse_file("payment.js", SAMPLE_CODE)
    fe = FeatureExtractor()
    graph = fe.build_call_graph(symbols)
    
    rag = HybridGraphRAGEngine()
    rag.index_repository({"payment.js": SAMPLE_CODE}, symbols, graph)

    ans = rag.answer_question("Where is payment processed?")
    assert ans["evidence_status"] == "supported"
    assert any(c["symbol_name"] == "processPayment" for c in ans["citations"])

def test_guided_tour_synthesizer():
    from AI_Model.guided_tour import CodebaseTourSynthesizer
    synthesizer = CodebaseTourSynthesizer()
    parser = ASTCodeParser()
    symbols = parser.parse_file("payment.js", SAMPLE_CODE)
    fe = FeatureExtractor()
    graph = fe.build_call_graph(symbols)

    overview = synthesizer.generate_project_overview({"payment.js": SAMPLE_CODE}, symbols, {"repo_name": "PaymentApp"})
    assert "payment.js" in overview["entry_points"]
    assert len(overview["main_features"]) > 0

    tour = synthesizer.generate_guided_tour({"payment.js": SAMPLE_CODE}, symbols, graph, persona="developer")
    assert len(tour) == 5
    assert tour[0]["title"] == "The Starting Point"

    flow = synthesizer.trace_feature_flow("How does user authentication work?", symbols)
    assert flow["established"] is True
    assert len(flow["steps"]) > 0

def test_security_scanner():
    from AI_Model.security_scanner import SecurityScanner
    scanner = SecurityScanner()
    code_with_leak = 'const apiKey = "ghp_123456789012345678901234567890123456";\neval("dangerous()");'
    findings = scanner.scan_codebase({"vuln.js": code_with_leak})
    assert len(findings) >= 2
    rule_ids = [f["rule_id"] for f in findings]
    assert "GITHUB_PERSONAL_ACCESS_TOKEN" in rule_ids
    assert "INSECURE_EVAL_EXECUTION" in rule_ids

def test_refactoring_engine():
    from AI_Model.refactoring_engine import RefactoringEngine
    parser = ASTCodeParser()
    symbols = parser.parse_file("payment.js", SAMPLE_CODE)
    engine = RefactoringEngine()
    res = engine.generate_refactoring(symbols[0])
    assert "refactored_code" in res
    assert "unified_diff" in res
    assert res["metrics"]["cognitive_after"] <= res["metrics"]["cognitive_before"]

