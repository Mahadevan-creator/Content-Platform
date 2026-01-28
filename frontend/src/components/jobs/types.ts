export interface Job {
  id: string;
  title: string;
  description: string;
  guidelines: string;
  guidelinesUrl?: string;
  githubPrUrl?: string;
  award: number;
  skills: string[];
  dueDate: string; // ISO date string
  category: 'review' | 'testing' | 'feature' | 'bugfix' | 'documentation';
  status: 'open' | 'in_progress' | 'completed';
  checklist: ChecklistItem[];
  repoName: string;
  repoUrl: string;
  createdAt: string;
}

export interface ChecklistItem {
  id: string;
  label: string;
  completed: boolean;
}
