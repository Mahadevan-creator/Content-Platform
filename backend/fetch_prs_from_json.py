#!/usr/bin/env python3
"""
Fetch PR data from a JSON input file containing candidate names and their PR links.
Creates a summary.json file with LLM-based scoring similar to rank_contributors.py.

Input JSON format:
{
  "CANDIDATE_NAME_1": {
    "PR_LINKS": ["https://github.com/owner/repo/pull/123", "https://github.com/owner/repo/pull/456", ...]
  },
  "CANDIDATE_NAME_2": {
    "PR_LINKS": ["https://github.com/owner/repo/pull/789", ...]
  }
}

Usage:
  export GITHUB_TOKEN="..."
  python3 fetch_prs_from_json.py input.json

Optional env vars:
  SLEEP_SECS=0.2          # pacing between API calls (helps avoid secondary limits)
  OUTPUT_PREFIX="candidates"  # prefix for output files
  LLM_MODEL="llama3:latest"  # LLM model for scoring
"""

import os
import re
import sys
import json
import time
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse

import requests

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("Warning: ollama not installed. LLM features will be disabled.")
    print("Install with: pip install ollama")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    print("ERROR: set GITHUB_TOKEN environment variable with a GitHub token")
    sys.exit(1)

SLEEP_SECS = float(os.getenv("SLEEP_SECS", "0.2"))
TIMEOUT_SECS = float(os.getenv("TIMEOUT_SECS", "60"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "8"))
OUTPUT_PREFIX = os.getenv("OUTPUT_PREFIX", "candidates")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3:latest")

SESSION = requests.Session()
SESSION.headers.update({
    "Authorization": f"bearer {GITHUB_TOKEN}",
    "Accept": "application/json",
    "User-Agent": "hackerrank-sourcing-agent/1.0"
})

GRAPHQL_URL = "https://api.github.com/graphql"


def parse_pr_url(url: str):
    """Parse a PR URL to extract owner, repo, and PR number."""
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    parts = path.split("/")
    if len(parts) < 4 or parts[2] != "pull":
        raise ValueError(f"Cannot parse PR URL: {url}")
    owner = parts[0]
    repo = parts[1]
    pr_number = int(parts[3])
    return owner, repo, pr_number


def backoff_sleep(attempt: int):
    wait = min(60, (2 ** attempt))
    logging.warning("Backing off for %ss", wait)
    time.sleep(wait)


def gql(query: str, variables: dict):
    attempt = 0
    while True:
        try:
            resp = SESSION.post(
                GRAPHQL_URL,
                json={"query": query, "variables": variables},
                timeout=TIMEOUT_SECS,
            )
        except requests.exceptions.RequestException as e:
            attempt += 1
            logging.warning("Network error talking to GitHub GraphQL: %r", e)
            if attempt > MAX_RETRIES:
                raise
            backoff_sleep(attempt)
            continue

        if resp.status_code in (502, 503, 504):
            attempt += 1
            if attempt > MAX_RETRIES:
                raise RuntimeError(f"GitHub GraphQL repeatedly returned {resp.status_code}")
            backoff_sleep(attempt)
            continue

        if resp.status_code == 403:
            attempt += 1
            logging.warning("403 from GitHub (possible secondary rate limit). Resp: %s", resp.text[:300])
            if attempt > MAX_RETRIES:
                raise RuntimeError("GitHub GraphQL repeatedly returned 403 (rate limit?)")
            backoff_sleep(attempt)
            continue

        if resp.status_code == 401:
            raise RuntimeError("Unauthorized: check GITHUB_TOKEN")

        try:
            data = resp.json()
        except ValueError:
            attempt += 1
            logging.warning("Non-JSON response from GitHub (%s): %s", resp.status_code, resp.text[:300])
            if attempt > MAX_RETRIES:
                raise RuntimeError("GitHub GraphQL returned non-JSON too many times")
            backoff_sleep(attempt)
            continue

        if "errors" in data:
            msg = json.dumps(data["errors"])[:500]
            if "rate limit" in msg.lower() or "secondary rate limit" in msg.lower():
                attempt += 1
                if attempt > MAX_RETRIES:
                    raise RuntimeError("GitHub GraphQL kept rate-limiting (see errors field)")
                backoff_sleep(attempt)
                continue
            raise RuntimeError(f"GraphQL errors: {data['errors']}")

        return data["data"]


def safe_user(node):
    if not node:
        return None
    return {
        "login": node.get("login"),
        "id": node.get("databaseId"),
        "url": node.get("url"),
        "typename": node.get("__typename")
    }


PR_QUERY = """
query($owner:String!, $name:String!, $number:Int!) {
  repository(owner:$owner, name:$name) {
    pullRequest(number:$number) {
      id
      number
      title
      body
      url
      state
      createdAt
      updatedAt
      closedAt
      mergedAt
      merged
      additions
      deletions
      changedFiles

      author {
        __typename
        login
        url
        ... on User { databaseId }
      }

      labels(first:50) {
        nodes { name }
      }

      assignees(first:20) {
        nodes {
          __typename
          login
          url
          ... on User { databaseId }
        }
      }

      comments { totalCount }
      reviews { totalCount }
    }
  }
}
"""

COMMENTS_PAGE_QUERY = """
query($prId:ID!, $after:String) {
  node(id:$prId) {
    ... on PullRequest {
      comments(first:100, after:$after) {
        pageInfo { hasNextPage endCursor }
        nodes {
          databaseId
          body
          createdAt
          updatedAt
          author {
            __typename
            login
            url
            ... on User { databaseId }
          }
        }
      }
    }
  }
}
"""

REVIEWS_PAGE_QUERY = """
query($prId:ID!, $after:String) {
  node(id:$prId) {
    ... on PullRequest {
      reviews(first:100, after:$after) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          state
          body
          createdAt
          updatedAt
          author {
            __typename
            login
            url
            ... on User { databaseId }
          }
        }
      }
    }
  }
}
"""


def fetch_pr_data(owner: str, repo: str, pr_number: int):
    """Fetch a single PR with all its comments and reviews."""
    logging.info("Fetching PR #%d from %s/%s", pr_number, owner, repo)
    
    data = gql(PR_QUERY, {"owner": owner, "name": repo, "number": pr_number})
    pr_node = (data.get("repository") or {}).get("pullRequest")
    
    if not pr_node:
        logging.warning("PR #%d not found in %s/%s", pr_number, owner, repo)
        return None
    
    pr_id = pr_node["id"]
    
    comments = fetch_all_comments(pr_id)
    reviews = fetch_all_reviews(pr_id)
    
    author = safe_user(pr_node.get("author"))
    assignees = [safe_user(a) for a in ((pr_node.get("assignees") or {}).get("nodes") or [])]
    labels = [l["name"] for l in ((pr_node.get("labels") or {}).get("nodes") or [])]
    
    comments_out = []
    for c in comments:
        u = safe_user(c.get("author"))
        comments_out.append({
            "id": c.get("databaseId"),
            "body": c.get("body"),
            "created_at": c.get("createdAt"),
            "updated_at": c.get("updatedAt"),
            "user": u
        })
    
    reviews_out = []
    for r in reviews:
        u = safe_user(r.get("author"))
        reviews_out.append({
            "id": r.get("id"),
            "state": r.get("state"),
            "body": r.get("body"),
            "created_at": r.get("createdAt"),
            "updated_at": r.get("updatedAt"),
            "user": u
        })
    
    pr_obj = {
        "pr_number": pr_node.get("number"),
        "title": pr_node.get("title"),
        "body": pr_node.get("body"),
        "url": pr_node.get("url"),
        "state": pr_node.get("state"),
        "created_at": pr_node.get("createdAt"),
        "updated_at": pr_node.get("updatedAt"),
        "closed_at": pr_node.get("closedAt"),
        "merged_at": pr_node.get("mergedAt"),
        "merged": pr_node.get("merged"),
        "additions": pr_node.get("additions"),
        "deletions": pr_node.get("deletions"),
        "changed_files": pr_node.get("changedFiles"),
        "author": author,
        "assignees": assignees,
        "labels": labels,
        "comments_count": (pr_node.get("comments") or {}).get("totalCount", 0),
        "comments": comments_out,
        "reviews_count": (pr_node.get("reviews") or {}).get("totalCount", 0),
        "reviews": reviews_out
    }
    
    time.sleep(SLEEP_SECS)
    return pr_obj


def fetch_all_comments(pr_id: str):
    """Fetch ALL comments for a PR via cursor pagination."""
    after = None
    comments = []
    while True:
        data = gql(COMMENTS_PAGE_QUERY, {"prId": pr_id, "after": after})
        node = data.get("node") or {}
        comments_conn = (node.get("comments") or {})
        nodes = comments_conn.get("nodes") or []
        comments.extend(nodes)
        
        pi = comments_conn.get("pageInfo") or {}
        if not pi.get("hasNextPage"):
            break
        after = pi.get("endCursor")
        time.sleep(SLEEP_SECS)
    
    return comments


def fetch_all_reviews(pr_id: str):
    """Fetch ALL reviews for a PR via cursor pagination."""
    after = None
    reviews = []
    while True:
        data = gql(REVIEWS_PAGE_QUERY, {"prId": pr_id, "after": after})
        node = data.get("node") or {}
        reviews_conn = (node.get("reviews") or {})
        nodes = reviews_conn.get("nodes") or []
        reviews.extend(nodes)
        
        pi = reviews_conn.get("pageInfo") or {}
        if not pi.get("hasNextPage"):
            break
        after = pi.get("endCursor")
        time.sleep(SLEEP_SECS)
    
    return reviews


def is_bot_user_simple(username: str, user_obj: dict = None) -> bool:
    """
    Quick bot detection (without API call).
    Checks username patterns and user object type field.
    """
    if not username:
        return False
    
    username_lower = username.lower()
    
    # Common bot patterns
    bot_patterns = [
        username_lower.endswith('[bot]'),
        username_lower.endswith('-bot'),
        username_lower.endswith('_bot'),
        username_lower.startswith('bot-'),
        username_lower.startswith('bot_'),
    ]
    
    # Common known bot names
    known_bots = [
        'dependabot',
        'renovate',
        'greenkeeper',
        'snyk-bot',
        'codecov',
        'allcontributors',
        'stale',
        'mergify',
        'imgbot',
        'github-actions',
        'actions-user',
        'prettier-ci',
        'semantic-release',
    ]
    
    if any(bot_patterns) or username_lower in known_bots:
        return True
    
    # Check user object type if provided
    if user_obj:
        typename = user_obj.get('typename', '').lower()
        if typename == 'bot':
            return True
    
    return False


def add_contrib(contributors_index: dict, login: str, user_obj: dict, role: str, pr_obj: dict):
    if not login:
        return
    
    # Skip bot users
    if is_bot_user_simple(login, user_obj):
        logging.debug(f"🤖 Skipping bot user: {login}")
        return
    
    idx = contributors_index.setdefault(login, {
        "login": login,
        "id": user_obj.get("id") if user_obj else None,
        "profile_url": user_obj.get("url") if user_obj else None,
        "typename": user_obj.get("typename") if user_obj else None,
        "pr_count": 0,
        "prs": [],
        "roles_summary": {}
    })
    pr_number = pr_obj.get("pr_number")
    existing_pr = next((p for p in idx["prs"] if p.get("pr_number") == pr_number), None)
    if not existing_pr:
        pr_obj_copy = pr_obj.copy()
        pr_obj_copy.pop("contributors", None)  # Remove contributors array
        idx["prs"].append(pr_obj_copy)
        idx["pr_count"] += 1
    idx["roles_summary"][role] = idx["roles_summary"].get(role, 0) + 1


def score_loc(loc_total: Optional[int]) -> float:
    """Score LOC (Lines of Code). Returns 0-5."""
    if loc_total is None or loc_total <= 0:
        return 0.0
    if loc_total >= 2000:
        return 5.0
    if loc_total >= 1500:
        return 4.5
    if loc_total >= 1000:
        return 4.0
    if loc_total >= 500:
        return 3.5
    if loc_total >= 300:
        return 3.0
    if loc_total >= 200:
        return 2.5
    if loc_total >= 100:
        return 2.0
    if loc_total >= 50:
        return 1.5
    return 1.0


def calculate_pr_time_taken(pr: Dict[str, Any]) -> Optional[float]:
    """Calculate time taken for a PR in days. Returns None if dates are missing."""
    created_at = pr.get("created_at")
    merged_at = pr.get("merged_at")
    closed_at = pr.get("closed_at")
    
    if not created_at:
        return None
    
    from datetime import datetime
    try:
        created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        end_date = None
        
        if merged_at:
            end_date = datetime.fromisoformat(merged_at.replace('Z', '+00:00'))
        elif closed_at:
            end_date = datetime.fromisoformat(closed_at.replace('Z', '+00:00'))
        else:
            return None  # PR is still open
        
        delta = end_date - created
        return delta.total_seconds() / (24 * 3600)  # Convert to days
    except (ValueError, AttributeError):
        return None


def score_time_taken(avg_days: Optional[float]) -> float:
    """Score time taken (average days to merge). Lower is better. Returns 0-5."""
    if avg_days is None:
        return 2.5  # Default score if data unavailable
    
    # Lower time = higher score
    # Ideal: < 1 day = 5.0
    # Good: 1-3 days = 4.0-4.5
    # Average: 3-7 days = 3.0-3.5
    # Slow: 7-14 days = 2.0-2.5
    # Very slow: > 14 days = 0.0-1.5
    
    if avg_days <= 1:
        return 5.0
    if avg_days <= 2:
        return 4.5
    if avg_days <= 3:
        return 4.0
    if avg_days <= 5:
        return 3.5
    if avg_days <= 7:
        return 3.0
    if avg_days <= 10:
        return 2.5
    if avg_days <= 14:
        return 2.0
    if avg_days <= 21:
        return 1.5
    if avg_days <= 30:
        return 1.0
    return 0.5


def score_pr_merge_rate(rate: float) -> float:
    """Score PR merge rate. Returns 0-5."""
    if rate >= 0.95:
        return 5.0
    if rate >= 0.85:
        return 4.5
    if rate >= 0.75:
        return 4.0
    if rate >= 0.65:
        return 3.5
    if rate >= 0.50:
        return 3.0
    if rate >= 0.40:
        return 2.5
    if rate >= 0.30:
        return 2.0
    if rate >= 0.20:
        return 1.5
    if rate >= 0.10:
        return 1.0
    return 0.5


def score_pr_count(total_prs: int) -> float:
    """Score total PRs contributed. Returns 0-5."""
    if total_prs < 1:
        return 0.0
    if total_prs >= 20:
        return 5.0
    if total_prs >= 15:
        return 4.5
    if total_prs >= 10:
        return 4.0
    if total_prs >= 8:
        return 3.5
    if total_prs >= 6:
        return 3.0
    if total_prs >= 3:
        return 2.5
    return 1.5


# ----------------------------
# LLM Functions
# ----------------------------

LLM_SYSTEM = (
    "You are a strict evaluator for open-source contributions. "
    "Return ONLY valid JSON. No markdown. No extra text."
)


def ollama_json(model: str, prompt: str, temperature: float = 0.1) -> Dict[str, Any]:
    """Call Ollama and parse JSON response."""
    if not OLLAMA_AVAILABLE:
        raise RuntimeError("Ollama not available")
    try:
        resp = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": LLM_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            options={"temperature": temperature},
        )
        txt = (resp.get("message", {}).get("content") or "").strip()
        if not txt:
            logging.warning("Ollama returned empty response")
            return {}
        
        m = re.search(r"\{.*\}", txt, flags=re.S)
        if m:
            txt = m.group(0)
        
        try:
            return json.loads(txt)
        except json.JSONDecodeError as e:
            logging.warning(f"Failed to parse JSON from Ollama response: {e}. Response: {txt[:200]}")
            return {}
    except Exception as e:
        logging.error(f"Error calling Ollama: {e}")
        raise


def llm_score_pr_quality(model: str, pr: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze PR quality: description, tech stack, and code quality."""
    title = pr.get("title", "")
    body = pr.get("body", "")[:3000]
    labels = pr.get("labels", [])
    additions = pr.get("additions", 0)
    deletions = pr.get("deletions", 0)
    changed_files = pr.get("changed_files", 0)
    
    prompt = f"""
Analyze this GitHub Pull Request for quality, tech stack, and code quality.

PR title: {title}
PR labels: {labels}
PR body: {body[:2000]}
Code changes: +{additions} / -{deletions} lines, {changed_files} files changed

Evaluate:
1. Description quality (0-5): How clear, actionable, and well-documented is the PR?
2. Tech stack detection: Identify technologies mentioned (.net, react, node, spring boot, go, django, typescript, javascript, python, java, etc.)
3. Code quality (0-5): Based on PR description, labels, and change size, assess technical quality

Return ONLY JSON:
{{
  "quality_score_0_5": 0,
  "description_quality_0_5": 0,
  "code_quality_0_5": 0,
  "tech_stack_detected": [],
  "summary": ""
}}

quality_score_0_5 = (description_quality * 0.4) + (code_quality * 0.6)
"""
    try:
        if not OLLAMA_AVAILABLE:
            raise RuntimeError("Ollama not available")
        out = ollama_json(model=model, prompt=prompt, temperature=0.1)
        
        # Handle case where ollama_json returns None
        if out is None:
            logging.warning(f"ollama_json returned None for PR quality scoring")
            raise RuntimeError("LLM returned None")
        
        def num(x):
            try:
                return float(x)
            except Exception:
                return 2.5
        
        quality = max(0.0, min(5.0, num(out.get("quality_score_0_5"))))
        desc_quality = max(0.0, min(5.0, num(out.get("description_quality_0_5"))))
        code_quality = max(0.0, min(5.0, num(out.get("code_quality_0_5"))))
        
        if quality == 2.5 and (desc_quality != 2.5 or code_quality != 2.5):
            quality = (desc_quality * 0.4) + (code_quality * 0.6)
        
        tech_stack = out.get("tech_stack_detected", [])
        if isinstance(tech_stack, str):
            tech_stack = [tech_stack] if tech_stack else []
        elif not isinstance(tech_stack, list):
            tech_stack = []
        
        return {
            "quality_score_0_5": quality,
            "description_quality_0_5": desc_quality,
            "code_quality_0_5": code_quality,
            "tech_stack_detected": tech_stack,
            "summary": str(out.get("summary", ""))[:240],
        }
    except Exception as e:
        logging.warning(f"Error in LLM PR quality scoring: {e}")
        return {
            "quality_score_0_5": 2.5,
            "description_quality_0_5": 2.5,
            "code_quality_0_5": 2.5,
            "tech_stack_detected": [],
            "summary": (pr.get("title") or "")[:240],
        }


def llm_score_pr_comments(model: str, pr: Dict[str, Any], candidate_username: str) -> Dict[str, Any]:
    """
    Analyze PR comment quality: should be less, helpful, not repetitive.
    Returns JSON:
    {
      "comment_quality_score_0_5": number,
      "comment_count_score_0_5": number,  # lower count = higher score
      "helpfulness_score_0_5": number,  # how helpful are the comments
      "repetitiveness_score_0_5": number,  # 5 = not repetitive, 0 = very repetitive
      "summary": string
    }
    """
    comments = pr.get("comments", [])
    candidate_comments = [c for c in comments if (c.get("user") or {}).get("login") == candidate_username]
    
    if not candidate_comments:
        return {
            "comment_quality_score_0_5": 5.0,  # No comments = efficient
            "comment_count_score_0_5": 5.0,
            "helpfulness_score_0_5": 5.0,
            "repetitiveness_score_0_5": 5.0,
            "summary": "No comments by candidate",
        }
    
    # Prepare comment data
    comments_data = []
    for c in candidate_comments:
        comments_data.append({
            "body": (c.get("body") or "")[:500],
            "created_at": c.get("created_at"),
        })
    
    pr_title = pr.get("title", "")
    pr_url = pr.get("url", "")
    pr_body = (pr.get("body") or "")[:1000]
    pr_merged = pr.get("merged", False)
    
    prompt = f"""
Analyze comments by candidate "{candidate_username}" on this GitHub Pull Request.

PR title: {pr_title}
PR URL: {pr_url}
PR body: {pr_body}
PR merged: {pr_merged}

Candidate comments ({len(candidate_comments)} total):
{json.dumps(comments_data, ensure_ascii=False)}

Evaluate:
1. Comment count score (0-5): Fewer comments is better. Score based on efficiency (5 = very few, 0 = too many)
2. Helpfulness score (0-5): How helpful and constructive are the comments? Do they add value? (5 = very helpful, 0 = not helpful)
3. Repetitiveness score (0-5): Are comments repetitive? (5 = not repetitive, unique, 0 = very repetitive/noisy)

The comment_quality_score_0_5 should be: (comment_count_score * 0.3) + (helpfulness_score * 0.4) + (repetitiveness_score * 0.3)

Return ONLY JSON with exactly these keys:
{{
  "comment_quality_score_0_5": 0,
  "comment_count_score_0_5": 0,
  "helpfulness_score_0_5": 0,
  "repetitiveness_score_0_5": 0,
  "summary": ""
}}
"""
    try:
        if not OLLAMA_AVAILABLE:
            raise RuntimeError("Ollama not available")
        out = ollama_json(model=model, prompt=prompt, temperature=0.1)
        
        def num(x):
            try:
                return float(x)
            except Exception:
                return 2.5
        
        count_score = max(0.0, min(5.0, num(out.get("comment_count_score_0_5"))))
        helpful_score = max(0.0, min(5.0, num(out.get("helpfulness_score_0_5"))))
        rep_score = max(0.0, min(5.0, num(out.get("repetitiveness_score_0_5"))))
        
        # Calculate overall comment quality
        quality = (count_score * 0.3) + (helpful_score * 0.4) + (rep_score * 0.3)
        
        return {
            "comment_quality_score_0_5": quality,
            "comment_count_score_0_5": count_score,
            "helpfulness_score_0_5": helpful_score,
            "repetitiveness_score_0_5": rep_score,
            "summary": str(out.get("summary", ""))[:240],
        }
    except Exception as e:
        logging.warning(f"Error in LLM PR comment scoring: {e}")
        # Fallback: score based on count
        count = len(candidate_comments)
        count_score = 5.0 if count <= 2 else (4.0 if count <= 5 else (2.0 if count <= 10 else 0.0))
        return {
            "comment_quality_score_0_5": count_score,
            "comment_count_score_0_5": count_score,
            "helpfulness_score_0_5": 2.5,
            "repetitiveness_score_0_5": 2.5,
            "summary": f"{count} comments by candidate",
        }


def llm_generate_rubric_summary(
    model: str,
    rubric_name: str,
    username: str,
    score: float,
    prs: List[Dict[str, Any]],
    rubric_specific_data: Dict[str, Any],
) -> str:
    """Generate a user-specific summary for a rubric based on their PRs."""
    prs_info = []
    for pr in prs[:15]:
        prs_info.append({
            "number": pr.get("pr_number"),
            "title": pr.get("title", "")[:150],
            "labels": pr.get("labels", [])[:5],
            "url": pr.get("url", ""),
        })
    
    rubric_prompts = {
        "pr_quality": f"""
Candidate "{username}" has a PR quality score of {score}/5.0.
PRs: {json.dumps(prs_info, ensure_ascii=False)}
PR quality details: {json.dumps(rubric_specific_data.get('pr_details', [])[:10], ensure_ascii=False)}
Tech stack: {rubric_specific_data.get('tech_stack', [])}
Analyze the quality of PRs. Provide a 2-3 sentence summary.
""",
        "comment_quality": f"""
Candidate "{username}" has a comment quality score of {score}/5.0.
PRs: {json.dumps(prs_info, ensure_ascii=False)}
Comment quality details: {json.dumps(rubric_specific_data.get('comment_details', [])[:10], ensure_ascii=False)}
Analyze how this candidate communicates in PRs. Provide a 2-3 sentence summary explaining:
1. Their commenting style and efficiency (fewer comments is better)
2. Quality of their communication (helpful vs. repetitive)
3. Overall communication effectiveness
""",
        "loc": f"""
Candidate "{username}" has a LOC score of {score}/5.0.
Total LOC: {rubric_specific_data.get('loc_total', 0)}
PRs: {json.dumps(prs_info, ensure_ascii=False)}
Analyze code volume. Provide a 2-3 sentence summary.
""",
        "time_taken": f"""
Candidate "{username}" has a time taken score of {score}/5.0.
Average time taken: {rubric_specific_data.get('avg_time_taken_days', 0):.1f} days
PRs: {json.dumps(prs_info, ensure_ascii=False)}
Analyze how quickly this candidate completes PRs. Lower time is better. Provide a 2-3 sentence summary.
""",
    }
    
    prompt = rubric_prompts.get(rubric_name, f"Candidate {username} scored {score}/5.0 in {rubric_name}.")
    full_prompt = f"""
{prompt}
Return ONLY JSON with "summary" key (max 300 chars):
{{"summary": ""}}
"""
    
    try:
        if not OLLAMA_AVAILABLE:
            raise RuntimeError("Ollama not available")
        out = ollama_json(model=model, prompt=full_prompt, temperature=0.3)
        summary = str(out.get("summary", "")).strip()
        if not summary:
            summary = f"{username} scored {score}/5.0 in {rubric_name} based on {len(prs)} PRs."
        return summary[:300]
    except Exception as e:
        logging.warning(f"Could not generate {rubric_name} summary: {e}")
        return f"{username} scored {score}/5.0 in {rubric_name} based on {len(prs)} PRs."


def llm_generate_candidate_summary(model: str, prs: List[Dict[str, Any]], candidate_username: str) -> Dict[str, Any]:
    """Generate comprehensive summary for candidate's contributions."""
    if not prs:
        return {
            "tech_stack": [],
            "features": [],
            "overall_summary": "No PRs contributed",
        }
    
    prs_summary = []
    for pr in prs[:20]:
        prs_summary.append({
            "pr_number": pr.get("pr_number"),
            "title": pr.get("title", "")[:200],
            "body": (pr.get("body") or "")[:500],
            "labels": pr.get("labels", [])[:10],
            "url": pr.get("url", ""),
            "merged": pr.get("merged", False),
            "additions": pr.get("additions", 0),
            "deletions": pr.get("deletions", 0),
        })
    
    prompt = f"""
Analyze contributions by "{candidate_username}" across {len(prs)} Pull Requests.
PRs: {json.dumps(prs_summary, ensure_ascii=False)}
Provide:
1. Tech stack: List technologies used
2. Features: List key features/areas worked on
3. Overall summary: 2-3 sentence summary of contributions, expertise, and impact
Return ONLY JSON:
{{"tech_stack": [], "features": [], "overall_summary": ""}}
"""
    try:
        if not OLLAMA_AVAILABLE:
            raise RuntimeError("Ollama not available")
        out = ollama_json(model=model, prompt=prompt, temperature=0.2)
        
        tech_stack = out.get("tech_stack", [])
        if isinstance(tech_stack, str):
            tech_stack = [tech_stack] if tech_stack else []
        elif not isinstance(tech_stack, list):
            tech_stack = []
        
        features = out.get("features", [])
        if isinstance(features, str):
            features = [features] if features else []
        elif not isinstance(features, list):
            features = []
        
        return {
            "tech_stack": tech_stack[:10],
            "features": features[:10],
            "overall_summary": str(out.get("overall_summary", ""))[:500],
        }
    except Exception as e:
        logging.warning(f"Error generating candidate summary: {e}")
        tech_keywords = [".net", "react", "node", "spring boot", "go", "django", "typescript", "javascript", "python", "java"]
        detected_tech = []
        all_text = " ".join([pr.get("title", "") + " " + (pr.get("body") or "") for pr in prs]).lower()
        for tech in tech_keywords:
            if tech in all_text:
                detected_tech.append(tech)
        
        return {
            "tech_stack": detected_tech,
            "features": [],
            "overall_summary": f"Contributed to {len(prs)} PRs with focus on various features.",
        }


def main():
    if len(sys.argv) < 2:
        print("usage: fetch_prs_from_json.py <input.json>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            candidates_data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: Input file not found: {input_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in input file: {e}")
        sys.exit(1)
    
    jsonl_file = f"{OUTPUT_PREFIX}_prs.jsonl"
    summary_file = f"{OUTPUT_PREFIX}_summary.json"
    
    contributors_index = {}
    all_prs = []
    candidates_summary = {}
    
    # Calculate total PRs for progress tracking
    total_candidates = len(candidates_data)
    total_prs = sum(len(info.get("PR_LINKS", [])) for info in candidates_data.values() if isinstance(info, dict))
    
    logging.info("="*80)
    logging.info("Starting PR fetch process")
    logging.info("Total candidates: %d", total_candidates)
    logging.info("Total PRs to fetch: %d", total_prs)
    logging.info("="*80)
    
    candidate_num = 0
    pr_num = 0
    
    # Process each candidate
    for candidate_name, candidate_info in candidates_data.items():
        candidate_num += 1
        
        if not isinstance(candidate_info, dict):
            logging.warning("Skipping invalid candidate entry: %s", candidate_name)
            continue
        
        pr_links = candidate_info.get("PR_LINKS", [])
        if not isinstance(pr_links, list):
            logging.warning("PR_LINKS must be a list for candidate: %s", candidate_name)
            continue
        
        logging.info("")
        logging.info("[%d/%d] Processing candidate: %s with %d PR links", 
                    candidate_num, total_candidates, candidate_name, len(pr_links))
        
        candidate_prs = []
        
        for pr_idx, pr_link in enumerate(pr_links, 1):
            pr_num += 1
            logging.info("  [%d/%d] Fetching PR %d/%d for %s: %s", 
                        pr_num, total_prs, pr_idx, len(pr_links), candidate_name, pr_link)
            try:
                owner, repo, pr_number = parse_pr_url(pr_link)
                pr_obj = fetch_pr_data(owner, repo, pr_number)
                
                if not pr_obj:
                    logging.warning("  ⚠️  PR #%d not found or failed to fetch", pr_number)
                    continue
                
                logging.info("  ✅ Successfully fetched PR #%d (%d comments, %d reviews)", 
                            pr_number, 
                            pr_obj.get("comments_count", 0),
                            pr_obj.get("reviews_count", 0))
                
                pr_obj["candidate_name"] = candidate_name
                pr_obj["pr_link"] = pr_link
                
                all_prs.append(pr_obj)
                candidate_prs.append(pr_obj)
                
                # Only add candidates from input JSON to contributors_index
                author = pr_obj.get("author")
                if author:
                    add_contrib(contributors_index, candidate_name, author, "author", pr_obj)
                else:
                    placeholder_user = {
                        "login": candidate_name,
                        "id": None,
                        "url": f"https://github.com/{candidate_name}",
                        "typename": "User"
                    }
                    add_contrib(contributors_index, candidate_name, placeholder_user, "author", pr_obj)
                
            except Exception as e:
                logging.error("Error processing PR link %s: %r", pr_link, e)
                continue
        
        candidates_summary[candidate_name] = {
            "pr_count": len(candidate_prs),
            "pr_links": [pr.get("url") for pr in candidate_prs],
            "pr_numbers": [pr.get("pr_number") for pr in candidate_prs]
        }
    
    # Write all PRs to JSONL file
    logging.info("")
    logging.info("="*80)
    logging.info("Writing PRs to JSONL file...")
    with open(jsonl_file, "w", encoding="utf-8") as out:
        for pr_obj in all_prs:
            out.write(json.dumps(pr_obj, ensure_ascii=False) + "\n")
    
    logging.info("✅ Written %d PRs to %s", len(all_prs), jsonl_file)
    
    # Calculate metrics and scores for each candidate
    logging.info("")
    logging.info("="*80)
    logging.info("Calculating metrics and scores for %d candidates", len(contributors_index))
    logging.info("="*80)
    
    contributor_list = list(contributors_index.items())
    for idx, (login, contributor) in enumerate(contributor_list, 1):
        prs = contributor.get("prs", [])
        logging.info("")
        logging.info("[%d/%d] Processing candidate: %s (%d PRs)", idx, len(contributor_list), login, len(prs))
        
        prs_authored = 0
        prs_merged = 0
        total_additions = 0
        total_deletions = 0
        total_changed_files = 0
        
        pr_quality_scores = []
        pr_quality_details = []
        comment_quality_scores = []
        comment_quality_details = []
        all_tech_stack = set()
        
        for pr in prs:
            if not isinstance(pr, dict) or "pr_number" not in pr:
                logging.warning(f"Invalid PR object for contributor {login}, skipping")
                continue
            
            pr_author = pr.get("author", {})
            candidate_name = pr.get("candidate_name")
            if pr_author.get("login") == login or candidate_name == login:
                prs_authored += 1
                if pr.get("merged"):
                    prs_merged += 1
                total_additions += int(pr.get("additions") or 0)
                total_deletions += int(pr.get("deletions") or 0)
                total_changed_files += int(pr.get("changed_files") or 0)
                
                # LLM score PR quality
                if OLLAMA_AVAILABLE:
                    try:
                        logging.info("    Scoring PR quality for PR #%d...", pr.get("pr_number"))
                        quality_result = llm_score_pr_quality(LLM_MODEL, pr)
                        score = quality_result["quality_score_0_5"]
                        pr_quality_scores.append(score)
                        pr_quality_details.append({
                            "pr_number": pr.get("pr_number"),
                            "pr_url": pr.get("url", ""),
                            "score": round(score, 2),
                            "summary": quality_result.get("summary", ""),
                        })
                        all_tech_stack.update(quality_result.get("tech_stack_detected", []))
                        logging.info("    ✅ PR quality score: %.2f/5.0", score)
                        time.sleep(SLEEP_SECS)
                    except Exception as e:
                        logging.warning(f"    ⚠️  Error scoring PR quality for {login} PR #{pr.get('pr_number')}: {e}")
                        pr_quality_scores.append(2.5)
                else:
                    pr_quality_scores.append(2.5)
                
                # LLM score comment quality
                if OLLAMA_AVAILABLE:
                    try:
                        logging.info("    Scoring comment quality for PR #%d...", pr.get("pr_number"))
                        comment_result = llm_score_pr_comments(LLM_MODEL, pr, login)
                        comment_score = comment_result["comment_quality_score_0_5"]
                        comment_quality_scores.append(comment_score)
                        comment_quality_details.append({
                            "pr_number": pr.get("pr_number"),
                            "pr_url": pr.get("url", ""),
                            "score": round(comment_score, 2),
                            "comment_count_score": round(comment_result.get("comment_count_score_0_5", 0), 2),
                            "helpfulness_score": round(comment_result.get("helpfulness_score_0_5", 0), 2),
                            "repetitiveness_score": round(comment_result.get("repetitiveness_score_0_5", 0), 2),
                            "summary": comment_result.get("summary", ""),
                        })
                        logging.info("    ✅ Comment quality score: %.2f/5.0", comment_score)
                        time.sleep(SLEEP_SECS)
                    except Exception as e:
                        logging.warning(f"    ⚠️  Error scoring comment quality for {login} PR #{pr.get('pr_number')}: {e}")
                        comment_quality_scores.append(2.5)
                else:
                    comment_quality_scores.append(2.5)
        
        pr_count = contributor.get("pr_count", 0)
        pr_merge_rate = (prs_merged / prs_authored) if prs_authored > 0 else 0.0
        loc_total = total_additions + total_deletions  # Sum across all PRs
        
        # Calculate time taken for top 3 PRs (by quality score)
        # Sort PRs by quality score and take top 3
        prs_with_scores = []
        for idx, pr in enumerate(prs):
            if isinstance(pr, dict) and "pr_number" in pr:
                quality_score = pr_quality_scores[idx] if idx < len(pr_quality_scores) else 2.5
                prs_with_scores.append((quality_score, pr))
        
        # Sort by quality score (descending) and take top 3
        prs_with_scores.sort(key=lambda x: x[0], reverse=True)
        top_3_prs = [pr for _, pr in prs_with_scores[:3]]
        
        # Calculate average time taken for top 3 PRs
        time_taken_days = []
        for pr in top_3_prs:
            days = calculate_pr_time_taken(pr)
            if days is not None:
                time_taken_days.append(days)
        
        avg_time_taken = sum(time_taken_days) / len(time_taken_days) if time_taken_days else None
        
        # Calculate scores (aggregated across all PRs)
        pr_quality_score = sum(pr_quality_scores) / len(pr_quality_scores) if pr_quality_scores else 2.5  # Average across all PRs
        comment_quality_score = sum(comment_quality_scores) / len(comment_quality_scores) if comment_quality_scores else 2.5  # Average across all PRs
        time_taken_score = score_time_taken(avg_time_taken)  # Based on average time taken for top 3 PRs
        
        # Calculate issue_quality based on PRs that reference issues
        issue_quality_score = None
        if prs:
            prs_with_issues = 0
            for pr in prs:
                body = pr.get('body', '') or ''
                title = pr.get('title', '') or ''
                # Check for issue references (e.g., "Fixes #123", "#123", "closes #456")
                if '#' in body or '#' in title:
                    prs_with_issues += 1
            
            # Calculate issue_quality score (0-5.0)
            # Based on percentage of PRs that reference issues
            if len(prs) > 0:
                issue_reference_rate = prs_with_issues / len(prs)
                # Score: 0-5.0 based on reference rate
                if issue_reference_rate >= 0.8:
                    issue_quality_score = 5.0
                elif issue_reference_rate >= 0.6:
                    issue_quality_score = 4.0
                elif issue_reference_rate >= 0.4:
                    issue_quality_score = 3.0
                elif issue_reference_rate >= 0.2:
                    issue_quality_score = 2.0
                else:
                    issue_quality_score = 1.0
        else:
            issue_quality_score = 2.5  # Default if no PRs
        
        rubric_summaries = {}
        if OLLAMA_AVAILABLE:
            try:
                rubric_summaries["pr_quality"] = llm_generate_rubric_summary(
                    LLM_MODEL, "pr_quality", login, pr_quality_score, prs,
                    {"pr_details": pr_quality_details, "tech_stack": list(all_tech_stack)}
                )
                time.sleep(SLEEP_SECS)
                rubric_summaries["comment_quality"] = llm_generate_rubric_summary(
                    LLM_MODEL, "comment_quality", login, comment_quality_score, prs,
                    {"comment_details": comment_quality_details}
                )
                time.sleep(SLEEP_SECS)
                rubric_summaries["time_taken"] = llm_generate_rubric_summary(
                    LLM_MODEL, "time_taken", login, time_taken_score, top_3_prs, {"avg_time_taken_days": avg_time_taken}
                )
                time.sleep(SLEEP_SECS)
            except Exception as e:
                logging.warning(f"Error generating rubric summaries for {login}: {e}")
        
        # Ensure time_taken summary is always included (fallback if LLM not available)
        if "time_taken" not in rubric_summaries:
            if avg_time_taken is not None:
                rubric_summaries["time_taken"] = (
                    f"{login} has an average time taken of {avg_time_taken:.1f} days to complete PRs "
                    f"(score: {time_taken_score:.2f}/5.0). "
                    f"{'Fast' if avg_time_taken <= 3 else 'Moderate' if avg_time_taken <= 7 else 'Slow'} completion time."
                )
            else:
                rubric_summaries["time_taken"] = f"{login} time taken data unavailable (score: {time_taken_score:.2f}/5.0)."
        
        comprehensive_summary = {}
        if OLLAMA_AVAILABLE:
            try:
                comprehensive_summary = llm_generate_candidate_summary(LLM_MODEL, prs, login)
                time.sleep(SLEEP_SECS)
            except Exception as e:
                logging.warning(f"Error generating comprehensive summary for {login}: {e}")
                comprehensive_summary = {
                    "tech_stack": list(all_tech_stack)[:10],
                    "features": [],
                    "overall_summary": f"Contributed to {pr_count} PRs.",
                }
        else:
            comprehensive_summary = {
                "tech_stack": list(all_tech_stack)[:10],
                "features": [],
                "overall_summary": f"Contributed to {pr_count} PRs.",
            }
        
        summary_parts = []
        if comprehensive_summary.get("tech_stack"):
            summary_parts.append(f"Tech: {', '.join(comprehensive_summary['tech_stack'][:3])}")
        if pr_count > 0:
            summary_parts.append(f"{pr_count} PR{'s' if pr_count > 1 else ''}")
        if prs_merged > 0:
            summary_parts.append(f"{prs_merged}/{prs_authored} merged")
        summary = " | ".join(summary_parts) if summary_parts else f"{login} - {pr_count} PRs"
        
        contributor["raw_metrics"] = {
            "additions": total_additions,
            "deletions": total_deletions,
            "changed_files": total_changed_files,
            "loc_total": loc_total,
        }
        
        contributor["scores"] = {
            "pr_quality": round(pr_quality_score, 2),
            "comment_quality": round(comment_quality_score, 2),
            "issue_quality": round(issue_quality_score, 2) if issue_quality_score is not None else 2.5,
            "time_taken": round(time_taken_score, 2),
        }
        
        # Add time taken metrics to raw_metrics
        contributor["raw_metrics"]["avg_time_taken_days"] = round(avg_time_taken, 2) if avg_time_taken else None
        contributor["raw_metrics"]["time_taken_prs_count"] = len(time_taken_days)
        
        contributor["summary"] = summary
        contributor["rubric_summaries"] = rubric_summaries
        contributor["comprehensive_summary"] = comprehensive_summary
    
    # Only save contributors_index to the output file
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(contributors_index, f, indent=2, ensure_ascii=False)
    
    logging.info("")
    logging.info("="*80)
    logging.info("✅ PROCESS COMPLETE")
    logging.info("="*80)
    logging.info("PRs JSONL: %s", jsonl_file)
    logging.info("Summary JSON: %s", summary_file)
    logging.info("Processed %d candidates with %d total PRs", len(candidates_summary), len(all_prs))
    logging.info("="*80)


if __name__ == "__main__":
    main()
