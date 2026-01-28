"""
GitHub API service for fetching contributors and analyzing PRs
"""
import os
import re
import requests
from typing import List, Dict, Optional, Callable
from urllib.parse import urlparse

# Priority labels that boost PR score
PRIORITY_LABELS = ['feature', 'high priority', 'bounty', '$', 'money', 'reward', 'points']

def get_github_token() -> Optional[str]:
    """Get GitHub API token from environment"""
    return os.getenv('GITHUB_TOKEN')

def parse_repo_url(repo_url: str) -> Optional[Dict[str, str]]:
    """Extract owner and repo from GitHub URL"""
    try:
        # Handle various URL formats
        repo_url = repo_url.replace('.git', '')
        if 'github.com' not in repo_url:
            return None
        
        # Extract owner/repo from URL
        match = re.search(r'github\.com[/:]([^/]+)/([^/]+)', repo_url)
        if match:
            return {
                'owner': match.group(1),
                'repo': match.group(2)
            }
        return None
    except Exception:
        return None

def github_request(url: str, progress_callback: Optional[Callable] = None) -> requests.Response:
    """Make GitHub API request with authentication"""
    headers = {
        'Accept': 'application/vnd.github.v3+json',
    }
    
    token = get_github_token()
    if token:
        headers['Authorization'] = f'token {token}'
    else:
        print("⚠️  WARNING: GITHUB_TOKEN not set. Using unauthenticated requests (60 requests/hour limit)")
    
    response = requests.get(url, headers=headers, timeout=30)
    
    if response.status_code == 403:
        # Check if it's a rate limit issue
        rate_limit_remaining = response.headers.get('X-RateLimit-Remaining', 'unknown')
        rate_limit_reset = response.headers.get('X-RateLimit-Reset', 'unknown')
        
        # Try to parse remaining as int to check if it's actually 0
        try:
            remaining_int = int(rate_limit_remaining) if rate_limit_remaining != 'unknown' else None
        except (ValueError, TypeError):
            remaining_int = None
        
        # Check response body for secondary rate limit messages
        response_text = response.text.lower() if response.text else ''
        is_secondary_rate_limit = 'secondary rate limit' in response_text or 'abuse detection' in response_text
        
        # Only raise rate limit error if:
        # 1. Remaining requests is actually 0 or very low (< 10), OR
        # 2. It's a secondary rate limit (abuse detection)
        if remaining_int is not None and remaining_int == 0:
            if not token:
                error_msg = (
                    'GitHub API rate limit exceeded (60 requests/hour for unauthenticated requests). '
                    'Please set GITHUB_TOKEN environment variable to increase the limit to 5000 requests/hour. '
                    f'Remaining requests: {rate_limit_remaining}. '
                    'Get a token from: https://github.com/settings/tokens'
                )
            else:
                error_msg = (
                    f'GitHub API rate limit exceeded. '
                    f'Remaining requests: {rate_limit_remaining}. '
                    f'Rate limit resets at: {rate_limit_reset}'
                )
            raise Exception(error_msg)
        elif is_secondary_rate_limit or (remaining_int is not None and remaining_int < 10):
            # Secondary rate limit or very low remaining - wait and retry might help
            # But for now, raise a more specific error
            error_msg = (
                f'GitHub API secondary rate limit or low rate limit. '
                f'Remaining requests: {rate_limit_remaining}. '
                f'Rate limit resets at: {rate_limit_reset}. '
                f'This may be due to making too many requests too quickly. Please wait before retrying.'
            )
            raise Exception(error_msg)
        else:
            # 403 but not a rate limit issue - could be access denied, repository not accessible, etc.
            error_msg = (
                f'GitHub API returned 403 (Forbidden). '
                f'This may be due to repository access restrictions, not rate limits. '
                f'Remaining requests: {rate_limit_remaining}. '
                f'Response: {response.text[:200]}'
            )
            raise Exception(error_msg)
    
    if response.status_code == 404:
        raise Exception('Repository not found. Please check the repository URL.')
    
    if not response.ok:
        raise Exception(f'GitHub API error: {response.status_code} {response.text}')
    
    return response

def fetch_all_pages(url: str, progress_callback: Optional[Callable] = None) -> List[Dict]:
    """Fetch all pages from GitHub API (handles pagination)"""
    all_data = []
    page = 1
    per_page = 100
    
    while True:
        url_with_page = f"{url}{'&' if '?' in url else '?'}page={page}&per_page={per_page}"
        
        if progress_callback:
            progress_callback(0, f"Fetching page {page}...")
        
        response = github_request(url_with_page, progress_callback)
        data = response.json()
        
        if isinstance(data, list):
            all_data.extend(data)
            if len(data) < per_page:
                break
        else:
            all_data.append(data)
            break
        
        page += 1
        if page > 10:  # Safety limit
            break
    
    return all_data

def fetch_top_contributors(repo_url: str, progress_callback: Optional[Callable] = None) -> List[Dict]:
    """Fetch top 100 contributors from a repository"""
    repo = parse_repo_url(repo_url)
    if not repo:
        raise ValueError('Invalid repository URL')
    
    if progress_callback:
        progress_callback(10, f"Fetching contributors from {repo['owner']}/{repo['repo']}...")
    
    url = f"https://api.github.com/repos/{repo['owner']}/{repo['repo']}/contributors"
    contributors = fetch_all_pages(url, progress_callback)
    
    # Sort by contributions and take top 100
    contributors.sort(key=lambda x: x.get('contributions', 0), reverse=True)
    return contributors[:100]

def calculate_label_score(labels: List[Dict]) -> float:
    """Calculate label score for a PR"""
    score = 0
    label_names = [label.get('name', '').lower() for label in labels]
    
    for priority_label in PRIORITY_LABELS:
        if any(priority_label.lower() in name for name in label_names):
            score += 10  # Each priority label adds 10 points
    
    return score

def fetch_pr_files(owner: str, repo: str, pr_number: int) -> Dict:
    """Fetch PR files and calculate metrics"""
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
        files = fetch_all_pages(url)
        
        files_changed = len(files)
        lines_of_code = sum(file.get('additions', 0) + file.get('deletions', 0) for file in files)
        
        return {
            'files': files,
            'files_changed': files_changed,
            'lines_of_code': lines_of_code
        }
    except Exception as e:
        print(f"Error fetching files for PR #{pr_number}: {e}")
        return {
            'files': [],
            'files_changed': 0,
            'lines_of_code': 0
        }

def fetch_pr_commits(owner: str, repo: str, pr_number: int) -> Dict:
    """Fetch PR commits"""
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/commits"
        commits = fetch_all_pages(url)
        
        return {
            'commits': commits,
            'commits_count': len(commits)
        }
    except Exception as e:
        print(f"Error fetching commits for PR #{pr_number}: {e}")
        return {
            'commits': [],
            'commits_count': 0
        }

def fetch_pr_linked_issues(owner: str, repo: str, pr_number: int) -> List[str]:
    """Fetch linked issues for a PR using GitHub API timeline endpoint"""
    issue_links = []
    
    try:
        # GitHub API endpoint for PR timeline events (includes linked issues)
        # Note: This endpoint requires authentication and may have rate limits
        url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/timeline"
        events = fetch_all_pages(url)
        
        for event in events:
            # Check for "cross-referenced" events which indicate linked issues
            if event.get('event') == 'cross-referenced':
                source = event.get('source', {})
                if source.get('type') == 'issue':
                    issue = source.get('issue', {})
                    issue_number = issue.get('number')
                    if issue_number:
                        # Get the issue's repository (might be different repo)
                        issue_repo = issue.get('repository', {})
                        if issue_repo:
                            issue_owner = issue_repo.get('owner', {}).get('login') or owner
                            issue_repo_name = issue_repo.get('name') or repo
                        else:
                            # Fallback to PR's repo if issue repo not available
                            issue_owner = owner
                            issue_repo_name = repo
                        issue_links.append(f"https://github.com/{issue_owner}/{issue_repo_name}/issues/{issue_number}")
    except Exception as e:
        # Timeline API might require authentication or not be available
        # This is expected for many repos, so we silently fail and fall back to body parsing
        # The error is usually 404 (not available) or 403 (requires auth)
        pass
    
    return issue_links

def analyze_pr(pr: Dict, owner: str, repo: str) -> Dict:
    """Analyze a single PR and calculate its score"""
    pr_number = pr.get('number')
    
    # Fetch files, commits, and linked issues
    files_data = fetch_pr_files(owner, repo, pr_number)
    commits_data = fetch_pr_commits(owner, repo, pr_number)
    linked_issues = fetch_pr_linked_issues(owner, repo, pr_number)
    
    labels = pr.get('labels', [])
    label_score = calculate_label_score(labels)
    
    files_changed = files_data['files_changed']
    lines_of_code = files_data['lines_of_code']
    commits_count = commits_data['commits_count']
    
    # Calculate composite score
    # Weights:
    # - Label score: 40% (max 40 points if all priority labels present)
    # - Files changed: 20% (normalized, max 20 points)
    # - LOC: 20% (normalized, max 20 points)
    # - Commits: 20% (normalized, max 20 points)
    
    normalized_files = min((files_changed / 50) * 20, 20)  # 50 files = 20 points
    normalized_loc = min((lines_of_code / 5000) * 20, 20)  # 5000 LOC = 20 points
    normalized_commits = min((commits_count / 20) * 20, 20)  # 20 commits = 20 points
    
    score = label_score + normalized_files + normalized_loc + normalized_commits
    
    return {
        **pr,
        'score': score,
        'files_changed': files_changed,
        'lines_of_code': lines_of_code,
        'commits_count': commits_count,
        'label_score': label_score,
        'linked_issues': linked_issues,  # Add linked issues from API
        'files': files_data['files'],
        'commits': commits_data['commits']
    }

def fetch_contributor_prs(contributor_login: str, progress_callback: Optional[Callable] = None) -> List[Dict]:
    """Fetch merged PRs for a contributor across ALL repositories (personal profile)"""
    try:
        # Search for merged PRs by the contributor across all repositories
        # This gets their overall top PRs from their entire GitHub profile
        query = f"author:{contributor_login} type:pr is:merged"
        url = f"https://api.github.com/search/issues?q={query}"
        
        if progress_callback:
            progress_callback(0, f"Searching PRs for {contributor_login} across all repositories...")
        
        response = github_request(url, progress_callback)
        search_results = response.json()
        issues = search_results.get('items', [])
        
        # Fetch full PR data for each issue
        prs = []
        for issue in issues[:100]:  # Limit to 100 PRs per contributor (increased since we're searching all repos)
            try:
                # Extract owner and repo from the issue URL
                issue_url = issue.get('html_url', '')
                # Format: https://github.com/owner/repo/pull/123
                parts = issue_url.replace('https://github.com/', '').split('/')
                if len(parts) >= 3:
                    issue_owner = parts[0]
                    issue_repo = parts[1]
                    pr_number = issue['number']
                    
                    pr_url = f"https://api.github.com/repos/{issue_owner}/{issue_repo}/pulls/{pr_number}"
                    pr_response = github_request(pr_url, progress_callback)
                    pr = pr_response.json()
                    
                    if pr.get('merged_at'):
                        prs.append(pr)
            except Exception as e:
                print(f"Error fetching PR #{issue.get('number')}: {e}")
                continue
        
        return prs
    except Exception as e:
        print(f"Error searching PRs for {contributor_login}: {e}")
        return []

def analyze_contributor(repo_url: str, contributor: Dict, progress_callback: Optional[Callable] = None) -> Dict:
    """Analyze a contributor by fetching their PRs and selecting top 3 from their overall profile"""
    contributor_login = contributor.get('login')
    
    if progress_callback:
        progress_callback(0, f"Analyzing {contributor_login}...")
    
    # Fetch all merged PRs for this contributor across ALL repositories (personal profile)
    # This gets their overall best PRs, not just from the input repository
    prs = fetch_contributor_prs(contributor_login, progress_callback)
    
    if len(prs) == 0:
        return {
            'contributor': contributor,
            'top_prs': [],
            'total_prs': 0
        }
    
    # Analyze all PRs to find top 3
    analyzed_prs = []
    total_prs = len(prs)
    
    for i, pr in enumerate(prs):
        if progress_callback:
            # Show clearer progress message
            progress_callback(0, f"Analyzing {contributor_login}'s PRs ({i+1}/{total_prs}) - Finding top 3...")
        
        # Extract owner and repo from PR data
        pr_url = pr.get('html_url', '')
        # Format: https://github.com/owner/repo/pull/123
        parts = pr_url.replace('https://github.com/', '').split('/')
        if len(parts) >= 2:
            pr_owner = parts[0]
            pr_repo = parts[1]
            analyzed_pr = analyze_pr(pr, pr_owner, pr_repo)
            analyzed_prs.append(analyzed_pr)
    
    # Sort by score and take top 3
    analyzed_prs.sort(key=lambda x: x.get('score', 0), reverse=True)
    top_prs = analyzed_prs[:3]
    
    # Log contributor and top 3 PRs to console
    print(f"\n{'='*80}")
    print(f"Contributor: {contributor_login}")
    print(f"Total PRs found (across all repositories): {len(prs)}")
    print(f"Top 3 PRs selected (from overall profile):")
    for idx, pr in enumerate(top_prs, 1):
        pr_repo = pr.get('html_url', '').replace('https://github.com/', '').split('/')[:2]
        repo_name = '/'.join(pr_repo) if len(pr_repo) == 2 else 'N/A'
        print(f"  {idx}. PR #{pr.get('number')} in {repo_name}: {pr.get('title', 'N/A')}")
        print(f"     Score: {pr.get('score', 0):.2f} | Files: {pr.get('files_changed', 0)} | LOC: {pr.get('lines_of_code', 0)} | Commits: {pr.get('commits_count', 0)}")
        print(f"     URL: {pr.get('html_url', 'N/A')}")
    print(f"{'='*80}\n")
    
    return {
        'contributor': contributor,
        'top_prs': top_prs,
        'total_prs': len(prs)
    }

def select_normalized_contributors(contributors: List[Dict]) -> List[Dict]:
    """
    Select contributors from different rank ranges for normalized distribution:
    - 2 contributors from rank 30-40
    - 2 contributors from rank 40-50
    - 2 contributors from rank 50-60
    - 2 contributors from rank 60-70
    - 2 contributors from rank 70-100
    
    Returns:
        List of selected contributors (total: 10)
    """
    import random
    
    selected = []
    
    # 2 contributors from rank 30-40
    if len(contributors) >= 40:
        range_30_40 = contributors[30:40]
        selected.extend(random.sample(range_30_40, min(2, len(range_30_40))))
    elif len(contributors) > 30:
        range_30_40 = contributors[30:]
        selected.extend(random.sample(range_30_40, min(2, len(range_30_40))))
    
    # 2 contributors from rank 40-50
    if len(contributors) >= 50:
        range_40_50 = contributors[40:50]
        selected.extend(random.sample(range_40_50, min(2, len(range_40_50))))
    elif len(contributors) > 40:
        range_40_50 = contributors[40:]
        selected.extend(random.sample(range_40_50, min(2, len(range_40_50))))
    
    # 2 contributors from rank 50-60
    if len(contributors) >= 60:
        range_50_60 = contributors[50:60]
        selected.extend(random.sample(range_50_60, min(2, len(range_50_60))))
    elif len(contributors) > 50:
        range_50_60 = contributors[50:]
        selected.extend(random.sample(range_50_60, min(2, len(range_50_60))))
    
    # 2 contributors from rank 60-70
    if len(contributors) >= 70:
        range_60_70 = contributors[60:70]
        selected.extend(random.sample(range_60_70, min(2, len(range_60_70))))
    elif len(contributors) > 60:
        range_60_70 = contributors[60:]
        selected.extend(random.sample(range_60_70, min(2, len(range_60_70))))
    
    # 2 contributors from rank 70-100
    if len(contributors) >= 100:
        range_70_100 = contributors[70:100]
        selected.extend(random.sample(range_70_100, min(2, len(range_70_100))))
    elif len(contributors) > 70:
        range_70_100 = contributors[70:]
        selected.extend(random.sample(range_70_100, min(2, len(range_70_100))))
    
    return selected

def analyze_repository_contributors(repo_url: str, progress_callback: Optional[Callable] = None) -> List[Dict]:
    """
    Analyze contributors from a repository using normalized distribution.
    
    Selection strategy:
    - 2 contributors from rank 30-40
    - 2 contributors from rank 40-50
    - 2 contributors from rank 50-60
    - 2 contributors from rank 60-70
    - 2 contributors from rank 70-100
    
    Args:
        repo_url: GitHub repository URL
        progress_callback: Optional callback function(progress: float, message: str) for progress updates
    
    Returns:
        List of contributor analyses (10 total)
    """
    # Fetch top 100 contributors
    if progress_callback:
        progress_callback(5, "Fetching top contributors...")
    
    contributors = fetch_top_contributors(repo_url, progress_callback)
    
    print(f"\n{'#'*80}")
    print(f"Starting analysis for repository: {repo_url}")
    print(f"Found {len(contributors)} top contributors")
    
    # Select normalized contributors from different rank ranges
    selected_contributors = select_normalized_contributors(contributors)
    
    print(f"Selected {len(selected_contributors)} contributors using normalized distribution:")
    print(f"  - 2 from rank 30-40")
    print(f"  - 2 from rank 40-50")
    print(f"  - 2 from rank 50-60")
    print(f"  - 2 from rank 60-70")
    print(f"  - 2 from rank 70-100")
    print(f"{'#'*80}\n")
    
    if progress_callback:
        progress_callback(20, f"Selected {len(selected_contributors)} contributors. Starting analysis...")
    
    # Analyze each selected contributor
    analyses = []
    total_contributors = len(selected_contributors)
    
    for i, contributor in enumerate(selected_contributors):
        try:
            contributor_login = contributor.get('login', 'unknown')
            contributor_rank = contributors.index(contributor) + 1  # 1-based rank
            
            print(f"[{i+1}/{total_contributors}] Processing contributor: {contributor_login} (rank #{contributor_rank})")
            
            if progress_callback:
                base_progress = 20
                contributor_progress = (i / total_contributors) * 80
                progress_callback(
                    base_progress + contributor_progress,
                    f"Analyzing contributor {i+1}/{total_contributors}: {contributor_login} - Finding their top 3 PRs..."
                )
            
            analysis = analyze_contributor(repo_url, contributor, progress_callback)
            analyses.append(analysis)
            
            # Small delay to avoid hitting rate limits
            import time
            time.sleep(0.1)
            
        except Exception as e:
            print(f"❌ Error analyzing contributor {contributor.get('login')}: {e}")
            # Continue with other contributors even if one fails
            analyses.append({
                'contributor': contributor,
                'top_prs': [],
                'total_prs': 0
            })
    
    print(f"\n{'#'*80}")
    print(f"Analysis completed for {repo_url}")
    print(f"Total contributors processed: {len(analyses)}")
    print(f"{'#'*80}\n")
    
    if progress_callback:
        progress_callback(100, f"Analysis completed. Found {len(analyses)} contributors.")
    
    return analyses
