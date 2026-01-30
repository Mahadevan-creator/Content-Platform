import { useState, useEffect } from 'react';

// MongoDB Expert type (matches the MongoDB document structure - flat fields only)
export interface MongoDBExpert {
  _id?: string;
  github_username: string;
  github_profile_url?: string | null;
  git_score?: number | null;
  
  // Agent scores (0-5.0 scale, each contributes 16.6% to git_score)
  pr_quality?: number | null;
  comment_quality?: number | null;
  time_taken?: number | null;
  
  // Agent summaries
  pr_quality_summary?: string | null;
  comment_quality_summary?: string | null;
  time_taken_summary?: string | null;
  
  // Comprehensive summary (flattened)
  tech_stack?: string[];
  features?: string[];
  overall_summary?: string;
  
  // Profile metrics
  pr_merged_total?: number | null;
  avg_pr_merge_rate_per_week?: number | null;
  consistency_score?: number | null;
  num_repos?: number | null;
  
  // Personal details
  email?: string | null;
  portfolio_url?: string | null;
  twitter_url?: string | null;
  linkedin_url?: string | null;
  location?: string | null;
  
  // Interview information
  interview_report_url?: string | null;
  interview_url?: string | null;
  interview_id?: string | null;
  
  // Contribution heatmap (organized by year, keys are strings in MongoDB)
  contribution_heatmap?: {
    [year: string]: Array<{
      week: number;
      day: number;
      value: number;  // 0-4 (normalized for display)
      count?: number;  // Actual contribution count
      date?: string;  // Date string (YYYY-MM-DD)
    }>;
  };
  
  // Timestamps
  created_at?: string;
  updated_at?: string;
}

type Expert = MongoDBExpert;

export interface ExpertWithDisplay extends Expert {
  name: string;
  email: string;
  role: string;
  status: 'available' | 'assessment' | 'interviewing' | 'onboarded' | 'contracted';
  skills: string[];
  rating: number;
  gitScore: number;
  workflow: {
    emailSent: 'pending' | 'sent' | 'opened';
    testSent: 'pending' | 'sent' | 'completed' | 'passed' | 'failed';
    interview: 'pending' | 'scheduled' | 'completed';
    interviewResult: 'pending' | 'pass' | 'fail' | 'strong_pass';
  };
}

export function useExperts() {
  const [experts, setExperts] = useState<ExpertWithDisplay[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const fetchExperts = async () => {
    try {
      setLoading(true);
      const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s timeout
      const response = await fetch(`${API_BASE_URL}/api/experts`, {
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`Failed to fetch experts: ${response.statusText}`);
      }

      const data = await response.json();
      const expertsData: MongoDBExpert[] = data.experts || [];

      // Transform MongoDB data to match UI format
      const transformedExperts: ExpertWithDisplay[] = expertsData.map((expert) => ({
        ...expert,
        id: expert._id || expert.github_username, // Ensure id field exists
        name: (expert as any).display_name || expert.github_username,
        email: expert.email || '',
        role: 'Developer',  // Can be updated later if needed
        status: ((expert as any).status || 'available') as 'available' | 'assessment' | 'interviewing' | 'onboarded' | 'contracted',
        skills: expert.tech_stack || [],
        rating: expert.git_score || 0,
        gitScore: expert.git_score || 0,
        workflow: (expert as any).workflow || {
          emailSent: 'pending' as const,
          testSent: 'pending' as const,
          interview: 'pending' as const,
          interviewResult: 'pending' as const,
        },
      }));

      // Sort by created_at descending (most recent first)
      transformedExperts.sort((a, b) => {
        const dateA = a.created_at ? new Date(a.created_at).getTime() : 0;
        const dateB = b.created_at ? new Date(b.created_at).getTime() : 0;
        return dateB - dateA;
      });

      setExperts(transformedExperts);
      setError(null);
    } catch (err) {
      const error = err as Error;
      const message = error.name === 'AbortError'
        ? 'Request timed out. Is the backend running on port 8001? Run: cd backend && python3 main.py'
        : error.message;
      setError(new Error(message));
      console.error('Error fetching experts:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExperts();
  }, [refreshTrigger]);

  // Listen for refresh events from other components
  useEffect(() => {
    const handleRefresh = () => {
      fetchExperts();
    };
    
    window.addEventListener('refresh-experts', handleRefresh);
    return () => {
      window.removeEventListener('refresh-experts', handleRefresh);
    };
  }, []);

  return { 
    experts, 
    loading, 
    error, 
    refetch: () => {
      setRefreshTrigger(prev => prev + 1);
    }
  };
}
