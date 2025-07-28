import json
import os
import asyncio
import subprocess
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from typing import Dict, List
from pydantic import Field

# Initialize the FastMCP server
mcp = FastMCP("pr-agent")

# PR template directory
PR_TEMPLATE_DIR = Path(__file__).parent.parent / "pr_templates"


@mcp.tool(
    name="analyze_file_changes",
    description="Get the full diff and list of changed files in the current git repository.",
)
def analyze_file_changes(
    include_diff: bool = True,
    max_diff_lines: int = 1000,
) -> str:
    """Get the full diff and list of changed files in the current git repository.

    Args:
        include_diff: Include the full diff content (default: True)
        max_diff_lines: Maximum number of diff lines to include (default: 500)

    Output:
        {
        "changed_files": [...],
        "diff": "patch text",
        "diff_line_count": N,
        "truncated": false
        }
    """
    result = {
        "changed_files": [],
        "diff": "",
        "diff_line_count": 0,
        "truncated": False,
        "error": None,
    }

    try:
        # 1. filenames
        files_proc = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        result["changed_files"] = [
            f for f in files_proc.stdout.splitlines() if f.strip()
        ]

        if include_diff:
            # 2. patch
            diff_proc = subprocess.run(
                ["git", "diff", "--cached"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
            lines = diff_proc.stdout.splitlines()
            result["diff_line_count"] = len(lines)

            if len(lines) > max_diff_lines:
                result["diff"] = "\n".join(lines[:max_diff_lines])
                result["truncated"] = True
            else:
                result["diff"] = diff_proc.stdout

    except subprocess.CalledProcessError as e:
        result["error"] = e.stderr.strip() or str(e)

    return json.dumps(result)


@mcp.resource(
    "templates://documents",
    description="List available PR templates in the repository.",
    mime_type="application/json",
)
def list_available_pr_templates() -> str:
    result = {"templates": []}
    try:
        if not os.path.exists(PR_TEMPLATE_DIR) or not os.path.isdir(PR_TEMPLATE_DIR):
            return json.dumps(
                {"error": f"Directory '{PR_TEMPLATE_DIR}' does not exist."}
            )

        for fname in os.listdir(PR_TEMPLATE_DIR):
            fpath = os.path.join(PR_TEMPLATE_DIR, fname)
            if not os.path.isfile(fpath):
                continue
            try:
                with open(fpath, encoding="utf-8") as f:
                    content = f.read()
                result["templates"].append({"filename": fname, "content": content})
            except Exception as file_err:
                result["templates"].append({"filename": fname, "error": str(file_err)})
    except Exception as e:
        return json.dumps({"error": str(e)})

    return json.dumps(result)


@mcp.resource(
    "templates://documents/{template_name}",
    description="Fetch a specific PR template by name.",
    mime_type="text/markdown",
)
def fetch_pr_template(
    template_name: str = Field(
        description="Name of the PR template to fetch (e.g., 'bugfix', 'feature', etc. without extension)"
    ),
) -> str:
    """Fetch a specific PR template by name."""
    template_path = PR_TEMPLATE_DIR / f"{template_name}.md"
    if not template_path.exists() or not template_path.is_file():
        return json.dumps({"error": f"Template '{template_name}' not found."})

    try:
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    except Exception as e:
        return json.dumps({"error": str(e)})


def _find_best_template(
    change_type: str, templates: List[Dict[str, str]]
) -> Dict[str, str]:
    """Try to pick the best template whose filename or content matches the change_type."""
    ct = change_type.lower()
    # Common canonical name mappings
    canonical_map = {
        "bug": ["bug", "fix", "bugfix"],
        "feature": ["feature", "enhancement", "new"],
        "docs": ["doc", "docs", "documentation"],
        "refactor": ["refactor", "cleanup"],
        "test": ["test", "tests"],
        "performance": ["performance", "speed", "optimization", "optimize"],
        "security": ["security", "secure", "vulnerability", "auth", "encryption"],
    }
    # Build a search set
    search_terms = canonical_map.get(ct, [ct])

    # 1. Try to match filename
    for t in templates:
        fname = t["filename"].lower()
        if any(term in fname for term in search_terms):
            return t

    # 2. Try to match first line/content
    for t in templates:
        content_lower = t["content"][:512].lower()
        if any(term in content_lower for term in search_terms):
            return t

    # 3. As fallback, just return the first template if it exists
    if templates:
        return templates[0]
    return {}


@mcp.tool(
    name="suggest_template",
    description="Analyze changes and suggest the most appropriate PR template based on change type.",
)
def suggest_template(
    changes_summary: str = Field(description="Your analysis of what the changes do"),
    change_type: str = Field(
        description="The type of change you've identified (bug, feature, docs, refactor, test, etc.)"
    ),
) -> str:
    """Suggest the best-matching PR template based on change_type."""
    templates = list_available_pr_templates()
    if not templates:
        return json.dumps({"error": f"No templates found in {TEMPLATES_DIR}."})
    best = _find_best_template(change_type, templates)
    if best:
        return json.dumps(
            {
                "selected_template": best,
                "reason": f"Template matched for change_type '{change_type}'.",
                "available_templates": [t["filename"] for t in templates],
            }
        )
    else:
        return json.dumps(
            {
                "error": "No suitable template found.",
                "available_templates": [t["filename"] for t in templates],
            }
        )


if __name__ == "__main__":
    mcp.run(transport="stdio")
