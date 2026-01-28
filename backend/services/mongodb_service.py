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
