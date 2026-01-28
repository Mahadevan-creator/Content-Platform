"""
Git Score Calculator
Calculates git score based on 6 metrics:
1. Total PRs merged and avg PR merged/week over 1 year
2. Consistency (based on heatmap and contributions with penalties)
3. Comment quality (from agent JSON)
4. PR quality (from agent JSON)
5. Time taken (from agent JSON)
6. Number of repos
"""
from typing import Dict, Optional


def score_pr_activity(total_prs_merged: int, avg_prs_per_week: float) -> float:
    """
    Score PR activity based on total PRs merged and average PRs per week.
    Returns a score from 0-100.
    """
    # Score based on total PRs merged (0-100 scale)
    if total_prs_merged >= 50:
        pr_count_score = 100.0
    elif total_prs_merged >= 30:
        pr_count_score = 80.0
    elif total_prs_merged >= 20:
        pr_count_score = 70.0
    elif total_prs_merged >= 10:
        pr_count_score = 60.0
    elif total_prs_merged >= 5:
        pr_count_score = 50.0
    elif total_prs_merged >= 2:
        pr_count_score = 40.0
    elif total_prs_merged >= 1:
        pr_count_score = 30.0
    else:
        pr_count_score = 0.0
    
    # Score based on average PRs per week (0-100 scale)
    if avg_prs_per_week >= 2.0:
        frequency_score = 100.0
    elif avg_prs_per_week >= 1.0:
        frequency_score = 80.0
    elif avg_prs_per_week >= 0.5:
        frequency_score = 60.0
    elif avg_prs_per_week >= 0.25:
        frequency_score = 40.0
    elif avg_prs_per_week > 0:
        frequency_score = 20.0
    else:
        frequency_score = 0.0
    
    # Combined score (weighted: 60% count, 40% frequency)
    activity_score = (pr_count_score * 0.6) + (frequency_score * 0.4)
    return round(activity_score, 2)


def score_consistency(consistency_score: float) -> float:
    """
    Score consistency (already in 0-100 scale from calculate_consistency_score).
    Just ensure it's in valid range.
    """
    # Consistency score is already 0-100 from calculate_consistency_score
    return round(max(0.0, min(100.0, consistency_score)), 2)


def score_comment_quality(comment_quality_score: Optional[float]) -> float:
    """
    Score comment quality (convert from agent JSON 0-5.0 to 0-100 scale).
    Returns 50.0 as default if missing (equivalent to 2.5/5.0).
    """
    if comment_quality_score is None:
        return 50.0
    # Convert from 0-5.0 to 0-100
    return round(max(0.0, min(100.0, comment_quality_score * 20)), 2)


def score_pr_quality(pr_quality_score: Optional[float]) -> float:
    """
    Score PR quality (convert from agent JSON 0-5.0 to 0-100 scale).
    Returns 50.0 as default if missing (equivalent to 2.5/5.0).
    """
    if pr_quality_score is None:
        return 50.0
    # Convert from 0-5.0 to 0-100
    return round(max(0.0, min(100.0, pr_quality_score * 20)), 2)


def score_time_taken(time_taken_score: Optional[float]) -> float:
    """
    Score time taken (convert from agent JSON 0-5.0 to 0-100 scale).
    Returns 50.0 as default if missing (equivalent to 2.5/5.0).
    """
    if time_taken_score is None:
        return 50.0
    # Convert from 0-5.0 to 0-100
    return round(max(0.0, min(100.0, time_taken_score * 20)), 2)


def score_num_repos(num_repos: int) -> float:
    """
    Score based on number of repositories contributed to.
    Returns a score from 0-100.
    """
    if num_repos >= 20:
        return 100.0
    elif num_repos >= 15:
        return 90.0
    elif num_repos >= 10:
        return 80.0
    elif num_repos >= 7:
        return 70.0
    elif num_repos >= 5:
        return 60.0
    elif num_repos >= 3:
        return 50.0
    elif num_repos >= 2:
        return 40.0
    elif num_repos >= 1:
        return 30.0
    else:
        return 0.0


def calculate_git_score(
    profile_metrics: Dict,
    agent_metrics: Dict
) -> Dict:
    """
    Calculate final git score from all 6 metrics.
    
    Args:
        profile_metrics: {
            'total_prs_merged': int,
            'avg_prs_per_week': float,
            'consistency_score': float,
            'num_repos': int
        }
        agent_metrics: {
            'comment_quality': Optional[float],  # 0-5.0 (from agent, will be converted to 0-100)
            'pr_quality': Optional[float],       # 0-5.0 (from agent, will be converted to 0-100)
            'time_taken': Optional[float]        # 0-5.0 (from agent, will be converted to 0-100)
        }
    
    Returns: {
        'git_score': float,  # 0-100 (average of all 6 metrics)
        'breakdown': {
            'pr_activity': float,      # 0-100
            'consistency': float,       # 0-100
            'comment_quality': float,  # 0-100
            'pr_quality': float,        # 0-100
            'time_taken': float,        # 0-100
            'num_repos': float          # 0-100
        }
    }
    """
    # Calculate individual scores
    pr_activity_score = score_pr_activity(
        profile_metrics.get('total_prs_merged', 0),
        profile_metrics.get('avg_prs_per_week', 0.0)
    )
    consistency_score = score_consistency(
        profile_metrics.get('consistency_score', 0.0)
    )
    comment_quality_score = score_comment_quality(
        agent_metrics.get('comment_quality')
    )
    pr_quality_score = score_pr_quality(
        agent_metrics.get('pr_quality')
    )
    time_taken_score = score_time_taken(
        agent_metrics.get('time_taken')
    )
    num_repos_score = score_num_repos(
        profile_metrics.get('num_repos', 0)
    )
    
    # Calculate git score as average of all 6 metrics (each 0-100 scale)
    # With equal weights, git_score is simply the average
    git_score = (
        pr_activity_score +
        consistency_score +
        comment_quality_score +
        pr_quality_score +
        time_taken_score +
        num_repos_score
    ) / 6.0
    
    # Ensure score is between 0-100
    git_score = max(0.0, min(100.0, git_score))
    
    return {
        'git_score': round(git_score, 2),
        'breakdown': {
            'pr_activity': pr_activity_score,
            'consistency': consistency_score,
            'comment_quality': comment_quality_score,
            'pr_quality': pr_quality_score,
            'time_taken': time_taken_score,
            'num_repos': num_repos_score
        }
    }
