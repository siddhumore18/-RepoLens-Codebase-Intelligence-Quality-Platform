"""
GitHub Ingestion Module
Fetches real public GitHub repositories, resolves commit SHAs, walks git trees,
and downloads source blobs securely via the GitHub REST API.
"""

import os
import re
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Tuple, Optional

class GitHubRepositoryFetcher:
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("GITHUB_TOKEN", "").strip() or None
        self.user_agent = "RepoLens-ML-Analyzer/2.0"
        self.max_files = 150
        self.max_file_size_bytes = 150 * 1024
        self.supported_extensions = ('.js', '.jsx', '.mjs', '.cjs', '.py', '.ts', '.tsx', '.json', '.md')
        self.ignored_dirs = ('node_modules', 'dist', 'build', '.git', 'coverage', 'venv', '__pycache__', 'vendor')

    def parse_repo_url(self, url: str) -> Tuple[str, str]:
        clean_url = url.strip().rstrip('/')
        if clean_url.endswith('.git'):
            clean_url = clean_url[:-4]
        match = re.search(r'github\.com/([^/]+)/([^/]+)', clean_url)
        if not match:
            raise ValueError(f"Invalid GitHub URL format: '{url}'. Expected format: 'https://github.com/owner/repo'")
        return match.group(1), match.group(2)

    def _make_request(self, url: str) -> Dict[str, Any]:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', self.user_agent)
        req.add_header('Accept', 'application/vnd.github.v3+json')
        if self.token:
            req.add_header('Authorization', f'Bearer {self.token}')

        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                data = response.read().decode('utf-8')
                return json.loads(data)
        except urllib.error.HTTPError as e:
            if e.code == 403:
                raise ValueError("GitHub API rate limit exceeded. Please provide a GitHub Personal Access Token or try again later.")
            elif e.code == 404:
                raise ValueError("GitHub repository not found. Please verify the owner and repository name are public and correct.")
            else:
                raise ValueError(f"GitHub API error (HTTP {e.code}): {e.reason}")
        except Exception as e:
            raise ValueError(f"Failed to connect to GitHub API: {str(e)}")

    def fetch_repository(self, repo_url: str, branch: Optional[str] = None) -> Dict[str, Any]:
        owner, repo = self.parse_repo_url(repo_url)

        repo_info_url = f"https://api.github.com/repos/{owner}/{repo}"
        repo_meta = self._make_request(repo_info_url)
        default_branch = branch or repo_meta.get("default_branch", "main")
        stars = repo_meta.get("stargazers_count", 0)
        description = repo_meta.get("description") or "No description provided."

        ref_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{default_branch}"
        commit_data = self._make_request(ref_url)
        commit_sha = commit_data.get("sha", default_branch)

        tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{commit_sha}?recursive=1"
        tree_data = self._make_request(tree_url)
        tree_entries = tree_data.get("tree", [])

        selected_files = []
        for entry in tree_entries:
            if entry.get("type") != "blob":
                continue
            path = entry.get("path", "")
            size = entry.get("size", 0)

            if any(part in self.ignored_dirs for part in path.split('/')):
                continue

            if path.endswith(self.supported_extensions):
                if size <= self.max_file_size_bytes:
                    selected_files.append(entry)

            if len(selected_files) >= self.max_files:
                break

        files_dict = {}
        for entry in selected_files:
            path = entry.get("path")
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{commit_sha}/{path}"
            req = urllib.request.Request(raw_url)
            req.add_header('User-Agent', self.user_agent)
            if self.token:
                req.add_header('Authorization', f'Bearer {self.token}')

            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    content = resp.read().decode('utf-8', errors='replace')
                    files_dict[path] = content
            except Exception:
                pass

        if not files_dict:
            raise ValueError(f"No parseable source code files found in repository {owner}/{repo}.")

        return {
            "owner": owner,
            "repo": repo,
            "repo_name": f"{owner}/{repo}",
            "description": description,
            "stars": stars,
            "commit_sha": commit_sha,
            "branch": default_branch,
            "files": files_dict,
            "file_count": len(files_dict)
        }
