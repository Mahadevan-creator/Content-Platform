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
from services.mongodb_service import get_expert, get_mongodb_collection
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
    """Proxy to HackerRank POST /x/api/v3/interviews. Requires HACKERRANK_API_KEY in env."""
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
        return r.json()
    except req.exceptions.RequestException as e:
        detail = getattr(e, "response", None) and getattr(e.response, "text", str(e)) or str(e)
        raise HTTPException(status_code=getattr(e, "response", None) and e.response.status_code or 502, detail=detail)


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

def save_results_to_json(job_id: str, repo_url: Optional[str], result: Dict, repo_urls: Optional[List[str]] = None, csv_file: Optional[str] = None):
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
