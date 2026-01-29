from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import asyncio
from datetime import datetime
import uuid
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables: backend .env first, then frontend .env as fallback
load_dotenv()
_backend_dir = Path(__file__).resolve().parent
_frontend_env = _backend_dir.parent / "frontend" / ".env"
if _frontend_env.exists():
    load_dotenv(_frontend_env)

from services.github_service import analyze_repository_contributors, get_github_token
from services.mongodb_service import get_expert, get_expert_by_email, get_mongodb_collection, update_expert_interview, update_expert_interview_completion
import logging

app = FastAPI(title="Content Platform API", version="1.0.0")

# Check for GitHub token on startup
@app.on_event("startup")
async def startup_event():
    token = get_github_token()
    if not token:
        print("\n" + "="*80)
        print("⚠️  WARNING: GITHUB_TOKEN environment variable is not set!")
        print("   Without a token, you're limited to 60 requests/hour (unauthenticated)")
        print("   With a token, you get 5000 requests/hour")
        print("   Get your token from: https://github.com/settings/tokens")
        print("   Then set it: export GITHUB_TOKEN=your_token_here")
        print("   Or create a .env file in the backend directory with: GITHUB_TOKEN=your_token_here")
        print("="*80 + "\n")
    else:
        print(f"✅ GitHub token found. API rate limit: 5000 requests/hour")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:5173", "http://127.0.0.1:8080", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for job status (in production, use Redis or database)
job_status: Dict[str, Dict] = {}

# Request/Response models
class AnalyzeRepoRequest(BaseModel):
    repo_url: str

class AnalyzeReposRequest(BaseModel):
    repo_urls: List[str]

class AddUsernamesRequest(BaseModel):
    usernames: List[str]

class JobStatusResponse(BaseModel):
    job_id: str
    status: str  # "pending", "processing", "completed", "failed"
    progress: float
    current_repo: Optional[str] = None
    message: Optional[str] = None
    result: Optional[Dict] = None
    error: Optional[str] = None

class ContributorAnalysis(BaseModel):
    contributor: Dict
    top_prs: List[Dict]
    total_prs: int

class AnalyzeRepoResponse(BaseModel):
    analyses: List[ContributorAnalysis]
    repo_url: str


# HackerRank Interview API (proxy)
class InterviewerItem(BaseModel):
    email: str
    name: str

class CandidateInfo(BaseModel):
    name: Optional[str] = None
    email: str

class CreateInterviewRequest(BaseModel):
    from_: Optional[str] = Field(None, alias="from")  # ISO datetime
    to: Optional[str] = None
    title: str
    notes: Optional[str] = None
    resume_url: Optional[str] = None
    interviewers: Optional[List[InterviewerItem]] = None
    result_url: Optional[str] = None
    candidate: CandidateInfo
    send_email: Optional[bool] = True
    metadata: Optional[Dict] = None
    interview_template_id: Optional[int] = None

    class Config:
        populate_by_name = True

@app.get("/")
async def root():
    return {"message": "Content Platform API", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/api/experts")
async def get_experts():
    """Get all experts from MongoDB"""
    try:
        collection = get_mongodb_collection()
        if collection is None:
            raise HTTPException(status_code=503, detail="MongoDB connection not available")
        
        # Fetch all experts from MongoDB
        experts = list(collection.find({}))
        
        # Convert ObjectId to string for JSON serialization
        for expert in experts:
            if '_id' in expert:
                expert['_id'] = str(expert['_id'])
        
        return {"experts": experts, "count": len(experts)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching experts: {str(e)}")

@app.get("/api/experts/{github_username}")
async def get_expert_by_username(github_username: str):
    """Get a specific expert by GitHub username"""
    try:
        expert = get_expert(github_username)
        if expert is None:
            raise HTTPException(status_code=404, detail=f"Expert with username {github_username} not found")
        return expert
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching expert: {str(e)}")

@app.post("/api/github/analyze", response_model=JobStatusResponse)
async def analyze_repository(
    request: AnalyzeRepoRequest,
    background_tasks: BackgroundTasks
):
    """Start analysis of a single repository"""
    job_id = str(uuid.uuid4())
    
    # Initialize job status
    job_status[job_id] = {
        "status": "pending",
        "progress": 0.0,
        "current_repo": request.repo_url,
        "message": "Starting analysis...",
        "result": None,
        "error": None
    }
    
    # Start background task
    background_tasks.add_task(process_repository_analysis, job_id, request.repo_url)
    
    return JobStatusResponse(
        job_id=job_id,
        status="pending",
        progress=0.0,
        current_repo=request.repo_url,
        message="Analysis started"
    )

@app.post("/api/github/analyze-multiple", response_model=JobStatusResponse)
async def analyze_repositories(
    request: AnalyzeReposRequest,
    background_tasks: BackgroundTasks
):
    """Start analysis of multiple repositories"""
    job_id = str(uuid.uuid4())
    
    # Initialize job status
    job_status[job_id] = {
        "status": "pending",
        "progress": 0.0,
        "current_repo": None,
        "message": "Starting analysis...",
        "result": None,
        "error": None,
        "repo_urls": request.repo_urls
    }
    
    # Start background task
    background_tasks.add_task(process_multiple_repositories, job_id, request.repo_urls)
    
    return JobStatusResponse(
        job_id=job_id,
        status="pending",
        progress=0.0,
        message="Analysis started"
    )

@app.get("/api/github/job/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get the status of an analysis job"""
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    status = job_status[job_id]
    return JobStatusResponse(
        job_id=job_id,
        status=status["status"],
        progress=status["progress"],
        current_repo=status.get("current_repo"),
        message=status.get("message"),
        result=status.get("result"),
        error=status.get("error")
    )

@app.post("/api/interviews/create")
@app.post("/api/interviews/create/")  # support with trailing slash
async def create_interview(request: CreateInterviewRequest):
    """Proxy to HackerRank POST /x/api/v3/interviews. Requires HACKERRANK_API_KEY in env.
    Also updates candidate's MongoDB record with interview report URL and status."""
    import requests as req
    api_key = os.getenv("HACKERRANK_API_KEY")
    base_url = (os.getenv("HACKERRANK_API_BASE") or "https://www.hackerrank.com").rstrip("/")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="HackerRank API key not configured. Set HACKERRANK_API_KEY in environment."
        )
    payload = request.model_dump(by_alias=True, exclude_none=True)
    url = f"{base_url}/x/api/v3/interviews"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        r = req.post(url, json=payload, headers=headers, timeout=30)
        r.raise_for_status()
        interview_response = r.json()
        
        # Update candidate's MongoDB record with interview information
        candidate_email = request.candidate.email
        if candidate_email and interview_response:
            # Extract report_url and interview_id from response
            report_url = interview_response.get('report_url')
            interview_url = interview_response.get('url')
            interview_id = interview_response.get('id')
            
            if report_url:
                # Update MongoDB with interview report URL, status, and interview_id
                update_result = update_expert_interview(
                    email=candidate_email,
                    interview_report_url=report_url,
                    interview_url=interview_url
                )
                # Also store interview_id for future status checks
                if update_result and interview_id:
                    collection = get_mongodb_collection()
                    if collection is not None:
                        collection.update_one(
                            {'email': candidate_email},
                            {'$set': {'interview_id': interview_id}}
                        )
                if update_result:
                    print(f"✅ Updated MongoDB record for candidate {candidate_email} with interview info (ID: {interview_id})")
                else:
                    print(f"⚠️  Failed to update MongoDB record for candidate {candidate_email}")
            else:
                print(f"⚠️  No report_url in interview response for candidate {candidate_email}")
        
        return interview_response
    except req.exceptions.RequestException as e:
        detail = getattr(e, "response", None) and getattr(e.response, "text", str(e)) or str(e)
        raise HTTPException(status_code=getattr(e, "response", None) and e.response.status_code or 502, detail=detail)


@app.get("/api/interviews/{interview_id}")
async def get_interview_status(interview_id: str):
    """Get interview status from HackerRank API by interview ID."""
    import requests as req
    api_key = os.getenv("HACKERRANK_API_KEY")
    base_url = (os.getenv("HACKERRANK_API_BASE") or "https://www.hackerrank.com").rstrip("/")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="HackerRank API key not configured. Set HACKERRANK_API_KEY in environment."
        )
    url = f"{base_url}/x/api/v3/interviews/{interview_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        r = req.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        interview_response = r.json()
        return interview_response
    except req.exceptions.RequestException as e:
        detail = getattr(e, "response", None) and getattr(e.response, "text", str(e)) or str(e)
        raise HTTPException(status_code=getattr(e, "response", None) and e.response.status_code or 502, detail=detail)


class UpdateInterviewCompletionRequest(BaseModel):
    email: str
    interview_id: Optional[str] = None
    interview_status: Optional[str] = None  # From HackerRank: 'completed', 'in_progress', etc.
    interview_result: Optional[str] = None  # 'pass', 'fail', 'strong_pass'


class SendTestRequest(BaseModel):
    test_id: str  # HackerRank test ID
    candidate_email: str
    candidate_name: Optional[str] = None
    send_email: Optional[bool] = True
    test_result_url: Optional[str] = None  # Webhook URL for test results
    subject: Optional[str] = None
    message: Optional[str] = None


@app.post("/api/interviews/update-completion")
async def update_interview_completion(request: UpdateInterviewCompletionRequest):
    """Update interview completion status and result in MongoDB.
    
    This endpoint can be called:
    1. Manually by admin to set pass/fail result
    2. By a webhook from HackerRank (if configured)
    3. By a polling job that checks interview status
    """
    try:
        # If interview_id is provided, fetch latest status from HackerRank
        interview_status = request.interview_status
        if request.interview_id and not interview_status:
            import requests as req
            api_key = os.getenv("HACKERRANK_API_KEY")
            base_url = (os.getenv("HACKERRANK_API_BASE") or "https://www.hackerrank.com").rstrip("/")
            if api_key:
                try:
                    url = f"{base_url}/x/api/v3/interviews/{request.interview_id}"
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    }
                    r = req.get(url, headers=headers, timeout=30)
                    r.raise_for_status()
                    interview_data = r.json()
                    interview_status = interview_data.get('status')
                    
                    # Determine result from HackerRank data if not provided
                    if not request.interview_result and interview_status == 'completed':
                        # Check thumbs_up field (if available) or other indicators
                        thumbs_up = interview_data.get('thumbs_up')
                        if thumbs_up is True:
                            request.interview_result = 'pass'
                        elif thumbs_up is False:
                            request.interview_result = 'fail'
                except Exception as e:
                    print(f"⚠️  Could not fetch interview status from HackerRank: {e}")
        
        # Update MongoDB with completion status and result
        update_result = update_expert_interview_completion(
            email=request.email,
            interview_status=interview_status or 'completed',
            interview_result=request.interview_result,
            interview_id=request.interview_id
        )
        
        if update_result:
            return {
                "success": True,
                "message": f"Interview completion updated for {request.email}",
                "data": update_result
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Expert with email {request.email} not found or update failed"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating interview completion: {str(e)}")


@app.get("/api/interviews/check-status")
async def check_interview_status_by_email(email: str):
    """Check interview status for a candidate by email.
    
    This endpoint:
    1. Finds the candidate in MongoDB
    2. Gets their interview_id (if stored)
    3. Fetches latest status from HackerRank
    4. Updates MongoDB with latest status and result
    
    Usage: GET /api/interviews/check-status?email=candidate@example.com
    """
    if not email:
        raise HTTPException(status_code=400, detail="Email parameter is required")
    
    try:
        # Get expert from MongoDB
        expert = get_expert_by_email(email)
        if not expert:
            raise HTTPException(status_code=404, detail=f"Expert with email {email} not found")
        
        interview_id = expert.get('interview_id')
        if not interview_id:
            raise HTTPException(
                status_code=400,
                detail=f"No interview_id found for candidate {email}. Interview may not have been created yet."
            )
        
        # Fetch status from HackerRank
        import requests as req
        api_key = os.getenv("HACKERRANK_API_KEY")
        base_url = (os.getenv("HACKERRANK_API_BASE") or "https://www.hackerrank.com").rstrip("/")
        if not api_key:
            raise HTTPException(
                status_code=503,
                detail="HackerRank API key not configured."
            )
        
        url = f"{base_url}/x/api/v3/interviews/{interview_id}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        r = req.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        interview_data = r.json()
        
        # Extract status and determine result
        interview_status = interview_data.get('status', 'unknown')
        interview_result = None
        
        # Determine result from HackerRank data
        if interview_status == 'completed':
            thumbs_up = interview_data.get('thumbs_up')
            if thumbs_up is True:
                interview_result = 'pass'
            elif thumbs_up is False:
                interview_result = 'fail'
            # If thumbs_up is None, result stays None (pending manual review)
        
        # Update MongoDB
        update_result = update_expert_interview_completion(
            email=email,
            interview_status=interview_status,
            interview_result=interview_result,
            interview_id=interview_id
        )
        
        return {
            "success": True,
            "interview_status": interview_status,
            "interview_result": interview_result,
            "interview_data": interview_data,
            "updated": update_result is not None
        }
    except HTTPException:
        raise
    except Exception as e:
        import requests as req
        if isinstance(e, req.exceptions.RequestException):
            detail = getattr(e, "response", None) and getattr(e.response, "text", str(e)) or str(e)
            raise HTTPException(status_code=getattr(e, "response", None) and e.response.status_code or 502, detail=detail)
        raise HTTPException(status_code=500, detail=f"Error checking interview status: {str(e)}")


@app.post("/api/tests/send")
async def send_test_to_candidate(request: SendTestRequest):
    """Send a HackerRank test invite to a candidate.
    
    This endpoint:
    1. Invites candidate to the test via HackerRank API
    2. Updates MongoDB with test information
    3. Updates workflow status
    """
    import requests as req
    api_key = os.getenv("HACKERRANK_API_KEY")
    base_url = (os.getenv("HACKERRANK_API_BASE") or "https://www.hackerrank.com").rstrip("/")
    
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="HackerRank API key not configured. Set HACKERRANK_API_KEY in environment."
        )
    
    # Prepare payload for HackerRank API
    payload = {
        "email": request.candidate_email,
        "send_email": request.send_email or True,
    }
    
    if request.candidate_name:
        payload["full_name"] = request.candidate_name
    
    if request.subject:
        payload["subject"] = request.subject
    
    if request.message:
        payload["message"] = request.message
    
    if request.test_result_url:
        payload["test_result_url"] = request.test_result_url
        payload["accept_result_updates"] = True
    
    url = f"{base_url}/x/api/v3/tests/{request.test_id}/candidates"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    # Log request details for debugging
    print(f"📧 Sending test invite: test_id={request.test_id}, email={request.candidate_email}")
    print(f"   URL: {url}")
    
    try:
        r = req.post(url, json=payload, headers=headers, timeout=30)
        r.raise_for_status()
        test_response = r.json()
        print(f"✅ HackerRank API response: {test_response}")
        
        # Update candidate's MongoDB record with test information
        collection = get_mongodb_collection()
        if collection is not None:
            from datetime import datetime
            current_time = datetime.utcnow().isoformat()
            
            # Get existing expert
            expert = collection.find_one({'email': request.candidate_email})
            if expert:
                # Get existing workflow or create default structure
                existing_workflow = expert.get('workflow', {})
                if not isinstance(existing_workflow, dict):
                    existing_workflow = {}
                
                # Preserve all existing workflow fields
                if 'emailSent' not in existing_workflow:
                    existing_workflow['emailSent'] = 'pending'
                if 'interview' not in existing_workflow:
                    existing_workflow['interview'] = 'pending'
                if 'interviewResult' not in existing_workflow:
                    existing_workflow['interviewResult'] = 'pending'
                
                # Update test status
                existing_workflow['testSent'] = 'sent'
                
                # Prepare update data
                # Set status to 'assessment' when test is sent (candidate is in test/assessment phase)
                update_data = {
                    'updated_at': current_time,
                    'status': 'assessment',
                    'workflow': existing_workflow,
                    'test_id': request.test_id,
                    'test_link': test_response.get('test_link'),
                    'test_candidate_id': test_response.get('id'),
                }
                
                # Update the document
                collection.update_one(
                    {'email': request.candidate_email},
                    {'$set': update_data}
                )
                print(f"✅ Updated MongoDB record for candidate {request.candidate_email} with test info")
        
        return {
            "success": True,
            "message": f"Test invite sent to {request.candidate_email}",
            "test_link": test_response.get('test_link'),
            "candidate_id": test_response.get('id'),
            "email": test_response.get('email'),
        }
    except req.exceptions.HTTPError as e:
        error_detail = f"HackerRank API error: {e.response.status_code}"
        error_text = ""
        try:
            error_text = e.response.text
            error_json = e.response.json()
            print(f"❌ HackerRank API error response: {error_json}")
            
            # Extract error message from various possible formats
            if 'errors' in error_json and isinstance(error_json['errors'], list) and len(error_json['errors']) > 0:
                # HackerRank often returns errors as a list
                error_detail = f"HackerRank API error: {error_json['errors'][0]}"
            elif 'message' in error_json:
                error_detail = f"HackerRank API error: {error_json['message']}"
            elif 'error' in error_json:
                if isinstance(error_json['error'], str):
                    error_detail = f"HackerRank API error: {error_json['error']}"
                elif isinstance(error_json['error'], dict) and 'message' in error_json['error']:
                    error_detail = f"HackerRank API error: {error_json['error']['message']}"
            else:
                error_detail = f"HackerRank API error ({e.response.status_code}): {error_text[:200]}"
        except Exception as parse_error:
            print(f"❌ HackerRank API error (raw): {error_text}")
            print(f"❌ Error parsing response: {parse_error}")
        print(f"❌ Full error: {error_detail}")
        raise HTTPException(status_code=502, detail=error_detail)
    except req.exceptions.RequestException as e:
        error_msg = f"Failed to connect to HackerRank API: {str(e)}"
        print(f"❌ Request exception: {error_msg}")
        raise HTTPException(status_code=502, detail=error_msg)
    except Exception as e:
        error_msg = f"Error sending test invite: {str(e)}"
        print(f"❌ Unexpected error: {error_msg}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_msg)


class HackerRankWebhookPayload(BaseModel):
    """Webhook payload from HackerRank when interview status changes"""
    interview_id: str
    status: str
    candidate_email: Optional[str] = None
    thumbs_up: Optional[bool] = None
    ended_at: Optional[str] = None


@app.post("/api/interviews/webhook")
async def hackerrank_webhook(payload: HackerRankWebhookPayload):
    """Webhook endpoint for HackerRank to notify when interview status changes.
    
    This endpoint can be configured in HackerRank settings to receive notifications
    when interviews are completed or status changes.
    
    If candidate_email is not provided, we'll try to find the candidate by interview_id.
    """
    try:
        interview_id = payload.interview_id
        interview_status = payload.status
        candidate_email = payload.candidate_email
        
        # If email not provided, try to find candidate by interview_id
        if not candidate_email:
            collection = get_mongodb_collection()
            if collection:
                expert = collection.find_one({'interview_id': interview_id})
                if expert:
                    candidate_email = expert.get('email')
        
        if not candidate_email:
            return {
                "success": False,
                "message": f"Could not find candidate for interview {interview_id}"
            }
        
        # Determine result from thumbs_up if status is completed
        interview_result = None
        if interview_status == 'completed':
            if payload.thumbs_up is True:
                interview_result = 'pass'
            elif payload.thumbs_up is False:
                interview_result = 'fail'
        
        # Update MongoDB
        update_result = update_expert_interview_completion(
            email=candidate_email,
            interview_status=interview_status,
            interview_result=interview_result,
            interview_id=interview_id
        )
        
        if update_result:
            return {
                "success": True,
                "message": f"Interview status updated for {candidate_email}",
                "status": interview_status,
                "result": interview_result
            }
        else:
            return {
                "success": False,
                "message": f"Failed to update interview status for {candidate_email}"
            }
    except Exception as e:
        print(f"❌ Error processing HackerRank webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing webhook: {str(e)}")


@app.post("/api/interviews/check-all-pending")
async def check_all_pending_interviews():
    """Check interview status for all candidates with scheduled interviews.
    
    This endpoint is designed to be called by a background job/cron.
    It finds all experts with:
    - interview_id set
    - workflow.interview = 'scheduled'
    
    Then checks their status from HackerRank and updates MongoDB.
    """
    try:
        collection = get_mongodb_collection()
        if collection is None:
            raise HTTPException(status_code=503, detail="MongoDB connection not available")
        
        # Find all experts with scheduled interviews
        query = {
            'interview_id': {'$exists': True, '$ne': None},
            'workflow.interview': 'scheduled'
        }
        
        experts_with_interviews = list(collection.find(query))
        
        if not experts_with_interviews:
            return {
                "success": True,
                "message": "No pending interviews found",
                "checked": 0,
                "updated": 0
            }
        
        import requests as req
        api_key = os.getenv("HACKERRANK_API_KEY")
        base_url = (os.getenv("HACKERRANK_API_BASE") or "https://www.hackerrank.com").rstrip("/")
        
        if not api_key:
            raise HTTPException(status_code=503, detail="HackerRank API key not configured")
        
        checked_count = 0
        updated_count = 0
        errors = []
        
        for expert in experts_with_interviews:
            try:
                interview_id = expert.get('interview_id')
                email = expert.get('email')
                
                if not interview_id or not email:
                    continue
                
                # Fetch status from HackerRank
                url = f"{base_url}/x/api/v3/interviews/{interview_id}"
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                
                r = req.get(url, headers=headers, timeout=30)
                r.raise_for_status()
                interview_data = r.json()
                
                # Extract status and determine result
                interview_status = interview_data.get('status', 'unknown')
                interview_result = None
                
                if interview_status == 'completed':
                    thumbs_up = interview_data.get('thumbs_up')
                    if thumbs_up is True:
                        interview_result = 'pass'
                    elif thumbs_up is False:
                        interview_result = 'fail'
                
                # Update MongoDB if status changed
                if interview_status == 'completed':
                    update_result = update_expert_interview_completion(
                        email=email,
                        interview_status=interview_status,
                        interview_result=interview_result,
                        interview_id=interview_id
                    )
                    if update_result:
                        updated_count += 1
                
                checked_count += 1
                
            except Exception as e:
                errors.append({
                    "email": expert.get('email', 'unknown'),
                    "error": str(e)
                })
                continue
        
        return {
            "success": True,
            "message": f"Checked {checked_count} interviews, updated {updated_count}",
            "checked": checked_count,
            "updated": updated_count,
            "errors": errors if errors else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking pending interviews: {str(e)}")


@app.post("/api/candidates/upload-csv", response_model=JobStatusResponse)
async def upload_csv_candidates(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """Upload CSV file with candidate usernames and process them"""
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV file")
    
    job_id = str(uuid.uuid4())
    
    # Initialize job status
    job_status[job_id] = {
        "status": "pending",
        "progress": 0.0,
        "current_repo": None,
        "message": "Starting CSV processing...",
        "result": None,
        "error": None
    }
    
    # Save uploaded file temporarily
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file_path = uploads_dir / f"candidates_{timestamp}_{job_id[:8]}.csv"
    
    try:
        # Save file
        with open(csv_file_path, 'wb') as f:
            content = await file.read()
            f.write(content)
        
        # Start background task
        background_tasks.add_task(process_csv_candidates, job_id, str(csv_file_path))
        
        return JobStatusResponse(
            job_id=job_id,
            status="pending",
            progress=0.0,
            message="CSV file uploaded, processing started"
        )
    except Exception as e:
        # Clean up file on error
        if csv_file_path.exists():
            csv_file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")


@app.post("/api/candidates/add-usernames", response_model=JobStatusResponse)
async def add_usernames_candidates(
    request: AddUsernamesRequest,
    background_tasks: BackgroundTasks = None
):
    """Add candidates by GitHub usernames - EXACT same flow as CSV and repo-based"""
    usernames = [u.strip() for u in request.usernames if u and str(u).strip()]
    if not usernames:
        raise HTTPException(status_code=400, detail="At least one username is required")
    # Limit to 10 like CSV
    usernames = usernames[:10]

    job_id = str(uuid.uuid4())
    job_status[job_id] = {
        "status": "pending",
        "progress": 0.0,
        "current_repo": None,
        "message": "Starting usernames processing...",
        "result": None,
        "error": None
    }
    background_tasks.add_task(process_usernames_candidates, job_id, usernames)
    return JobStatusResponse(
        job_id=job_id,
        status="pending",
        progress=0.0,
        message="Usernames processing started"
    )


async def process_repository_analysis(job_id: str, repo_url: str):
    """Process a single repository analysis"""
    try:
        job_status[job_id]["status"] = "processing"
        job_status[job_id]["progress"] = 10.0
        job_status[job_id]["message"] = f"Fetching contributors from {repo_url}..."
        
        # Create a progress callback
        def progress_callback(progress: float, message: str):
            update_job_progress(job_id, progress, message, repo_url)
        
        # Run the analysis (this is a blocking operation, so we run it in executor)
        loop = asyncio.get_event_loop()
        analyses = await loop.run_in_executor(
            None,
            analyze_repository_contributors,
            repo_url,
            progress_callback
        )
        
        # Convert to simplified format
        result = format_analysis_results(analyses, repo_url)
        
        # Save results to JSON file
        save_results_to_json(job_id, repo_url, result)
        
        job_status[job_id]["status"] = "completed"
        job_status[job_id]["progress"] = 100.0
        job_status[job_id]["message"] = f"Analysis completed. Found {len(analyses)} contributors."
        job_status[job_id]["result"] = result
        
    except Exception as e:
        job_status[job_id]["status"] = "failed"
        job_status[job_id]["error"] = str(e)
        job_status[job_id]["message"] = f"Analysis failed: {str(e)}"

async def process_csv_candidates(job_id: str, csv_file_path: str):
    """Process candidates from CSV file - EXACT same flow as repo-based"""
    try:
        job_status[job_id]["status"] = "processing"
        job_status[job_id]["progress"] = 10.0
        job_status[job_id]["message"] = "Reading CSV file and getting top 3 PRs for each candidate..."
        
        # Import functions dynamically to avoid circular imports
        import importlib.util
        calculate_scores_path = Path(__file__).parent / "calculate_git_scores.py"
        spec = importlib.util.spec_from_file_location("calculate_git_scores", calculate_scores_path)
        calculate_git_scores_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(calculate_git_scores_module)
        read_candidates_from_csv = calculate_git_scores_module.read_candidates_from_csv
        get_top_3_prs_for_user = calculate_git_scores_module.get_top_3_prs_for_user
        
        # Step 1: Read usernames from CSV (equivalent to getting contributors from repo)
        loop = asyncio.get_event_loop()
        usernames = await loop.run_in_executor(
            None,
            read_candidates_from_csv,
            csv_file_path,
            10  # limit to 10 candidates
        )
        
        if not usernames:
            raise ValueError("No usernames found in CSV file")
        
        job_status[job_id]["progress"] = 20.0
        job_status[job_id]["message"] = f"Found {len(usernames)} candidates. Getting top 3 PRs for each (same as repo-based flow)..."
        
        # Step 2: For each username, get top 3 PRs (EXACT same as repo-based flow)
        # This mimics analyze_contributor() which gets top 3 PRs
        # Format: { "username": { "PR_LINKS": ["url1", "url2", "url3"] } }
        result = {}
        total_candidates = len(usernames)
        
        for idx, username in enumerate(usernames):
            try:
                progress = 20 + (idx / total_candidates) * 50  # 20-70% for PR fetching
                job_status[job_id]["progress"] = progress
                job_status[job_id]["message"] = f"Getting top 3 PRs for {username} ({idx+1}/{total_candidates})..."
                
                # Get top 3 PRs (same as repo-based: analyze_contributor -> fetch_contributor_prs -> analyze_pr -> top 3)
                top_3_prs = await loop.run_in_executor(
                    None,
                    get_top_3_prs_for_user,
                    username
                )
                
                # Format PR links (EXACT same format as repo-based flow in format_analysis_results)
                pr_links = []
                for pr in top_3_prs:
                    pr_url = pr.get('html_url', '')
                    if pr_url:
                        pr_links.append(pr_url)
                
                # Format as expected by fetch_prs_from_json.py (EXACT same as repo-based)
                result[username] = {
                    "PR_LINKS": pr_links
                }
                
            except Exception as e:
                logging.warning(f"Error processing {username}: {e}")
                # Still add them with empty PR links (same as repo-based would do)
                result[username] = {
                    "PR_LINKS": []
                }
                continue
        
        job_status[job_id]["progress"] = 70.0
        job_status[job_id]["message"] = "Saving results and calling fetch_prs_from_json.py (same as repo-based flow)..."
        
        # Step 3: Save results to JSON file and call fetch_prs_from_json.py (EXACT same as repo-based flow)
        # This will:
        #   - Save JSON file
        #   - Call fetch_prs_from_json.py (which analyzes PRs with LLM and generates candidates_summary.json)
        #   - Then fetch_prs_from_json.py calls calculate_git_scores.py (which stores in MongoDB)
        save_results_to_json(job_id, None, result, None, csv_file_path)
        
        job_status[job_id]["status"] = "completed"
        job_status[job_id]["progress"] = 100.0
        job_status[job_id]["message"] = f"CSV processing completed. Found {len(usernames)} candidates. PR analysis running in background (same as repo-based flow)..."
        job_status[job_id]["result"] = {
            "total_candidates": len(usernames),
            "candidates": list(result.keys()),
            "note": "Same flow as repo-based: fetch_prs_from_json.py → calculate_git_scores.py → MongoDB"
        }
        
    except Exception as e:
        job_status[job_id]["status"] = "failed"
        job_status[job_id]["error"] = str(e)
        job_status[job_id]["message"] = f"CSV processing failed: {str(e)}"
        
        # Clean up CSV file on error
        csv_path = Path(csv_file_path)
        if csv_path.exists():
            csv_path.unlink()


async def process_usernames_candidates(job_id: str, usernames: List[str]):
    """Process candidates from GitHub usernames list - EXACT same flow as CSV and repo-based"""
    try:
        job_status[job_id]["status"] = "processing"
        job_status[job_id]["progress"] = 10.0
        job_status[job_id]["message"] = "Getting top 3 PRs for each username (same as repo-based flow)..."

        import importlib.util
        calculate_scores_path = Path(__file__).parent / "calculate_git_scores.py"
        spec = importlib.util.spec_from_file_location("calculate_git_scores", calculate_scores_path)
        calculate_git_scores_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(calculate_git_scores_module)
        get_top_3_prs_for_user = calculate_git_scores_module.get_top_3_prs_for_user

        result = {}
        total_candidates = len(usernames)
        loop = asyncio.get_event_loop()

        for idx, username in enumerate(usernames):
            try:
                progress = 10 + (idx / total_candidates) * 60
                job_status[job_id]["progress"] = progress
                job_status[job_id]["message"] = f"Getting top 3 PRs for {username} ({idx+1}/{total_candidates})..."

                top_3_prs = await loop.run_in_executor(
                    None,
                    get_top_3_prs_for_user,
                    username
                )
                pr_links = []
                for pr in top_3_prs:
                    pr_url = pr.get('html_url', '')
                    if pr_url:
                        pr_links.append(pr_url)
                result[username] = {"PR_LINKS": pr_links}
            except Exception as e:
                logging.warning(f"Error processing {username}: {e}")
                result[username] = {"PR_LINKS": []}

        job_status[job_id]["progress"] = 70.0
        job_status[job_id]["message"] = "Saving results and calling fetch_prs_from_json.py (same as repo-based flow)..."

        save_results_to_json(job_id, None, result, None, None, usernames)

        job_status[job_id]["status"] = "completed"
        job_status[job_id]["progress"] = 100.0
        job_status[job_id]["message"] = f"Usernames processing completed. Found {len(usernames)} candidates. PR analysis running in background (same as repo-based flow)..."
        job_status[job_id]["result"] = {
            "total_candidates": len(usernames),
            "candidates": list(result.keys()),
            "note": "Same flow as repo-based: fetch_prs_from_json.py → calculate_git_scores.py → MongoDB"
        }
    except Exception as e:
        job_status[job_id]["status"] = "failed"
        job_status[job_id]["error"] = str(e)
        job_status[job_id]["message"] = f"Usernames processing failed: {str(e)}"


async def process_multiple_repositories(job_id: str, repo_urls: List[str]):
    """Process multiple repository analyses"""
    try:
        job_status[job_id]["status"] = "processing"
        all_analyses = []
        
        for i, repo_url in enumerate(repo_urls):
            job_status[job_id]["current_repo"] = repo_url
            job_status[job_id]["message"] = f"Analyzing {i+1}/{len(repo_urls)}: {repo_url}"
            job_status[job_id]["progress"] = (i / len(repo_urls)) * 100
            
            # Create a progress callback for this repo
            def progress_callback(progress: float, message: str):
                total_progress = (i / len(repo_urls)) * 100 + (progress / len(repo_urls))
                update_job_progress(job_id, total_progress, message, repo_url)
            
            # Run the analysis
            loop = asyncio.get_event_loop()
            analyses = await loop.run_in_executor(
                None,
                analyze_repository_contributors,
                repo_url,
                progress_callback
            )
            
            all_analyses.extend(analyses)
        
        # Combine results in simplified format
        result = format_analysis_results(all_analyses, None, repo_urls)
        
        # Save results to JSON file
        save_results_to_json(job_id, None, result, repo_urls)
        
        job_status[job_id]["status"] = "completed"
        job_status[job_id]["progress"] = 100.0
        job_status[job_id]["message"] = f"Analysis completed. Found {len(all_analyses)} contributors from {len(repo_urls)} repositories."
        job_status[job_id]["result"] = result
        job_status[job_id]["current_repo"] = None
        
    except Exception as e:
        job_status[job_id]["status"] = "failed"
        job_status[job_id]["error"] = str(e)
        job_status[job_id]["message"] = f"Analysis failed: {str(e)}"

def update_job_progress(job_id: str, progress: float, message: str, current_repo: Optional[str] = None):
    """Update job progress (called from sync functions)"""
    if job_id in job_status:
        job_status[job_id]["progress"] = min(progress, 99.0)  # Cap at 99% until completion
        job_status[job_id]["message"] = message
        if current_repo:
            job_status[job_id]["current_repo"] = current_repo

def format_analysis_results(analyses: List[Dict], repo_url: Optional[str] = None, repo_urls: Optional[List[str]] = None) -> Dict:
    """
    Format analysis results to match fetch_prs_from_json.py input format:
    {
      "CANDIDATE_NAME": {
        "PR_LINKS": ["url1", "url2", "url3"]
      }
    }
    """
    result = {}
    
    for analysis in analyses:
        contributor = analysis.get("contributor", {})
        contributor_name = contributor.get("login", "unknown")
        top_prs = analysis.get("top_prs", [])
        
        # Extract PR links as a simple array of URLs
        pr_links = []
        for pr in top_prs:
            pr_url = pr.get("html_url", "")
            if pr_url:
                pr_links.append(pr_url)
        
        # Format as expected by fetch_prs_from_json.py
        result[contributor_name] = {
            "PR_LINKS": pr_links
        }
    
    return result

def save_results_to_json(job_id: str, repo_url: Optional[str], result: Dict, repo_urls: Optional[List[str]] = None, csv_file: Optional[str] = None, usernames_list: Optional[List[str]] = None):
    """Save analysis results to a JSON file and call fetch_prs_from_json.py"""
    try:
        # Create results directory if it doesn't exist
        results_dir = Path("results")
        results_dir.mkdir(exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if csv_file:
            # CSV input
            csv_name = Path(csv_file).stem
            filename = f"analysis_csv_{csv_name}_{timestamp}_{job_id[:8]}.json"
        elif usernames_list is not None:
            # Usernames input
            filename = f"analysis_usernames_{timestamp}_{job_id[:8]}.json"
        elif repo_url:
            # Single repo - extract repo name from URL
            repo_name = repo_url.split("/")[-1].replace(".git", "")
            filename = f"analysis_{repo_name}_{timestamp}_{job_id[:8]}.json"
        else:
            # Multiple repos
            filename = f"analysis_multiple_{timestamp}_{job_id[:8]}.json"
        
        filepath = results_dir / filename
        
        # Prepare data for JSON (remove non-serializable fields if any)
        # result is already in the format expected by fetch_prs_from_json.py
        # (dict with candidate names as keys and PR_LINKS as values)
        total_contributors = len(result) if isinstance(result, dict) else 0
        
        json_data = {
            "job_id": job_id,
            "timestamp": timestamp,
            "repo_url": repo_url,
            "repo_urls": repo_urls,
            "csv_file": csv_file,
            "usernames_list": usernames_list,
            "total_contributors": total_contributors,
            "results": result
        }
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Results saved to: {filepath.absolute()}")
        print(f"   Total contributors: {total_contributors}")
        
        # Save a version for fetch_prs_from_json.py (just the candidate data)
        fetch_prs_input_file = results_dir / f"fetch_prs_input_{timestamp}_{job_id[:8]}.json"
        with open(fetch_prs_input_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Input file for fetch_prs_from_json.py saved to: {fetch_prs_input_file.absolute()}")
        
        # Call fetch_prs_from_json.py
        print(f"\n🔄 Calling fetch_prs_from_json.py...")
        logging.info(f"🔄 [Job {job_id}] Starting fetch_prs_from_json.py with input: {fetch_prs_input_file}")
        try:
            script_path = Path(__file__).parent / "fetch_prs_from_json.py"
            if not script_path.exists():
                error_msg = f"fetch_prs_from_json.py not found at {script_path}"
                print(f"⚠️  Warning: {error_msg}")
                logging.error(f"❌ [Job {job_id}] {error_msg}")
                return
            
            # Run the script (this does deep LLM analysis of PRs)
            logging.info(f"🔄 [Job {job_id}] Executing: {script_path} {fetch_prs_input_file}")
            process = subprocess.run(
                [sys.executable, str(script_path), str(fetch_prs_input_file)],
                cwd=Path(__file__).parent,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if process.returncode == 0:
                print(f"✅ fetch_prs_from_json.py completed successfully")
                logging.info(f"✅ [Job {job_id}] fetch_prs_from_json.py completed successfully")
                if process.stdout:
                    print(f"   Output: {process.stdout[-500:]}")  # Last 500 chars
                    logging.info(f"   [Job {job_id}] fetch_prs_from_json.py output: {process.stdout[-500:]}")
                
                # After fetch_prs_from_json.py completes, automatically run calculate_git_scores.py
                # This runs in SERIES: fetch_prs_from_json.py → candidates_summary.json → calculate_git_scores.py
                print(f"\n🔄 Calculating git scores and storing in MongoDB (running automatically in series after candidates_summary.json generation)...")
                logging.info(f"🔄 [Job {job_id}] Starting calculate_git_scores.py automatically after candidates_summary.json generation")
                
                try:
                    # Find the candidates_summary.json file (output from fetch_prs_from_json.py)
                    # It's saved in the same directory as the script
                    summary_file = Path(__file__).parent / "candidates_summary.json"
                    
                    # Wait a bit for file to be fully written (in case of race condition)
                    import time
                    max_wait = 10  # Wait up to 10 seconds for file to appear
                    waited = 0
                    while not summary_file.exists() and waited < max_wait:
                        time.sleep(0.5)
                        waited += 0.5
                        logging.info(f"   [Job {job_id}] Waiting for candidates_summary.json to be created... ({waited:.1f}s)")
                    
                    if summary_file.exists():
                        logging.info(f"✅ [Job {job_id}] Found candidates_summary.json at {summary_file}, executing calculate_git_scores.py...")
                        calculate_scores_script = Path(__file__).parent / "calculate_git_scores.py"
                        if calculate_scores_script.exists():
                            # Execute the command without waiting (non-blocking)
                            cmd = [sys.executable, str(calculate_scores_script), str(summary_file)]
                            print(f"   Executing: {' '.join(cmd)}")
                            logging.info(f"🔄 [Job {job_id}] Executing command: {' '.join(cmd)}")
                            
                            # Use Popen to start the process without blocking
                            # Redirect stdout/stderr to log file to prevent hanging
                            log_file = Path(__file__).parent / "results" / f"calculate_scores_{job_id}.log"
                            log_file.parent.mkdir(exist_ok=True)
                            
                            # Open log file in append mode and keep it open (process will write to it)
                            log_f = open(log_file, "w")
                            scores_process = subprocess.Popen(
                                cmd,
                                cwd=Path(__file__).parent,
                                stdout=log_f,
                                stderr=subprocess.STDOUT,
                                text=True,
                                start_new_session=True  # Detach from parent process
                            )
                            # Don't close log_f - let the process handle it
                            
                            print(f"✅ calculate_git_scores.py started in background (PID: {scores_process.pid})")
                            print(f"   Logs: {log_file}")
                            logging.info(f"✅ [Job {job_id}] calculate_git_scores.py started in background (PID: {scores_process.pid}, log: {log_file})")
                        else:
                            error_msg = f"calculate_git_scores.py not found at {calculate_scores_script}"
                            print(f"⚠️  Warning: {error_msg}")
                            logging.error(f"❌ [Job {job_id}] {error_msg}")
                    else:
                        error_msg = f"candidates_summary.json not found at {summary_file} after waiting {waited}s"
                        print(f"⚠️  Warning: {error_msg}")
                        logging.error(f"❌ [Job {job_id}] {error_msg}")
                except subprocess.TimeoutExpired:
                    error_msg = "calculate_git_scores.py timed out after 1 hour"
                    print(f"⚠️  Warning: {error_msg}")
                    logging.error(f"❌ [Job {job_id}] {error_msg}")
                except Exception as e:
                    error_msg = f"Failed to run calculate_git_scores.py: {e}"
                    print(f"⚠️  Warning: {error_msg}")
                    logging.error(f"❌ [Job {job_id}] {error_msg}", exc_info=True)
            else:
                error_msg = f"fetch_prs_from_json.py exited with code {process.returncode}"
                print(f"⚠️  Warning: {error_msg}")
                logging.error(f"❌ [Job {job_id}] {error_msg}")
                if process.stderr:
                    print(f"   Error: {process.stderr[-500:]}")
                    logging.error(f"   [Job {job_id}] fetch_prs_from_json.py stderr: {process.stderr[-500:]}")
        except subprocess.TimeoutExpired:
            error_msg = "fetch_prs_from_json.py timed out after 1 hour"
            print(f"⚠️  Warning: {error_msg}")
            logging.error(f"❌ [Job {job_id}] {error_msg}")
        except Exception as e:
            error_msg = f"Failed to run fetch_prs_from_json.py: {e}"
            print(f"⚠️  Warning: {error_msg}")
            logging.error(f"❌ [Job {job_id}] {error_msg}", exc_info=True)
        
    except Exception as e:
        print(f"⚠️  Warning: Failed to save results to JSON file: {e}")

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8001))  # Changed default to 8001
    uvicorn.run(app, host="0.0.0.0", port=port)
