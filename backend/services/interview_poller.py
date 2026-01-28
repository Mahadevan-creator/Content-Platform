"""
Background service to poll HackerRank API for interview status updates.
Runs every 30 minutes and checks all candidates with scheduled interviews.
"""
import os
import time
import requests
import logging
from datetime import datetime
from typing import Optional, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import MongoDB service
import sys
from pathlib import Path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from services.mongodb_service import get_mongodb_collection, update_expert_interview_completion

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('interview_poller.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
POLL_INTERVAL_MINUTES = 30
HACKERRANK_API_KEY = os.getenv("HACKERRANK_API_KEY")
HACKERRANK_API_BASE = os.getenv("HACKERRANK_API_BASE", "https://www.hackerrank.com").rstrip("/")


def check_interview_status(interview_id: str) -> Optional[Dict]:
    """Fetch interview status from HackerRank API."""
    if not HACKERRANK_API_KEY:
        logger.error("HACKERRANK_API_KEY not configured")
        return None
    
    url = f"{HACKERRANK_API_BASE}/x/api/v3/interviews/{interview_id}"
    headers = {
        "Authorization": f"Bearer {HACKERRANK_API_KEY}",
        "Content-Type": "application/json",
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error checking interview {interview_id}: {e.response.status_code} - {e.response.text}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error checking interview {interview_id}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error checking interview {interview_id}: {str(e)}")
        return None


def determine_interview_result(interview_data: Dict) -> Optional[str]:
    """Determine interview result from HackerRank data.
    
    Returns: 'pass', 'fail', or None (pending)
    """
    if not interview_data:
        return None
    
    interview_status = interview_data.get('status', 'unknown')
    if interview_status != 'completed':
        return None
    
    # thumbs_up can be: 1 (pass), 0 (fail), or None/absent (pending)
    thumbs_up = interview_data.get('thumbs_up')
    if thumbs_up == 1 or thumbs_up is True:
        return 'pass'
    elif thumbs_up == 0 or thumbs_up is False:
        return 'fail'
    else:
        return None  # Pending manual review


def poll_all_pending_interviews():
    """Check all candidates with scheduled interviews and update their status."""
    collection = get_mongodb_collection()
    if collection is None:
        logger.error("MongoDB connection not available")
        return
    
    # Find all experts with scheduled interviews
    # We check for status='interviewing' OR workflow.interview='scheduled'
    query = {
        '$or': [
            {'status': 'interviewing'},
            {'workflow.interview': 'scheduled'}
        ],
        'interview_id': {'$exists': True, '$ne': None}
    }
    
    experts_with_interviews = list(collection.find(query))
    
    if not experts_with_interviews:
        logger.info("No pending interviews found")
        return
    
    logger.info(f"Found {len(experts_with_interviews)} candidates with scheduled interviews")
    
    checked_count = 0
    updated_count = 0
    completed_count = 0
    errors = []
    
    for expert in experts_with_interviews:
        try:
            interview_id = expert.get('interview_id')
            email = expert.get('email')
            
            if not interview_id or not email:
                logger.warning(f"Skipping expert {expert.get('github_username', 'unknown')}: missing interview_id or email")
                continue
            
            # Fetch status from HackerRank
            interview_data = check_interview_status(interview_id)
            
            if not interview_data:
                errors.append({
                    "email": email,
                    "interview_id": interview_id,
                    "error": "Failed to fetch from HackerRank"
                })
                continue
            
            checked_count += 1
            
            # Extract status and determine result
            interview_status = interview_data.get('status', 'unknown')
            interview_result = determine_interview_result(interview_data)
            
            # Only update if interview is completed
            if interview_status == 'completed':
                update_result = update_expert_interview_completion(
                    email=email,
                    interview_status=interview_status,
                    interview_result=interview_result,
                    interview_id=interview_id
                )
                
                if update_result:
                    updated_count += 1
                    completed_count += 1
                    result_text = interview_result or 'pending review'
                    logger.info(f"✅ Updated {email}: Interview completed - Result: {result_text}")
                else:
                    errors.append({
                        "email": email,
                        "interview_id": interview_id,
                        "error": "Failed to update MongoDB"
                    })
            else:
                logger.debug(f"Interview {interview_id} for {email} still in status: {interview_status}")
                
        except Exception as e:
            logger.error(f"Error processing interview for {expert.get('email', 'unknown')}: {str(e)}", exc_info=True)
            errors.append({
                "email": expert.get('email', 'unknown'),
                "interview_id": expert.get('interview_id', 'unknown'),
                "error": str(e)
            })
            continue
    
    logger.info(f"Polling complete: Checked {checked_count}, Updated {updated_count} (Completed: {completed_count}), Errors: {len(errors)}")
    
    if errors:
        logger.warning(f"Errors encountered: {errors}")


def run_poller():
    """Main polling loop - runs every POLL_INTERVAL_MINUTES."""
    logger.info("=" * 80)
    logger.info("Starting Interview Status Poller Service")
    logger.info(f"Poll interval: {POLL_INTERVAL_MINUTES} minutes")
    logger.info(f"HackerRank API Base: {HACKERRANK_API_BASE}")
    logger.info("=" * 80)
    
    if not HACKERRANK_API_KEY:
        logger.error("HACKERRANK_API_KEY not set. Poller will not work correctly.")
        return
    
    while True:
        try:
            logger.info(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting polling cycle...")
            poll_all_pending_interviews()
            logger.info(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Polling cycle complete. Next check in {POLL_INTERVAL_MINUTES} minutes.")
        except KeyboardInterrupt:
            logger.info("Received interrupt signal. Shutting down poller...")
            break
        except Exception as e:
            logger.error(f"Unexpected error in polling cycle: {str(e)}", exc_info=True)
        
        # Sleep for the poll interval
        time.sleep(POLL_INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    run_poller()
