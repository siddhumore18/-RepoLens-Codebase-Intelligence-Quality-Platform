"""
Feature Extractor Module
Computes multidimensional static code metrics, AST complexity metrics,
and graph-theoretic centrality metrics for machine learning models.
"""

import math
import re
import networkx as nx
from typing import List, Dict, Any
from .ast_parser import CodeSymbol

class FeatureExtractor:
    """
    Extracts structural, cognitive, and graph features from parsed CodeSymbols.
    """

    def __init__(self):
        self.branch_pattern = re.compile(r'\b(if|else\s+if|for|while|case|catch)\b|\?|&&|\|\|')
        self.operator_pattern = re.compile(r'(\+|-|\*|/|%|=|==|===|!=|!==|<|>|<=|>=|&&|\|\||!|\?|\.|,|;|:|\(|\)|\[|\]|\{|\})')
        self.identifier_pattern = re.compile(r'\b[a-zA-Z_$][a-zA-Z0-9_$]*\b')

    def extract_features(self, symbols: List[CodeSymbol], call_graph: nx.DiGraph = None) -> List[Dict[str, Any]]:
        if call_graph is None:
            call_graph = self.build_call_graph(symbols)

        pagerank_scores = {}
        betweenness_scores = {}
        try:
            if len(call_graph.nodes) > 0:
                pagerank_scores = nx.pagerank(call_graph, alpha=0.85)
                betweenness_scores = nx.betweenness_centrality(call_graph)
        except Exception:
            pagerank_scores = {n: 0.0 for n in call_graph.nodes}
            betweenness_scores = {n: 0.0 for n in call_graph.nodes}

        dataset = []
        for sym in symbols:
            code = sym.source_code
            lines = [l for l in code.splitlines() if l.strip()]
            loc = len(lines)
            param_count = len(sym.parameters)

            # Cyclomatic Complexity
            branch_matches = len(self.branch_pattern.findall(code))
            cyclomatic_complexity = 1 + branch_matches

            # Nesting Depth & Cognitive Complexity
            max_nesting, cognitive_complexity = self._compute_nesting_and_cognitive(code)

            # Halstead Metrics
            halstead_volume, halstead_difficulty, halstead_effort = self._compute_halstead(code)

            # Graph Centrality
            node_key = sym.name
            in_degree = call_graph.in_degree(node_key) if node_key in call_graph else 0
            out_degree = call_graph.out_degree(node_key) if node_key in call_graph else 0
            pagerank = pagerank_scores.get(node_key, 0.0)
            betweenness = betweenness_scores.get(node_key, 0.0)

            # Maintainability Index
            safe_vol = max(1.0, halstead_volume)
            safe_loc = max(1.0, loc)
            maintainability_index = max(0.0, min(100.0, 
                171.0 - 5.2 * math.log(safe_vol) - 0.23 * cyclomatic_complexity - 16.2 * math.log(safe_loc)
            ))

            feature_dict = {
                "symbol_id": sym.symbol_id,
                "name": sym.name,
                "file_path": sym.file_path,
                "loc": loc,
                "param_count": param_count,
                "branch_count": branch_matches,
                "cyclomatic_complexity": cyclomatic_complexity,
                "max_nesting": max_nesting,
                "cognitive_complexity": cognitive_complexity,
                "halstead_volume": round(halstead_volume, 2),
                "halstead_difficulty": round(halstead_difficulty, 2),
                "halstead_effort": round(halstead_effort, 2),
                "maintainability_index": round(maintainability_index, 2),
                "in_degree": in_degree,
                "out_degree": out_degree,
                "pagerank": round(pagerank, 5),
                "betweenness": round(betweenness, 5),
                "is_async": 1 if sym.is_async else 0,
                "is_exported": 1 if sym.exported else 0
            }

            sym.metrics = feature_dict
            dataset.append(feature_dict)

        return dataset

    def build_call_graph(self, symbols: List[CodeSymbol]) -> nx.DiGraph:
        g = nx.DiGraph()
        symbol_names = {s.name for s in symbols}

        for s in symbols:
            g.add_node(s.name, file=s.file_path, loc=s.end_line - s.start_line + 1)

        for s in symbols:
            for callee in s.callees:
                if callee in symbol_names:
                    g.add_edge(s.name, callee)
                    for target in symbols:
                        if target.name == callee and s.name not in target.callers:
                            target.callers.append(s.name)

        return g

    def _compute_nesting_and_cognitive(self, code: str) -> (int, int):
        max_depth = 0
        current_depth = 0
        cognitive_score = 0
        lines = code.splitlines()

        for line in lines:
            trimmed = line.strip()
            opens = line.count('{')
            closes = line.count('}')
            
            if self.branch_pattern.search(trimmed):
                cognitive_score += (1 + current_depth)

            current_depth += opens
            if current_depth > max_depth:
                max_depth = current_depth
            current_depth = max(0, current_depth - closes)

        return max_depth, cognitive_score

    def _compute_halstead(self, code: str) -> (float, float, float):
        operators = self.operator_pattern.findall(code)
        operands = [w for w in self.identifier_pattern.findall(code) if not self.branch_pattern.match(w)]

        n1 = len(set(operators))
        n2 = len(set(operands))
        N1 = len(operators)
        N2 = len(operands)

        vocabulary = max(1, n1 + n2)
        length = max(1, N1 + N2)

        volume = length * math.log2(vocabulary) if vocabulary > 1 else 1.0
        difficulty = (n1 / 2.0) * (N2 / max(1.0, n2))
        effort = difficulty * volume

        return volume, difficulty, effort
