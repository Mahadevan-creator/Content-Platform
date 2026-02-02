# """
# Service to interact with MongoDB Atlas database.
# """
# import os
# from typing import Dict, Optional
# from pymongo import MongoClient
# from pymongo.collection import Collection
# from pymongo.database import Database
# from dotenv import load_dotenv

# load_dotenv()

# MONGODB_URI = os.getenv("MONGODB_URI")
# MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "content_platform")
# MONGODB_COLLECTION_NAME = os.getenv("MONGODB_COLLECTION_NAME", "experts")
# 2e9cbc9c-e10c-46d1-a486-bae30d70dbba

# private key
# -----BEGIN RSA PRIVATE KEY-----
# MIIEowIBAAKCAQEAqSyBFAZpaPne3gYtB+QynImyRwX/0Z1R6DLDn9Kx1eI+DliI
# xse2pI+H1XC6O9HXQu2+3E1Yjcn1q/YNwhFbJnjU8FcqLnreBl/P28zMDYNKo+dr
# 9Han/e3vK1qdwG+hQqVkDwmQ4vWyuoXv19oAuoJkCFb3W5Oy4/2UpVEhl0Nu/paV
# cWJBCxueJOwN2uD+AmbUev5vWcJtiQ98xr+Sk7AqnPfw5Isv/OyXcIPa6scsJEFx
# rLEMLf5dUTPGvO4ZhYegLBIGM1OAr+nn9jkKYy9ouvdCo0N5oaS2hdNDBLPanZBW
# gAxHbuHZdMafxK/VQ3gbzsGF4ReXILGjavI2ZwIDAQABAoIBAE7i0c3kr4KkAajG
# eHkVkAQusVMtGP1Fvsvn4BDGzuZNeWJ3JlCLED/sLgr5Zd4/G4G6GyXfa0uywTxO
# oFu+fCKUdbcc7i5+XMncI7D67qvebQ/A+jYknnFqYfx1ZNo3M5tAREg+zbEHoTAZ
# BJ5CqdROuRaqdu3dEa3+sTHlgyRlJ38JDrYDbwRKIuPoqdfBJSQQC1FsbWsd4v7u
# YCjyHb2KoqTf5mrOlVTaTjPMM4qLq2RD0Wd3SwILHCgmZWGMxyZ4AAqPFVm0xaju
# ZW5mi2/fgmZvto7HA+XxXMCpxLzuCUXWgLbjsbv/o3HYxQPFYxIgUK0qOHY+N1Rt
# erfO+wECgYEA/kOXTpvmoj0f32SL+hWFtxY1DlHVYJ63zrL2/xAGoUqj81xQ2m29
# wJz8Fy3XzPGSBnabkCsCcmeDd9i7uilStOkTernNXeOWnyCb45d7DdWjIX54Vae2
# 6UuhvzGxtWJc5AzrdDHzAc488xBwXFM5+J7ZIaXvhhoLKFj7VDhM+HUCgYEAqlQw
# wM9u+q97SGsI13QKnbs6wmVGjdz9op2oLiv7GRh1S37Sa1ms/5BT7T5uEhJpgPRK
# BZm8Hfxxh3y8j1Meq8Evd7hfu4nSmXhZ9adJbkq1aCiB5ksvHxrcEw5hTpVQvujW
# sFVMqvU02rgBGJUGjvnWLLXdNewejBxhNOIlN+sCgYBXulJ2WOwWhih9F2AEhXCB
# XzQnIK0SjTC2LKF0F79x3yL6UJvFAaA62O9RwAt5NtA/UqUR9QT/HCAMNcdvz9ot
# eU2zRnBJOME7XjDrMdTPTSrf35b9VsSRcfr40NiT0MBkHuEOUj2aHeKBquZZtI2H
# 7qbUKUCfcFTxMuJkiJhmEQKBgGbz/of8mesiuJTcRXrdZDFU4z5vMsc65YAuZWKL
# KPpRQ0y/unYyvRO4bFJBYwy/XlAY2Mkr1H4XgZPQfLTxG9/bJFLr+cmEk+w5x75p
# QERPGfl8SpAlr7TQameGUKDMNgM+/82TsYTANBNkFx2BrnYrYx6hSrV2JDyyRrtN
# WgvDAoGBAIsRKyT/Eif9XCwzBC7EvFu/DjgKYVqb67eq3iSp131u1+nmeq3xvvOT
# TYw5ltjPQweb1aytf9z4UNMqFLqjzBtIu7y2M+/H9XEorMQzPyEyi0f9ApH5Lgee
# C2KPvNQNmpkDWGg2iHZ6EyPlRSSGg909NOOho6jrC6KUf0Dcr5VO
# -----END RSA PRIVATE KEY-----


# _mongodb_client: Optional[MongoClient] = None
# _mongodb_db: Optional[Database] = None


# def get_mongodb_client() -> Optional[MongoClient]:
#     """Get or create MongoDB client."""
#     global _mongodb_client
    
#     if _mongodb_client is not None:
#         return _mongodb_client
    
#     if not MONGODB_URI:
#         print("⚠️  WARNING: MONGODB_URI not set. MongoDB features will be disabled.")
#         return None
    
#     try:
#         _mongodb_client = MongoClient(MONGODB_URI)
#         # Test connection
#         _mongodb_client.admin.command('ping')
#         return _mongodb_client
#     except Exception as e:
#         print(f"⚠️  WARNING: Failed to create MongoDB client: {e}")
#         return None


# def get_mongodb_collection() -> Optional[Collection]:
#     """Get MongoDB collection for experts."""
#     global _mongodb_db
    
#     client = get_mongodb_client()
#     if not client:
#         return None
    
#     if _mongodb_db is None:
#         _mongodb_db = client[MONGODB_DB_NAME]
    
#     return _mongodb_db[MONGODB_COLLECTION_NAME]


# def upsert_expert(github_username: str, data: Dict) -> Optional[Dict]:
#     """
#     Upsert expert data in MongoDB.
    
#     Args:
#         github_username: GitHub username (used as key)
#         data: Dictionary with expert data including:
#             - git_score: float
#             - git_score_breakdown: Dict with individual metric scores
#             - git_score_weights: Dict with weights for each metric
#             - total_prs: int
#             - merge_frequency: float (avg PRs per week)
#             - consistency_score: float
#             - num_repos: int
#             - agent_scores: Dict with agent-calculated scores
#             - rubric_summaries: Dict with agent summaries
#             - comprehensive_summary: Dict with tech stack and features
#             - raw_metrics: Dict with raw metrics from agent
#             - tech_stack: List[str]
#             - github_profile_url: str
#             - display_name: Optional[str]
#             - And other fields
    
#     Returns:
#         Dict with inserted/updated data or None if error
#     """
#     collection = get_mongodb_collection()
#     if collection is None:
#         print("⚠️  MongoDB client not available. Skipping database update.")
#         return None
    
#     try:
#         # Add timestamp for tracking updates
#         from datetime import datetime
#         current_time = datetime.utcnow().isoformat()
        
#         # Prepare comprehensive data for MongoDB - include all fields from data
#         mongodb_data = data.copy()
        
#         # Ensure github_username is set
#         mongodb_data['github_username'] = github_username
        
#         # Add/update timestamps
#         # Check if document already exists
#         existing_doc = collection.find_one({'github_username': github_username})
#         if existing_doc is None:
#             mongodb_data['created_at'] = current_time
#         mongodb_data['updated_at'] = current_time
        
#         # Remove None values from top-level fields only (keep nested structures even if they contain None)
#         # This preserves the structure of nested objects like agent_scores, rubric_summaries, etc.
#         cleaned_data = {}
#         for k, v in mongodb_data.items():
#             # Keep the field if it's not None, or if it's a dict/list (even if empty)
#             if v is not None or isinstance(v, (dict, list)):
#                 cleaned_data[k] = v
        
#         mongodb_data = cleaned_data
        
#         # Upsert (insert or update) using github_username as the unique identifier
#         result = collection.update_one(
#             {'github_username': github_username},
#             {'$set': mongodb_data},
#             upsert=True
#         )
        
#         if result.acknowledged:
#             # Fetch and return the updated document
#             updated_doc = collection.find_one({'github_username': github_username})
#             if updated_doc:
#                 # Convert ObjectId to string for JSON serialization
#                 if '_id' in updated_doc:
#                     updated_doc['_id'] = str(updated_doc['_id'])
#                 print(f"✅ Successfully upserted expert {github_username} to MongoDB")
#                 return updated_doc
#             else:
#                 print(f"⚠️  Upsert succeeded but could not retrieve document for {github_username}")
#                 return mongodb_data
#         else:
#             print(f"⚠️  Upsert not acknowledged for {github_username}")
#             return None
            
#     except Exception as e:
#         print(f"❌ Error upserting expert {github_username} to MongoDB: {e}")
#         return None


# def get_expert(github_username: str) -> Optional[Dict]:
#     """Get expert data from MongoDB by GitHub username."""
#     collection = get_mongodb_collection()
#     if collection is None:
#         return None
    
#     try:
#         result = collection.find_one({'github_username': github_username})
#         if result:
#             # Convert ObjectId to string for JSON serialization
#             if '_id' in result:
#                 result['_id'] = str(result['_id'])
#             return result
#         return None
#     except Exception as e:
#         print(f"❌ Error fetching expert {github_username} from MongoDB: {e}")
#         return None


# def get_expert_by_email(email: str) -> Optional[Dict]:
#     """Get expert data from MongoDB by email address."""
#     collection = get_mongodb_collection()
#     if collection is None:
#         return None
    
#     try:
#         result = collection.find_one({'email': email})
#         if result:
#             # Convert ObjectId to string for JSON serialization
#             if '_id' in result:
#                 result['_id'] = str(result['_id'])
#             return result
#         return None
#     except Exception as e:
#         print(f"❌ Error fetching expert by email {email} from MongoDB: {e}")
#         return None


# def update_expert_interview(email: str, interview_report_url: str, interview_url: str = None) -> Optional[Dict]:
#     """
#     Update expert's interview information in MongoDB.
    
#     Args:
#         email: Email address of the candidate
#         interview_report_url: URL to the interview report
#         interview_url: URL to the interview (optional)
    
#     Returns:
#         Updated document or None if error
#     """
#     collection = get_mongodb_collection()
#     if collection is None:
#         print("⚠️  MongoDB client not available. Skipping interview update.")
#         return None
    
#     try:
#         from datetime import datetime
#         current_time = datetime.utcnow().isoformat()
        
#         # Find the expert by email
#         expert = collection.find_one({'email': email})
#         if not expert:
#             print(f"⚠️  Expert with email {email} not found in MongoDB")
#             return None
        
#         # Prepare update data - handle nested workflow object properly
#         update_data = {
#             'updated_at': current_time,
#             'status': 'interviewing',
#             'interview_report_url': interview_report_url,
#         }
        
#         if interview_url:
#             update_data['interview_url'] = interview_url
        
#         # Get existing workflow or create default structure
#         existing_workflow = expert.get('workflow', {})
#         if not isinstance(existing_workflow, dict):
#             existing_workflow = {}
        
#         # Preserve all existing workflow fields and update interview status
#         # Default workflow structure if missing fields
#         if 'emailSent' not in existing_workflow:
#             existing_workflow['emailSent'] = 'pending'
#         if 'testSent' not in existing_workflow:
#             existing_workflow['testSent'] = 'pending'
#         if 'interviewResult' not in existing_workflow:
#             existing_workflow['interviewResult'] = 'pending'
        
#         # Update interview status to scheduled
#         existing_workflow['interview'] = 'scheduled'
#         update_data['workflow'] = existing_workflow
        
#         # Update the document
#         result = collection.update_one(
#             {'email': email},
#             {'$set': update_data}
#         )
        
#         if result.acknowledged and result.modified_count > 0:
#             # Fetch and return the updated document
#             updated_doc = collection.find_one({'email': email})
#             if updated_doc:
#                 # Convert ObjectId to string for JSON serialization
#                 if '_id' in updated_doc:
#                     updated_doc['_id'] = str(updated_doc['_id'])
#                 print(f"✅ Successfully updated interview info for expert with email {email}")
#                 return updated_doc
#             else:
#                 print(f"⚠️  Update succeeded but could not retrieve document for email {email}")
#                 return None
#         else:
#             print(f"⚠️  Update not acknowledged or no changes made for email {email}")
#             return None
            
#     except Exception as e:
#         print(f"❌ Error updating interview info for expert with email {email}: {e}")
#         return None


# def update_expert_interview_completion(email: str, interview_status: str, interview_result: str = None, interview_id: str = None) -> Optional[Dict]:
#     """
#     Update expert's interview completion status and result in MongoDB.
    
#     Args:
#         email: Email address of the candidate
#         interview_status: Status from HackerRank ('completed', 'in_progress', etc.)
#         interview_result: Result of the interview ('pass', 'fail', 'strong_pass', or None)
#         interview_id: HackerRank interview ID (optional, for tracking)
    
#     Returns:
#         Updated document or None if error
#     """
#     collection = get_mongodb_collection()
#     if collection is None:
#         print("⚠️  MongoDB client not available. Skipping interview completion update.")
#         return None
    
#     try:
#         from datetime import datetime
#         current_time = datetime.utcnow().isoformat()
        
#         # Find the expert by email
#         expert = collection.find_one({'email': email})
#         if not expert:
#             print(f"⚠️  Expert with email {email} not found in MongoDB")
#             return None
        
#         # Get existing workflow or create default structure
#         existing_workflow = expert.get('workflow', {})
#         if not isinstance(existing_workflow, dict):
#             existing_workflow = {}
        
#         # Preserve all existing workflow fields
#         if 'emailSent' not in existing_workflow:
#             existing_workflow['emailSent'] = 'pending'
#         if 'testSent' not in existing_workflow:
#             existing_workflow['testSent'] = 'pending'
#         if 'interviewResult' not in existing_workflow:
#             existing_workflow['interviewResult'] = 'pending'
        
#         # Update interview status based on HackerRank status ('ended' or 'completed' = done)
#         if interview_status in ('ended', 'completed'):
#             existing_workflow['interview'] = 'completed'
#             # Always update interviewResult when interview is completed (pass/fail from Yes/No, or pending)
#             existing_workflow['interviewResult'] = interview_result if interview_result else 'pending'
#         elif interview_status in ['in_progress', 'started']:
#             existing_workflow['interview'] = 'scheduled'  # Keep as scheduled if in progress
#         else:
#             # For other statuses, keep current state or default to scheduled
#             if 'interview' not in existing_workflow:
#                 existing_workflow['interview'] = 'scheduled'
        
#         # Update interview result if provided (for non-completed status updates)
#         if interview_result and interview_status not in ('ended', 'completed'):
#             existing_workflow['interviewResult'] = interview_result
#             # Update overall status based on result
#             if interview_result in ['pass', 'strong_pass']:
#                 # Keep status as 'interviewing' until manually moved to next stage
#                 pass
#             elif interview_result == 'fail':
#                 # Could optionally set status back to 'available' or keep as 'interviewing'
#                 pass
        
#         # Prepare update data
#         update_data = {
#             'updated_at': current_time,
#             'workflow': existing_workflow,
#         }
        
#         # Store interview ID if provided
#         if interview_id:
#             update_data['interview_id'] = interview_id
        
#         # Update the document
#         result = collection.update_one(
#             {'email': email},
#             {'$set': update_data}
#         )
        
#         if result.acknowledged and result.modified_count > 0:
#             # Fetch and return the updated document
#             updated_doc = collection.find_one({'email': email})
#             if updated_doc:
#                 # Convert ObjectId to string for JSON serialization
#                 if '_id' in updated_doc:
#                     updated_doc['_id'] = str(updated_doc['_id'])
#                 print(f"✅ Successfully updated interview completion for expert with email {email}: status={interview_status}, result={interview_result}")
#                 return updated_doc
#             else:
#                 print(f"⚠️  Update succeeded but could not retrieve document for email {email}")
#                 return None
#         else:
#             print(f"⚠️  Update not acknowledged or no changes made for email {email}")
#             return None
            
#     except Exception as e:
#         print(f"❌ Error updating interview completion for expert with email {email}: {e}")
#         return None


# def update_expert_assessment_completion(
#     email: str,
#     assessment_result: str,  # 'passed' or 'failed'
#     hrw_score: float,
#     test_id: str = None,
#     test_candidate_id: str = None
# ) -> Optional[Dict]:
#     """
#     Update expert's assessment (HackerRank test) completion in MongoDB.
    
#     Args:
#         email: Email address of the candidate
#         assessment_result: 'passed' (score>=75 and no plagiarism) or 'failed'
#         hrw_score: The HackerRank test score (0-100)
#         test_id: HackerRank test ID (optional, for tracking)
#         test_candidate_id: HackerRank test candidate ID (optional, for tracking)
    
#     Returns:
#         Updated document or None if error
#     """
#     collection = get_mongodb_collection()
#     if collection is None:
#         print("⚠️  MongoDB client not available. Skipping assessment completion update.")
#         return None
    
#     try:
#         from datetime import datetime
#         current_time = datetime.utcnow().isoformat()
        
#         expert = collection.find_one({'email': email})
#         if not expert:
#             print(f"⚠️  Expert with email {email} not found in MongoDB")
#             return None
        
#         existing_workflow = expert.get('workflow', {})
#         if not isinstance(existing_workflow, dict):
#             existing_workflow = {}
        
#         if 'emailSent' not in existing_workflow:
#             existing_workflow['emailSent'] = 'pending'
#         if 'interview' not in existing_workflow:
#             existing_workflow['interview'] = 'pending'
#         if 'interviewResult' not in existing_workflow:
#             existing_workflow['interviewResult'] = 'pending'
        
#         # Update testSent: 'sent' -> 'passed' or 'failed' based on assessment result
#         existing_workflow['testSent'] = assessment_result  # 'passed' or 'failed'
        
#         update_data = {
#             'updated_at': current_time,
#             'workflow': existing_workflow,
#             'hrw_score': hrw_score,
#         }
        
#         if test_id:
#             update_data['test_id'] = test_id
#         if test_candidate_id:
#             update_data['test_candidate_id'] = test_candidate_id
        
#         # If passed, keep status as 'assessment' (or could move to 'available' for next stage)
#         # If failed, keep status as 'assessment' - user can manually move if needed
#         # Don't change status here - let workflow reflect the result
        
#         result = collection.update_one(
#             {'email': email},
#             {'$set': update_data}
#         )
        
#         if result.acknowledged and result.modified_count > 0:
#             updated_doc = collection.find_one({'email': email})
#             if updated_doc:
#                 if '_id' in updated_doc:
#                     updated_doc['_id'] = str(updated_doc['_id'])
#                 print(f"✅ Updated assessment for {email}: {assessment_result} (score={hrw_score})")
#                 return updated_doc
#             return None
#         else:
#             print(f"⚠️  Update not acknowledged or no changes for {email}")
#             return None
            
#     except Exception as e:
#         print(f"❌ Error updating assessment for {email}: {e}")
#         return None
"""
Service to interact with MongoDB Atlas database.
"""
import os
from typing import Dict, List, Optional
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


def update_expert_contact(
    github_username: str,
    email: Optional[str] = None,
    linkedin_url: Optional[str] = None,
    portfolio_url: Optional[str] = None,
) -> Optional[Dict]:
    """
    Update expert's contact fields (email, linkedin_url, portfolio_url).
    Only sets fields that are passed as non-None.
    """
    collection = get_mongodb_collection()
    if collection is None:
        return None
    try:
        from datetime import datetime
        updates = {"updated_at": datetime.utcnow().isoformat()}
        if email is not None:
            updates["email"] = email
        if linkedin_url is not None:
            updates["linkedin_url"] = linkedin_url
        if portfolio_url is not None:
            updates["portfolio_url"] = portfolio_url
        if len(updates) <= 1:
            return get_expert(github_username)
        result = collection.update_one(
            {"github_username": github_username},
            {"$set": updates}
        )
        if result.matched_count:
            return get_expert(github_username)
        return None
    except Exception as e:
        print(f"❌ Error updating expert contact {github_username}: {e}")
        return None


def update_expert_from_form(form_data: Dict) -> Optional[Dict]:
    """
    Update expert by GitHub username from Google Form response data.
    Finds expert by github_username and updates name, email, phone, linkedin, tech_stack, etc.

    Form field mapping (flexible key matching):
    - Timestamp -> form_submitted_at
    - Email -> email
    - Name -> display_name
    - Phone number -> phone
    - Github Username -> used to find expert
    - Which frontend or backend technologies... -> tech_stack (parsed from text)
    - How many hours per week... -> hours_per_week
    - Where do you currently work... -> job_title / company
    - Please provide your Linkedin profile -> linkedin_url
    - When can you start? -> availability / start_date

    Args:
        form_data: Dict from Google Form (keys = question titles)

    Returns:
        Updated document or None if expert not found
    """
    collection = get_mongodb_collection()
    if collection is None:
        return None

    def _get(key_variants: List[str]) -> Optional[str]:
        for k in key_variants:
            v = form_data.get(k)
            if v is not None:
                if isinstance(v, list):
                    v = "; ".join(str(x).strip() for x in v if x)
                s = str(v).strip()
                if s:
                    return s
        # Also try case-insensitive match for any key containing the variant
        for variant in key_variants:
            vn = variant.lower().replace(" ", "").replace("?", "").replace("\n", "")
            for form_key, form_val in form_data.items():
                if form_val and (form_key == variant or form_key.lower().replace(" ", "").replace("?", "").replace("\n", "") == vn):
                    if isinstance(form_val, list):
                        form_val = "; ".join(str(x).strip() for x in form_val if x)
                    s = str(form_val).strip()
                    if s:
                        return s
        return None

    github_username = _get([
        "Github Username", "Github username", "github_username", "GitHub Username",
        "GitHub username", "github username"
    ])
    if not github_username:
        print("⚠️  Form webhook: no github_username in payload")
        return None

    expert = collection.find_one({"github_username": github_username})
    if not expert:
        print(f"⚠️  Form webhook: expert not found for github_username={github_username}")
        return None

    from datetime import datetime
    updates: Dict = {"updated_at": datetime.utcnow().isoformat()}

    email = _get(["Email", "email"])
    if email:
        updates["email"] = email

    name = _get(["Name", "name"])
    if name:
        updates["display_name"] = name

    phone = _get([
        "Phone number", "Phone Number", "phone number", "phone", "Phone"
    ])
    if phone:
        updates["phone"] = phone

    linkedin = _get([
        "Please provide your Linkedin profile", "Please provide your Linkedin profile ",
        "Linkedin profile", "LinkedIn", "linkedin_url", "LinkedIn profile"
    ])
    if linkedin:
        if linkedin and "linkedin.com" not in linkedin.lower():
            linkedin = f"https://linkedin.com/in/{linkedin}" if not linkedin.startswith("http") else linkedin
        updates["linkedin_url"] = linkedin

    tech = _get([
        "Which frontend or backend technologies are you proficient in ?",
        "Which frontend or backend technologies are you proficient in?",
        "Technologies", "tech_stack", "technologies"
    ])
    if tech:
        tech_list = [t.strip() for t in tech.replace(",", ";").split(";") if t.strip()]
        if tech_list:
            updates["tech_stack"] = tech_list

    hours = _get([
        "How many hours per week can you devote ?",
        "How many hours per week can you devote?",
        "Hours per week", "hours_per_week"
    ])
    if hours:
        updates["hours_per_week"] = hours

    job_info = _get([
        "where do you currently work ? what is your job title ?",
        "where do you currently work ? what is your job title ?\n",
        "Where do you currently work? What is your job title?",
        "Job title", "job_title", "Current work"
    ])
    if job_info:
        updates["job_title"] = job_info

    availability = _get([
        "When can you start ?", "When can you start?",
        "When can you start ?\n", "Availability", "availability", "Start date"
    ])
    if availability:
        updates["availability"] = availability

    # Always set status to responded when form is submitted
    updates["status"] = "responded"

    try:
        result = collection.update_one(
            {"github_username": github_username},
            {"$set": updates}
        )
        if result.matched_count:
            updated = collection.find_one({"github_username": github_username})
            if updated and "_id" in updated:
                updated["_id"] = str(updated["_id"])
            print(f"✅ Updated expert {github_username} from form: {list(updates.keys())}")
            return updated
        return None
    except Exception as e:
        print(f"❌ Error updating expert from form {github_username}: {e}")
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


def update_expert_email_sent(emails: List[str]) -> int:
    """
    Mark workflow.emailSent as 'sent' for experts with the given emails.
    Returns the number of experts updated.
    """
    collection = get_mongodb_collection()
    if collection is None:
        return 0
    try:
        from datetime import datetime
        updated = 0
        for email in emails:
            if not email or "@" not in str(email):
                continue
            result = collection.update_one(
                {"email": email},
                {
                    "$set": {
                        "workflow.emailSent": "sent",
                        "updated_at": datetime.utcnow().isoformat(),
                    }
                },
            )
            if result.modified_count:
                updated += 1
        if updated:
            print(f"✅ Marked emailSent=sent for {updated} expert(s)")
        return updated
    except Exception as e:
        print(f"❌ Error updating emailSent for experts: {e}")
        return 0


def update_expert_contract_sent(
    email: str,
    envelope_id: str,
) -> Optional[Dict]:
    """
    Mark workflow.contractSent as 'sent' and store DocuSign envelope ID for expert.

    Args:
        email: Email address of the candidate
        envelope_id: DocuSign envelope ID for tracking

    Returns:
        Updated document or None if error
    """
    collection = get_mongodb_collection()
    if collection is None:
        print("⚠️  MongoDB client not available. Skipping contract update.")
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
        if 'testSent' not in existing_workflow:
            existing_workflow['testSent'] = 'pending'
        if 'interview' not in existing_workflow:
            existing_workflow['interview'] = 'pending'
        if 'interviewResult' not in existing_workflow:
            existing_workflow['interviewResult'] = 'pending'

        existing_workflow['contractSent'] = 'sent'
        update_data = {
            'updated_at': current_time,
            'workflow': existing_workflow,
            'docusign_envelope_id': envelope_id,
        }

        result = collection.update_one(
            {'email': email},
            {'$set': update_data}
        )

        if result.acknowledged and result.modified_count > 0:
            updated_doc = collection.find_one({'email': email})
            if updated_doc:
                if '_id' in updated_doc:
                    updated_doc['_id'] = str(updated_doc['_id'])
                print(f"✅ Marked contractSent=sent for {email} (envelope: {envelope_id})")
                return updated_doc
            return None
        else:
            print(f"⚠️  Update not acknowledged or no changes for {email}")
            return None

    except Exception as e:
        print(f"❌ Error updating contract sent for {email}: {e}")
        return None


def get_expert_by_envelope_id(envelope_id: str) -> Optional[Dict]:
    """
    Find expert by DocuSign envelope ID.

    Args:
        envelope_id: DocuSign envelope ID stored when contract was sent

    Returns:
        Expert document or None if not found
    """
    collection = get_mongodb_collection()
    if collection is None:
        return None
    try:
        result = collection.find_one({"docusign_envelope_id": envelope_id})
        if result:
            if "_id" in result:
                result["_id"] = str(result["_id"])
            return result
        return None
    except Exception as e:
        print(f"❌ Error fetching expert by envelope_id {envelope_id}: {e}")
        return None


def update_expert_contract_status_by_envelope_id(
    envelope_id: str,
    contract_status: str,  # 'sent' | 'signed' | 'voided' | 'declined'
) -> Optional[Dict]:
    """
    Update workflow.contractSent for the expert with the given DocuSign envelope ID.

    Args:
        envelope_id: DocuSign envelope ID
        contract_status: 'sent', 'signed', 'voided', or 'declined'

    Returns:
        Updated document or None if expert not found
    """
    expert = get_expert_by_envelope_id(envelope_id)
    if not expert or not expert.get("email"):
        return None
    return update_expert_contract_status(expert["email"], contract_status)


def update_expert_contract_status(
    email: str,
    contract_status: str,  # 'sent' | 'signed' | 'voided' | 'declined'
) -> Optional[Dict]:
    """
    Update workflow.contractSent status (e.g. when DocuSign envelope is completed).
    When contract_status is 'signed', also sets status='contracted' (Result column unchanged).

    Args:
        email: Email address of the candidate
        contract_status: 'sent', 'signed', 'voided', or 'declined'

    Returns:
        Updated document or None if error
    """
    collection = get_mongodb_collection()
    if collection is None:
        return None
    try:
        from datetime import datetime
        expert = collection.find_one({"email": email})
        if not expert:
            return None
        existing_workflow = expert.get("workflow", {}) or {}
        existing_workflow["contractSent"] = contract_status

        update_fields = {
            "workflow": existing_workflow,
            "updated_at": datetime.utcnow().isoformat(),
        }
        if contract_status == "signed":
            update_fields["status"] = "contracted"

        result = collection.update_one(
            {"email": email},
            {"$set": update_fields},
        )
        if result.modified_count:
            updated = collection.find_one({"email": email})
            if updated and "_id" in updated:
                updated["_id"] = str(updated["_id"])
            print(f"✅ Updated contract status for {email}: {contract_status}")
            return updated
        return None
    except Exception as e:
        print(f"❌ Error updating contract status for {email}: {e}")
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
        
        # Update interview status based on HackerRank status ('ended' or 'completed' = done)
        if interview_status in ('ended', 'completed'):
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
        # When test fails, also set interviewResult to 'fail' so Result column shows Failed (not —)
        if assessment_result == 'failed':
            existing_workflow['interviewResult'] = 'fail'
        
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
