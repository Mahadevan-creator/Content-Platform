"""
Background service to poll HackerRank API for test (assessment) results.
Runs every 30 minutes and checks all candidates with status 'assessment'.
Pass criteria: score >= 75 AND plagiarism is false.
"""
import os
import time
import requests
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import MongoDB service
import sys
from pathlib import Path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from services.mongodb_service import get_mongodb_collection, update_expert_assessment_completion

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_poller.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
POLL_INTERVAL_MINUTES = 30
PASS_SCORE_THRESHOLD = 75
HACKERRANK_API_KEY = os.getenv("HACKERRANK_API_KEY")
HACKERRANK_API_BASE = os.getenv("HACKERRANK_API_BASE", "https://www.hackerrank.com").rstrip("/")


def check_test_candidate_status(test_id: str, test_candidate_id: str) -> Optional[Dict]:
    """
    Fetch test candidate status/results from HackerRank API.
    Tries GET /x/api/v3/tests/{test_id}/candidates/{candidate_id}
    """
    if not HACKERRANK_API_KEY:
        logger.error("HACKERRANK_API_KEY not configured")
        return None
    
    url = f"{HACKERRANK_API_BASE}/x/api/v3/tests/{test_id}/candidates/{test_candidate_id}"
    headers = {
        "Authorization": f"Bearer {HACKERRANK_API_KEY}",
        "Content-Type": "application/json",
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        logger.warning(f"HTTP error checking test candidate {test_id}/{test_candidate_id}: {e.response.status_code} - {e.response.text[:200]}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error checking test candidate {test_id}/{test_candidate_id}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error checking test candidate {test_id}/{test_candidate_id}: {str(e)}")
        return None


def extract_score(data: Dict) -> Optional[float]:
    """Extract score (0-100) from HackerRank API response. Handles various field names."""
    if not data:
        return None
    # Common field names for score/percentage
    for key in ('score', 'score_percentage', 'percentage', 'total_score', 'percentage_score'):
        val = data.get(key)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                pass
    # Nested: data.model or data.result
    for nested in ('model', 'result', 'data'):
        obj = data.get(nested)
        if isinstance(obj, dict):
            for key in ('score', 'score_percentage', 'percentage', 'total_score'):
                val = obj.get(key)
                if val is not None:
                    try:
                        return float(val)
                    except (TypeError, ValueError):
                        pass
    return None


def extract_plagiarism(data: Dict) -> bool:
    """
    Extract plagiarism flag from HackerRank API response.
    Returns True if plagiarism detected, False if clean.
    Handles various field names and types.
    """
    if not data:
        return False  # Assume no plagiarism if no data
    
    def is_plagiarism(val: Any) -> bool:
        if val is None:
            return False
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ('true', 'yes', '1', 'flagged', 'detected')
        if isinstance(val, (int, float)):
            return val != 0
        return False
    
    # Common field names (plagiarism_status: true = plagiarism detected)
    for key in ('plagiarism', 'plagiarism_detected', 'plagiarism_flag', 'plagiarism_detected_flag',
                'plagiarism_status', 'suspicious_activity', 'has_plagiarism', 'is_plagiarism'):
        val = data.get(key)
        if val is not None:
            return is_plagiarism(val)
    
    # Nested
    for nested in ('model', 'result', 'data', 'plagiarism_report'):
        obj = data.get(nested)
        if isinstance(obj, dict):
            for key in ('plagiarism', 'plagiarism_detected', 'flagged', 'has_plagiarism'):
                val = obj.get(key)
                if val is not None:
                    return is_plagiarism(val)
    
    return False


def is_test_completed(data: Dict) -> bool:
    """Check if test is completed (submitted) so we can read score."""
    if not data:
        return False
    # attempt_endtime present = candidate submitted the test
    if data.get('attempt_endtime'):
        return True
    status = data.get('status') or data.get('state')
    if status is not None:
        if isinstance(status, str):
            if str(status).lower() in ('completed', 'submitted', 'done', 'finished'):
                return True
        elif isinstance(status, (int, float)):
            # HackerRank uses numeric status: 7 = completed
            if int(status) == 7:
                return True
    # If we have score/percentage_score (even 0), consider it completed
    return extract_score(data) is not None


def poll_all_assessment_candidates():
    """Check all candidates with status 'assessment' and update their test results."""
    collection = get_mongodb_collection()
    if collection is None:
        logger.error("MongoDB connection not available")
        return
    
    # Pull candidates: status='assessment', have test_id and test_candidate_id (test was sent)
    query = {
        'status': 'assessment',
        'test_id': {'$exists': True, '$ne': None},
        'test_candidate_id': {'$exists': True, '$ne': None}
    }
    
    experts = list(collection.find(query))
    
    if not experts:
        logger.info("No assessment candidates found")
        return
    
    contributor_names = [e.get('display_name') or e.get('github_username') or e.get('email') or 'unknown' for e in experts]
    logger.info(f"Found {len(experts)} candidates in assessment stage: {contributor_names}")
    
    checked_count = 0
    updated_count = 0
    passed_count = 0
    failed_count = 0
    errors = []
    
    for expert in experts:
        try:
            contributor_label = expert.get('display_name') or expert.get('github_username') or expert.get('email') or 'unknown'
            test_id = str(expert.get('test_id', ''))
            test_candidate_id = str(expert.get('test_candidate_id', ''))
            email = expert.get('email')
            
            if not test_id or not test_candidate_id or not email:
                logger.warning(f"Skipping {contributor_label}: missing test_id, test_candidate_id, or email")
                continue
            
            # Skip if already passed/failed (workflow.testSent)
            workflow = expert.get('workflow', {}) or {}
            test_sent = workflow.get('testSent', '')
            if test_sent in ('passed', 'failed'):
                logger.debug(f"Skipping {contributor_label} ({email}): already {test_sent}")
                continue
            
            logger.info(f"Checking assessment: {contributor_label} ({email})")
            data = check_test_candidate_status(test_id, test_candidate_id)
            
            if not data:
                logger.warning(f"  {contributor_label}: Failed to fetch from HackerRank")
                errors.append({"email": email, "contributor": contributor_label, "error": "Failed to fetch from HackerRank"})
                continue
            
            checked_count += 1
            
            if not is_test_completed(data):
                logger.info(f"  {contributor_label}: Test not yet completed (status may be in_progress)")
                continue
            
            score = extract_score(data)
            plagiarism = extract_plagiarism(data)
            
            if score is None:
                logger.warning(f"  {contributor_label}: No score in response. Raw keys: {list(data.keys())}")
                continue
            
            # Pass: score >= 75 AND plagiarism is false
            passed = score >= PASS_SCORE_THRESHOLD and not plagiarism
            
            update_result = update_expert_assessment_completion(
                email=email,
                assessment_result='passed' if passed else 'failed',
                hrw_score=score,
                test_id=test_id,
                test_candidate_id=test_candidate_id
            )
            
            if update_result:
                updated_count += 1
                if passed:
                    passed_count += 1
                    logger.info(f"  ✅ {contributor_label}: PASSED (score={score}, no plagiarism)")
                else:
                    failed_count += 1
                    reason = "plagiarism" if plagiarism else f"score {score} < {PASS_SCORE_THRESHOLD}"
                    logger.info(f"  ✅ {contributor_label}: FAILED ({reason})")
            else:
                logger.warning(f"  {contributor_label}: Failed to update MongoDB")
                errors.append({"email": email, "contributor": contributor_label, "error": "Failed to update MongoDB"})
                
        except Exception as e:
            contributor_label = expert.get('display_name') or expert.get('github_username') or expert.get('email') or 'unknown'
            logger.error(f"Error processing assessment for {contributor_label}: {str(e)}", exc_info=True)
            errors.append({"email": expert.get('email', 'unknown'), "contributor": contributor_label, "error": str(e)})
            continue
    
    logger.info(f"Polling complete: Checked {checked_count}, Updated {updated_count} (Passed: {passed_count}, Failed: {failed_count}), Errors: {len(errors)}")
    
    if errors:
        logger.warning(f"Errors: {errors}")


def run_poller():
    """Main polling loop - runs every POLL_INTERVAL_MINUTES."""
    logger.info("=" * 80)
    logger.info("Starting Test (Assessment) Poller Service")
    logger.info(f"Poll interval: {POLL_INTERVAL_MINUTES} minutes")
    logger.info(f"Pulls candidates: status='assessment' with test_id + test_candidate_id")
    logger.info(f"Pass threshold: score >= {PASS_SCORE_THRESHOLD}, plagiarism = false")
    logger.info(f"HackerRank API Base: {HACKERRANK_API_BASE}")
    logger.info("=" * 80)
    
    if not HACKERRANK_API_KEY:
        logger.error("HACKERRANK_API_KEY not set. Poller will not work correctly.")
        return
    
    while True:
        try:
            logger.info(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting polling cycle...")
            poll_all_assessment_candidates()
            logger.info(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Polling cycle complete. Next check in {POLL_INTERVAL_MINUTES} minutes.")
        except KeyboardInterrupt:
            logger.info("Received interrupt signal. Shutting down poller...")
            break
        except Exception as e:
            logger.error(f"Unexpected error in polling cycle: {str(e)}", exc_info=True)
        
        time.sleep(POLL_INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    run_poller()
