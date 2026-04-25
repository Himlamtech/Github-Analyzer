from __future__ import annotations

CODE_SUMMARY_PROMPT = """
You are an expert Senior Software Engineer.
Please analyze the following repository README and source code excerpts.
Provide a comprehensive technical summary including:
1. Primary purpose of the project.
2. Architecture and Technology stack.
3. Key features.
4. Potential areas of improvement or security risks.

Repository Content:
{content}
"""

PR_REVIEW_PROMPT = """
You are an automated Code Review Assistant.
Review the following pull request diff.
Identify bugs, performance issues, and suggest improvements.

Diff:
{diff}
"""
