// API client for backend communication

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

export interface JobStatus {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  current_repo?: string | null;
  message?: string | null;
  result?: {
    repo_url?: string;
    repo_urls?: string[];
    analyses?: ContributorAnalysis[];
    processed?: number;
    failed?: number;
    skipped_bots?: number;
    results?: any[];
  } | null;
  error?: string | null;
}

export interface ContributorAnalysis {
  contributor: {
    login: string;
    id: number;
    avatar_url: string;
    contributions: number;
    html_url: string;
  };
  top_prs: Array<{
    id: number;
    number: number;
    title: string;
    score: number;
    files_changed: number;
    lines_of_code: number;
    commits_count: number;
    label_score: number;
    html_url: string;
  }>;
  total_prs: number;
}

export async function analyzeRepositories(repoUrls: string[]): Promise<JobStatus> {
  const response = await fetch(`${API_BASE_URL}/api/github/analyze-multiple`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ repo_urls: repoUrls }),
  });

  if (!response.ok) {
    throw new Error(`Failed to start analysis: ${response.statusText}`);
  }

  return response.json();
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const response = await fetch(`${API_BASE_URL}/api/github/job/${jobId}`);

  if (!response.ok) {
    throw new Error(`Failed to get job status: ${response.statusText}`);
  }

  return response.json();
}

export async function pollJobStatus(
  jobId: string,
  onProgress?: (status: JobStatus) => void,
  interval: number = 2000
): Promise<JobStatus> {
  return new Promise((resolve, reject) => {
    const poll = async () => {
      try {
        const status = await getJobStatus(jobId);
        
        if (onProgress) {
          onProgress(status);
        }

        if (status.status === 'completed') {
          resolve(status);
        } else if (status.status === 'failed') {
          reject(new Error(status.error || 'Job failed'));
        } else {
          // Continue polling
          setTimeout(poll, interval);
        }
      } catch (error) {
        reject(error);
      }
    };

    poll();
  });
}

export async function uploadCsvCandidates(file: File): Promise<JobStatus> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/api/candidates/upload-csv`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to upload CSV: ${errorText || response.statusText}`);
  }

  return response.json();
}

// HackerRank Interview API (proxied via backend)
export interface InterviewerItem {
  email: string;
  name: string;
}

export interface CandidateInfo {
  name?: string;
  email: string;
}

export interface CreateInterviewPayload {
  from?: string; // ISO datetime
  to?: string;
  title: string;
  notes?: string;
  resume_url?: string;
  interviewers?: InterviewerItem[];
  result_url?: string;
  candidate: CandidateInfo;
  send_email?: boolean;
  metadata?: Record<string, unknown>;
  interview_template_id?: number;
}

export interface CreateInterviewResponse {
  id: string;
  from?: string;
  to?: string;
  status: string;
  url: string;
  title: string;
  candidate?: { name?: string; email: string };
  report_url?: string;
  ended_at?: string;
  [key: string]: unknown;
}

export async function createInterview(payload: CreateInterviewPayload): Promise<CreateInterviewResponse> {
  const response = await fetch(`${API_BASE_URL}/api/interviews/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(typeof err.detail === 'string' ? err.detail : 'Failed to create interview');
  }

  return response.json();
}

export interface UpdateInterviewCompletionPayload {
  email: string;
  interview_id?: string;
  interview_status?: string;
  interview_result?: 'pass' | 'fail' | 'strong_pass';
}

export interface UpdateInterviewCompletionResponse {
  success: boolean;
  message: string;
  data?: any;
}

export async function updateInterviewCompletion(
  payload: UpdateInterviewCompletionPayload
): Promise<UpdateInterviewCompletionResponse> {
  const response = await fetch(`${API_BASE_URL}/api/interviews/update-completion`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(typeof err.detail === 'string' ? err.detail : 'Failed to update interview completion');
  }

  return response.json();
}

export interface CheckInterviewStatusResponse {
  success: boolean;
  interview_status: string;
  interview_result: 'pass' | 'fail' | 'strong_pass' | null;
  interview_data?: any;
  updated: boolean;
}

export async function checkInterviewStatus(email: string): Promise<CheckInterviewStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/api/interviews/check-status?email=${encodeURIComponent(email)}`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(typeof err.detail === 'string' ? err.detail : 'Failed to check interview status');
  }

  return response.json();
}

// HackerRank Test API
export interface SendTestPayload {
  test_id: string;
  candidate_email: string;
  candidate_name?: string;
  send_email?: boolean;
  test_result_url?: string;
  subject?: string;
  message?: string;
}

export interface SendTestResponse {
  success: boolean;
  message: string;
  test_link?: string;
  candidate_id?: string;
  email?: string;
}

export async function sendTestToCandidate(payload: SendTestPayload): Promise<SendTestResponse> {
  const response = await fetch(`${API_BASE_URL}/api/tests/send`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(typeof err.detail === 'string' ? err.detail : 'Failed to send test invite');
  }

  return response.json();
}
