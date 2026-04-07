"""Prompt builders for README audit and upgrade workflows."""


def build_system_prompt() -> str:
    return (
        "You are a Senior DevOps and Technical Architect. Your goal is to IMPROVE the repository's documentation. "
        "Do NOT just copy the existing README. Instead: "
        "1. Audit the current README for missing information (e.g., specific API routes, hidden config files). "
        "2. Use 'get_file_contents' to inspect package.json and source code for features not mentioned in the README. "
        "3. Add a 'Modern Architecture' section explaining folder structure and design choices. "
        "4. If you find secrets or risky practices, add a 'Security' or 'Best Practices' section. "
        "Your output must be a SIGNIFICANT upgrade over the original."
    )


def build_user_prompt(repo_target: str) -> str:
    return (
        f"Perform a deep audit of '{repo_target}'. Compare the existing README with the actual code "
        "and generate a professional and detailed README V2."
    )