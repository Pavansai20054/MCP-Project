import argparse
import asyncio
from pathlib import Path
import re

from src.config.env import config
from src.app_service import generate_readme_upgrade, missing_env_vars


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an upgraded README by auditing a GitHub repository via MCP + Groq."
    )
    parser.add_argument(
        "--repo",
        default="",
        help="Target repository in owner/repo format.",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=10,
        help="Maximum think-act-observe iterations.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="Optional file path to save generated README content.",
    )
    return parser.parse_args()


def resolve_repo(repo_arg: str) -> str:
    """Resolve repo from CLI or prompt the user for owner/repo."""
    pattern = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
    candidate = repo_arg.strip()

    while not candidate:
        candidate = input("Enter repository (owner/repo): ").strip()

    while not pattern.match(candidate):
        print("Invalid format. Please use owner/repo (example: octocat/Hello-World)")
        candidate = input("Enter repository (owner/repo): ").strip()

    return candidate


def validate_env() -> bool:
    missing = missing_env_vars()
    if missing:
        print("Missing required environment variables:")
        for key in missing:
            print(f"- {key}")
        return False
    return True


async def main() -> None:
    args = parse_args()
    if not validate_env():
        return
    repo_target = resolve_repo(args.repo)

    print("Launching GitHub MCP server...")
    print(f"Using model: {config.GROQ_MODEL}")
    print(f"Auditing repository: {repo_target}")

    final_content, error_message = await generate_readme_upgrade(
        repo_target=repo_target,
        max_iterations=args.max_iterations,
    )

    if not final_content:
        if error_message:
            print(f"Generation failed: {error_message}")
        else:
            print("No content generated. Try increasing --max-iterations.")
        return

    print("\n" + "=" * 50)
    print("FINAL GENERATED README")
    print("=" * 50 + "\n")
    print(final_content)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(final_content, encoding="utf-8")
        print(f"\nSaved output to: {out_path}")

if __name__ == "__main__":
    asyncio.run(main())