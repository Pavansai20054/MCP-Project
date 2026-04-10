"""Application services shared by CLI and UI entrypoints."""

from __future__ import annotations

import httpx
import json
import base64
import re
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import stdio_client

from src.config.env import config
from src.orchestrator import run_readme_upgrade
from src.tools.mcp_bridge import build_server_params, to_groq_tools


def _build_github_headers(github_token: str | None = None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "readme-upgrade-studio",
    }
    token = (github_token or config.GITHUB_TOKEN or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


async def generate_readme_upgrade(
    repo_target: str,
    max_iterations: int,
    author_linkedin: str | None = None,
    author_email: str | None = None,
    github_token: str | None = None,
) -> tuple[str | None, str | None]:
    """Generate upgraded README content for a target repository."""
    server_params = build_server_params(github_token=github_token)
    repo_snapshot = fetch_repo_snapshot(repo_target, github_token=github_token)

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_res = await session.list_tools()
            groq_tools = to_groq_tools(tools_res.tools)

            generated_content, error_message = await run_readme_upgrade(
                session=session,
                repo_target=repo_target,
                groq_tools=groq_tools,
                max_iterations=max_iterations,
                repo_snapshot=repo_snapshot,
                author_linkedin=author_linkedin,
                author_email=author_email,
            )
            if generated_content:
                generated_content = _apply_deterministic_tech_stack(generated_content, repo_snapshot)
            return generated_content, error_message


def missing_env_vars() -> list[str]:
    """Return list of required environment variables that are not set."""
    missing: list[str] = []
    if not config.GROQ_API_KEY:
        missing.append("GROQ_API_KEY")
    return missing


def list_public_repositories(username: str, github_token: str | None = None) -> tuple[list[str], str | None]:
    """Return all public repository names for a GitHub username."""
    repos: list[str] = []
    page = 1
    headers = _build_github_headers(github_token)

    with httpx.Client(timeout=20.0, headers=headers) as client:
        while True:
            url = f"https://api.github.com/users/{username}/repos"
            response = client.get(url, params={"type": "public", "per_page": 100, "page": page})

            if response.status_code == 404:
                return [], "GitHub username not found."
            if response.status_code >= 400:
                return [], f"GitHub API error ({response.status_code})."

            data = response.json()
            if not isinstance(data, list):
                return [], "Unexpected response from GitHub API."
            if not data:
                break

            repos.extend([repo.get("name", "") for repo in data if repo.get("name")])
            if len(data) < 100:
                break
            page += 1

    repos = sorted(set(repos), key=str.lower)
    if not repos:
        return [], "No public repositories found for this user."
    return repos, None


def fetch_repo_snapshot(repo_target: str, github_token: str | None = None) -> str | None:
    """Fetch concise repository context to reduce hallucinations in README generation."""
    parsed = _parse_repo_target(repo_target)
    if not parsed:
        return None

    owner, repo = parsed
    headers = _build_github_headers(github_token)

    try:
        with httpx.Client(timeout=20.0, headers=headers) as client:
            repo_resp = client.get(f"https://api.github.com/repos/{owner}/{repo}")
            if repo_resp.status_code >= 400:
                return None

            repo_data = repo_resp.json()
            default_branch = repo_data.get("default_branch") or "main"

            languages_resp = client.get(f"https://api.github.com/repos/{owner}/{repo}/languages")
            github_languages_bytes: dict[str, int] = {}
            github_languages_percent: dict[str, float] = {}
            if languages_resp.status_code < 400:
                languages_data = languages_resp.json()
                if isinstance(languages_data, dict):
                    normalized: dict[str, int] = {}
                    for lang, byte_count in languages_data.items():
                        if isinstance(lang, str) and isinstance(byte_count, int):
                            normalized[lang] = byte_count
                    github_languages_bytes = normalized
                    total_bytes = sum(normalized.values())
                    if total_bytes > 0:
                        github_languages_percent = {
                            lang: round((count / total_bytes) * 100.0, 2)
                            for lang, count in normalized.items()
                        }

            tree_resp = client.get(
                f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}",
                params={"recursive": "1"},
            )
            tree_paths: list[str] = []
            if tree_resp.status_code < 400:
                tree_data = tree_resp.json()
                tree_items = tree_data.get("tree", []) if isinstance(tree_data, dict) else []
                for item in tree_items:
                    if not isinstance(item, dict):
                        continue
                    path = item.get("path")
                    item_type = item.get("type")
                    if isinstance(path, str) and item_type in {"tree", "blob"}:
                        tree_paths.append(path)

            tree_paths = sorted(set(tree_paths))
            top_level = sorted({path.split("/", 1)[0] for path in tree_paths})

            def _fetch_text_file(path: str) -> str | None:
                resp = client.get(f"https://api.github.com/repos/{owner}/{repo}/contents/{path}", params={"ref": default_branch})
                if resp.status_code >= 400:
                    return None
                data = resp.json()
                if not isinstance(data, dict):
                    return None
                encoded = data.get("content")
                if not isinstance(encoded, str):
                    return None
                try:
                    decoded = base64.b64decode(encoded.encode("utf-8"), validate=False).decode("utf-8", errors="replace")
                except Exception:
                    return None
                return decoded[:2000]

            manifest_candidates = [
                "requirements.txt",
                "pyproject.toml",
                "setup.py",
                "setup.cfg",
                "package.json",
                "vite.config.js",
                "vite.config.ts",
                "tsconfig.json",
                "Dockerfile",
                "docker-compose.yml",
                "docker-compose.yaml",
                ".streamlit/config.toml",
            ]
            manifest_summaries: dict[str, str] = {}
            for candidate in manifest_candidates:
                if candidate in tree_paths:
                    content = _fetch_text_file(candidate)
                    if content:
                        manifest_summaries[candidate] = content

            def _append_unique(items: list[str], value: str) -> None:
                if value and value not in items:
                    items.append(value)

            def _parse_requirements_text(text: str) -> list[str]:
                packages: list[str] = []
                for raw_line in text.splitlines():
                    line = raw_line.strip()
                    if not line or line.startswith("#"):
                        continue
                    line = line.split("#", 1)[0].strip()
                    if line.startswith(("-r", "--", "git+", "http://", "https://")):
                        continue
                    base = re.split(r"[<>=!~\[; ]", line, maxsplit=1)[0].strip()
                    if base:
                        packages.append(base.lower())
                return packages

            def _parse_pyproject_text(text: str) -> list[str]:
                packages: list[str] = []
                # Works for poetry and pep621 style arrays/inline values.
                for match in re.findall(r"^\s*([A-Za-z0-9_.-]+)\s*=\s*\"[^\"]+\"", text, flags=re.MULTILINE):
                    packages.append(match.lower())
                for match in re.findall(r"[\"']([A-Za-z0-9_.-]+)\s*[<>=!~]", text):
                    packages.append(match.lower())
                return packages

            def _parse_package_json_text(text: str) -> list[str]:
                packages: list[str] = []
                try:
                    data = json.loads(text)
                    if isinstance(data, dict):
                        for section in ("dependencies", "devDependencies", "peerDependencies"):
                            section_data = data.get(section)
                            if isinstance(section_data, dict):
                                for dep_name in section_data.keys():
                                    if isinstance(dep_name, str):
                                        packages.append(dep_name.lower())
                except Exception:
                    pass
                return packages

            parsed_dependencies: dict[str, list[str]] = {
                "python": [],
                "javascript": [],
            }
            if "requirements.txt" in manifest_summaries:
                for dep in _parse_requirements_text(manifest_summaries["requirements.txt"]):
                    _append_unique(parsed_dependencies["python"], dep)
            if "pyproject.toml" in manifest_summaries:
                for dep in _parse_pyproject_text(manifest_summaries["pyproject.toml"]):
                    _append_unique(parsed_dependencies["python"], dep)
            if "package.json" in manifest_summaries:
                for dep in _parse_package_json_text(manifest_summaries["package.json"]):
                    _append_unique(parsed_dependencies["javascript"], dep)

            detected_tech_stack: dict[str, list[str]] = {
                "Frontend": [],
                "Backend": [],
                "Database": [],
                "Tools": [],
            }

            lower_paths = [path.lower() for path in tree_paths]
            basename_set = {path.rsplit("/", 1)[-1].lower() for path in tree_paths}

            frontend_languages = {"JavaScript", "TypeScript", "HTML", "CSS", "SCSS", "Vue", "Svelte"}
            backend_languages = {"Python", "Go", "Java", "Kotlin", "Ruby", "Rust", "C#", "PHP"}
            for lang_name, percent in sorted(github_languages_percent.items(), key=lambda item: item[1], reverse=True):
                label = f"{lang_name} ({percent:.2f}%)"
                if lang_name in frontend_languages:
                    _append_unique(detected_tech_stack["Frontend"], label)
                elif lang_name in backend_languages:
                    _append_unique(detected_tech_stack["Backend"], label)
                else:
                    _append_unique(detected_tech_stack["Tools"], label)

            # Language/tooling signals from manifests.
            if any(name in basename_set for name in {"requirements.txt", "pyproject.toml", "setup.py", "setup.cfg"}):
                _append_unique(detected_tech_stack["Tools"], "pip")

            # File extension signals.
            if any(path.endswith(".py") for path in lower_paths):
                _append_unique(detected_tech_stack["Backend"], "Python")
            if any(path.endswith((".js", ".jsx", ".ts", ".tsx")) for path in lower_paths):
                _append_unique(detected_tech_stack["Frontend"], "JavaScript/TypeScript")
            if any(path.endswith(".ipynb") for path in lower_paths):
                _append_unique(detected_tech_stack["Tools"], "Jupyter Notebook")

            # Documentation/content-heavy repositories should still expose practical tools.
            if any(path.endswith(".md") for path in lower_paths):
                _append_unique(detected_tech_stack["Tools"], "Markdown")
            if any(path.endswith(".pdf") for path in lower_paths):
                _append_unique(detected_tech_stack["Tools"], "PDF documents")
            if any(path.endswith((".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx")) for path in lower_paths):
                _append_unique(detected_tech_stack["Tools"], "Microsoft Office documents")

            # CI / packaging / infra signals.
            if any(path.startswith(".github/workflows/") for path in lower_paths):
                _append_unique(detected_tech_stack["Tools"], "GitHub Actions")
            if any(name in basename_set for name in {"dockerfile", "docker-compose.yml", "docker-compose.yaml"}):
                _append_unique(detected_tech_stack["Tools"], "Docker")

            js_dep_names = set(parsed_dependencies["javascript"])
            py_dep_names = set(parsed_dependencies["python"])

            if any(name in js_dep_names for name in {"react", "next", "vue", "nuxt", "angular", "svelte"}):
                _append_unique(detected_tech_stack["Frontend"], "Frontend framework (React/Vue/Angular/Svelte)")
            if any(name in js_dep_names for name in {"express", "fastify", "koa", "nestjs", "hapi"}):
                _append_unique(detected_tech_stack["Backend"], "Node.js server framework")

            db_keywords = ("sql", "mongo", "redis", "postgres", "mysql", "sqlite", "prisma", "sequelize", "typeorm", "mongoose")
            if any(any(keyword in dep for keyword in db_keywords) for dep in js_dep_names.union(py_dep_names)):
                _append_unique(detected_tech_stack["Database"], "Database client/ORM")

            # Parse Python manifests for framework/database clues.
            python_manifest_blob = "\n".join(
                [manifest_summaries.get("requirements.txt", ""), manifest_summaries.get("pyproject.toml", "")]
            ).lower()
            if python_manifest_blob:
                if any(term in python_manifest_blob for term in ("streamlit", "gradio", "flask", "django", "fastapi")):
                    _append_unique(detected_tech_stack["Backend"], "Python web framework")
                    if "streamlit" in python_manifest_blob:
                        _append_unique(detected_tech_stack["Frontend"], "Streamlit")
                if any(term in python_manifest_blob for term in ("sqlalchemy", "psycopg", "pymongo", "mysqlclient", "sqlite")):
                    _append_unique(detected_tech_stack["Database"], "Database client/ORM")

            tech_signals = sorted({item for values in detected_tech_stack.values() for item in values})

            preview_paths = tree_paths[:250]
            snapshot = {
                "repo": f"{owner}/{repo}",
                "default_branch": default_branch,
                "description": repo_data.get("description") or "",
                "language": repo_data.get("language") or "",
                "top_level_entries": top_level,
                "path_preview": preview_paths,
                "tech_signals": sorted(set(tech_signals)),
                "manifest_summaries": manifest_summaries,
                "github_languages": github_languages_percent,
                "parsed_dependencies": parsed_dependencies,
                "detected_tech_stack": detected_tech_stack,
            }
            return json.dumps(snapshot, indent=2)
    except Exception:
        return None


_TECH_STACK_SECTION_RE = re.compile(r"(?ims)^##\s+.*tech\s*stack.*?(?=^##\s+|\Z)")


def _build_tech_stack_section_from_snapshot(repo_snapshot: str | None) -> str | None:
    """Build a deterministic Tech Stack section from detected snapshot signals."""
    if not repo_snapshot:
        return None

    try:
        snapshot_data = json.loads(repo_snapshot)
    except Exception:
        return None

    if not isinstance(snapshot_data, dict):
        return None

    detected = snapshot_data.get("detected_tech_stack")
    order = ["Frontend", "Backend", "Database", "Tools"]

    lines: list[str] = ["## Tech Stack", ""]
    non_empty_categories = 0

    if isinstance(detected, dict):
        for category in order:
            raw_values = detected.get(category, [])
            values = [
                str(value).strip()
                for value in raw_values
                if isinstance(value, str) and value.strip()
            ] if isinstance(raw_values, list) else []

            if not values:
                continue

            non_empty_categories += 1
            lines.append(f"### {category}")
            for value in values:
                lines.append(f"- {value}")
            lines.append("")

    if non_empty_categories == 0:
        tech_signals = snapshot_data.get("tech_signals")
        signals = [
            str(value).strip()
            for value in tech_signals
            if isinstance(value, str) and value.strip()
        ] if isinstance(tech_signals, list) else []
        if not signals:
            return None
        lines.append("### Tools")
        for value in signals[:8]:
            lines.append(f"- {value}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def _apply_deterministic_tech_stack(content: str, repo_snapshot: str | None) -> str:
    """Replace generated Tech Stack section with deterministic snapshot-based content."""
    tech_stack_section = _build_tech_stack_section_from_snapshot(repo_snapshot)
    if not tech_stack_section:
        return content

    if _TECH_STACK_SECTION_RE.search(content):
        return _TECH_STACK_SECTION_RE.sub(tech_stack_section + "\n", content, count=1)

    installation_heading = re.search(r"(?im)^##\s+.*installation.*$", content)
    if installation_heading:
        before = content[: installation_heading.start()].rstrip()
        after = content[installation_heading.start() :].lstrip()
        return f"{before}\n\n{tech_stack_section}\n{after}"

    return content.rstrip() + "\n\n" + tech_stack_section


def _normalize_text_for_compare(value: str) -> str:
    return value.replace("\r\n", "\n").rstrip()


def _check_repo_write_access(owner: str, repo: str, github_token: str | None = None) -> tuple[bool, str | None]:
    """Check whether the configured token can push to this repository."""
    headers = _build_github_headers(github_token)
    if "Authorization" not in headers:
        return False, "GitHub token is missing. Set GITHUB_PERSONAL_ACCESS_TOKEN."

    try:
        with httpx.Client(timeout=20.0, headers=headers) as client:
            repo_resp = client.get(f"https://api.github.com/repos/{owner}/{repo}")
            if repo_resp.status_code == 404:
                return False, "Repository not found or token has no access to this repository."
            if repo_resp.status_code >= 400:
                return False, f"Unable to read repository metadata ({repo_resp.status_code})."

            repo_data_raw = repo_resp.json()
            data = repo_data_raw if isinstance(repo_data_raw, dict) else {}
            permissions = data.get("permissions") if isinstance(data, dict) else None
            if not isinstance(permissions, dict):
                return (
                    False,
                    "Could not verify repository push permission from token. Ensure token has Contents: Read and write and repository access.",
                )

            if not permissions.get("push"):
                return False, "Token does not have push permission for this repository."

            return True, None
    except Exception as exc:
        return False, str(exc)


def _resolve_update_branch(
    owner: str,
    repo: str,
    requested_branch: str,
    github_token: str | None = None,
) -> tuple[str | None, str | None]:
    """Resolve an update branch that exists, with fallback to repository default branch."""
    headers = _build_github_headers(github_token)
    try:
        with httpx.Client(timeout=20.0, headers=headers) as client:
            repo_resp = client.get(f"https://api.github.com/repos/{owner}/{repo}")
            if repo_resp.status_code == 404:
                return None, "Repository not found or token has no access to this repository."
            if repo_resp.status_code >= 400:
                return None, f"Unable to read repository metadata ({repo_resp.status_code})."

            repo_data_raw = repo_resp.json()
            repo_data = repo_data_raw if isinstance(repo_data_raw, dict) else {}
            default_branch = str(repo_data.get("default_branch") or "main").strip() or "main"

            normalized_requested = requested_branch.strip() if requested_branch else ""
            if not normalized_requested:
                return default_branch, None

            branch_resp = client.get(f"https://api.github.com/repos/{owner}/{repo}/branches/{normalized_requested}")
            if branch_resp.status_code < 400:
                return normalized_requested, None

            # Requested branch does not exist or is inaccessible; fall back to default branch.
            return default_branch, None
    except Exception as exc:
        return None, str(exc)


def _verify_readme_updated(
    owner: str,
    repo: str,
    branch: str,
    expected_content: str,
    github_token: str | None = None,
) -> tuple[bool, str | None]:
    headers = _build_github_headers(github_token)
    try:
        with httpx.Client(timeout=20.0, headers=headers) as client:
            resp = client.get(
                f"https://api.github.com/repos/{owner}/{repo}/contents/README.md",
                params={"ref": branch},
            )
            if resp.status_code >= 400:
                return False, f"verification request failed with status {resp.status_code}"

            data = resp.json()
            encoded = data.get("content") if isinstance(data, dict) else None
            if not isinstance(encoded, str):
                return False, "verification response did not include README content"

            decoded = base64.b64decode(encoded.encode("utf-8"), validate=False).decode("utf-8", errors="replace")
            if _normalize_text_for_compare(decoded) != _normalize_text_for_compare(expected_content):
                return False, "README content on GitHub does not match the submitted update"
            return True, None
    except Exception as exc:
        return False, str(exc)


def _update_readme_via_github_api(
    owner: str,
    repo: str,
    branch: str,
    readme_content: str,
    commit_message: str,
    github_token: str | None = None,
) -> tuple[bool, str]:
    """Fallback path that updates README.md directly with the GitHub Contents API."""
    headers = _build_github_headers(github_token)
    if "Authorization" not in headers:
        return False, "GitHub token is required for direct README updates."

    content_b64 = base64.b64encode(readme_content.encode("utf-8")).decode("utf-8")

    try:
        with httpx.Client(timeout=20.0, headers=headers) as client:
            read_url = f"https://api.github.com/repos/{owner}/{repo}/contents/README.md"
            read_resp = client.get(read_url, params={"ref": branch})
            sha = None
            if read_resp.status_code < 400:
                read_data = read_resp.json()
                if isinstance(read_data, dict):
                    sha_value = read_data.get("sha")
                    if isinstance(sha_value, str) and sha_value:
                        sha = sha_value

            payload: dict[str, Any] = {
                "message": commit_message,
                "content": content_b64,
                "branch": branch,
            }
            if sha:
                payload["sha"] = sha

            put_resp = client.put(read_url, json=payload)
            if put_resp.status_code >= 400:
                if put_resp.status_code == 404:
                    # GitHub can mask missing write permissions as 404 even when read access works.
                    repo_check = client.get(f"https://api.github.com/repos/{owner}/{repo}")
                    contents_check = client.get(read_url, params={"ref": branch})
                    if repo_check.status_code < 400 and contents_check.status_code < 400:
                        return (
                            False,
                            "GitHub API write access appears unavailable for this token. "
                            "Your token can read the repository but cannot update contents. "
                            "Create/update a token with repository Contents permission set to Read and write, "
                            "then restart the app.",
                        )
                try:
                    error_data = put_resp.json()
                    error_message = error_data.get("message", "Unknown GitHub API error")
                except Exception:
                    error_message = put_resp.text[:220]
                return False, f"GitHub API update failed ({put_resp.status_code}): {error_message}"

            verified, verify_error = _verify_readme_updated(
                owner,
                repo,
                branch,
                readme_content,
                github_token=github_token,
            )
            if not verified:
                return False, f"GitHub API update completed but verification failed ({verify_error})"

            return True, "README.md updated successfully in GitHub repository."
    except Exception as exc:
        return False, str(exc)


def _parse_repo_target(repo_target: str) -> tuple[str, str] | None:
    cleaned = repo_target.strip()
    if "/" not in cleaned:
        return None
    owner, repo = cleaned.split("/", 1)
    owner = owner.strip()
    repo = repo.strip()
    if not owner or not repo:
        return None
    return owner, repo


def _set_first_key(args: dict[str, Any], properties: dict[str, Any], candidates: list[str], value: Any) -> None:
    """Set the first matching candidate key that exists in properties."""
    for key in candidates:
        if key in properties and key not in args:
            args[key] = value
            return


def _build_candidate_arguments(
    tool_name: str,
    properties: dict[str, Any],
    owner: str,
    repo: str,
    readme_content: str,
    commit_message: str,
    branch: str,
) -> list[dict[str, Any]]:
    lower_name = tool_name.lower()
    candidates: list[dict[str, Any]] = []
    readme_file_payload = [{"path": "README.md", "content": readme_content}]

    # Push tools use a different schema; prefer push payload first and avoid noisy invalid calls.
    if "push" in lower_name:
        push_args: dict[str, Any] = {}
        _set_first_key(push_args, properties, ["owner", "repoOwner", "repository_owner"], owner)
        _set_first_key(push_args, properties, ["repo", "repository", "repo_name", "name"], repo)
        _set_first_key(push_args, properties, ["branch", "ref"], branch)
        _set_first_key(push_args, properties, ["message", "commitMessage", "commit_message"], commit_message)

        if "files" in properties:
            push_args["files"] = readme_file_payload
        elif "changes" in properties:
            push_args["changes"] = readme_file_payload
        elif "updates" in properties:
            push_args["updates"] = readme_file_payload
        else:
            # Known GitHub MCP push_files requires files[] even when schema is partial.
            push_args["files"] = readme_file_payload

        if push_args:
            candidates.append(push_args)
        return candidates

    # Build argument set 1: Standard file update/create shape.
    # Try owner/repo + path/content approach
    args1: dict[str, Any] = {}
    _set_first_key(args1, properties, ["owner", "repoOwner", "repository_owner"], owner)
    _set_first_key(args1, properties, ["repo", "repository", "repo_name", "name"], repo)
    _set_first_key(args1, properties, ["path", "filePath", "filepath", "file_path"], "README.md")
    _set_first_key(args1, properties, ["content", "contents", "fileContent", "file_content", "text"], readme_content)
    _set_first_key(args1, properties, ["message", "commitMessage", "commit_message"], commit_message)
    _set_first_key(args1, properties, ["branch", "ref"], branch)
    
    if args1:
        candidates.append(args1)

    # Build argument set 2: Alternative with fullname (owner/repo)
    args2: dict[str, Any] = {}
    if "repository" in properties or "fullName" in properties or "name" in properties:
        full_name = f"{owner}/{repo}"
        for key in ["repository", "fullName", "full_name", "repo", "name"]:
            if key in properties and key not in args2:
                args2[key] = full_name
                break
    else:
        _set_first_key(args2, properties, ["owner", "repoOwner"], owner)
        _set_first_key(args2, properties, ["repo"], repo)
    
    _set_first_key(args2, properties, ["path", "filePath", "filepath", "file_path"], "README.md")
    _set_first_key(args2, properties, ["content", "contents", "fileContent", "file_content", "text"], readme_content)
    _set_first_key(args2, properties, ["message", "commitMessage", "commit_message"], commit_message)
    _set_first_key(args2, properties, ["branch", "ref"], branch)
    
    if args2 and args2 != args1:
        candidates.append(args2)

    # Build argument set 3: Push/batch semantics (for non-push tool names that still expose batch fields)
    args3: dict[str, Any] = {}
    _set_first_key(args3, properties, ["owner", "repoOwner", "repository_owner"], owner)
    _set_first_key(args3, properties, ["repo", "repository", "repo_name", "name"], repo)
    _set_first_key(args3, properties, ["branch", "ref"], branch)
    _set_first_key(args3, properties, ["message", "commitMessage", "commit_message"], commit_message)
    
    # Handle files array (most common in push operations)
    if "files" in properties:
        args3["files"] = readme_file_payload
    elif "changes" in properties:
        args3["changes"] = readme_file_payload
    elif "updates" in properties:
        args3["updates"] = readme_file_payload
    elif "push" in lower_name:
        # Some MCP schemas under-specify push payload fields; include files explicitly.
        args3["files"] = readme_file_payload
    
    if args3 and ("files" in args3 or "changes" in args3 or "updates" in args3):
        candidates.append(args3)

    return candidates


async def update_repository_readme(
    repo_target: str,
    readme_content: str,
    commit_message: str,
    branch: str = "main",
    github_token: str | None = None,
) -> tuple[bool, str]:
    """Update README.md in a GitHub repository via MCP server write tools."""
    parsed = _parse_repo_target(repo_target)
    if not parsed:
        return False, "Invalid repository target. Use owner/repo format."

    owner, repo = parsed
    resolved_branch, branch_error = _resolve_update_branch(owner, repo, branch, github_token=github_token)
    if not resolved_branch:
        return False, f"Unable to resolve target branch for update. {branch_error or ''}".strip()

    # Primary path: direct GitHub API update (more reliable than MCP write tools).
    api_ok, api_message = _update_readme_via_github_api(
        owner=owner,
        repo=repo,
        branch=resolved_branch,
        readme_content=readme_content,
        commit_message=commit_message,
        github_token=github_token,
    )
    if api_ok:
        return True, api_message

    server_params = build_server_params(github_token=github_token)

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_res = await session.list_tools()

            preferred_file_tools = {"create_or_update_file", "update_file", "push_files", "create_file"}
            write_tools = []
            for tool in tools_res.tools:
                tool_name = tool.name.lower()
                if tool.name in preferred_file_tools:
                    write_tools.append(tool)
                    continue
                if "file" in tool_name and any(token in tool_name for token in ("create", "update", "push")):
                    write_tools.append(tool)

            preferred_order = ["create_or_update_file", "update_file", "push_files", "create_file"]
            write_tools.sort(
                key=lambda tool: (
                    next((idx for idx, name in enumerate(preferred_order) if name == tool.name), len(preferred_order)),
                    tool.name,
                )
            )

            if not write_tools:
                return False, "No writable GitHub MCP tool was found to update README.md."

            failures: list[str] = []

            for tool in write_tools:
                input_schema = tool.inputSchema if isinstance(tool.inputSchema, dict) else {}
                properties = input_schema.get("properties", {}) if isinstance(input_schema, dict) else {}
                candidates = _build_candidate_arguments(
                    tool_name=tool.name,
                    properties=properties if isinstance(properties, dict) else {},
                    owner=owner,
                    repo=repo,
                    readme_content=readme_content,
                    commit_message=commit_message,
                    branch=resolved_branch,
                )

                for args in candidates:
                    try:
                        tool_result = await session.call_tool(tool.name, args)
                        result_content = str(getattr(tool_result, "content", ""))
                        
                        if not result_content:
                            failures.append(f"{tool.name}: empty response")
                            continue
                        if "error" in result_content.lower():
                            failures.append(f"{tool.name}: {result_content[:220]}")
                            continue
                        
                        verified, verify_error = _verify_readme_updated(
                            owner=owner,
                            repo=repo,
                            branch=resolved_branch,
                            expected_content=readme_content,
                            github_token=github_token,
                        )
                        if not verified:
                            failures.append(f"{tool.name}: write call returned but verification failed ({verify_error})")
                            continue
                        return True, "README.md updated successfully in GitHub repository."
                    except Exception as exc:
                        exc_str = str(exc)
                        # Truncate long error messages but keep key details
                        if len(exc_str) > 200:
                            exc_str = exc_str[:200] + "..."
                        failures.append(f"{tool.name}: {exc_str}")

            failure_preview = " | ".join(failures[:3]) if failures else "No tool call attempts were made."
            return (
                False,
                f"Failed to update README for {owner}/{repo} on branch '{resolved_branch}'. "
                f"GitHub API: {api_message} | MCP: {failure_preview}",
            )