# Content Platform Backend API

FastAPI backend for GitHub repository analysis.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file (optional but recommended):
```bash
cp .env.example .env
# Edit .env and add your GitHub token
```

3. Run the server:
```bash
python main.py
# or
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

The API will be available at `http://localhost:8001`

## API Endpoints

### POST `/api/github/analyze`
Start analysis of a single repository.

**Request:**
```json
{
  "repo_url": "https://github.com/owner/repo"
}
```

**Response:**
```json
{
  "job_id": "uuid",
  "status": "pending",
  "progress": 0.0,
  "current_repo": "https://github.com/owner/repo",
  "message": "Analysis started"
}
```

### POST `/api/github/analyze-multiple`
Start analysis of multiple repositories.

**Request:**
```json
{
  "repo_urls": [
    "https://github.com/owner/repo1",
    "https://github.com/owner/repo2"
  ]
}
```

### GET `/api/github/job/{job_id}`
Get the status of an analysis job.

**Response:**
```json
{
  "job_id": "uuid",
  "status": "processing",
  "progress": 45.5,
  "current_repo": "https://github.com/owner/repo",
  "message": "Analyzing contributor...",
  "result": null,
  "error": null
}
```

Status values: `pending`, `processing`, `completed`, `failed`

## Environment Variables

- `GITHUB_TOKEN`: GitHub personal access token (optional but **highly recommended**)

### Setting up GitHub Token

Without a token, you're limited to **60 requests/hour**. With a token, you get **5000 requests/hour**.

1. Go to https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a name (e.g., "Content Platform API")
4. Select scopes: `public_repo` (or just `repo` for private repos)
5. Click "Generate token"
6. Copy the token

**To set the token:**

**Option 1: Environment variable (recommended)**
```bash
export GITHUB_TOKEN=your_token_here
python main.py
```

**Option 2: Create a `.env` file**
```bash
# In backend/.env
GITHUB_TOKEN=your_token_here
```

Then install python-dotenv and load it in main.py (already included in requirements.txt)

**Option 3: Set in your shell profile**
```bash
# Add to ~/.zshrc or ~/.bashrc
export GITHUB_TOKEN=your_token_here
```
