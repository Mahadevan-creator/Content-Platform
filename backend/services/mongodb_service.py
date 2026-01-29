"""
Service to interact with MongoDB Atlas database.
"""
import os
from typing import Dict, Optional
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "content_platform")
MONGODB_COLLECTION_NAME = os.getenv("MONGODB_COLLECTION_NAME", "experts")

_mongodb_client: Optional[MongoClient] = None
_mongodb_db: Optional[Database] = None


def get_mongodb_client() -> Optional[MongoClient]:
    """Get or create MongoDB client."""
    global _mongodb_client
    
    if _mongodb_client is not None:
        return _mongodb_client
    
    if not MONGODB_URI:
        print("⚠️  WARNING: MONGODB_URI not set. MongoDB features will be disabled.")
        return None
    
    try:
        _mongodb_client = MongoClient(MONGODB_URI)
        # Test connection
        _mongodb_client.admin.command('ping')
        return _mongodb_client
    except Exception as e:
        print(f"⚠️  WARNING: Failed to create MongoDB client: {e}")
        return None


def get_mongodb_collection() -> Optional[Collection]:
    """Get MongoDB collection for experts."""
    global _mongodb_db
    
    client = get_mongodb_client()
    if not client:
        return None
    
    if _mongodb_db is None:
        _mongodb_db = client[MONGODB_DB_NAME]
    
    return _mongodb_db[MONGODB_COLLECTION_NAME]


def upsert_expert(github_username: str, data: Dict) -> Optional[Dict]:
    """
    Upsert expert data in MongoDB.
    
    Args:
        github_username: GitHub username (used as key)
        data: Dictionary with expert data including:
            - git_score: float
            - git_score_breakdown: Dict with individual metric scores
            - git_score_weights: Dict with weights for each metric
            - total_prs: int
            - merge_frequency: float (avg PRs per week)
            - consistency_score: float
            - num_repos: int
            - agent_scores: Dict with agent-calculated scores
            - rubric_summaries: Dict with agent summaries
            - comprehensive_summary: Dict with tech stack and features
            - raw_metrics: Dict with raw metrics from agent
            - tech_stack: List[str]
            - github_profile_url: str
            - display_name: Optional[str]
            - And other fields
    
    Returns:
        Dict with inserted/updated data or None if error
    """
    collection = get_mongodb_collection()
    if collection is None:
        print("⚠️  MongoDB client not available. Skipping database update.")
        return None
    
    try:
        # Add timestamp for tracking updates
        from datetime import datetime
        current_time = datetime.utcnow().isoformat()
        
        # Prepare comprehensive data for MongoDB - include all fields from data
        mongodb_data = data.copy()
        
        # Ensure github_username is set
        mongodb_data['github_username'] = github_username
        
        # Add/update timestamps
        # Check if document already exists
        existing_doc = collection.find_one({'github_username': github_username})
        if existing_doc is None:
            mongodb_data['created_at'] = current_time
        mongodb_data['updated_at'] = current_time
        
        # Remove None values from top-level fields only (keep nested structures even if they contain None)
        # This preserves the structure of nested objects like agent_scores, rubric_summaries, etc.
        cleaned_data = {}
        for k, v in mongodb_data.items():
            # Keep the field if it's not None, or if it's a dict/list (even if empty)
            if v is not None or isinstance(v, (dict, list)):
                cleaned_data[k] = v
        
        mongodb_data = cleaned_data
        
        # Upsert (insert or update) using github_username as the unique identifier
        result = collection.update_one(
            {'github_username': github_username},
            {'$set': mongodb_data},
            upsert=True
        )
        
        if result.acknowledged:
            # Fetch and return the updated document
            updated_doc = collection.find_one({'github_username': github_username})
            if updated_doc:
                # Convert ObjectId to string for JSON serialization
                if '_id' in updated_doc:
                    updated_doc['_id'] = str(updated_doc['_id'])
                print(f"✅ Successfully upserted expert {github_username} to MongoDB")
                return updated_doc
            else:
                print(f"⚠️  Upsert succeeded but could not retrieve document for {github_username}")
                return mongodb_data
        else:
            print(f"⚠️  Upsert not acknowledged for {github_username}")
            return None
            
    except Exception as e:
        print(f"❌ Error upserting expert {github_username} to MongoDB: {e}")
        return None


def get_expert(github_username: str) -> Optional[Dict]:
    """Get expert data from MongoDB by GitHub username."""
    collection = get_mongodb_collection()
    if collection is None:
        return None
    
    try:
        result = collection.find_one({'github_username': github_username})
        if result:
            # Convert ObjectId to string for JSON serialization
            if '_id' in result:
                result['_id'] = str(result['_id'])
            return result
        return None
    except Exception as e:
        print(f"❌ Error fetching expert {github_username} from MongoDB: {e}")
        return None


def get_expert_by_email(email: str) -> Optional[Dict]:
    """Get expert data from MongoDB by email address."""
    collection = get_mongodb_collection()
    if collection is None:
        return None
    
    try:
        result = collection.find_one({'email': email})
        if result:
            # Convert ObjectId to string for JSON serialization
            if '_id' in result:
                result['_id'] = str(result['_id'])
            return result
        return None
    except Exception as e:
        print(f"❌ Error fetching expert by email {email} from MongoDB: {e}")
        return None


def update_expert_interview(email: str, interview_report_url: str, interview_url: str = None) -> Optional[Dict]:
    """
    Update expert's interview information in MongoDB.
    
    Args:
        email: Email address of the candidate
        interview_report_url: URL to the interview report
        interview_url: URL to the interview (optional)
    
    Returns:
        Updated document or None if error
    """
    collection = get_mongodb_collection()
    if collection is None:
        print("⚠️  MongoDB client not available. Skipping interview update.")
        return None
    
    try:
        from datetime import datetime
        current_time = datetime.utcnow().isoformat()
        
        # Find the expert by email
        expert = collection.find_one({'email': email})
        if not expert:
            print(f"⚠️  Expert with email {email} not found in MongoDB")
            return None
        
        # Prepare update data - handle nested workflow object properly
        update_data = {
            'updated_at': current_time,
            'status': 'interviewing',
            'interview_report_url': interview_report_url,
        }
        
        if interview_url:
            update_data['interview_url'] = interview_url
        
        # Get existing workflow or create default structure
        existing_workflow = expert.get('workflow', {})
        if not isinstance(existing_workflow, dict):
            existing_workflow = {}
        
        # Preserve all existing workflow fields and update interview status
        # Default workflow structure if missing fields
        if 'emailSent' not in existing_workflow:
            existing_workflow['emailSent'] = 'pending'
        if 'testSent' not in existing_workflow:
            existing_workflow['testSent'] = 'pending'
        if 'interviewResult' not in existing_workflow:
            existing_workflow['interviewResult'] = 'pending'
        
        # Update interview status to scheduled
        existing_workflow['interview'] = 'scheduled'
        update_data['workflow'] = existing_workflow
        
        # Update the document
        result = collection.update_one(
            {'email': email},
            {'$set': update_data}
        )
        
        if result.acknowledged and result.modified_count > 0:
            # Fetch and return the updated document
            updated_doc = collection.find_one({'email': email})
            if updated_doc:
                # Convert ObjectId to string for JSON serialization
                if '_id' in updated_doc:
                    updated_doc['_id'] = str(updated_doc['_id'])
                print(f"✅ Successfully updated interview info for expert with email {email}")
                return updated_doc
            else:
                print(f"⚠️  Update succeeded but could not retrieve document for email {email}")
                return None
        else:
            print(f"⚠️  Update not acknowledged or no changes made for email {email}")
            return None
            
    except Exception as e:
        print(f"❌ Error updating interview info for expert with email {email}: {e}")
        return None


def update_expert_interview_completion(email: str, interview_status: str, interview_result: str = None, interview_id: str = None) -> Optional[Dict]:
    """
    Update expert's interview completion status and result in MongoDB.
    
    Args:
        email: Email address of the candidate
        interview_status: Status from HackerRank ('completed', 'in_progress', etc.)
        interview_result: Result of the interview ('pass', 'fail', 'strong_pass', or None)
        interview_id: HackerRank interview ID (optional, for tracking)
    
    Returns:
        Updated document or None if error
    """
    collection = get_mongodb_collection()
    if collection is None:
        print("⚠️  MongoDB client not available. Skipping interview completion update.")
        return None
    
    try:
        from datetime import datetime
        current_time = datetime.utcnow().isoformat()
        
        # Find the expert by email
        expert = collection.find_one({'email': email})
        if not expert:
            print(f"⚠️  Expert with email {email} not found in MongoDB")
            return None
        
        # Get existing workflow or create default structure
        existing_workflow = expert.get('workflow', {})
        if not isinstance(existing_workflow, dict):
            existing_workflow = {}
        
        # Preserve all existing workflow fields
        if 'emailSent' not in existing_workflow:
            existing_workflow['emailSent'] = 'pending'
        if 'testSent' not in existing_workflow:
            existing_workflow['testSent'] = 'pending'
        if 'interviewResult' not in existing_workflow:
            existing_workflow['interviewResult'] = 'pending'
        
        # Update interview status based on HackerRank status
        if interview_status == 'completed':
            existing_workflow['interview'] = 'completed'
        elif interview_status in ['in_progress', 'started']:
            existing_workflow['interview'] = 'scheduled'  # Keep as scheduled if in progress
        else:
            # For other statuses, keep current state or default to scheduled
            if 'interview' not in existing_workflow:
                existing_workflow['interview'] = 'scheduled'
        
        # Update interview result if provided
        if interview_result:
            existing_workflow['interviewResult'] = interview_result
            # Update overall status based on result
            if interview_result in ['pass', 'strong_pass']:
                # Keep status as 'interviewing' until manually moved to next stage
                pass
            elif interview_result == 'fail':
                # Could optionally set status back to 'available' or keep as 'interviewing'
                pass
        
        # Prepare update data
        update_data = {
            'updated_at': current_time,
            'workflow': existing_workflow,
        }
        
        # Store interview ID if provided
        if interview_id:
            update_data['interview_id'] = interview_id
        
        # Update the document
        result = collection.update_one(
            {'email': email},
            {'$set': update_data}
        )
        
        if result.acknowledged and result.modified_count > 0:
            # Fetch and return the updated document
            updated_doc = collection.find_one({'email': email})
            if updated_doc:
                # Convert ObjectId to string for JSON serialization
                if '_id' in updated_doc:
                    updated_doc['_id'] = str(updated_doc['_id'])
                print(f"✅ Successfully updated interview completion for expert with email {email}: status={interview_status}, result={interview_result}")
                return updated_doc
            else:
                print(f"⚠️  Update succeeded but could not retrieve document for email {email}")
                return None
        else:
            print(f"⚠️  Update not acknowledged or no changes made for email {email}")
            return None
            
    except Exception as e:
        print(f"❌ Error updating interview completion for expert with email {email}: {e}")
        return None


def update_expert_assessment_completion(
    email: str,
    assessment_result: str,  # 'passed' or 'failed'
    hrw_score: float,
    test_id: str = None,
    test_candidate_id: str = None
) -> Optional[Dict]:
    """
    Update expert's assessment (HackerRank test) completion in MongoDB.
    
    Args:
        email: Email address of the candidate
        assessment_result: 'passed' (score>=75 and no plagiarism) or 'failed'
        hrw_score: The HackerRank test score (0-100)
        test_id: HackerRank test ID (optional, for tracking)
        test_candidate_id: HackerRank test candidate ID (optional, for tracking)
    
    Returns:
        Updated document or None if error
    """
    collection = get_mongodb_collection()
    if collection is None:
        print("⚠️  MongoDB client not available. Skipping assessment completion update.")
        return None
    
    try:
        from datetime import datetime
        current_time = datetime.utcnow().isoformat()
        
        expert = collection.find_one({'email': email})
        if not expert:
            print(f"⚠️  Expert with email {email} not found in MongoDB")
            return None
        
        existing_workflow = expert.get('workflow', {})
        if not isinstance(existing_workflow, dict):
            existing_workflow = {}
        
        if 'emailSent' not in existing_workflow:
            existing_workflow['emailSent'] = 'pending'
        if 'interview' not in existing_workflow:
            existing_workflow['interview'] = 'pending'
        if 'interviewResult' not in existing_workflow:
            existing_workflow['interviewResult'] = 'pending'
        
        # Update testSent: 'sent' -> 'passed' or 'failed' based on assessment result
        existing_workflow['testSent'] = assessment_result  # 'passed' or 'failed'
        
        update_data = {
            'updated_at': current_time,
            'workflow': existing_workflow,
            'hrw_score': hrw_score,
        }
        
        if test_id:
            update_data['test_id'] = test_id
        if test_candidate_id:
            update_data['test_candidate_id'] = test_candidate_id
        
        # If passed, keep status as 'assessment' (or could move to 'available' for next stage)
        # If failed, keep status as 'assessment' - user can manually move if needed
        # Don't change status here - let workflow reflect the result
        
        result = collection.update_one(
            {'email': email},
            {'$set': update_data}
        )
        
        if result.acknowledged and result.modified_count > 0:
            updated_doc = collection.find_one({'email': email})
            if updated_doc:
                if '_id' in updated_doc:
                    updated_doc['_id'] = str(updated_doc['_id'])
                print(f"✅ Updated assessment for {email}: {assessment_result} (score={hrw_score})")
                return updated_doc
            return None
        else:
            print(f"⚠️  Update not acknowledged or no changes for {email}")
            return None
            
    except Exception as e:
        print(f"❌ Error updating assessment for {email}: {e}")
        return None
