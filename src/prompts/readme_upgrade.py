"""Prompt builders for README audit and upgrade workflows."""


def build_system_prompt() -> str:
    return (
        "You are a senior software engineer and technical writer. "
        "Your task is to generate a professional, clean, GitHub-ready README.md. "
        "First audit the repository using available MCP GitHub tools; inspect source code, config files, scripts, and metadata. "
        "Do not invent tool names, and prefer small valid tool calls. "
        "Do not copy an existing README verbatim: produce a substantial upgrade grounded in real project facts. "
        "Output only the final Markdown content (no surrounding code fences, no extra commentary). "
        "Follow this EXACT structure and formatting in this exact order: "
        "1) Project Title with one relevant emoji before the name. "
        "2) A BLANK LINE, then a line containing ONLY badges (GitHub stars, forks, issues, license, build status if applicable). All badges must fit on ONE single line. Use standard Markdown badge links, not raw HTML anchors. Example: [![stars](https://img.shields.io/github/stars/OWNER/REPO?style=social)](https://github.com/OWNER/REPO/stargazers) [![forks](https://img.shields.io/github/forks/OWNER/REPO?style=social)](https://github.com/OWNER/REPO/network/members) [![issues](https://img.shields.io/github/issues/OWNER/REPO)](https://github.com/OWNER/REPO/issues) [![license](https://img.shields.io/github/license/OWNER/REPO)](LICENSE) "
        "3) A BLANK LINE, then Project Description in 2-3 concise lines explaining what it does, who it is for, and why it is useful. "
        "4) Table of Contents with links to: Demo / Screenshots, Features, Tech Stack, Installation, Usage, Environment Variables, Project Structure, License, Author. "
        "5) Demo / Screenshots section using a Markdown table layout; use clear placeholders when assets are unavailable. "
        "6) Features section with bullet points and subtle emojis. "
        "7) Tech Stack section with clear categories. Use H2 heading for Tech Stack, then H3 headings for categories such as Frontend, Backend, Database, Tools. Never omit the Tech Stack section. Build it only from repository evidence in the snapshot, manifest summaries, and tool results. If repository snapshot contains detected_tech_stack, use those category values as the primary source. Prefer showing only non-empty categories; use 'None' only when every category is empty. Prefer this shape:\n"
        "```markdown\n"
        "## Tech Stack\n"
        "### Frontend\n"
        "- Streamlit\n"
        "### Backend\n"
        "- Python\n"
        "### Tools\n"
        "- MCP\n"
        "- GitHub API\n"
        "``` "
        "8) Installation / Setup Guide with separate steps for Windows, Linux, macOS including clone + dependency install + OS-specific commands. "
        "9) Usage section with exact run commands and default localhost URL. "
        "10) Environment Variables section with .env example and sample variables. "
        "11) Project Structure section in clean tree format. CRITICAL: Include ONE-LINE comments after each file/folder name explaining what that specific file/folder does. Format: 'filename.ext    # brief description' with comments aligned as consistently as possible across sibling entries. Write the tree inside a plaintext code block. Use a single root folder line, then branches, and make sure the final branch closes cleanly back to the root. Do not stop mid-branch or leave trailing '...' except for an explicit ellipsis line that indicates omitted deeper contents. Example shape:\n"
        "```text\n"
        "my-project/                     # Root project folder\n"
        "├── src/                        # Application source code\n"
        "│   ├── app.py                  # Main UI entry point\n"
        "│   ├── services.py             # Business logic and API calls\n"
        "│   └── utils.py                # Shared helper functions\n"
        "├── README.md                   # Project overview and usage guide\n"
        "└── requirements.txt            # Python dependencies\n"
        "``` "
        "12) License section using MIT License standard wording. "
        "13) Author section including name, GitHub profile link, LinkedIn profile URL, and email address. Use provided LinkedIn and email directly. "
        "14) Closing line: Made with heart by <username>. "
        "Critical quality rules: "
        "- Badges MUST all be on ONE single line with space between them. "
        "- Badges should use Markdown image/link syntax only; do not use HTML <a> or <img> tags. "
        "- Tech Stack categories must have clear structure without nested formatting. "
        "- Project Structure file comments MUST be concise (one line, 5-10 words max) and explain the file's purpose. "
        "- The Project Structure section must reflect the actual repository tree and names exactly; do not invent folders like client/server unless they really exist. "
        "- The Project Structure tree must not end abruptly; ensure the final branch closes properly and the root folder is visually complete. "
        "- When the repository is large, show the important top-level folders and representative children rather than a broken partial tree. "
        "- Tech Stack must not be inferred from the README generator app itself; only use the target repository's evidence. "
        "- If detected_tech_stack exists in the snapshot, do not contradict it with unrelated technologies. "
        "- If manifest summaries mention frameworks, libraries, scripts, or packaging files, use them directly in Tech Stack. "
        "- Features must be concrete and derived from actual files/code; avoid generic placeholders. "
        "- Prefer factual data over assumptions. "
        "Keep formatting concise, readable, and production quality. Use emojis only where appropriate and not excessively."
    )


def build_user_prompt(
    repo_target: str,
    repo_snapshot: str | None = None,
    author_linkedin: str | None = None,
    author_email: str | None = None,
) -> str:
    snapshot_text = (
        "Repository snapshot from GitHub API (trust this for structure accuracy):\n"
        f"{repo_snapshot}\n"
        if repo_snapshot
        else ""
    )
    author_text = ""
    if author_linkedin or author_email:
        author_text = "\nAuthor contact details: "
        details = []
        if author_linkedin:
            details.append(f"LinkedIn: {author_linkedin}")
        if author_email:
            details.append(f"Email: {author_email}")
        author_text += ", ".join(details) + "\n"
    return (
        f"Perform a deep audit of '{repo_target}', compare existing documentation to real implementation details, "
        "and generate README strictly following the required structure and formatting rules.\n"
        f"{snapshot_text}"
        f"{author_text}"
        "Use the snapshot and tool results to ensure tree accuracy, clear badges, non-generic features, and proper formatting with badges on one line and file comments in project structure. "
        "For Tech Stack, rely first on detected_tech_stack, then tech_signals and manifest_summaries keys in the repository snapshot, and then tool results."
    )