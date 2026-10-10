"""
AST and Symbol Parser Module
Extracts structural symbols, lexical scopes, control flow nodes, and call sites
from source code safely without executing it.
"""

import re
import os
from typing import List, Dict, Any, Optional

class CodeSymbol:
    def __init__(
        self,
        symbol_id: str,
        name: str,
        file_path: str,
        kind: str,
        start_line: int,
        end_line: int,
        parameters: List[str],
        is_async: bool = False,
        exported: bool = False,
        source_code: str = ""
    ):
        self.symbol_id = symbol_id
        self.name = name
        self.file_path = file_path
        self.kind = kind
        self.start_line = start_line
        self.end_line = end_line
        self.parameters = parameters
        self.is_async = is_async
        self.exported = exported
        self.source_code = source_code
        self.callees: List[str] = []
        self.callers: List[str] = []
        self.metrics: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol_id": self.symbol_id,
            "name": self.name,
            "file_path": self.file_path,
            "kind": self.kind,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "parameters": self.parameters,
            "is_async": self.is_async,
            "exported": self.exported,
            "line_count": max(1, self.end_line - self.start_line + 1),
            "callees": self.callees,
            "callers": self.callers,
            "metrics": self.metrics
        }


class ASTCodeParser:
    """
    Robust pattern-based and lexical AST parser for JS/JSX/Python source code.
    Identifies functions, classes, imports, exports, and call-sites.
    """

    def __init__(self):
        self.fn_patterns = [
            re.compile(r'^(?P<export>export\s+)?(?P<default>default\s+)?(?P<async>async\s+)?function\s+(?P<name>[a-zA-Z0-9_$]+)\s*\((?P<params>[^)]*)\)', re.MULTILINE),
            re.compile(r'^(?P<export>export\s+)?(?:const|let|var)\s+(?P<name>[a-zA-Z0-9_$]+)\s*=\s*(?P<async>async\s+)?(?:\((?P<params>[^)]*)\)|(?P<single_param>[a-zA-Z0-9_$]+))\s*=>', re.MULTILINE),
            re.compile(r'^\s*(?P<async>async\s+)?(?P<name>[a-zA-Z0-9_$]+)\s*\((?P<params>[^)]*)\)\s*\{', re.MULTILINE),
            re.compile(r'^\s*(?P<async>async\s+)?def\s+(?P<name>[a-zA-Z0-9_]+)\s*\((?P<params>[^)]*)\):', re.MULTILINE),
        ]
        self.call_pattern = re.compile(r'\b(?P<callee>[a-zA-Z0-9_$]+)\s*\(')

    def parse_file(self, file_path: str, content: str) -> List[CodeSymbol]:
        lines = content.splitlines()
        symbols: List[CodeSymbol] = []

        for i, line in enumerate(lines):
            line_num = i + 1
            trimmed = line.strip()
            
            if trimmed.startswith('//') or trimmed.startswith('#') or trimmed.startswith('/*'):
                continue

            for pattern in self.fn_patterns:
                match = pattern.search(line)
                if match:
                    name = match.group('name')
                    if not name or name in {'if', 'for', 'while', 'switch', 'catch'}:
                        continue
                    
                    is_async = bool(match.groupdict().get('async'))
                    exported = bool(match.groupdict().get('export'))
                    params_str = match.groupdict().get('params') or match.groupdict().get('single_param') or ""
                    params = [p.strip() for p in params_str.split(',') if p.strip()]

                    start_idx = i
                    end_idx = self._find_block_end(lines, start_idx, file_path)
                    fn_code = "\n".join(lines[start_idx:end_idx + 1])

                    symbol_id = f"{file_path}::{name}::{line_num}"
                    symbol = CodeSymbol(
                        symbol_id=symbol_id,
                        name=name,
                        file_path=file_path,
                        kind="function",
                        start_line=line_num,
                        end_line=end_idx + 1,
                        parameters=params,
                        is_async=is_async,
                        exported=exported,
                        source_code=fn_code
                    )

                    symbol.callees = self._extract_callees(fn_code, name)
                    symbols.append(symbol)
                    break

        return symbols

    def _find_block_end(self, lines: List[str], start_idx: int, file_path: str) -> int:
        if file_path.endswith('.py'):
            base_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
            for idx in range(start_idx + 1, len(lines)):
                l = lines[idx]
                if not l.strip() or l.strip().startswith('#'):
                    continue
                curr_indent = len(l) - len(l.lstrip())
                if curr_indent <= base_indent:
                    return max(start_idx, idx - 1)
            return len(lines) - 1

        brace_count = 0
        found_first_brace = False
        for idx in range(start_idx, len(lines)):
            line = lines[idx]
            for char in line:
                if char == '{':
                    brace_count += 1
                    found_first_brace = True
                elif char == '}':
                    brace_count -= 1
                    if found_first_brace and brace_count == 0:
                        return idx
        return min(start_idx + 30, len(lines) - 1)

    def _extract_callees(self, code: str, current_fn_name: str) -> List[str]:
        keywords = {'if', 'for', 'while', 'switch', 'catch', 'function', 'return', 'import', 'require', 'typeof', 'sizeof', 'console', 'log'}
        callees = set()
        for match in self.call_pattern.finditer(code):
            callee = match.group('callee')
            if callee and callee not in keywords and callee != current_fn_name:
                callees.add(callee)
        return sorted(list(callees))
