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
