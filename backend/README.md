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
- **Send Email**: SMTP - see below

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

### Setting up Send Email (SMTP)

Add to `.env`:

**Microsoft 365 (@hackerrank.com):**
```
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=your.name@hackerrank.com
SMTP_PASSWORD=your_password_or_app_password
SMTP_FROM_NAME=Your Name
SMTP_FROM_TITLE=Technical Product Manager II
```

`SMTP_FROM_NAME` (optional) – display name in signatures (e.g. "Dhruvi Shah"). If unset, derived from SMTP_USER.
`SMTP_FROM_TITLE` (optional) – job title in signatures (e.g. "Technical Product Manager II").

If MFA is enabled, create an **App Password** at https://mysignins.microsoft.com/security-info → Add sign-in method → App password.

> **Note:** Some orgs disable SMTP AUTH. If you get "SmtpClientAuthentication is disabled for the Tenant", contact IT or use a transactional provider (SendGrid, Mailgun, etc.).

**Gmail (personal):**
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your_app_password
```

Use an App Password from myaccount.google.com/apppasswords (requires 2FA).

**Troubleshooting:**
1. **Test config** – `GET http://localhost:8001/api/email/test` to verify env vars.
2. **Check spam folder** – Emails often land in spam until sender reputation builds.
3. **Check backend logs** – Failure details are printed when send fails.

**Option 3: Set in your shell profile**
```bash
# Add to ~/.zshrc or ~/.bashrc
export GITHUB_TOKEN=your_token_here
```

## Background Pollers

Run these in separate terminals (or as separate processes) for interview and test status updates.

### Interview Poller
Polls HackerRank every 30 minutes for interview status. Updates MongoDB when interviews complete.
```bash
# From project root:
cd backend && python3 services/interview_poller.py

# Or if already in backend directory:
python3 services/interview_poller.py
```

### Test (Assessment) Poller
Polls HackerRank every 30 minutes for test results. Candidates with status `assessment` are checked.
- **Pass**: score >= 75 AND plagiarism is false
- **Fail**: score < 75 OR plagiarism detected
```bash
# From project root:
cd backend && python3 services/test_poller.py

# Or if already in backend directory:
python3 services/test_poller.py
```

Requires `HACKERRANK_API_KEY` in `.env`.
