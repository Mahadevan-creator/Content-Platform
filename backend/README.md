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
- **Send Email**: Use Brevo (no app password) or SMTP - see below

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

### Setting up Send Email (free)

**Option A - Brevo (recommended, no app password needed)**

300 free emails/day forever. Works with any account - no Gmail App Password required.

1. Sign up at https://www.brevo.com (free)
2. Go to **SMTP & API** → **API Keys** → Create
3. Add to `.env`:
```
BREVO_API_KEY=your-brevo-api-key
BREVO_FROM_EMAIL=your@email.com
```

**Option B - SMTP (Gmail, Outlook, etc.)**

Gmail requires an App Password (not available for Workspace/school accounts). If you have a personal Gmail with 2FA, create one at myaccount.google.com/apppasswords

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your_app_password
```

**Troubleshooting (email not received):**

1. **Verify sender in Brevo** – Go to Brevo dashboard → Senders & IPs → Add sender → Add your sender email → Verify with 6-digit code sent to that email.
2. **Check spam folder** – Emails often land in spam until sender reputation builds.
3. **Test config** – `GET http://localhost:8001/api/email/test` to verify env vars are loaded.
4. **Check backend logs** – Look for `📧 Sending email via Brevo` and `✅ Brevo accepted` or `❌ Brevo error`.

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
