// GitHub API service for fetching contributors and analyzing PRs

export interface GitHubLabel {
  name: string;
  color: string;
}

export interface GitHubPR {
  id: number;
  number: number;
  title: string;
  state: string;
  merged_at: string | null;
  labels: GitHubLabel[];
  user: {
    login: string;
    avatar_url: string;
  };
  commits_url: string;
  files_url: string;
  html_url: string;
  created_at: string;
  closed_at: string | null;
}

export interface PRFile {
  filename: string;
  additions: number;
  deletions: number;
  changes: number;
  status: string;
}

export interface PRCommit {
  sha: string;
  commit: {
    message: string;
    author: {
      name: string;
      date: string;
    };
  };
}

export interface AnalyzedPR extends GitHubPR {
  score: number;
  filesChanged: number;
  linesOfCode: number;
  commitsCount: number;
  labelScore: number;
  files: PRFile[];
  commits: PRCommit[];
}

export interface Contributor {
  login: string;
  id: number;
  avatar_url: string;
  contributions: number;
  html_url: string;
}

export interface ContributorAnalysis {
  contributor: Contributor;
  topPRs: AnalyzedPR[];
  totalPRs: number;
}

// Priority labels that boost PR score
const PRIORITY_LABELS = ['feature', 'high priority', 'bounty', '$', 'money', 'reward', 'points'];

/**
 * Extract owner and repo from GitHub URL
 */
export function parseRepoUrl(repoUrl: string): { owner: string; repo: string } | null {
  try {
    const url = new URL(repoUrl);
    const pathParts = url.pathname.split('/').filter(Boolean);
    
    if (pathParts.length >= 2) {
      return {
        owner: pathParts[0],
        repo: pathParts[1].replace('.git', ''),
      };
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * Get GitHub API token from environment
 */
function getGitHubToken(): string | null {
  // Vite only exposes env vars prefixed with VITE_ to the frontend
  return import.meta.env.VITE_GITHUB_TOKEN || null;
}

/**
 * Make GitHub API request with authentication
 */
async function githubRequest(url: string): Promise<any> {
  const token = getGitHubToken();
  const headers: HeadersInit = {
    'Accept': 'application/vnd.github.v3+json',
  };

  if (token) {
    headers['Authorization'] = `token ${token}`;
  }

  const response = await fetch(url, { headers });

  if (!response.ok) {
    if (response.status === 403) {
      throw new Error('GitHub API rate limit exceeded. Please add a GitHub token in your environment variables (GITHUB_TOKEN).');
    }
    if (response.status === 404) {
      throw new Error('Repository not found. Please check the repository URL.');
    }
    throw new Error(`GitHub API error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

/**
 * Fetch all pages from GitHub API (handles pagination)
 */
async function fetchAllPages<T>(url: string, perPage: number = 100): Promise<T[]> {
  const allData: T[] = [];
  let page = 1;
  let hasMore = true;

  while (hasMore) {
    const urlWithPage = `${url}${url.includes('?') ? '&' : '?'}page=${page}&per_page=${perPage}`;
    const data = await githubRequest(urlWithPage);
    
    if (Array.isArray(data)) {
      allData.push(...data);
      hasMore = data.length === perPage;
    } else {
      allData.push(data);
      hasMore = false;
    }
    
    page++;
    
    // Safety limit to prevent infinite loops
    if (page > 10) break;
  }

  return allData;
}

/**
 * Fetch top 25 contributors from a repository
 */
export async function fetchTopContributors(repoUrl: string): Promise<Contributor[]> {
  const repo = parseRepoUrl(repoUrl);
  if (!repo) {
    throw new Error('Invalid repository URL');
  }

  const url = `https://api.github.com/repos/${repo.owner}/${repo.repo}/contributors`;
  const contributors = await fetchAllPages<Contributor>(url);

  // Sort by contributions and take top 25
  return contributors
    .sort((a, b) => b.contributions - a.contributions)
    .slice(0, 25);
}

/**
 * Calculate label score for a PR
 */
function calculateLabelScore(labels: GitHubLabel[]): number {
  let score = 0;
  const labelNames = labels.map(l => l.name.toLowerCase());

  for (const priorityLabel of PRIORITY_LABELS) {
    if (labelNames.some(name => name.includes(priorityLabel.toLowerCase()))) {
      score += 10; // Each priority label adds 10 points
    }
  }

  return score;
}

/**
 * Fetch PR files and calculate metrics
 */
async function fetchPRFiles(owner: string, repo: string, prNumber: number): Promise<{ files: PRFile[]; filesChanged: number; linesOfCode: number }> {
  try {
    // Use the proper GitHub API endpoint for PR files
    const url = `https://api.github.com/repos/${owner}/${repo}/pulls/${prNumber}/files`;
    const files = await fetchAllPages<PRFile>(url);
    const filesChanged = files.length;
    const linesOfCode = files.reduce((sum, file) => sum + file.additions + file.deletions, 0);

    return { files, filesChanged, linesOfCode };
  } catch (error) {
    console.error(`Error fetching files for PR #${prNumber}:`, error);
    return { files: [], filesChanged: 0, linesOfCode: 0 };
  }
}

/**
 * Fetch PR commits
 */
async function fetchPRCommits(owner: string, repo: string, prNumber: number): Promise<{ commits: PRCommit[]; commitsCount: number }> {
  try {
    // Use the proper GitHub API endpoint for PR commits
    const url = `https://api.github.com/repos/${owner}/${repo}/pulls/${prNumber}/commits`;
    const commits = await fetchAllPages<PRCommit>(url);
    return { commits, commitsCount: commits.length };
  } catch (error) {
    console.error(`Error fetching commits for PR #${prNumber}:`, error);
    return { commits: [], commitsCount: 0 };
  }
}

/**
 * Analyze a single PR and calculate its score
 */
export async function analyzePR(pr: GitHubPR, owner: string, repo: string): Promise<AnalyzedPR> {
  // Fetch files and commits in parallel
  const [filesData, commitsData] = await Promise.all([
    fetchPRFiles(owner, repo, pr.number),
    fetchPRCommits(owner, repo, pr.number),
  ]);

  const labelScore = calculateLabelScore(pr.labels);

  // Calculate composite score
  // Weights:
  // - Label score: 40% (max 40 points if all priority labels present)
  // - Files changed: 20% (normalized, max 20 points)
  // - LOC: 20% (normalized, max 20 points)
  // - Commits: 20% (normalized, max 20 points)
  
  const filesChanged = filesData.filesChanged;
  const linesOfCode = filesData.linesOfCode;
  const commitsCount = commitsData.commitsCount;

  // Normalize metrics (using reasonable max values)
  const normalizedFiles = Math.min((filesChanged / 50) * 20, 20); // 50 files = 20 points
  const normalizedLOC = Math.min((linesOfCode / 5000) * 20, 20); // 5000 LOC = 20 points
  const normalizedCommits = Math.min((commitsCount / 20) * 20, 20); // 20 commits = 20 points

  const score = labelScore + normalizedFiles + normalizedLOC + normalizedCommits;

  return {
    ...pr,
    score,
    filesChanged,
    linesOfCode,
    commitsCount,
    labelScore,
    files: filesData.files,
    commits: commitsData.commits,
  };
}

/**
 * Fetch merged PRs for a contributor
 */
export async function fetchContributorPRs(
  owner: string,
  repo: string,
  contributorLogin: string
): Promise<GitHubPR[]> {
  // Search for merged PRs by the contributor
  const query = `repo:${owner}/${repo} author:${contributorLogin} type:pr is:merged`;
  const url = `https://api.github.com/search/issues?q=${encodeURIComponent(query)}`;
  
  try {
    const response = await githubRequest(url);
    const issues = response.items || [];

    // Convert issues to PRs (we need to fetch full PR data for files/commits)
    const prs: GitHubPR[] = [];
    
    for (const issue of issues.slice(0, 50)) { // Limit to 50 PRs per contributor
      try {
        const prUrl = `https://api.github.com/repos/${owner}/${repo}/pulls/${issue.number}`;
        const pr = await githubRequest(prUrl);
        if (pr && pr.merged_at) {
          prs.push(pr);
        }
      } catch (error) {
        console.error(`Error fetching PR #${issue.number}:`, error);
      }
    }

    return prs;
  } catch (error) {
    console.error(`Error searching PRs for ${contributorLogin}:`, error);
    return [];
  }
}

/**
 * Analyze a contributor by fetching their PRs and selecting top 3
 */
export async function analyzeContributor(
  repoUrl: string,
  contributor: Contributor
): Promise<ContributorAnalysis> {
  const repo = parseRepoUrl(repoUrl);
  if (!repo) {
    throw new Error('Invalid repository URL');
  }

  // Fetch all merged PRs for this contributor
  const prs = await fetchContributorPRs(repo.owner, repo.repo, contributor.login);

  if (prs.length === 0) {
    return {
      contributor,
      topPRs: [],
      totalPRs: 0,
    };
  }

  // Analyze all PRs
  const analyzedPRs = await Promise.all(prs.map(pr => analyzePR(pr, repo.owner, repo.repo)));

  // Sort by score and take top 3
  const topPRs = analyzedPRs
    .sort((a, b) => b.score - a.score)
    .slice(0, 3);

  return {
    contributor,
    topPRs,
    totalPRs: prs.length,
  };
}

/**
 * Analyze all contributors from a repository
 */
export async function analyzeRepositoryContributors(
  repoUrl: string
): Promise<ContributorAnalysis[]> {
  // Fetch top 25 contributors
  const contributors = await fetchTopContributors(repoUrl);

  // Analyze each contributor (with rate limiting consideration)
  const analyses: ContributorAnalysis[] = [];

  for (const contributor of contributors) {
    try {
      const analysis = await analyzeContributor(repoUrl, contributor);
      analyses.push(analysis);
      
      // Small delay to avoid hitting rate limits
      await new Promise(resolve => setTimeout(resolve, 100));
    } catch (error) {
      console.error(`Error analyzing contributor ${contributor.login}:`, error);
      // Continue with other contributors even if one fails
      analyses.push({
        contributor,
        topPRs: [],
        totalPRs: 0,
      });
    }
  }

  return analyses;
}
