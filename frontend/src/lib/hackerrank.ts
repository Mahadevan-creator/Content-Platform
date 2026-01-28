// HackerRank API service for scheduling interviews

export interface HackerRankInterviewer {
  email: string;
  name: string;
  full_name: string;
}

export interface HackerRankCandidate {
  email: string;
  name: string;
  uuid?: string;
}

export interface CreateInterviewRequest {
  title: string;
  candidate: HackerRankCandidate;
  interviewers: HackerRankInterviewer[];
  from: string; // ISO 8601 datetime
  to: string; // ISO 8601 datetime
  notes?: string;
  timezone?: string;
  interview_template_id?: string | null;
  quickpad?: boolean;
  resume_url?: string;
  result_url?: string;
}

export interface HackerRankInterviewResponse {
  id: string;
  status: string;
  created_at: string;
  updated_at: string;
  title: string;
  feedback: string | null;
  notes: string | null;
  metadata: Record<string, any>;
  quickpad: boolean;
  ended_at: string | null;
  timezone: string | null;
  interview_template_id: string | null;
  from: string;
  to: string;
  url: string;
  user: number;
  thumbs_up: boolean | null;
  resume_url: string | null;
  interviewers: HackerRankInterviewer[];
  candidate: HackerRankCandidate;
  result_url: string | null;
  report_url: string;
  scorecard_id: string | null;
}

/**
 * Get HackerRank API token from environment
 */
function getHackerRankToken(): string | null {
  // Vite only exposes env vars prefixed with VITE_ to the frontend
  return import.meta.env.VITE_HACKERRANK_TOKEN || null;
}

/**
 * Create an interview in HackerRank
 */
export async function createHackerRankInterview(
  request: CreateInterviewRequest
): Promise<HackerRankInterviewResponse> {
  const token = getHackerRankToken();
  
  if (!token) {
    throw new Error('HackerRank API token not configured. Please set VITE_HACKERRANK_TOKEN in your .env file.');
  }

  // Log the request for debugging (without sensitive data)
  console.log('Creating HackerRank interview:', {
    title: request.title,
    candidate: request.candidate.email,
    interviewers: request.interviewers.map(i => i.email),
    from: request.from,
    to: request.to,
  });

  const response = await fetch('https://www.hackerrank.com/x/api/v3/interviews', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(request),
  });

  const responseText = await response.text();
  
  if (!response.ok) {
    let errorMessage = `HackerRank API error: ${response.status} ${response.statusText}`;
    
    try {
      const errorJson = JSON.parse(responseText);
      if (errorJson.message || errorJson.error) {
        errorMessage = errorJson.message || errorJson.error;
      }
      // Log full error for debugging
      console.error('HackerRank API error:', errorJson);
    } catch {
      // If parsing fails, use the raw error text if available
      if (responseText) {
        errorMessage = responseText;
      }
      console.error('HackerRank API error (raw):', responseText);
    }
    
    throw new Error(errorMessage);
  }

  let interviewResponse: HackerRankInterviewResponse;
  try {
    interviewResponse = JSON.parse(responseText);
  } catch (e) {
    console.error('Failed to parse HackerRank response:', responseText);
    throw new Error('Invalid response from HackerRank API');
  }

  // Log successful response
  console.log('HackerRank interview created:', {
    id: interviewResponse.id,
    status: interviewResponse.status,
    url: interviewResponse.url,
    candidate: interviewResponse.candidate.email,
    interviewers: interviewResponse.interviewers.map(i => i.email),
  });

  return interviewResponse;
}

/**
 * Convert date and time strings to ISO 8601 format for HackerRank API
 */
export function formatDateTimeForHackerRank(date: string, time: string, durationMinutes: number = 60): { from: string; to: string } {
  // Parse the date (YYYY-MM-DD) and time (HH:MM AM/PM)
  const dateObj = new Date(date);
  
  // Parse time string (e.g., "09:00 AM" or "02:30 PM")
  const timeMatch = time.match(/(\d+):(\d+)\s*(AM|PM)/i);
  if (!timeMatch) {
    throw new Error('Invalid time format. Expected format: HH:MM AM/PM');
  }
  
  let hours = parseInt(timeMatch[1], 10);
  const minutes = parseInt(timeMatch[2], 10);
  const ampm = timeMatch[3].toUpperCase();
  
  // Convert to 24-hour format
  if (ampm === 'PM' && hours !== 12) {
    hours += 12;
  } else if (ampm === 'AM' && hours === 12) {
    hours = 0;
  }
  
  // Set the time on the date object
  dateObj.setHours(hours, minutes, 0, 0);
  
  // Create 'from' datetime
  const from = dateObj.toISOString();
  
  // Create 'to' datetime by adding duration
  const toDate = new Date(dateObj);
  toDate.setMinutes(toDate.getMinutes() + durationMinutes);
  const to = toDate.toISOString();
  
  return { from, to };
}
