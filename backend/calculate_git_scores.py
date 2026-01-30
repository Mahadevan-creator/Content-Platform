#!/usr/bin/env python3
"""
Calculate git scores for candidates from candidates_summary.json and store in MongoDB Atlas.

This script:
1. Reads candidates_summary.json (output from fetch_prs_from_json.py)
2. Fetches personal GitHub profile metrics for each candidate
3. Calculates git score based on 6 metrics
4. Stores results in MongoDB Atlas

Usage:
  export GITHUB_TOKEN="..."
  export MONGODB_URI="mongodb+srv://..."
  export MONGODB_DB_NAME="content_platform"  # optional, defaults to content_platform
  export MONGODB_COLLECTION_NAME="experts"  # optional, defaults to experts
  python3 calculate_git_scores.py candidates_summary.json
"""
import os
import sys
import json
import csv
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from services.git_profile_service import fetch_user_profile_metrics, is_bot_user
from services.git_score_calculator import calculate_git_score
from services.mongodb_service import upsert_expert
from services.github_service import fetch_contributor_prs, analyze_pr

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def extract_agent_metrics(candidate_data: Dict) -> Dict:
    """
    Extract metrics from agent JSON (candidates_summary.json).
    Returns: {
        'comment_quality': Optional[float],
        'pr_quality': Optional[float],
        'time_taken': Optional[float]
    }
    """
    scores = candidate_data.get('scores', {})
    
    # Extract comment_quality (already calculated by agent)
    comment_quality = scores.get('comment_quality')
    
    # Extract pr_quality (already calculated by agent)
    pr_quality = scores.get('pr_quality')
    
    # Extract time_taken (already calculated by agent)
    time_taken = scores.get('time_taken')
    
    return {
        'comment_quality': comment_quality,
        'pr_quality': pr_quality,
        'time_taken': time_taken
    }


def process_candidates(summary_file: str) -> Dict:
    """
    Process all candidates from summary file and calculate git scores.
    Returns: {
        'processed': int,
        'failed': int,
        'results': List[Dict]
    }
    """
    try:
        with open(summary_file, 'r', encoding='utf-8') as f:
            candidates_data = json.load(f)
    except FileNotFoundError:
        logging.error(f"File not found: {summary_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in file: {e}")
        sys.exit(1)
    
    results = []
    processed = 0
    failed = 0
    skipped_bots = 0
    
    total_candidates = len(candidates_data)
    logging.info(f"Processing {total_candidates} candidates...")
    
    for idx, (username, candidate_data) in enumerate(candidates_data.items(), 1):
        logging.info("")
        logging.info("="*80)
        logging.info(f"[{idx}/{total_candidates}] Processing candidate: {username}")
        logging.info("="*80)
        
        try:
            # Quick bot check before processing (username pattern only)
            if is_bot_user(username):
                logging.warning(f"🤖 Skipping bot user: {username}")
                skipped_bots += 1
                continue
            # Extract agent metrics
            agent_metrics = extract_agent_metrics(candidate_data)
            logging.info(f"Agent metrics: comment_quality={agent_metrics.get('comment_quality')}, "
                        f"pr_quality={agent_metrics.get('pr_quality')}, "
                        f"time_taken={agent_metrics.get('time_taken')}")
            
            # Fetch personal profile metrics
            logging.info("Fetching personal GitHub profile metrics...")
            profile_metrics = fetch_user_profile_metrics(username)
            logging.info(f"Profile metrics: total_prs_merged={profile_metrics['total_prs_merged']}, "
                        f"avg_prs_per_week={profile_metrics['avg_prs_per_week']}, "
                        f"consistency_score={profile_metrics['consistency_score']}, "
                        f"num_repos={profile_metrics['num_repos']}, "
                        f"tech_stack_count={len(profile_metrics.get('tech_stack', []))}")
            
            # Calculate git score
            logging.info("Calculating git score...")
            git_score_result = calculate_git_score(profile_metrics, agent_metrics)
            logging.info(f"Git score: {git_score_result['git_score']}/100")
            logging.info(f"Breakdown: {git_score_result['breakdown']}")
            
            # Prepare comprehensive data for MongoDB
            comprehensive_summary = candidate_data.get('comprehensive_summary', {})
            agent_scores = candidate_data.get('scores', {})
            rubric_summaries = candidate_data.get('rubric_summaries', {})
            raw_metrics = candidate_data.get('raw_metrics', {})
            
            # Extract comprehensive summary fields
            # Use tech_stack from GitHub profile (all repos) instead of agent's tech_stack (just PRs)
            tech_stack_list = profile_metrics.get('tech_stack', [])  # From GitHub repos
            features_list = comprehensive_summary.get('features', [])
            overall_summary_text = comprehensive_summary.get('overall_summary', '')
            
            # Extract personal details from profile metrics
            personal_details = profile_metrics.get('personal_details', {})
            
            mongodb_data = {
                # Basic info
                'github_username': username,
                'github_profile_url': candidate_data.get('profile_url', f'https://github.com/{username}'),
                'display_name': username,  # Default to username, can be updated later
                
                # Git score
                'git_score': git_score_result['git_score'],
                
                # Agent scores (stored as 0-100 scale after conversion)
                # Note: agent_scores from JSON are 0-5.0, but we convert to 0-100 in git_score_calculator
                # We store the converted 0-100 values here
                'pr_quality': git_score_result['breakdown']['pr_quality'],
                'comment_quality': git_score_result['breakdown']['comment_quality'],
                'time_taken': git_score_result['breakdown']['time_taken'],
                
                # Agent summaries
                'pr_quality_summary': rubric_summaries.get('pr_quality', ''),
                'comment_quality_summary': rubric_summaries.get('comment_quality', ''),
                'time_taken_summary': rubric_summaries.get('time_taken', ''),
                
                # Comprehensive summary (flattened)
                'tech_stack': tech_stack_list,
                'features': features_list,
                'overall_summary': overall_summary_text,
                
                # Profile metrics
                'pr_merged_total': profile_metrics['total_prs_merged'],
                'avg_pr_merge_rate_per_week': profile_metrics['avg_prs_per_week'],
                'consistency_score': profile_metrics['consistency_score'],
                'num_repos': profile_metrics['num_repos'],
                'contribution_heatmap': profile_metrics.get('contribution_heatmap', {}),  # Dict by year
                
                # Personal details (extracted from GitHub profile)
                'email': personal_details.get('email'),
                'portfolio_url': personal_details.get('portfolio') or personal_details.get('website'),
                'twitter_url': personal_details.get('twitter') or personal_details.get('x_com'),
                'linkedin_url': personal_details.get('linkedin'),
                'location': personal_details.get('location'),
                
                # Display name (default to username, can be updated later)
                'display_name': username,
                
                # Status and workflow (for table display)
                'status': 'available',  # available, interviewing, onboarded, contracted
                'workflow': {
                    'emailSent': 'pending',  # pending, sent, opened
                    'testSent': 'pending',   # pending, sent, completed, passed, failed
                    'interview': 'pending',  # pending, scheduled, completed
                    'interviewResult': 'pending'  # pending, pass, fail, strong_pass
                },
            }
            
            # Store in MongoDB
            logging.info("Storing in MongoDB...")
            mongodb_result = upsert_expert(username, mongodb_data)
            
            if mongodb_result:
                logging.info(f"✅ Successfully processed {username}")
            else:
                logging.warning(f"⚠️  Failed to store {username} in MongoDB (but calculation succeeded)")
            
            results.append({
                'username': username,
                'git_score': git_score_result['git_score'],
                'breakdown': git_score_result['breakdown'],
                'profile_metrics': profile_metrics,
                'agent_metrics': agent_metrics,
                'mongodb_stored': mongodb_result is not None
            })
            
            processed += 1
            
        except ValueError as e:
            # Bot detected - skip this user
            if "bot account" in str(e).lower():
                logging.warning(f"🤖 Skipping bot user: {username}")
                skipped_bots += 1
            else:
                logging.error(f"❌ Error processing {username}: {e}", exc_info=True)
                failed += 1
            continue
        except Exception as e:
            logging.error(f"❌ Error processing {username}: {e}", exc_info=True)
            failed += 1
            continue
    
    return {
        'processed': processed,
        'failed': failed,
        'skipped_bots': skipped_bots,
        'results': results
    }


def read_candidates_from_csv(csv_file: str, limit: int = 10) -> List[str]:
    """
    Read usernames from CSV file (Username column).
    Returns list of usernames, limited to 'limit' candidates.
    """
    usernames = []
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            # Auto-detect delimiter
            sample = f.read(1024)
            f.seek(0)
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter
            
            reader = csv.DictReader(f, delimiter=delimiter)
            
            # Find Username column (case-insensitive)
            username_col = None
            for col in reader.fieldnames or []:
                if col.lower() == 'username':
                    username_col = col
                    break
            
            if not username_col:
                logging.error("❌ 'Username' column not found in CSV file")
                return []
            
            # Read usernames
            for row in reader:
                username = row.get(username_col, '').strip()
                if username and len(usernames) < limit:
                    usernames.append(username)
        
        logging.info(f"📋 Read {len(usernames)} usernames from CSV (limit: {limit})")
        return usernames
    
    except Exception as e:
        logging.error(f"❌ Error reading CSV file: {e}")
        return []


def get_top_3_prs_for_user(username: str) -> List[Dict]:
    """
    Get top 3 PRs for a user from their overall profile (same as repo-based flow).
    Reuses fetch_contributor_prs() and analyze_pr() from github_service.
    Returns list of analyzed PR objects with scores.
    """
    logging.info(f"📦 Fetching all merged PRs for {username} across all repositories...")
    
    # Fetch all merged PRs (same as repo-based flow)
    prs = fetch_contributor_prs(username)
    
    if not prs:
        logging.warning(f"⚠️  No PRs found for {username}")
        return []
    
    logging.info(f"   Found {len(prs)} merged PRs, analyzing to find top 3...")
    
    # Analyze all PRs to find top 3 (same as repo-based flow)
    analyzed_prs = []
    for pr in prs:
        try:
            # Extract owner and repo from PR data
            pr_url = pr.get('html_url', '')
            # Format: https://github.com/owner/repo/pull/123
            parts = pr_url.replace('https://github.com/', '').split('/')
            if len(parts) >= 2:
                pr_owner = parts[0]
                pr_repo = parts[1]
                analyzed_pr = analyze_pr(pr, pr_owner, pr_repo)
                analyzed_prs.append(analyzed_pr)
        except Exception as e:
            logging.warning(f"⚠️  Error analyzing PR: {e}")
            continue
    
    # Sort by score and take top 3 (same as repo-based flow)
    analyzed_prs.sort(key=lambda x: x.get('score', 0), reverse=True)
    top_3_prs = analyzed_prs[:3]
    
    logging.info(f"✅ Selected top 3 PRs for {username}:")
    for idx, pr in enumerate(top_3_prs, 1):
        pr_repo = pr.get('html_url', '').replace('https://github.com/', '').split('/')[:2]
        repo_name = '/'.join(pr_repo) if len(pr_repo) == 2 else 'N/A'
        logging.info(f"   {idx}. PR #{pr.get('number')} in {repo_name}: {pr.get('title', 'N/A')[:50]}... (Score: {pr.get('score', 0):.2f})")
    
    return top_3_prs


def convert_analyzed_pr_to_fetch_format(analyzed_pr: Dict) -> Dict:
    """
    Convert analyzed PR from analyze_pr() format to fetch_prs_from_json.py format.
    This allows reuse of the existing analysis functions.
    """
    return {
        'pr_number': analyzed_pr.get('number'),
        'title': analyzed_pr.get('title', ''),
        'body': analyzed_pr.get('body', ''),
        'url': analyzed_pr.get('html_url', ''),
        'state': analyzed_pr.get('state', ''),
        'created_at': analyzed_pr.get('created_at', ''),
        'updated_at': analyzed_pr.get('updated_at', ''),
        'merged_at': analyzed_pr.get('merged_at', ''),
        'merged': analyzed_pr.get('merged', False),
        'additions': analyzed_pr.get('additions', 0),
        'deletions': analyzed_pr.get('deletions', 0),
        'changed_files': analyzed_pr.get('files_changed', 0),
        'author': analyzed_pr.get('author', {}),
        'labels': analyzed_pr.get('labels', []),
        'comments_count': analyzed_pr.get('comments_count', 0),
        'reviews_count': analyzed_pr.get('reviews_count', 0),
    }


def analyze_prs_for_candidate(username: str, analyzed_prs: List[Dict]) -> Dict:
    """
    Analyze top 3 PRs for a candidate (same as fetch_prs_from_json.py flow).
    Takes analyzed PRs from analyze_pr() and converts them for LLM analysis.
    Returns candidate data in the same format as candidates_summary.json.
    """
    # Import LLM functions from fetch_prs_from_json
    try:
        import sys
        import importlib.util
        fetch_prs_path = Path(__file__).parent / "fetch_prs_from_json.py"
        if fetch_prs_path.exists():
            spec = importlib.util.spec_from_file_location("fetch_prs_from_json", fetch_prs_path)
            fetch_prs_module = importlib.util.module_from_spec(spec)
            sys.modules['fetch_prs_from_json'] = fetch_prs_module
            spec.loader.exec_module(fetch_prs_module)
            
            llm_score_pr_quality = fetch_prs_module.llm_score_pr_quality
            llm_score_pr_comments = fetch_prs_module.llm_score_pr_comments
            llm_generate_rubric_summary = fetch_prs_module.llm_generate_rubric_summary
            llm_generate_candidate_summary = fetch_prs_module.llm_generate_candidate_summary
            calculate_pr_time_taken = fetch_prs_module.calculate_pr_time_taken
            score_time_taken = fetch_prs_module.score_time_taken
            OLLAMA_AVAILABLE = getattr(fetch_prs_module, 'OLLAMA_AVAILABLE', False)
            LLM_MODEL = getattr(fetch_prs_module, 'LLM_MODEL', os.getenv("LLM_MODEL", "llama3:latest"))
            SLEEP_SECS = getattr(fetch_prs_module, 'SLEEP_SECS', float(os.getenv("SLEEP_SECS", "0.2")))
        else:
            raise ImportError("fetch_prs_from_json.py not found")
        import time
    except (ImportError, AttributeError, Exception) as e:
        logging.warning(f"⚠️  LLM functions not available: {e}, using defaults")
        OLLAMA_AVAILABLE = False
        LLM_MODEL = None
        SLEEP_SECS = 0.2
        # Define stub functions
        def llm_score_pr_quality(*args, **kwargs):
            return {"quality_score_0_5": 2.5, "tech_stack_detected": [], "summary": ""}
        def llm_score_pr_comments(*args, **kwargs):
            return {"comment_quality_score_0_5": 2.5, "summary": ""}
        def llm_generate_rubric_summary(*args, **kwargs):
            return ""
        def llm_generate_candidate_summary(*args, **kwargs):
            return {"tech_stack": [], "features": [], "overall_summary": ""}
        def calculate_pr_time_taken(pr):
            return None
        def score_time_taken(days):
            return 2.5
        import time
    
    # Convert analyzed PRs to format expected by fetch_prs_from_json functions
    prs = [convert_analyzed_pr_to_fetch_format(pr) for pr in analyzed_prs]
    
    if not prs:
        logging.warning(f"⚠️  No PRs found for {username}, using default scores")
        return {
            'scores': {
                'pr_quality': 2.5,
                'comment_quality': 2.5,
                'time_taken': 2.5,
            },
            'rubric_summaries': {},
            'comprehensive_summary': {
                'tech_stack': [],
                'features': [],
                'overall_summary': f'{username} - No PRs found'
            },
            'raw_metrics': {}
        }
    
    pr_quality_scores = []
    pr_quality_details = []
    comment_quality_scores = []
    comment_quality_details = []
    all_tech_stack = set()
    time_taken_days = []
    
    # Analyze each PR
    for pr in prs:
        # Score PR quality
        if OLLAMA_AVAILABLE:
            try:
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
                time.sleep(SLEEP_SECS)
            except Exception as e:
                logging.warning(f"⚠️  Error scoring PR quality: {e}")
                pr_quality_scores.append(2.5)
        else:
            pr_quality_scores.append(2.5)
        
        # Score comment quality
        if OLLAMA_AVAILABLE:
            try:
                comment_result = llm_score_pr_comments(LLM_MODEL, pr, username)
                comment_score = comment_result["comment_quality_score_0_5"]
                comment_quality_scores.append(comment_score)
                comment_quality_details.append({
                    "pr_number": pr.get("pr_number"),
                    "pr_url": pr.get("url", ""),
                    "score": round(comment_score, 2),
                    "summary": comment_result.get("summary", ""),
                })
                time.sleep(SLEEP_SECS)
            except Exception as e:
                logging.warning(f"⚠️  Error scoring comment quality: {e}")
                comment_quality_scores.append(2.5)
        else:
            comment_quality_scores.append(2.5)
        
        # Calculate time taken
        days = calculate_pr_time_taken(pr) if OLLAMA_AVAILABLE else None
        if days is not None:
            time_taken_days.append(days)
    
    # Calculate average scores
    pr_quality_score = sum(pr_quality_scores) / len(pr_quality_scores) if pr_quality_scores else 2.5
    comment_quality_score = sum(comment_quality_scores) / len(comment_quality_scores) if comment_quality_scores else 2.5
    avg_time_taken = sum(time_taken_days) / len(time_taken_days) if time_taken_days else None
    time_taken_score = score_time_taken(avg_time_taken) if OLLAMA_AVAILABLE else 2.5
    
    # Generate summaries
    rubric_summaries = {}
    if OLLAMA_AVAILABLE:
        try:
            rubric_summaries["pr_quality"] = llm_generate_rubric_summary(
                LLM_MODEL, "pr_quality", username, pr_quality_score, prs,
                {"pr_details": pr_quality_details, "tech_stack": list(all_tech_stack)}
            )
            time.sleep(SLEEP_SECS)
            rubric_summaries["comment_quality"] = llm_generate_rubric_summary(
                LLM_MODEL, "comment_quality", username, comment_quality_score, prs,
                {"comment_details": comment_quality_details}
            )
            time.sleep(SLEEP_SECS)
            top_3_prs = sorted(prs, key=lambda p: pr_quality_scores[prs.index(p)] if prs.index(p) < len(pr_quality_scores) else 0, reverse=True)[:3]
            rubric_summaries["time_taken"] = llm_generate_rubric_summary(
                LLM_MODEL, "time_taken", username, time_taken_score, top_3_prs, {"avg_time_taken_days": avg_time_taken}
            )
            time.sleep(SLEEP_SECS)
        except Exception as e:
            logging.warning(f"⚠️  Error generating rubric summaries: {e}")
    
    # Generate comprehensive summary
    comprehensive_summary = {}
    if OLLAMA_AVAILABLE:
        try:
            comprehensive_summary = llm_generate_candidate_summary(LLM_MODEL, prs, username)
            time.sleep(SLEEP_SECS)
        except Exception as e:
            logging.warning(f"⚠️  Error generating comprehensive summary: {e}")
            comprehensive_summary = {
                "tech_stack": list(all_tech_stack)[:10],
                "features": [],
                "overall_summary": f"{username} contributed to {len(prs)} PRs.",
            }
    else:
        comprehensive_summary = {
            "tech_stack": list(all_tech_stack)[:10],
            "features": [],
            "overall_summary": f"{username} contributed to {len(prs)} PRs.",
        }
    
    return {
        'scores': {
            'pr_quality': round(pr_quality_score, 2),
            'comment_quality': round(comment_quality_score, 2),
            'time_taken': round(time_taken_score, 2),
        },
        'rubric_summaries': rubric_summaries,
        'comprehensive_summary': comprehensive_summary,
        'raw_metrics': {
            'avg_time_taken_days': round(avg_time_taken, 2) if avg_time_taken else None,
            'time_taken_prs_count': len(time_taken_days),
        }
    }


def find_top_repos_for_user(username: str, top_n: int = 3) -> List[Dict]:
    """
    Find top N repositories for a user based on stars and activity.
    Returns list of repo dicts with owner, name, stars, etc.
    """
    try:
        from services.github_service import github_request
        
        # Fetch user's repositories from GitHub API
        repos_url = f"https://api.github.com/users/{username}/repos?type=all&per_page=100&sort=updated"
        all_repos = []
        page = 1
        
        # Fetch up to 3 pages (300 repos) to find top repos
        while page <= 3:
            paginated_url = f"{repos_url}&page={page}"
            try:
                repos_response = github_request(paginated_url)
                repos = repos_response.json()
            except Exception as e:
                logging.error(f"❌ Error fetching repos page {page} for {username}: {e}")
                break
            
            if not repos:
                break
            
            all_repos.extend(repos)
            if len(repos) < 100:  # Last page
                break
            page += 1
        
        if not all_repos:
            logging.warning(f"⚠️  No repositories found for {username}")
            return []
        
        # Sort by stars (descending), then by updated_at
        repos_sorted = sorted(
            all_repos,
            key=lambda r: (r.get('stargazers_count', 0), r.get('updated_at', '')),
            reverse=True
        )
        
        top_repos = repos_sorted[:top_n]
        logging.info(f"📦 Found top {len(top_repos)} repos for {username}")
        for repo in top_repos:
            logging.info(f"   - {repo.get('full_name')} ({repo.get('stargazers_count', 0)} stars)")
        
        return top_repos
    except Exception as e:
        logging.warning(f"⚠️  Error fetching repos for {username}: {e}")
        return []


def process_candidate_from_csv(username: str) -> Optional[Dict]:
    """
    Process a single candidate from CSV.
    Gets top 3 PRs from their overall profile (same as repo-based flow), analyzes them, then calculates git score.
    """
    try:
        # Quick bot check
        if is_bot_user(username):
            logging.warning(f"🤖 Skipping bot user: {username}")
            return None
        
        # Get top 3 PRs from user's overall profile (same as repo-based flow)
        logging.info(f"📦 Getting top 3 PRs for {username} from their overall profile...")
        top_3_analyzed_prs = get_top_3_prs_for_user(username)
        
        # Find top 3 repos for storing in MongoDB
        logging.info(f"🔍 Finding top 3 repos for {username}...")
        top_repos = find_top_repos_for_user(username, top_n=3)
        
        if not top_3_analyzed_prs:
            logging.warning(f"⚠️  No PRs found for {username}, will use profile metrics only")
        
        # Analyze top 3 PRs (get agent metrics) - same flow as repo-based
        candidate_data = {}
        if top_3_analyzed_prs:
            logging.info(f"🔍 Analyzing top 3 PRs for {username}...")
            candidate_data = analyze_prs_for_candidate(username, top_3_analyzed_prs)
        else:
            # No PRs found, use defaults
            candidate_data = {
                'scores': {'pr_quality': None, 'comment_quality': None, 'time_taken': None},
                'rubric_summaries': {},
                'comprehensive_summary': {'tech_stack': [], 'features': [], 'overall_summary': ''},
                'raw_metrics': {}
            }
        
        # Extract agent metrics
        agent_metrics = extract_agent_metrics(candidate_data)
        logging.info(f"Agent metrics: comment_quality={agent_metrics.get('comment_quality')}, "
                    f"pr_quality={agent_metrics.get('pr_quality')}, "
                    f"time_taken={agent_metrics.get('time_taken')}")
        
        # Fetch personal profile metrics
        logging.info("Fetching personal GitHub profile metrics...")
        profile_metrics = fetch_user_profile_metrics(username)
        logging.info(f"Profile metrics: total_prs_merged={profile_metrics['total_prs_merged']}, "
                    f"avg_prs_per_week={profile_metrics['avg_prs_per_week']}, "
                    f"consistency_score={profile_metrics['consistency_score']}, "
                    f"num_repos={profile_metrics['num_repos']}, "
                    f"tech_stack_count={len(profile_metrics.get('tech_stack', []))}")
        
        # Calculate git score
        logging.info("Calculating git score...")
        git_score_result = calculate_git_score(profile_metrics, agent_metrics)
        logging.info(f"Git score: {git_score_result['git_score']}/100")
        logging.info(f"Breakdown: {git_score_result['breakdown']}")
        
        # Prepare comprehensive data for MongoDB
        comprehensive_summary = candidate_data.get('comprehensive_summary', {})
        rubric_summaries = candidate_data.get('rubric_summaries', {})
        
        # Use tech_stack from GitHub profile (all repos) instead of just from analyzed PRs
        tech_stack_list = profile_metrics.get('tech_stack', [])
        features_list = comprehensive_summary.get('features', [])
        overall_summary_text = comprehensive_summary.get('overall_summary', '')
        
        # Extract personal details
        personal_details = profile_metrics.get('personal_details', {})
        
        mongodb_data = {
            # Basic info
            'github_username': username,
            'github_profile_url': f'https://github.com/{username}',
            
            # Git score
            'git_score': git_score_result['git_score'],
            
            # Agent scores
            'pr_quality': git_score_result['breakdown']['pr_quality'],
            'comment_quality': git_score_result['breakdown']['comment_quality'],
            'time_taken': git_score_result['breakdown']['time_taken'],
            
            # Agent summaries
            'pr_quality_summary': rubric_summaries.get('pr_quality', ''),
            'comment_quality_summary': rubric_summaries.get('comment_quality', ''),
            'time_taken_summary': rubric_summaries.get('time_taken', ''),
            
            # Comprehensive summary
            'tech_stack': tech_stack_list,
            'features': features_list,
            'overall_summary': overall_summary_text,
            
            # Profile metrics
            'pr_merged_total': profile_metrics['total_prs_merged'],
            'avg_pr_merge_rate_per_week': profile_metrics['avg_prs_per_week'],
            'consistency_score': profile_metrics['consistency_score'],
            'num_repos': profile_metrics['num_repos'],
            'contribution_heatmap': profile_metrics.get('contribution_heatmap', {}),
            
            # Personal details
            'email': personal_details.get('email'),
            'portfolio_url': personal_details.get('portfolio') or personal_details.get('website'),
            'twitter_url': personal_details.get('twitter') or personal_details.get('x_com'),
            'linkedin_url': personal_details.get('linkedin'),
            'location': personal_details.get('location'),
            
            # Display name (default to username, can be updated later)
            'display_name': username,
            
            # Status and workflow (for table display)
            'status': 'available',  # available, interviewing, onboarded, contracted
            'workflow': {
                'emailSent': 'pending',  # pending, sent, opened
                'testSent': 'pending',   # pending, sent, completed, passed, failed
                'interview': 'pending',  # pending, scheduled, completed
                'interviewResult': 'pending'  # pending, pass, fail, strong_pass
            },
            
            # Top repos info
            'top_repos': [
                {
                    'name': repo.get('name'),
                    'full_name': repo.get('full_name'),
                    'stars': repo.get('stargazers_count', 0),
                    'url': repo.get('html_url'),
                }
                for repo in top_repos
            ]
        }
        
        # Store in MongoDB
        logging.info("Storing in MongoDB...")
        mongodb_result = upsert_expert(username, mongodb_data)
        
        if mongodb_result:
            logging.info(f"✅ Successfully processed {username}")
        else:
            logging.warning(f"⚠️  Failed to store {username} in MongoDB (but calculation succeeded)")
        
        return {
            'username': username,
            'git_score': git_score_result['git_score'],
            'breakdown': git_score_result['breakdown'],
            'profile_metrics': profile_metrics,
            'agent_metrics': agent_metrics,
            'top_repos': top_repos,
            'mongodb_stored': mongodb_result is not None
        }
        
    except ValueError as e:
        if "bot account" in str(e).lower():
            logging.warning(f"🤖 Skipping bot user: {username}")
            return None
        else:
            logging.error(f"❌ Error processing {username}: {e}", exc_info=True)
            return None
    except Exception as e:
        logging.error(f"❌ Error processing {username}: {e}", exc_info=True)
        return None


def process_candidates_from_csv(csv_file: str, limit: int = 10) -> Dict:
    """
    Process candidates from CSV file.
    Reads usernames, gets top 3 PRs for each, analyzes them, calculates scores.
    """
    usernames = read_candidates_from_csv(csv_file, limit)
    
    if not usernames:
        logging.error("❌ No usernames found in CSV file")
        return {
            'processed': 0,
            'failed': 0,
            'skipped_bots': 0,
            'results': []
        }
    
    results = []
    processed = 0
    failed = 0
    skipped_bots = 0
    
    total_candidates = len(usernames)
    logging.info(f"Processing {total_candidates} candidates from CSV...")
    
    for idx, username in enumerate(usernames, 1):
        logging.info("")
        logging.info("="*80)
        logging.info(f"[{idx}/{total_candidates}] Processing candidate: {username}")
        logging.info("="*80)
        
        try:
            result = process_candidate_from_csv(username)
            if result:
                results.append(result)
                processed += 1
            else:
                skipped_bots += 1
        except Exception as e:
            logging.error(f"❌ Error processing {username}: {e}", exc_info=True)
            failed += 1
            continue
    
    return {
        'processed': processed,
        'failed': failed,
        'skipped_bots': skipped_bots,
        'results': results
    }


def main():
    if len(sys.argv) < 2:
        print("usage: calculate_git_scores.py <input_file> [--csv]")
        print("  input_file: candidates_summary.json (JSON) or candidates.csv (CSV)")
        print("  --csv: Process as CSV file (reads Username column, limit 10)")
        sys.exit(1)
    
    input_file = sys.argv[1]
    is_csv = '--csv' in sys.argv
    
    if not Path(input_file).exists():
        logging.error(f"File not found: {input_file}")
        sys.exit(1)
    
    # Check for required environment variables
    if not os.getenv('GITHUB_TOKEN'):
        logging.error("GITHUB_TOKEN environment variable is required")
        sys.exit(1)
    
    logging.info("="*80)
    logging.info("Starting git score calculation")
    logging.info(f"Input file: {input_file}")
    logging.info(f"Input type: {'CSV' if is_csv else 'JSON'}")
    logging.info("="*80)
    
    # Process candidates
    if is_csv:
        result = process_candidates_from_csv(input_file, limit=10)
    else:
        result = process_candidates(input_file)
    
    logging.info("")
    logging.info("="*80)
    logging.info("✅ PROCESS COMPLETE")
    logging.info("="*80)
    logging.info(f"Processed: {result['processed']}")
    logging.info(f"Failed: {result['failed']}")
    logging.info(f"Skipped bots: {result.get('skipped_bots', 0)}")
    logging.info("="*80)
    
    # Save results to JSON file
    output_file = Path(input_file).parent / "git_scores_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    logging.info(f"Results saved to: {output_file}")

    # Populate social/contact links (email, LinkedIn, portfolio) for every expert and store in DB
    usernames = [r.get('username') for r in result.get('results', []) if r.get('username')]
    if usernames:
        try:
            from services.email_populator_service import populate_contacts_for_usernames
            logging.info("")
            logging.info("="*80)
            logging.info("Populating contact info (email, LinkedIn, portfolio) for every profile...")
            logging.info("="*80)
            pop_result = populate_contacts_for_usernames(
                usernames,
                github_token=os.getenv('GITHUB_TOKEN'),
                use_selenium=False,
                only_if_missing_email=False,
            )
            logging.info(f"Contact populator: updated={pop_result['updated']} skipped={pop_result['skipped']} errors={pop_result['errors']}")
            for line in pop_result.get('details', [])[:20]:
                logging.info(f"  {line}")
            if len(pop_result.get('details', [])) > 20:
                logging.info(f"  ... and {len(pop_result['details']) - 20} more")
            logging.info("="*80)
        except Exception as e:
            logging.warning(f"Contact populator failed (experts already stored): {e}")


if __name__ == "__main__":
    main()
