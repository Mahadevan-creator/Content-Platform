"""
Service to fetch personal GitHub profile metrics for git score calculation.
Fetches:
1. Total PRs merged and avg PR merged/week over 1 year
2. Consistency (based on heatmap and contributions)
3. Number of repos
"""
import os
import requests
import logging
import re
from typing import Dict, Optional, List
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from services.github_service import get_github_token, github_request, fetch_all_pages


def is_bot_user(username: str, user_data: Dict = None) -> bool:
    """
    Detect if a GitHub user is a bot account.
    Checks multiple indicators:
    1. GitHub API user type field (type: "Bot")
    2. Username patterns (ends with [bot], contains -bot, _bot, etc.)
    3. Common bot names
    
    Args:
        username: GitHub username to check
        user_data: Optional user data from GitHub API (to avoid extra API call)
    
    Returns:
        True if user is a bot, False otherwise
    """
    # Check username patterns first (fastest check)
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
        logging.info(f"🤖 [Bot Detection] {username} detected as bot (username pattern)")
        return True
    
    # Check GitHub API user type if user_data provided
    if user_data:
        user_type = user_data.get('type', '').lower()
        if user_type == 'bot':
            logging.info(f"🤖 [Bot Detection] {username} detected as bot (GitHub API type: Bot)")
            return True
    
    return False


def fetch_user_merged_prs_last_year(username: str) -> Dict:
    """
    Fetch ALL merged PRs for a user across ALL repositories (not restricted to specific repos).
    For avg calculation, uses PRs from the last 1 year.
    Returns: {
        'total_prs_merged': int,  # Total PRs merged (all time)
        'avg_prs_per_week': float,  # Average PRs per week over last 1 year
        'prs': List[Dict]  # List of PR objects with merged_at dates
    }
    """
    logging.info(f"📊 [PRs] Starting to fetch merged PRs for {username}...")
    
    token = get_github_token()
    if not token:
        raise ValueError("GITHUB_TOKEN is required for fetching user profile data")
    
    # Calculate date 1 year ago for avg calculation (use UTC for consistency)
    one_year_ago = datetime.now(timezone.utc) - timedelta(days=365)
    one_year_ago_str = one_year_ago.strftime("%Y-%m-%dT%H:%M:%SZ")
    logging.info(f"📅 [PRs] Calculating avg PRs per week for PRs merged after {one_year_ago_str}")
    
    # Search for ALL merged PRs by the user (across all repos, all time)
    query = f"author:{username} type:pr is:merged"
    url = f"https://api.github.com/search/issues?q={query}&sort=updated&order=desc&per_page=100"
    
    try:
        all_prs = []
        page = 1
        
        # Fetch all pages of results (GitHub search API returns max 1000 results)
        while page <= 10:  # Max 10 pages = 1000 PRs
            paginated_url = f"{url}&page={page}"
            response = github_request(paginated_url)
            search_results = response.json()
            issues = search_results.get('items', [])
            
            if not issues:
                break
            
            logging.info(f"📄 [PRs] Page {page}: Found {len(issues)} PRs")
            
            # Fetch full PR data for each issue to get merged_at dates
            for issue in issues:
                try:
                    # Extract owner and repo from the issue URL
                    issue_url = issue.get('html_url', '')
                    parts = issue_url.replace('https://github.com/', '').split('/')
                    if len(parts) >= 3:
                        issue_owner = parts[0]
                        issue_repo = parts[1]
                        pr_number = issue['number']
                        
                        pr_url = f"https://api.github.com/repos/{issue_owner}/{issue_repo}/pulls/{pr_number}"
                        pr_response = github_request(pr_url)
                        pr = pr_response.json()
                        
                        if pr.get('merged_at'):
                            all_prs.append({
                                'merged_at': pr.get('merged_at'),
                                'created_at': pr.get('created_at'),
                                'number': pr.get('number'),
                                'url': pr.get('html_url'),
                                'title': pr.get('title'),
                            })
                except Exception as e:
                    logging.warning(f"⚠️  [PRs] Error fetching PR #{issue.get('number')}: {e}")
                    continue
            
            # Check if there are more pages
            if len(issues) < 100:
                break
            page += 1
        
        # Calculate total PRs merged (all time)
        total_prs_merged = len(all_prs)
        logging.info(f"✅ [PRs] Total PRs merged (all time): {total_prs_merged}")
        
        # Calculate average PRs per week over the last 1 year
        prs_last_year = []
        for pr in all_prs:
            if pr.get('merged_at'):
                try:
                    pr_date = datetime.fromisoformat(pr['merged_at'].replace('Z', '+00:00'))
                    if pr_date >= one_year_ago:
                        prs_last_year.append(pr)
                except Exception:
                    continue
        
        logging.info(f"📅 [PRs] PRs merged in last year: {len(prs_last_year)}")
        
        if len(prs_last_year) > 0:
            # Get the date range for last year's PRs
            merged_dates = []
            for pr in prs_last_year:
                if pr.get('merged_at'):
                    try:
                        pr_date = datetime.fromisoformat(pr['merged_at'].replace('Z', '+00:00'))
                        merged_dates.append(pr_date)
                    except Exception:
                        continue
            if merged_dates:
                earliest = min(merged_dates)
                latest = max(merged_dates)
                now = datetime.now(timezone.utc)
                
                # Option 2: Use actual days since first PR, but cap at 52 weeks
                # This gives accurate rate for recent contributors while being fair
                days_since_first = (now - earliest).days
                weeks = min(52.0, max(1, days_since_first / 7.0))  # Cap at 52 weeks, min 1 week
                avg_prs_per_week = len(prs_last_year) / weeks if weeks > 0 else 0.0
                
                logging.info(f"📊 [PRs] PR merge rate calculation (Option 2 - capped at 52 weeks):")
                logging.info(f"   - PRs in last year: {len(prs_last_year)}")
                logging.info(f"   - First PR date: {earliest.strftime('%Y-%m-%d')}")
                logging.info(f"   - Last PR date: {latest.strftime('%Y-%m-%d')}")
                logging.info(f"   - Days since first PR: {days_since_first} days")
                logging.info(f"   - Weeks used (capped at 52): {weeks:.2f} weeks")
                logging.info(f"   - Avg PRs per week: {avg_prs_per_week:.2f} = {len(prs_last_year)} / {weeks:.2f}")
            else:
                avg_prs_per_week = len(prs_last_year) / 52.0  # Default to 52 weeks if no dates
                logging.info(f"📊 [PRs] No valid dates found, using default 52 weeks: {avg_prs_per_week:.2f} PRs/week")
        else:
            avg_prs_per_week = 0.0
            logging.info(f"📊 [PRs] No PRs in last year, avg PRs per week: 0.0")
        
        result = {
            'total_prs_merged': total_prs_merged,
            'avg_prs_per_week': round(avg_prs_per_week, 2),
            'prs': all_prs  # Return all PRs for consistency calculation
        }
        logging.info(f"✅ [PRs] Final result for {username}: {result['total_prs_merged']} total PRs, {result['avg_prs_per_week']} PRs/week")
        return result
    except Exception as e:
        logging.error(f"❌ [PRs] Error fetching merged PRs for {username}: {e}")
        return {
            'total_prs_merged': 0,
            'avg_prs_per_week': 0.0,
            'prs': []
        }


def fetch_user_commits(username: str) -> List[Dict]:
    """
    Fetch ALL commits by the user across ALL repositories (not limited to last year).
    Uses GitHub Events API to get all commit activity for heatmap.
    Returns list of commits with dates.
    """
    logging.info(f"📝 [Commits] Fetching ALL commits for {username} (no time limit)...")
    token = get_github_token()
    if not token:
        raise ValueError("GITHUB_TOKEN is required for fetching user profile data")
    
    try:
        # Method 1: Try GitHub Events API (user's public events)
        # Get user's public events (includes PushEvents which contain commits)
        events_url = f"https://api.github.com/users/{username}/events/public?per_page=100"
        commits = []
        page = 1
        total_events_processed = 0
        total_push_events = 0  # Track total PushEvents found
        
        # Fetch ALL events (no time limit for heatmap)
        while page <= 30:  # Increased to 30 pages = 3000 events (GitHub API limit is ~300 events per page effectively)
            paginated_url = f"{events_url}&page={page}"
            try:
                events_response = github_request(paginated_url)
                events = events_response.json()
            except Exception as e:
                logging.warning(f"⚠️  [Commits] Error fetching events page {page}: {e}")
                break
            
            if not events:
                logging.info(f"📝 [Commits] No more events at page {page}")
                break
            
            page_commits = 0
            push_events_count = 0
            for event in events:
                event_type = event.get('type', '')
                
                # Only process PushEvents (commits)
                if event_type == 'PushEvent':
                    push_events_count += 1
                    created_at = event.get('created_at', '')
                    actor = event.get('actor', {})
                    actor_login = actor.get('login', '') if actor else ''
                    
                    # Check if this push event is by the user we're looking for
                    # Sometimes events are for repos the user contributed to, not necessarily their own commits
                    if created_at:
                        try:
                            event_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            payload = event.get('payload', {})
                            
                            # GitHub Events API returns commits in payload.commits
                            # Note: GitHub only returns first 20 commits in PushEvent payload
                            # For pushes with >20 commits, we need to use the size field
                            commits_list = payload.get('commits', [])
                            push_size = payload.get('size', 0)  # Total commits in the push
                            
                            # Check if this push was made by the user
                            # The actor should match the username, or we check the repo owner
                            repo_info = event.get('repo', {})
                            repo_name = repo_info.get('name', '')
                            
                            # Use push_size if available (more accurate), otherwise use commits_list length
                            if push_size > 0:
                                commit_count = push_size
                            else:
                                commit_count = len(commits_list) if commits_list else 0
                            
                            # Only process if we have commits
                            if commit_count == 0:
                                continue
                            
                            total_push_events += 1
                            
                            # If we have the commits list, use individual commit dates if available
                            # Otherwise, use the push event date for all commits
                            if commits_list and len(commits_list) > 0:
                                # Use individual commit dates from the list
                                for commit in commits_list:
                                    commit_sha = commit.get('sha', '')
                                    commit_message = commit.get('message', '')
                                    # Use push event date (commits in payload don't have individual dates)
                                    commits.append({
                                        'date': created_at,
                                        'repo': event.get('repo', {}).get('name', ''),
                                        'count': 1,
                                        'sha': commit_sha
                                    })
                                page_commits += len(commits_list)
                                
                                # If push_size > commits_list length, add remaining commits with push date
                                if push_size > len(commits_list):
                                    remaining = push_size - len(commits_list)
                                    for _ in range(remaining):
                                        commits.append({
                                            'date': created_at,
                                            'repo': event.get('repo', {}).get('name', ''),
                                            'count': 1
                                        })
                                    page_commits += remaining
                            else:
                                # No commits list, but we have push_size, create entries for all
                                for _ in range(commit_count):
                                    commits.append({
                                        'date': created_at,
                                        'repo': event.get('repo', {}).get('name', ''),
                                        'count': 1
                                    })
                                page_commits += commit_count
                                
                        except Exception as e:
                            logging.warning(f"⚠️  [Commits] Error processing PushEvent: {e}")
                            continue
            
            total_events_processed += len(events)
            
            if push_events_count > 0:
                logging.info(f"📝 [Commits] Page {page}: Found {push_events_count} PushEvents, extracted {page_commits} commits")
            
            # Log event types breakdown for debugging
            event_types = {}
            for event in events:
                event_type = event.get('type', 'Unknown')
                event_types[event_type] = event_types.get(event_type, 0) + 1
            
            logging.info(f"📝 [Commits] Page {page}: Processed {len(events)} events, Event types: {dict(event_types)}, {page_commits} commits (Total commits so far: {len(commits)})")
            
            # If we got less than 100 events, we've reached the end
            if len(events) < 100:
                logging.info(f"📝 [Commits] Reached end of events at page {page}")
                break
            
            page += 1
        
        logging.info(f"✅ [Commits] Total commits fetched for {username}: {len(commits)} commits from {total_events_processed} events ({total_push_events} PushEvents)")
        
        # If no commits found via Events API, try alternative: Search API for commits
        if len(commits) == 0:
            logging.warning(f"⚠️  [Commits] No commits found via Events API for {username}")
            logging.info(f"🔄 [Commits] Trying alternative method: GitHub Search API for commits...")
            
            # Alternative: Use Search API to find commits by author
            # Note: Search API has rate limits but can find commits directly
            try:
                search_url = f"https://api.github.com/search/commits?q=author:{username}&sort=author-date&order=desc&per_page=100"
                search_response = github_request(search_url)
                search_results = search_response.json()
                
                search_commits = search_results.get('items', [])
                logging.info(f"📝 [Commits] Search API found {len(search_commits)} commits")
                
                for commit_item in search_commits:
                    commit_info = commit_item.get('commit', {})
                    author_info = commit_info.get('author', {})
                    commit_date = author_info.get('date', '')
                    
                    if commit_date:
                        commits.append({
                            'date': commit_date,
                            'repo': commit_item.get('repository', {}).get('full_name', ''),
                            'count': 1,
                            'sha': commit_item.get('sha', '')
                        })
                
                logging.info(f"✅ [Commits] Alternative method: Added {len(commits)} commits from Search API")
            except Exception as e:
                logging.warning(f"⚠️  [Commits] Alternative method also failed: {e}")
        
        if len(commits) == 0:
            logging.warning(f"⚠️  [Commits] No commits found for {username} after all methods. This could mean:")
            logging.warning(f"    - User has no public commits")
            logging.warning(f"    - User's repositories are private")
            logging.warning(f"    - User hasn't made any commits")
            logging.warning(f"    - GitHub API rate limit or access issue")
        
        return commits
    except Exception as e:
        logging.error(f"❌ [Commits] Error fetching commits for {username}: {e}")
        return []


def fetch_contributions_from_graphql(username: str, year: int = None) -> List[Dict]:
    """
    Fetch contribution data from GitHub GraphQL API (same as heatmap uses).
    Returns list of contribution days with date and count.
    More accurate than Events API as it uses GitHub's contribution calendar.
    """
    if year is None:
        year = datetime.now(timezone.utc).year
    
    logging.info(f"📊 [Consistency] Fetching contribution data from GraphQL for {username} (year {year})...")
    
    token = get_github_token()
    if not token:
        raise ValueError("GITHUB_TOKEN is required for fetching contribution data")
    
    try:
        # GraphQL query for contribution calendar
        query = """
        query($userName: String!, $from: DateTime!, $to: DateTime!) {
          user(login: $userName) {
            contributionsCollection(from: $from, to: $to) {
              contributionCalendar {
                totalContributions
                weeks {
                  contributionDays {
                    date
                    contributionCount
                    color
                  }
                }
              }
            }
          }
        }
        """
        
        from_date = f"{year}-01-01T00:00:00Z"
        to_date = f"{year}-12-31T23:59:59Z"
        
        variables = {
            "userName": username,
            "from": from_date,
            "to": to_date
        }
        
        # Make GraphQL request
        import requests
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        
        response = requests.post(
            'https://api.github.com/graphql',
            headers=headers,
            json={'query': query, 'variables': variables},
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"GraphQL request failed: {response.status_code}")
        
        result = response.json()
        
        if result.get('errors'):
            raise Exception(f"GraphQL errors: {result['errors']}")
        
        calendar = result.get('data', {}).get('user', {}).get('contributionsCollection', {}).get('contributionCalendar')
        if not calendar:
            logging.warning(f"⚠️  [Consistency] No contribution calendar data found for {username}")
            return []
        
        # Extract all contribution days
        contributions = []
        weeks = calendar.get('weeks', [])
        for week in weeks:
            days = week.get('contributionDays', [])
            for day in days:
                if day.get('contributionCount', 0) > 0:
                    contributions.append({
                        'date': day.get('date'),
                        'count': day.get('contributionCount', 0)
                    })
        
        logging.info(f"✅ [Consistency] Fetched {len(contributions)} contribution days from GraphQL (total: {calendar.get('totalContributions', 0)})")
        return contributions
        
    except Exception as e:
        logging.error(f"❌ [Consistency] Error fetching contributions from GraphQL: {e}")
        return []


def fetch_contributions_from_graphql(username: str, year: int = None) -> List[Dict]:
    """
    Fetch contribution data from GitHub GraphQL API (same as heatmap uses).
    Returns list of contribution days with date and count.
    More accurate than Events API as it uses GitHub's contribution calendar.
    """
    if year is None:
        year = datetime.now(timezone.utc).year
    
    logging.info(f"📊 [Consistency] Fetching contribution data from GraphQL for {username} (year {year})...")
    
    token = get_github_token()
    if not token:
        raise ValueError("GITHUB_TOKEN is required for fetching contribution data")
    
    try:
        # GraphQL query for contribution calendar
        query = """
        query($userName: String!, $from: DateTime!, $to: DateTime!) {
          user(login: $userName) {
            contributionsCollection(from: $from, to: $to) {
              contributionCalendar {
                totalContributions
                weeks {
                  contributionDays {
                    date
                    contributionCount
                    color
                  }
                }
              }
            }
          }
        }
        """
        
        from_date = f"{year}-01-01T00:00:00Z"
        to_date = f"{year}-12-31T23:59:59Z"
        
        variables = {
            "userName": username,
            "from": from_date,
            "to": to_date
        }
        
        # Make GraphQL request
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        
        response = requests.post(
            'https://api.github.com/graphql',
            headers=headers,
            json={'query': query, 'variables': variables},
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"GraphQL request failed: {response.status_code}")
        
        result = response.json()
        
        if result.get('errors'):
            raise Exception(f"GraphQL errors: {result['errors']}")
        
        calendar = result.get('data', {}).get('user', {}).get('contributionsCollection', {}).get('contributionCalendar')
        if not calendar:
            logging.warning(f"⚠️  [Consistency] No contribution calendar data found for {username}")
            return []
        
        # Extract all contribution days
        contributions = []
        weeks = calendar.get('weeks', [])
        for week in weeks:
            days = week.get('contributionDays', [])
            for day in days:
                if day.get('contributionCount', 0) > 0:
                    contributions.append({
                        'date': day.get('date'),
                        'count': day.get('contributionCount', 0)
                    })
        
        logging.info(f"✅ [Consistency] Fetched {len(contributions)} contribution days from GraphQL (total: {calendar.get('totalContributions', 0)})")
        return contributions
        
    except Exception as e:
        logging.error(f"❌ [Consistency] Error fetching contributions from GraphQL: {e}")
        return []


def calculate_consistency_score(username: str, prs: List[Dict], heatmap_data: Dict[str, List[Dict]] = None, commits: List[Dict] = None) -> float:
    """
    Calculate consistency score using the recruiter-grade formula:
    Consistency Index = (ActiveWeeksRatio × 60) + (AvgWeeklyScore × 25) - (GapPenalty × 5)
    
    This produces:
    - High output for steady contributors
    - Medium for seasonal contributors  
    - Low for burst-only profiles
    
    Uses heatmap data if available (all years: 2024, 2025, 2026), otherwise falls back to GraphQL API.
    
    Args:
        username: GitHub username
        prs: List of PR dictionaries
        heatmap_data: Optional heatmap data dict with year as key (e.g., {"2024": [...], "2025": [...]})
        commits: Optional list of commit dictionaries (used if heatmap_data not provided)
    
    Returns a score from 0-100.
    """
    logging.info(f"📊 [Consistency] Calculating consistency score for {username}...")
    
    contributions = []
    
    # ONLY use heatmap data - no API calls, no fallbacks
    if heatmap_data:
        logging.info(f"📊 [Consistency] Using ONLY heatmap data (years: {list(heatmap_data.keys())}) - NO API calls")
        logging.info(f"📊 [Consistency] Data source: Heatmap cells contain contributions from:")
        logging.info(f"   - GraphQL Contribution Calendar API (commits, issues, PRs, reviews)")
        logging.info(f"   - Merged PRs (weighted 2x in heatmap)")
        logging.info(f"   - Same data source as the visual heatmap you see in UI")
        
        # Extract contributions from heatmap data (all years)
        # Heatmap cells have: week, day, value (0-4), count (actual contribution count), date
        total_heatmap_contributions = 0
        active_days_by_year = {}
        for year_str, year_data in heatmap_data.items():
            year = int(year_str)
            year_contributions = 0
            active_days = 0
            for cell in year_data:
                count = cell.get('count', 0)  # Actual contribution count from heatmap
                date_str = cell.get('date', '')
                if count > 0 and date_str:
                    contributions.append({
                        'date': date_str,
                        'count': count
                    })
                    year_contributions += count
                    active_days += 1
            total_heatmap_contributions += year_contributions
            active_days_by_year[year] = active_days
            logging.info(f"📊 [Consistency] Year {year}: {active_days} active days, {year_contributions} total contributions")
        logging.info(f"📊 [Consistency] Summary: {len(contributions)} contribution days across all years, {total_heatmap_contributions} total contributions")
    else:
        logging.warning(f"⚠️  [Consistency] No heatmap data provided! Cannot calculate consistency without heatmap.")
        return 0.0
    
    if not contributions:
        logging.warning(f"⚠️  [Consistency] No contributions found for {username}, returning 0.0")
        return 0.0
    
    # Group contributions by week across ALL years (not just one year)
    # This gives a more accurate consistency score for long-term contributors
    weekly_commits = defaultdict(int)
    
    # Group contributions by ISO week (across all years)
    parsed_count = 0
    failed_count = 0
    for contribution in contributions:
        date_str = contribution.get('date', '')
        count = contribution.get('count', 1)
        if date_str:
            try:
                # Handle different date formats
                # Heatmap dates are typically "YYYY-MM-DD" format
                if 'T' in date_str or 'Z' in date_str:
                    contrib_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                else:
                    # Assume "YYYY-MM-DD" format
                    contrib_date = datetime.strptime(date_str, '%Y-%m-%d')
                    contrib_date = contrib_date.replace(tzinfo=timezone.utc)
                
                # Get ISO week number (1-53) with year
                year, week, _ = contrib_date.isocalendar()
                week_key = f"{year}-W{week:02d}"
                weekly_commits[week_key] += count
                parsed_count += 1
            except Exception as e:
                failed_count += 1
                if failed_count <= 3:  # Log first 3 failures for debugging
                    logging.warning(f"⚠️  [Consistency] Failed to parse date '{date_str}': {e}")
                continue
    
    logging.info(f"📊 [Consistency] Parsed {parsed_count} contributions, {failed_count} failed")
    
    if len(weekly_commits) == 0:
        logging.warning(f"⚠️  [Consistency] No valid contribution dates found for {username}, returning 0.0")
        return 0.0
    
    # Determine the time range we're analyzing
    # Get all unique years from contributions
    years_in_data = set()
    for contribution in contributions:
        date_str = contribution.get('date', '')
        if date_str:
            try:
                contrib_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                years_in_data.add(contrib_date.year)
            except Exception:
                continue
    
    if not years_in_data:
        logging.warning(f"⚠️  [Consistency] No valid years found in contributions, returning 0.0")
        return 0.0
    
    # Use the year with the MOST contributions (not just most recent)
    # This gives a better consistency score for active contributors
    year_contribution_counts = {}
    for contrib in contributions:
        date_str = contrib.get('date', '')
        count = contrib.get('count', 1)
        if date_str:
            try:
                if 'T' in date_str or 'Z' in date_str:
                    contrib_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                else:
                    contrib_date = datetime.strptime(date_str, '%Y-%m-%d')
                    contrib_date = contrib_date.replace(tzinfo=timezone.utc)
                year = contrib_date.year
                year_contribution_counts[year] = year_contribution_counts.get(year, 0) + count
            except Exception:
                continue
    
    if not year_contribution_counts:
        logging.warning(f"⚠️  [Consistency] Could not count contributions by year, returning 0.0")
        return 0.0
    
    # Find year with most contributions
    analysis_year = max(year_contribution_counts.items(), key=lambda x: x[1])[0]
    max_contribs = year_contribution_counts[analysis_year]
    logging.info(f"📊 [Consistency] Year contribution counts: {year_contribution_counts}")
    logging.info(f"📊 [Consistency] Analyzing year {analysis_year} (most active year with {max_contribs} contributions)")
    
    # Count contributions per week for the analysis year
    year_weekly_commits = defaultdict(int)
    for week_key, count in weekly_commits.items():
        week_year = int(week_key.split('-W')[0])
        if week_year == analysis_year:
            year_weekly_commits[week_key] = count
    
    logging.info(f"📊 [Consistency] Found {len(year_weekly_commits)} active weeks in {analysis_year}")
    
    # Calculate weekly scores and track gaps for the analysis year
    # ISO weeks: week 1 is the week containing Jan 4
    jan_4 = datetime(analysis_year, 1, 4, tzinfo=timezone.utc)
    year_start_week = jan_4.isocalendar()[1]  # Week number of Jan 4
    year_start_date = jan_4 - timedelta(days=jan_4.weekday())  # Monday of that week
    
    active_weeks = 0
    weekly_scores = []
    longest_gap = 0
    current_gap = 0
    
    # Process 52 weeks of the year
    total_weeks = 52
    for week_num in range(total_weeks):
        week_start = year_start_date + timedelta(weeks=week_num)
        year, week, _ = week_start.isocalendar()
        week_key = f"{year}-W{week:02d}"
        
        commits = year_weekly_commits.get(week_key, 0)
        
        if commits > 0:
            active_weeks += 1
            current_gap = 0
            # Score based on contribution count per week
            if commits <= 3:
                weekly_scores.append(0.5)
            elif commits <= 10:
                weekly_scores.append(0.8)
            else:
                weekly_scores.append(1.0)
        else:
            weekly_scores.append(0)
            current_gap += 1
            longest_gap = max(longest_gap, current_gap)
    
    # Calculate metrics
    active_weeks_ratio = active_weeks / total_weeks if total_weeks > 0 else 0
    avg_weekly_score = sum(weekly_scores) / len(weekly_scores) if weekly_scores else 0
    
    # Debug logging
    logging.info(f"📊 [Consistency] Analysis for year {analysis_year}:")
    logging.info(f"   - Total weeks analyzed: {total_weeks}")
    logging.info(f"   - Active weeks: {active_weeks}")
    logging.info(f"   - Total contributions in year: {sum(year_weekly_commits.values())}")
    logging.info(f"   - Weekly commits sample (first 5): {dict(list(year_weekly_commits.items())[:5])}")
    
    if active_weeks == 0:
        logging.error(f"❌ [Consistency] No active weeks found in year {analysis_year} despite {len(contributions)} contributions!")
        logging.error(f"   - Weekly commits dict has {len(year_weekly_commits)} entries")
        logging.error(f"   - Sample contributions (first 5): {contributions[:5]}")
        # Still return a minimum score if we have contributions but no active weeks (data issue)
        if len(contributions) > 0:
            logging.warning(f"⚠️  [Consistency] Returning minimum score due to data parsing issue")
            return 15.0  # Minimum score for having contributions
    
    # Improved gap penalty calculation - much more forgiving for all contributors
    # The key insight: if someone has many active weeks, gaps are less important
    # Only penalize gaps if the contributor has low overall activity
    # Even then, keep penalties minimal to avoid zero scores for good heatmaps
    gap_penalty = 0.0
    
    if longest_gap > 0:
        # Calculate gap penalty based on activity level
        # For highly active contributors (30+ weeks), gaps are almost irrelevant
        # For moderately active (15-30 weeks), very small gap penalty
        # For low activity (< 15 weeks), still minimal penalty to avoid zero scores
        if active_weeks >= 30:
            # Very active contributors: ignore gaps completely
            gap_penalty = 0.0  # No penalty for very active contributors
        elif active_weeks >= 25:
            # Highly active: only penalize extremely long gaps
            if longest_gap > 30:
                gap_penalty = (longest_gap / total_weeks) * 0.05  # Minimal penalty
            else:
                gap_penalty = 0.0
        elif active_weeks >= 20:
            # Moderately active: very light penalty only for very long gaps
            if longest_gap > 25:
                gap_penalty = (longest_gap / total_weeks) * 0.1  # Very light
            elif longest_gap > 20:
                gap_penalty = (longest_gap / total_weeks) * 0.05  # Minimal
            else:
                gap_penalty = 0.0  # No penalty for reasonable gaps
        elif active_weeks >= 15:
            # Somewhat active: light penalty for long gaps
            if longest_gap > 25:
                gap_penalty = (longest_gap / total_weeks) * 0.15  # Light
            elif longest_gap > 15:
                gap_penalty = (longest_gap / total_weeks) * 0.08  # Very light
            else:
                gap_penalty = 0.0
        elif active_weeks >= 10:
            # Low activity: still minimal penalty to preserve heatmap value
            if longest_gap > 30:
                gap_penalty = min(0.2, (longest_gap / total_weeks) * 0.2)  # Capped light
            elif longest_gap > 20:
                gap_penalty = (longest_gap / total_weeks) * 0.12  # Light
            elif longest_gap > 10:
                gap_penalty = (longest_gap / total_weeks) * 0.06  # Very light
            else:
                gap_penalty = 0.0
        else:
            # Very low activity: still keep penalty minimal to avoid zero scores
            if longest_gap > 30:
                gap_penalty = min(0.25, (longest_gap / total_weeks) * 0.25)  # Capped light-moderate
            elif longest_gap > 20:
                gap_penalty = min(0.15, (longest_gap / total_weeks) * 0.15)  # Capped light
            elif longest_gap > 10:
                gap_penalty = (longest_gap / total_weeks) * 0.1  # Light
            else:
                gap_penalty = (longest_gap / total_weeks) * 0.05  # Very light
    
    logging.info(f"📊 [Consistency] Weekly stats:")
    logging.info(f"   - Active weeks: {active_weeks} of {total_weeks}")
    logging.info(f"   - Active weeks ratio: {active_weeks_ratio:.3f}")
    logging.info(f"   - Average weekly score: {avg_weekly_score:.3f}")
    logging.info(f"   - Longest gap: {longest_gap} weeks")
    logging.info(f"   - Gap penalty (activity-aware): {gap_penalty:.3f}")
    
    # Calculate consistency index with improved formula
    # For long-term active contributors, focus more on activity and less on gaps
    # Base score from activity and weekly quality
    base_score = (active_weeks_ratio * 60) + (avg_weekly_score * 25)
    
    # Apply gap penalty (much reduced multiplier - was 15, now 5 for less harsh impact)
    # The gap_penalty itself is already reduced based on activity level
    consistency_index = base_score - (gap_penalty * 5)  # Reduced from 15 to 5
    
    # Clamp to 0-100
    consistency_score = max(0.0, min(100.0, consistency_index))
    
    # Enhanced safeguards for contributors with any meaningful activity
    # These ensure that good heatmaps don't result in 0 scores
    if active_weeks >= 30:
        # Very active: minimum 65 points (they're clearly consistent)
        consistency_score = max(consistency_score, 65.0)
        logging.info(f"📊 [Consistency] Applied high-activity safeguard: {consistency_score:.2f} (30+ active weeks)")
    elif active_weeks >= 25:
        # Highly active: minimum 55 points
        consistency_score = max(consistency_score, 55.0)
        logging.info(f"📊 [Consistency] Applied high-activity safeguard: {consistency_score:.2f} (25+ active weeks)")
    elif active_weeks >= 20:
        # Moderately active: minimum 45 points
        consistency_score = max(consistency_score, 45.0)
        logging.info(f"📊 [Consistency] Applied moderate-activity safeguard: {consistency_score:.2f} (20+ active weeks)")
    elif active_weeks >= 15:
        # Somewhat active: minimum 35 points
        consistency_score = max(consistency_score, 35.0)
        logging.info(f"📊 [Consistency] Applied moderate-activity safeguard: {consistency_score:.2f} (15+ active weeks)")
    elif active_weeks >= 10:
        # Minimal activity: minimum 25 points (good heatmap should get at least this)
        consistency_score = max(consistency_score, 25.0)
        logging.info(f"📊 [Consistency] Applied low-activity safeguard: {consistency_score:.2f} (10+ active weeks)")
    elif active_weeks >= 5:
        # Very minimal activity: minimum 15 points (any visible heatmap activity)
        consistency_score = max(consistency_score, 15.0)
        logging.info(f"📊 [Consistency] Applied minimal-activity safeguard: {consistency_score:.2f} (5+ active weeks)")
    elif active_weeks >= 3:
        # Barely any activity: minimum 10 points (at least some consistency)
        consistency_score = max(consistency_score, 10.0)
        logging.info(f"📊 [Consistency] Applied minimal-activity safeguard: {consistency_score:.2f} (3+ active weeks)")
    
    logging.info(f"✅ [Consistency] Consistency Index: {consistency_index:.2f} → Final: {consistency_score:.2f}/100")
    logging.info(f"   Formula: Base({active_weeks_ratio:.3f} × 60 + {avg_weekly_score:.3f} × 25 = {base_score:.2f}) - Gap({gap_penalty:.3f} × 15 = {gap_penalty * 15:.2f}) = {consistency_score:.2f}")
    
    return round(consistency_score, 2)


def fetch_user_tech_stack(username: str) -> List[str]:
    """
    Fetch all tech stacks (programming languages and frameworks) the user has worked on
    by analyzing languages used in their repositories AND scanning repo metadata for frameworks.
    Returns a list of unique programming languages/technologies.
    
    Uses a smarter approach:
    1. Fetches languages from GitHub languages API (programming languages)
    2. Scans repo names, descriptions, and topics for frameworks (React, Spring Boot, etc.)
    """
    logging.info(f"🔧 [Tech Stack] Fetching tech stack for {username}...")
    token = get_github_token()
    if not token:
        raise ValueError("GITHUB_TOKEN is required for fetching user profile data")
    
    # Framework keywords to look for in repo metadata
    # Using specific patterns to avoid false positives
    framework_keywords = {
        'React': [r'react', r'reactjs', r'react.js'],
        'Spring Boot': [r'spring-boot', r'springboot', r'spring boot'],
        'Django': [r'django'],
        'Node.js': [r'node.js', r'nodejs', r'node'],
        '.NET': [r'dotnet', r'\.net', r'asp\.net', r'csharp'],
        'Angular': [r'angular', r'angularjs', r'angular.js'],
        'Go': [r'go', r'golang'],
        'Vue.js': [r'vue', r'vuejs', r'vue.js'],
        'Next.js': [r'next\.js', r'nextjs', r'next'],
        'Express': [r'express', r'expressjs'],
        'Flask': [r'flask'],
        'FastAPI': [r'fastapi', r'fast-api'],
        'Laravel': [r'laravel'],
        'Rails': [r'rails', r'ruby-on-rails'],
        'Spring': [r'spring'],
        'TensorFlow': [r'tensorflow', r'tf'],
        'PyTorch': [r'pytorch'],
        'Kubernetes': [r'kubernetes', r'k8s'],
        'Docker': [r'docker'],
        'TypeScript': [r'typescript', r'ts'],
        'Svelte': [r'svelte'],
        'Nuxt': [r'nuxt', r'nuxtjs'],
    }
    
    try:
        # Get user's repositories
        repos_url = f"https://api.github.com/users/{username}/repos?type=all&per_page=100&sort=updated"
        all_technologies = set()  # Changed from all_languages to all_technologies
        page = 1
        repos_processed = 0
        repos_with_languages = 0
        total_repos_fetched = 0
        
        while page <= 10:  # Max 10 pages = 1000 repos
            paginated_url = f"{repos_url}&page={page}"
            try:
                repos_response = github_request(paginated_url)
                repos = repos_response.json()
            except Exception as e:
                logging.error(f"❌ [Tech Stack] Error fetching repos page {page} for {username}: {e}")
                break
            
            if not repos:
                logging.info(f"🔧 [Tech Stack] No more repos at page {page}")
                break
            
            total_repos_fetched += len(repos)
            logging.info(f"🔧 [Tech Stack] Page {page}: Processing {len(repos)} repositories...")
            
            for repo in repos:
                repo_name = repo.get('full_name', '')
                if not repo_name:
                    continue
                
                # Skip forks for now (or include them - user's choice)
                # if repo.get('fork', False):
                #     continue
                
                # 1. Get languages used in this repository from GitHub API
                try:
                    languages_url = f"https://api.github.com/repos/{repo_name}/languages"
                    languages_response = github_request(languages_url)
                    languages_data = languages_response.json()
                    
                    # languages_data is a dict like {"Python": 12345, "JavaScript": 6789, ...}
                    if languages_data and isinstance(languages_data, dict):
                        repo_languages = list(languages_data.keys())
                        if repo_languages:
                            for lang in repo_languages:
                                all_technologies.add(lang)
                            repos_with_languages += 1
                            logging.debug(f"🔧 [Tech Stack] {repo_name}: Languages from API: {repo_languages}")
                        repos_processed += 1
                    else:
                        logging.debug(f"🔧 [Tech Stack] {repo_name}: No languages detected (empty or null response)")
                        repos_processed += 1
                    
                    # Small delay to avoid secondary rate limits (abuse detection)
                    # GitHub has secondary rate limits that trigger on rapid requests
                    import time
                    time.sleep(0.1)  # 100ms delay between language API calls
                    
                except Exception as e:
                    error_msg = str(e)
                    # Don't log as warning if it's a 403 that's not a real rate limit (access denied)
                    # Only log actual rate limits or other real errors
                    if 'rate limit' in error_msg.lower() and 'remaining requests: 0' in error_msg.lower():
                        logging.warning(f"⚠️  [Tech Stack] Rate limit hit for {repo_name}: {error_msg}")
                        # If we hit actual rate limit, break the loop to avoid more errors
                        logging.warning(f"⚠️  [Tech Stack] Stopping language fetching due to rate limit. Will continue with repos already processed.")
                        break
                    elif '403' in error_msg or 'forbidden' in error_msg.lower():
                        # Access denied - skip this repo silently
                        logging.debug(f"🔧 [Tech Stack] Access denied for {repo_name}, skipping...")
                        repos_processed += 1
                    else:
                        logging.warning(f"⚠️  [Tech Stack] Error fetching languages for {repo_name}: {error_msg}")
                        repos_processed += 1
                    continue
                
                # 2. Scan repo metadata (name, description, topics) for frameworks
                # This helps detect frameworks that might not show up in language API
                try:
                    name = (repo.get("name") or "").lower()
                    description = (repo.get("description") or "").lower()
                    topics = [t.lower() for t in (repo.get("topics") or [])]
                    
                    for framework, keywords in framework_keywords.items():
                        found = False
                        # Check topics first (most reliable)
                        for kw in keywords:
                            if any(kw in topic for topic in topics):
                                found = True
                                break
                        
                        if not found:
                            # Check name and description with word boundaries to avoid false positives
                            for kw in keywords:
                                # Escape special regex characters in keyword
                                escaped_kw = re.escape(kw)
                                pattern = r'\b' + escaped_kw + r'\b'
                                if re.search(pattern, name) or re.search(pattern, description):
                                    found = True
                                    break
                        
                        if found:
                            all_technologies.add(framework)
                            logging.debug(f"🔧 [Tech Stack] {repo_name}: Detected framework: {framework}")
                except Exception as e:
                    logging.debug(f"🔧 [Tech Stack] Error scanning metadata for {repo_name}: {e}")
                    continue
            
            if len(repos) < 100:
                break
            page += 1
        
        tech_stack_list = sorted(list(all_technologies))
        logging.info(f"✅ [Tech Stack] Found {len(tech_stack_list)} technologies from {repos_with_languages}/{repos_processed} repositories (total repos fetched: {total_repos_fetched})")
        if tech_stack_list:
            logging.info(f"🔧 [Tech Stack] Technologies: {tech_stack_list}")
        else:
            logging.warning(f"⚠️  [Tech Stack] No technologies found for {username}. This could mean:")
            logging.warning(f"    - User has no repositories with detected languages")
            logging.warning(f"    - All repositories are empty or have no code")
            logging.warning(f"    - GitHub API rate limit or access issue")
        
        return tech_stack_list
    except Exception as e:
        logging.error(f"❌ [Tech Stack] Error fetching tech stack for {username}: {e}", exc_info=True)
        return []


def fetch_user_repos_count(username: str) -> int:
    """
    Fetch the total number of repositories OWNED by the user (not contributed repos).
    Uses GitHub API to get user's total public repository count from their profile.
    Returns the total count of repositories owned by the user.
    """
    logging.info(f"📦 [Repos] Fetching repository count for {username}...")
    
    token = get_github_token()
    if not token:
        raise ValueError("GITHUB_TOKEN is required for fetching user profile data")
    
    try:
        # Get user profile to get total public repos count (OWNED repos only)
        user_url = f"https://api.github.com/users/{username}"
        user_response = github_request(user_url)
        user_data = user_response.json()
        
        # Get public_repos count (repositories OWNED by the user)
        public_repos = user_data.get('public_repos', 0)
        
        logging.info(f"✅ [Repos] User {username} owns {public_repos} public repositories")
        
        # Return only the user's own repos (not contributed repos)
        total_repos = public_repos
        
        return total_repos
    except Exception as e:
        logging.error(f"❌ [Repos] Error fetching repos count for {username}: {e}")
        return 0


def generate_heatmap_from_contributions(contributions: List[Dict], prs: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Generate heatmap from GraphQL contributions (more reliable than Events API).
    Similar to generate_contribution_heatmap but uses contribution data directly.
    """
    logging.info(f"🗓️  [Heatmap] Generating heatmap from {len(contributions)} GraphQL contributions and {len(prs)} PRs...")
    
    years = [2024, 2025, 2026]
    heatmaps_by_year = {}
    
    for year in years:
        heatmap_grid = {}
        for week in range(52):
            for day in range(7):
                heatmap_grid[(week, day)] = {'count': 0, 'date': None}
        
        year_start = datetime(year, 1, 1, tzinfo=timezone.utc)
        year_end = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        
        # Get the first Monday of the year
        year_start_weekday = year_start.weekday()
        if year_start_weekday == 0:
            start_of_first_week = year_start
        else:
            days_to_previous_monday = year_start_weekday
            start_of_first_week = year_start - timedelta(days=days_to_previous_monday)
        
        # Process GraphQL contributions for this year
        contributions_this_year = 0
        for contrib in contributions:
            date_str = contrib.get('date', '')
            count = contrib.get('count', 1)
            if date_str:
                try:
                    # Handle both ISO format (with time) and simple date format (YYYY-MM-DD)
                    if 'T' in date_str or 'Z' in date_str:
                        contrib_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    else:
                        # Simple date format from GraphQL: "YYYY-MM-DD"
                        contrib_date = datetime.strptime(date_str, '%Y-%m-%d')
                        contrib_date = contrib_date.replace(tzinfo=timezone.utc)
                    
                    if year_start <= contrib_date <= year_end:
                        days_since_start = (contrib_date - start_of_first_week).days
                        week = min(51, days_since_start // 7)
                        day = contrib_date.weekday()
                        
                        if 0 <= week < 52 and 0 <= day < 7:
                            key = (week, day)
                            if key not in heatmap_grid:
                                heatmap_grid[key] = {'count': 0, 'date': None}
                            heatmap_grid[key]['count'] += count
                            if heatmap_grid[key]['date'] is None:
                                heatmap_grid[key]['date'] = contrib_date.strftime('%Y-%m-%d')
                            contributions_this_year += count
                except Exception as e:
                    logging.debug(f"⚠️  [Heatmap] Failed to parse contribution date '{date_str}': {e}")
                    continue
        
        # Process PRs for this year
        prs_this_year = 0
        for pr in prs:
            date_str = pr.get('merged_at', '')
            if date_str:
                try:
                    pr_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    if year_start <= pr_date <= year_end:
                        days_since_start = (pr_date - start_of_first_week).days
                        week = min(51, days_since_start // 7)
                        day = pr_date.weekday()
                        
                        if 0 <= week < 52 and 0 <= day < 7:
                            key = (week, day)
                            if key not in heatmap_grid:
                                heatmap_grid[key] = {'count': 0, 'date': None}
                            heatmap_grid[key]['count'] += 2  # PRs count more
                            if heatmap_grid[key]['date'] is None:
                                heatmap_grid[key]['date'] = pr_date.strftime('%Y-%m-%d')
                            prs_this_year += 1
                except Exception:
                    continue
        
        logging.info(f"🗓️  [Heatmap] Year {year}: {contributions_this_year} contributions, {prs_this_year} PRs")
        
        # Normalize values to 0-4 scale
        max_count = max(cell['count'] for cell in heatmap_grid.values()) if heatmap_grid.values() else 1
        
        heatmap_data = []
        for week in range(52):
            for day in range(7):
                key = (week, day)
                cell_data = heatmap_grid.get(key, {'count': 0, 'date': None})
                raw_count = cell_data['count']
                
                if cell_data['date']:
                    cell_date = cell_data['date']
                else:
                    days_offset = week * 7 + day
                    cell_datetime = start_of_first_week + timedelta(days=days_offset)
                    cell_date = cell_datetime.strftime('%Y-%m-%d')
                
                if max_count > 0:
                    normalized_value = min(4, int((raw_count / max_count) * 4))
                else:
                    normalized_value = 0
                
                heatmap_data.append({
                    'week': week,
                    'day': day,
                    'value': normalized_value,
                    'count': raw_count,
                    'date': cell_date
                })
        
        heatmaps_by_year[str(year)] = heatmap_data
        logging.info(f"🗓️  [Heatmap] Year {year}: Generated {len(heatmap_data)} cells, max count: {max_count}")
    
    return heatmaps_by_year


def generate_contribution_heatmap(commits: List[Dict], prs: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Generate contribution heatmap data organized by year (2024, 2025, 2026).
    Combines commits and PRs to create a comprehensive activity map.
    Returns: Dict with year as key and List of {week: int, day: int, value: int, count: int, date: str}
    where value is 0-4 (for display) and count is actual contribution count
    """
    logging.info(f"🗓️  [Heatmap] Generating heatmap from {len(commits)} commits and {len(prs)} PRs...")
    
    # Years to generate heatmaps for
    years = [2024, 2025, 2026]
    heatmaps_by_year = {}
    
    for year in years:
        # Initialize 52 weeks x 7 days grid for this year
        heatmap_grid = {}
        for week in range(52):
            for day in range(7):
                heatmap_grid[(week, day)] = {'count': 0, 'date': None}
        
        # Calculate start and end dates for this year
        year_start = datetime(year, 1, 1, tzinfo=timezone.utc)
        year_end = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        
        # Get the first Monday of the year (or start of year if it's Monday)
        # weekday() returns: Monday=0, Tuesday=1, ..., Sunday=6
        year_start_weekday = year_start.weekday()
        if year_start_weekday == 0:  # Already Monday
            start_of_first_week = year_start
        else:
            # Go back to the previous Monday
            days_to_previous_monday = year_start_weekday
            start_of_first_week = year_start - timedelta(days=days_to_previous_monday)
        
        # Process commits for this year
        commits_this_year = 0
        for commit in commits:
            date_str = commit.get('date', '')
            if date_str:
                try:
                    commit_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    
                    if year_start <= commit_date <= year_end:
                        # Calculate which week this falls into (0-51)
                        days_since_start = (commit_date - start_of_first_week).days
                        week = min(51, days_since_start // 7)
                        day = commit_date.weekday()  # Monday=0, Sunday=6
                        
                        if 0 <= week < 52 and 0 <= day < 7:
                            key = (week, day)
                            if key not in heatmap_grid:
                                heatmap_grid[key] = {'count': 0, 'date': None}
                            heatmap_grid[key]['count'] += 1
                            if heatmap_grid[key]['date'] is None:
                                heatmap_grid[key]['date'] = commit_date.strftime('%Y-%m-%d')
                            commits_this_year += 1
                except Exception:
                    continue
        
        # Process PRs (merged_at dates) for this year
        prs_this_year = 0
        for pr in prs:
            date_str = pr.get('merged_at', '')
            if date_str:
                try:
                    pr_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    
                    if year_start <= pr_date <= year_end:
                        days_since_start = (pr_date - start_of_first_week).days
                        week = min(51, days_since_start // 7)
                        day = pr_date.weekday()
                        
                        if 0 <= week < 52 and 0 <= day < 7:
                            key = (week, day)
                            if key not in heatmap_grid:
                                heatmap_grid[key] = {'count': 0, 'date': None}
                            heatmap_grid[key]['count'] += 2  # PRs count more than commits
                            if heatmap_grid[key]['date'] is None:
                                heatmap_grid[key]['date'] = pr_date.strftime('%Y-%m-%d')
                            prs_this_year += 1
                except Exception:
                    continue
        
        logging.info(f"🗓️  [Heatmap] Year {year}: {commits_this_year} commits, {prs_this_year} PRs")
        
        # Normalize values to 0-4 scale for this year
        max_count = max(cell['count'] for cell in heatmap_grid.values()) if heatmap_grid.values() else 1
        
        heatmap_data = []
        for week in range(52):
            for day in range(7):
                key = (week, day)
                cell_data = heatmap_grid.get(key, {'count': 0, 'date': None})
                raw_count = cell_data['count']
                
                # Calculate the actual date for this cell
                if cell_data['date']:
                    cell_date = cell_data['date']
                else:
                    # Calculate date from week and day
                    days_offset = week * 7 + day
                    cell_datetime = start_of_first_week + timedelta(days=days_offset)
                    cell_date = cell_datetime.strftime('%Y-%m-%d')
                
                # Normalize to 0-4 scale for display
                if max_count > 0:
                    normalized_value = min(4, int((raw_count / max_count) * 4))
                else:
                    normalized_value = 0
                
                heatmap_data.append({
                    'week': week,
                    'day': day,
                    'value': normalized_value,  # 0-4 for color display
                    'count': raw_count,  # Actual contribution count
                    'date': cell_date  # Date string for display
                })
        
        # Store with string key (MongoDB requires string keys)
        heatmaps_by_year[str(year)] = heatmap_data
        logging.info(f"🗓️  [Heatmap] Year {year}: Generated {len(heatmap_data)} cells, max count: {max_count}")
    
    return heatmaps_by_year


def extract_personal_details(user_data: Dict, social_accounts: List[Dict] = None) -> Dict[str, str]:
    """
    Extract personal details like LinkedIn, Twitter/X, portfolio, email, location from GitHub profile.
    Uses GitHub API fields and social_accounts endpoint for reliable extraction.
    Falls back to bio parsing if needed.
    """
    personal_details = {
        "email": None,
        "linkedin": None,
        "twitter": None,
        "x_com": None,
        "portfolio": None,
        "website": None,
        "location": None
    }
    
    # 1. Start with explicit fields from GitHub user data
    email = user_data.get("email")
    if email:
        personal_details["email"] = email.strip()
        logging.info(f"📧 [Personal Details] Found email: {email[:3]}***")
    
    # Location - fetch if available
    location = user_data.get("location")
    if location:
        personal_details["location"] = location.strip()
        logging.info(f"📍 [Personal Details] Found location: {location}")
    
    # Blog/Website - often contains portfolio or LinkedIn
    blog = user_data.get("blog")
    if blog:
        blog = blog.strip()
        if blog:
            if not blog.startswith("http"):
                blog = f"https://{blog}"
            # Check if blog is a social link
            blog_lower = blog.lower()
            if "linkedin.com" in blog_lower and not personal_details["linkedin"]:
                personal_details["linkedin"] = blog
                logging.info(f"💼 [Personal Details] Found LinkedIn from blog field: {blog}")
            elif ("twitter.com" in blog_lower or "x.com" in blog_lower) and not personal_details["twitter"]:
                personal_details["twitter"] = blog
                personal_details["x_com"] = blog
                logging.info(f"🐦 [Personal Details] Found Twitter/X from blog field: {blog}")
            else:
                personal_details["portfolio"] = blog
                personal_details["website"] = blog
                logging.info(f"🌐 [Personal Details] Found portfolio/website from blog field: {blog}")
    
    # Twitter username from profile (GitHub API field)
    twitter_username = user_data.get("twitter_username")
    if twitter_username and not personal_details["twitter"]:
        personal_details["twitter"] = f"https://x.com/{twitter_username}"
        personal_details["x_com"] = f"https://x.com/{twitter_username}"
        logging.info(f"🐦 [Personal Details] Found Twitter/X from twitter_username field: {twitter_username}")

    # 2. Add details from social accounts API (most reliable source)
    if social_accounts:
        for account in social_accounts:
            provider = account.get("provider", "").lower()
            url = account.get("url", "")
            if not url:
                continue
                
            if provider == "linkedin" or "linkedin.com" in url.lower():
                if not personal_details["linkedin"]:
                    personal_details["linkedin"] = url
                    logging.info(f"💼 [Personal Details] Found LinkedIn from social_accounts API: {url}")
            elif provider == "twitter" or "twitter.com" in url.lower() or "x.com" in url.lower():
                if not personal_details["twitter"]:
                    personal_details["twitter"] = url
                    personal_details["x_com"] = url
                    logging.info(f"🐦 [Personal Details] Found Twitter/X from social_accounts API: {url}")
            elif not personal_details["portfolio"]:
                # Use other social links as portfolio if nothing else exists
                personal_details["portfolio"] = url
                logging.info(f"🌐 [Personal Details] Found portfolio from social_accounts API: {url}")

    # 3. Parse bio for social links (as fallback or to find more)
    bio = user_data.get("bio", "") or ""
    # Also check company field (sometimes contains links)
    company = user_data.get("company", "") or ""
    # Combine bio and company for parsing
    combined_text = f"{bio} {company}".strip()
    
    if combined_text:
        # LinkedIn patterns
        if not personal_details["linkedin"]:
            linkedin_patterns = [
                r'(?:https?://)?(?:www\.)?linkedin\.com/in/([\w-]+)',
                r'LinkedIn[:\s]+([\w-]+)',
                r'LinkedIn[:\s]+(?:https?://)?(?:www\.)?linkedin\.com/in/([\w-]+)',
                r'in/([\w-]+)', # Common shorthand in bios
            ]
            for pattern in linkedin_patterns:
                match = re.search(pattern, combined_text, re.IGNORECASE)
                if match:
                    username = match.group(1)
                    if username.startswith("http"):
                        personal_details["linkedin"] = username
                    else:
                        personal_details["linkedin"] = f"https://www.linkedin.com/in/{username}"
                    logging.info(f"💼 [Personal Details] Found LinkedIn from bio: {personal_details['linkedin']}")
                    break
        
        # Twitter/X patterns - improved to catch more cases
        if not personal_details["twitter"]:
            twitter_patterns = [
                # Full URLs with x.com (most common now)
                r'(?:https?://)?(?:www\.)?x\.com/([\w]+)',
                r'(?:https?://)?(?:www\.)?x\.com/@?([\w]+)',
                # Full URLs with twitter.com
                r'(?:https?://)?(?:www\.)?twitter\.com/([\w]+)',
                r'(?:https?://)?(?:www\.)?twitter\.com/@?([\w]+)',
                # Just x.com or twitter.com without protocol (common in bios)
                r'\bx\.com/([\w]+)',
                r'\btwitter\.com/([\w]+)',
                # Text patterns with labels
                r'(?:Twitter|X)[:\s]+(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/?@?([\w]+)',
                r'(?:Twitter|X)[:\s]+@?([\w]+)',
                # Generic @username (might be wrong, but often used for Twitter)
                r'@([\w]+)',
            ]
            for pattern in twitter_patterns:
                match = re.search(pattern, combined_text, re.IGNORECASE)
                if match:
                    username = match.group(1).strip()
                    # Skip if it looks like an email
                    if '@' in username and '.' in username and not username.startswith('@'):
                        continue
                    # Skip common non-twitter usernames
                    if username.lower() in ['github', 'linkedin', 'email', 'mail', 'gmail']:
                        continue
                    if username.startswith("http"):
                        personal_details["twitter"] = username
                        personal_details["x_com"] = username
                    else:
                        # Prefer x.com over twitter.com
                        personal_details["twitter"] = f"https://x.com/{username}"
                        personal_details["x_com"] = f"https://x.com/{username}"
                    logging.info(f"🐦 [Personal Details] Found Twitter/X from bio: {personal_details['twitter']} (pattern: {pattern[:50]})")
                    break
        
        # Portfolio/website patterns in bio
        if not personal_details["portfolio"]:
            portfolio_patterns = [
                r'(?:portfolio|website|blog)[:\s]+(https?://[^\s\)]+)',
                r'(?:portfolio|website|blog)[:\s]+([^\s\)]+\.(?:me|io|dev|com|net|org|co|app|tech))',
                r'(https?://[^\s\)]+\.(?:me|io|dev|com|net|org|co|app|tech))', # Common portfolio domains
                r'([^\s\)]+\.(?:me|io|dev|tech))', # Shorthand domains like vishvam.me
            ]
            for pattern in portfolio_patterns:
                match = re.search(pattern, combined_text, re.IGNORECASE)
                if match:
                    url = match.group(1)
                    if "linkedin.com" not in url.lower() and "twitter.com" not in url.lower() and "x.com" not in url.lower():
                        if not url.startswith("http"):
                            url = f"https://{url}"
                        personal_details["portfolio"] = url
                        logging.info(f"🌐 [Personal Details] Found portfolio from bio: {url}")
                        break
        
        # Final fallback: Look for any URLs or domain mentions in the text
        # This catches cases where patterns above might have missed
        if not personal_details["linkedin"] or not personal_details["twitter"]:
            # Find all URLs in the text (with protocol)
            url_pattern = r'(https?://[^\s\)]+)'
            all_urls = re.findall(url_pattern, combined_text, re.IGNORECASE)
            for url in all_urls:
                url_lower = url.lower()
                # Check for LinkedIn
                if not personal_details["linkedin"] and "linkedin.com" in url_lower:
                    if "/in/" in url_lower or "/pub/" in url_lower or "/profile/" in url_lower:
                        personal_details["linkedin"] = url
                        logging.info(f"💼 [Personal Details] Found LinkedIn URL from fallback: {url}")
                # Check for Twitter/X
                if not personal_details["twitter"] and ("twitter.com" in url_lower or "x.com" in url_lower):
                    personal_details["twitter"] = url
                    personal_details["x_com"] = url
                    logging.info(f"🐦 [Personal Details] Found Twitter/X URL from fallback: {url}")
            
            # Also check for domain mentions without protocol (like "x.com/username")
            if not personal_details["twitter"]:
                # Look for x.com/username or twitter.com/username patterns (more aggressive)
                domain_patterns = [
                    r'\bx\.com/([\w]+)',  # Word boundary before x.com
                    r'\btwitter\.com/([\w]+)',  # Word boundary before twitter.com
                    r'[^\w/]x\.com/([\w]+)',  # Non-word char before x.com
                    r'[^\w/]twitter\.com/([\w]+)',  # Non-word char before twitter.com
                    r'x\.com/([\w]+)',  # Just x.com/username (catch all)
                    r'twitter\.com/([\w]+)',  # Just twitter.com/username (catch all)
                ]
                for pattern in domain_patterns:
                    match = re.search(pattern, combined_text, re.IGNORECASE)
                    if match:
                        username = match.group(1).strip()
                        if username and username.lower() not in ['github', 'linkedin', 'email', 'mail', 'gmail']:
                            personal_details["twitter"] = f"https://x.com/{username}"
                            personal_details["x_com"] = f"https://x.com/{username}"
                            logging.info(f"🐦 [Personal Details] Found Twitter/X from domain fallback: {personal_details['twitter']} (pattern: {pattern})")
                            break
    
    # Log what we found with actual values (for debugging)
    found_fields = []
    if personal_details.get("email"):
        found_fields.append(f"email: {personal_details['email'][:3]}***")
    if personal_details.get("location"):
        found_fields.append(f"location: {personal_details['location']}")
    if personal_details.get("linkedin"):
        found_fields.append(f"linkedin: {personal_details['linkedin']}")
    if personal_details.get("twitter") or personal_details.get("x_com"):
        twitter_url = personal_details.get("twitter") or personal_details.get("x_com")
        found_fields.append(f"twitter/x: {twitter_url}")
    if personal_details.get("portfolio") or personal_details.get("website"):
        portfolio_url = personal_details.get("portfolio") or personal_details.get("website")
        found_fields.append(f"portfolio/website: {portfolio_url}")
    
    if found_fields:
        logging.info(f"📧 [Personal Details] Extracted: {', '.join(found_fields)}")
    else:
        logging.info(f"📧 [Personal Details] No personal details found")
        # Log what we checked for debugging
        if user_data.get("bio"):
            logging.info(f"📝 [Personal Details] Bio was (full): {user_data.get('bio', '')}")
        if user_data.get("company"):
            logging.info(f"🏢 [Personal Details] Company was: {user_data.get('company', '')}")
        # Also log the combined text for debugging
        if combined_text:
            logging.info(f"📝 [Personal Details] Combined text (bio+company): {combined_text[:300]}")
    
    # Return all fields (including None values) so caller knows what was attempted
    # But filter None values for cleaner storage
    result = {k: v for k, v in personal_details.items() if v is not None}
    return result


def fetch_user_profile_metrics(username: str) -> Dict:
    """
    Fetch all personal GitHub profile metrics needed for git score calculation.
    Returns: {
        'total_prs_merged': int,
        'avg_prs_per_week': float,
        'consistency_score': float,  # 0-100
        'num_repos': int,
        'tech_stack': List[str],  # Technologies used across all repos
        'prs': List[Dict],  # List of PR objects
        'contribution_heatmap': List[Dict],  # Heatmap data for UI
        'personal_details': Dict[str, str]  # Email, LinkedIn, Twitter, portfolio, etc.
    }
    """
    logging.info(f"")
    logging.info(f"🔍 [Profile] ========== Fetching profile metrics for {username} ==========")
    
    # Fetch user profile data for personal details extraction and bot detection
    logging.info(f"📧 [Profile] Fetching user profile data...")
    try:
        user_url = f"https://api.github.com/users/{username}"
        user_response = github_request(user_url)
        user_data = user_response.json()
        
        # Log bio and company for debugging
        bio = user_data.get("bio", "") or ""
        company = user_data.get("company", "") or ""
        if bio:
            logging.info(f"📝 [Profile] User bio (full): {bio}")
        if company:
            logging.info(f"🏢 [Profile] User company: {company}")
        # Also log other fields that might contain links
        blog = user_data.get("blog", "")
        twitter_username = user_data.get("twitter_username")
        if blog:
            logging.info(f"🌐 [Profile] User blog/website: {blog}")
        if twitter_username:
            logging.info(f"🐦 [Profile] User twitter_username: {twitter_username}")
        
        # Check if user is a bot - skip processing if bot
        if is_bot_user(username, user_data):
            logging.warning(f"🤖 [Profile] Skipping bot user: {username}")
            raise ValueError(f"User {username} is a bot account and will be skipped")
        
        # Fetch social accounts from GitHub API (structured social links)
        social_accounts = []
        try:
            social_accounts_url = f"https://api.github.com/users/{username}/social_accounts"
            social_response = github_request(social_accounts_url)
            if social_response.status_code == 200:
                social_accounts = social_response.json()
                logging.info(f"🔗 [Profile] Fetched {len(social_accounts)} social accounts from API")
                for account in social_accounts:
                    logging.info(f"   - {account.get('provider', 'unknown')}: {account.get('url', '')}")
            else:
                logging.warning(f"⚠️  [Profile] Could not fetch social_accounts (status {social_response.status_code})")
        except Exception as e:
            logging.warning(f"⚠️  [Profile] Error fetching social_accounts: {e}")
            # Continue without social accounts - will use bio parsing as fallback
        
        # Extract personal details from user profile and social accounts
        personal_details = extract_personal_details(user_data, social_accounts=social_accounts)
    except ValueError as e:
        # Re-raise ValueError (bot detection) to skip processing
        raise
    except Exception as e:
        logging.warning(f"⚠️  [Profile] Error fetching user profile data: {e}")
        user_data = {}
        personal_details = {}
    
    # Fetch merged PRs in last year
    pr_data = fetch_user_merged_prs_last_year(username)
    
    # Fetch contributions from GraphQL API (more reliable than Events API)
    # This is the same API the frontend uses for heatmap, so it's consistent
    current_year = datetime.now(timezone.utc).year
    years_to_fetch = [current_year, current_year - 1, current_year - 2]  # 2024, 2025, 2026
    
    all_contributions = []
    for year in years_to_fetch:
        year_contributions = fetch_contributions_from_graphql(username, year)
        all_contributions.extend(year_contributions)
        logging.info(f"📊 [Profile] Fetched {len(year_contributions)} contributions for year {year}")
    
    logging.info(f"📊 [Profile] Total contributions from GraphQL: {len(all_contributions)}")
    
    # Also fetch commits via Events API as fallback (for heatmap generation)
    # But prioritize GraphQL contributions for consistency
    commits = fetch_user_commits(username)
    logging.info(f"📝 [Profile] Fetched {len(commits)} commit events (fallback for heatmap)")
    
    # Generate contribution heatmap (organized by year)
    # Use GraphQL contributions if available, otherwise fall back to Events API commits
    if all_contributions:
        # Convert GraphQL contributions to heatmap format
        # Group by year and create heatmap structure
        heatmaps_by_year = generate_heatmap_from_contributions(all_contributions, pr_data.get('prs', []))
    else:
        # Fallback to Events API commits
        heatmaps_by_year = generate_contribution_heatmap(commits, pr_data.get('prs', []))
    
    logging.info(f"🗓️  [Profile] Generated heatmap data for years: {list(heatmaps_by_year.keys())}")
    
    # Calculate consistency score using heatmap data (all years: 2024, 2025, 2026)
    # This reuses the heatmap data instead of making a separate API call
    consistency_score = calculate_consistency_score(
        username, 
        pr_data.get('prs', []), 
        heatmap_data=heatmaps_by_year,
        commits=commits if not all_contributions else None  # Only use commits if GraphQL failed
    )
    logging.info(f"📊 [Profile] Consistency score: {consistency_score:.2f}/100")
    
    # Fetch number of repos (OWNED repos only)
    num_repos = fetch_user_repos_count(username)
    
    # Fetch tech stack from all user's repositories
    tech_stack = fetch_user_tech_stack(username)
    logging.info(f"🔧 [Profile] Tech stack: {len(tech_stack)} technologies")
    
    result = {
        'total_prs_merged': pr_data['total_prs_merged'],
        'avg_prs_per_week': pr_data['avg_prs_per_week'],
        'consistency_score': consistency_score,
        'num_repos': num_repos,
        'tech_stack': tech_stack,  # Technologies from GitHub repos
        'prs': pr_data.get('prs', []),
        'contribution_heatmap': heatmaps_by_year,  # Dict with year as key
        'personal_details': personal_details  # Email, LinkedIn, Twitter, portfolio, etc.
    }
    
    logging.info(f"")
    logging.info(f"✅ [Profile] Final metrics for {username}:")
    logging.info(f"   - Total PRs merged (all time): {result['total_prs_merged']}")
    logging.info(f"   - Avg PRs per week (last year): {result['avg_prs_per_week']}")
    logging.info(f"   - Consistency score: {result['consistency_score']:.2f}/100")
    logging.info(f"   - Number of repos (owned): {result['num_repos']}")
    logging.info(f"   - Tech stack: {len(result['tech_stack'])} technologies - {result['tech_stack'][:10] if result['tech_stack'] else 'None'}")
    logging.info(f"   - Heatmap years: {list(result['contribution_heatmap'].keys())}")
    if personal_details:
        logging.info(f"   - Personal details: {list(personal_details.keys())}")
    logging.info(f"🔍 [Profile] ========== Completed profile metrics for {username} ==========")
    logging.info(f"")
    
    return result
