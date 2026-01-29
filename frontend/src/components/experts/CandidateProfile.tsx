import { useState } from 'react';
import { ArrowLeft, Github, Award, Linkedin, Twitter, Globe, GitMerge, Clock, Activity, GitPullRequest, Layers, Brain, Sparkles, TrendingUp, FileText, ClipboardCheck, ExternalLink, User, ChevronDown, ChevronRight, Mail, MapPin, MessageSquare, Code, CheckCircle } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { getGitGrade, getGradeColor, getGradeBgColor } from '@/lib/gitScore';
import ContributionHeatmap from './ContributionHeatmap';

interface CandidateProfileProps {
  expert: {
    id?: string;
    _id?: string;
    name: string;
    email: string;
    role: string;
    status: string;
    skills: string[];
    rating: number;
    gitScore?: number;
    hrwScore?: number;
    github_username?: string;
    github_profile_url?: string;
    linkedin_url?: string;
    twitter_url?: string;
    portfolio_url?: string;
    location?: string;
    pr_quality?: number | null;
    comment_quality?: number | null;
    time_taken?: number | null;
    pr_quality_summary?: string | null;
    comment_quality_summary?: string | null;
    time_taken_summary?: string | null;
    tech_stack?: string[];
    features?: string[];
    overall_summary?: string;
    pr_merged_total?: number | null;
    avg_pr_merge_rate_per_week?: number | null;
    consistency_score?: number | null;
    num_repos?: number | null;
    contribution_heatmap?: {
      [year: number]: Array<{
        week: number;
        day: number;
        value: number;  // 0-4
      }>;
    } | null;
    hrwTestReportUrl?: string;
    interviewReportUrl?: string;
    interview_report_url?: string;
    interview_url?: string;
  };
  onBack: () => void;
}

// Git score breakdown metrics
const gitScoreMetrics = [
  { icon: GitMerge, label: 'Merge Frequency', value: '4.2/week', description: 'Average merges per week' },
  { icon: Clock, label: 'Avg Task Time', value: '2.3 days', description: 'Time to complete tasks' },
  { icon: Activity, label: 'Recent Activity', value: '89%', description: 'Active in last 180 days' },
  { icon: GitPullRequest, label: 'PRs Pushed', value: '147', description: 'Total pull requests' },
  { icon: Layers, label: 'Stack Familiarity', value: '6 stacks', description: 'Technologies worked with' },
];

// Helper function to prepare radar chart data from metrics
const prepareRadarData = (metrics: any) => {
  // Calculate normalized PRs Merged (capped at 100 for 200+ PRs)
  const prsMergedValue = metrics.pr_merged_total 
    ? Math.min(100, Math.round((metrics.pr_merged_total / 200) * 100)) 
    : 0;
  
  return [
    { 
      dimension: 'PR Quality', 
      value: metrics.pr_quality ? Math.max(0, Math.min(100, Math.round(metrics.pr_quality))) : 0, 
      fullMark: 100,
      actualValue: metrics.pr_quality || 0
    },
    { 
      dimension: 'Comment Quality', 
      value: metrics.comment_quality ? Math.max(0, Math.min(100, Math.round(metrics.comment_quality))) : 0, 
      fullMark: 100,
      actualValue: metrics.comment_quality || 0
    },
    { 
      dimension: 'Code Quality', 
      value: 88, // Static value as requested
      fullMark: 100,
      actualValue: 88
    },
    { 
      dimension: 'Consistency', 
      value: metrics.consistency_score ? Math.max(0, Math.min(100, Math.round(metrics.consistency_score))) : 0, 
      fullMark: 100,
      actualValue: metrics.consistency_score || 0
    },
    { 
      dimension: 'PRs Merged', 
      value: prsMergedValue,
      fullMark: 100,
      actualValue: metrics.pr_merged_total || 0
    },
  ];
};

// Stack familiarity data
const stackFamiliarity = [
  { name: 'React', level: 95 },
  { name: 'TypeScript', level: 90 },
  { name: 'Node.js', level: 85 },
  { name: 'Python', level: 75 },
  { name: 'PostgreSQL', level: 70 },
  { name: 'AWS', level: 65 },
];

// Helper function to categorize metrics into strengths and weaknesses
const categorizeMetrics = (metrics: any, summaries: any) => {
  const strengths: Array<{ metric: string; score: number; insight: string }> = [];
  const weaknesses: Array<{ metric: string; score: number; insight: string }> = [];
  
  // Code Quality (static data)
  const codeQualityItem = {
    metric: 'Code Quality',
    score: 88,
    insight: 'Clean, maintainable code with comprehensive documentation.'
  };
  strengths.push(codeQualityItem);
  
  // PR Quality
  if (metrics.pr_quality !== undefined && metrics.pr_quality !== null) {
    const item = {
      metric: 'PR Quality',
      score: Math.round(metrics.pr_quality),
      insight: summaries.pr_quality || 'PR quality assessment based on contributions.'
    };
    if (metrics.pr_quality >= 60) {
      strengths.push(item);
    } else {
      weaknesses.push(item);
    }
  }
  
  // Comment Quality
  if (metrics.comment_quality !== undefined && metrics.comment_quality !== null) {
    const item = {
      metric: 'Comment Quality',
      score: Math.round(metrics.comment_quality),
      insight: summaries.comment_quality || 'Comment quality assessment based on code review contributions.'
    };
    if (metrics.comment_quality >= 60) {
      strengths.push(item);
    } else {
      weaknesses.push(item);
    }
  }
  
  // Time Taken
  if (metrics.time_taken !== undefined && metrics.time_taken !== null) {
    const item = {
      metric: 'Time Spent',
      score: Math.round(metrics.time_taken),
      insight: summaries.time_taken || 'Time efficiency assessment based on task completion speed.'
    };
    if (metrics.time_taken >= 60) {
      strengths.push(item);
    } else {
      weaknesses.push(item);
    }
  }
  
  return { strengths, weaknesses };
};


export function CandidateProfile({ expert, onBack }: CandidateProfileProps) {
  const gitScore = expert.gitScore || 0;
  const gitGrade = getGitGrade(gitScore);
  const hrwScore = (expert as any).hrwScore ?? (expert as any).hrw_score ?? 0;
  
  // HRW test report URL - from MongoDB (test_report_url) or construct from test_id + test_candidate_id
  const testId = (expert as any).test_id;
  const testCandidateId = (expert as any).test_candidate_id;
  const hrwTestReportUrl = (expert as any).test_report_url
    || (testId && testCandidateId
      ? `https://www.hackerrank.com/work/tests/${testId}/candidates/${testCandidateId}`
      : null);
  const hasHrwReportUrl = hrwTestReportUrl && hrwTestReportUrl.startsWith('http');
  
  // Social links from MongoDB
  const socialLinks = {
    linkedIn: expert.linkedin_url || '',
    twitter: expert.twitter_url || '',
    website: expert.portfolio_url || '',
    github: expert.github_profile_url || `https://github.com/${expert.github_username || ''}`,
  };
  
  // Report links - Interview Report when we have a real URL
  const interviewReportUrl = expert.interview_report_url || (expert as any).interviewReportUrl;
  
  // Interview Report link only when we have a real URL from MongoDB
  const hasRealInterviewReport = interviewReportUrl &&
    !interviewReportUrl.includes('example.com') &&
    interviewReportUrl.startsWith('http');
  
  const username = expert.github_username || expert.email.split('@')[0];
  
  // Get metrics from MongoDB (flat fields)
  const metrics = {
    pr_merged_total: expert.pr_merged_total || 0,
    avg_pr_merge_rate_per_week: expert.avg_pr_merge_rate_per_week || 0,
    consistency_score: expert.consistency_score || 0,
    num_repos: expert.num_repos || 0,
    pr_quality: expert.pr_quality || 0,
    comment_quality: expert.comment_quality || 0,
    time_taken: expert.time_taken || 0,
  };
  
  // Get summaries (flat fields)
  const summaries = {
    pr_quality: expert.pr_quality_summary || '',
    comment_quality: expert.comment_quality_summary || '',
    time_taken: expert.time_taken_summary || '',
    overall_summary: expert.overall_summary || '',
  };
  
  // Get skills (from tech_stack or skills field) - extracted from overall profile, not just one repo
  const skills = expert.tech_stack || expert.skills || [];
  
  // Get features implemented (from database)
  const features = expert.features || [];
  
  // State for showing all skills or just first 5
  const [showAllSkills, setShowAllSkills] = useState(false);
  const displayedSkills = showAllSkills ? skills : skills.slice(0, 5);
  const hasMoreSkills = skills.length > 5;
  
  const { toast } = useToast();
  
  // Categorize metrics for AI summary
  const { strengths, weaknesses } = categorizeMetrics(metrics, summaries);
  

  return (
    <div className="flex flex-col h-full gap-4 sm:gap-6 overflow-y-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-4">
        <button
          onClick={onBack}
          className="p-2 rounded-lg hover:bg-surface-2 transition-colors w-fit"
        >
          <ArrowLeft className="w-5 h-5 text-muted-foreground" />
        </button>
        <div className="flex-1">
          <h2 className="text-lg sm:text-xl font-semibold text-foreground">{expert.name}</h2>
          <p className="text-sm text-primary font-mono">@{username}</p>
          {expert.location && (
            <div className="flex flex-wrap items-center gap-2 text-xs sm:text-sm text-muted-foreground mt-1">
              <span className="flex items-center gap-1">
                <MapPin className="w-3 h-3" />
                {expert.location}
              </span>
            </div>
          )}
        </div>
        
        {/* Social Links */}
        <div className="flex items-center gap-2">
          <a
            href={socialLinks.github}
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 rounded-lg hover:bg-surface-2 transition-colors group"
            title="GitHub"
          >
            <Github className="w-5 h-5 text-muted-foreground group-hover:text-primary transition-colors" />
          </a>
          {socialLinks.linkedIn && (
            <a
              href={socialLinks.linkedIn}
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 rounded-lg hover:bg-surface-2 transition-colors group"
              title="LinkedIn"
            >
              <Linkedin className="w-5 h-5 text-muted-foreground group-hover:text-primary transition-colors" />
            </a>
          )}
          {socialLinks.twitter && (
            <a
              href={socialLinks.twitter}
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 rounded-lg hover:bg-surface-2 transition-colors group"
              title="Twitter/X"
            >
              <Twitter className="w-5 h-5 text-muted-foreground group-hover:text-primary transition-colors" />
            </a>
          )}
          {socialLinks.website && (
            <a
              href={socialLinks.website}
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 rounded-lg hover:bg-surface-2 transition-colors group"
              title="Portfolio"
            >
              <Globe className="w-5 h-5 text-muted-foreground group-hover:text-primary transition-colors" />
            </a>
          )}
        </div>
      </div>

      {/* Score Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="card-terminal p-6">
          <div className="flex items-center gap-3 mb-2">
            <Github className="w-5 h-5 text-primary" />
            <span className="text-sm text-muted-foreground font-mono uppercase">Git Grade</span>
          </div>
          <div className="flex items-baseline gap-3">
            <span className={`text-5xl font-bold ${getGradeColor(gitGrade)}`}>{gitGrade}</span>
            <span className={`px-2 py-1 rounded text-xs font-mono ${getGradeBgColor(gitGrade)} ${getGradeColor(gitGrade)}`}>
              {gitScore}/100
            </span>
          </div>
        </div>

        <div className="card-terminal p-6">
          <div className="flex items-center gap-3 mb-2">
            <Award className="w-5 h-5 text-terminal-amber" />
            <span className="text-sm text-muted-foreground font-mono uppercase">HRW Score</span>
          </div>
          <div className="flex items-baseline gap-2">
            {hasHrwReportUrl ? (
              <a
                href={hrwTestReportUrl!}
                target="_blank"
                rel="noopener noreferrer"
                className="text-4xl font-bold text-terminal-amber hover:text-terminal-amber/80 hover:underline transition-colors"
              >
                {hrwScore}
              </a>
            ) : (
              <span className="text-4xl font-bold text-terminal-amber">{hrwScore}</span>
            )}
            <span className="text-muted-foreground">/ 100</span>
          </div>
          {/* Report Links - HRW Report when test was sent, Interview Report when scheduled */}
          <div className="flex flex-wrap items-center gap-2 mt-4 pt-4 border-t border-border">
            {hasHrwReportUrl && (
              <a
                href={hrwTestReportUrl!}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-2.5 py-1.5 bg-terminal-amber/10 rounded border border-terminal-amber/20 hover:bg-terminal-amber/20 transition-colors group"
            >
              <FileText className="w-3.5 h-3.5 text-terminal-amber" />
              <span className="text-xs font-medium text-terminal-amber">View Test Report</span>
              <ExternalLink className="w-3 h-3 text-terminal-amber/60 group-hover:text-terminal-amber transition-colors" />
            </a>
            )}
            {hasRealInterviewReport && (
              <a
                href={interviewReportUrl!}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-2.5 py-1.5 bg-terminal-cyan/10 rounded border border-terminal-cyan/20 hover:bg-terminal-cyan/20 transition-colors group"
              >
                <ClipboardCheck className="w-3.5 h-3.5 text-terminal-cyan" />
                <span className="text-xs font-medium text-terminal-cyan">Interview Report</span>
                <ExternalLink className="w-3 h-3 text-terminal-cyan/60 group-hover:text-terminal-cyan transition-colors" />
              </a>
            )}
          </div>
        </div>

        <div className="card-terminal p-6">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-sm text-muted-foreground font-mono uppercase">Skills</span>
          </div>
          <div className="flex flex-wrap gap-2 mt-2">
            {displayedSkills.map((skill) => (
              <span
                key={skill}
                className="px-2 py-1 text-xs bg-surface-2 text-muted-foreground rounded font-mono"
              >
                {skill}
              </span>
            ))}
            {hasMoreSkills && (
              <button
                onClick={() => setShowAllSkills(!showAllSkills)}
                className="px-2 py-1 text-xs bg-surface-2 text-muted-foreground rounded font-mono hover:bg-surface-3 transition-colors flex items-center gap-1"
              >
                {showAllSkills ? (
                  <>
                    Show Less
                    <ChevronDown className="w-3 h-3" />
                  </>
                ) : (
                  <>
                    +{skills.length - 5} more
                    <ChevronRight className="w-3 h-3" />
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Profile Metrics */}
      <div className="card-terminal p-6">
        <h3 className="text-sm font-mono uppercase text-muted-foreground mb-4 flex items-center gap-2">
          <Activity className="w-4 h-4 text-primary" />
          Profile Metrics
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="p-4 bg-surface-2 rounded-lg border border-border">
            <GitPullRequest className="w-5 h-5 text-primary mb-2" />
            <div className="text-2xl font-bold text-foreground font-mono">{metrics.pr_merged_total}</div>
            <div className="text-xs text-muted-foreground">PRs Merged</div>
          </div>
          <div className="p-4 bg-surface-2 rounded-lg border border-border">
            <GitMerge className="w-5 h-5 text-primary mb-2" />
            <div className="text-2xl font-bold text-foreground font-mono">{metrics.avg_pr_merge_rate_per_week.toFixed(2)}</div>
            <div className="text-xs text-muted-foreground">PRs/Week (1 year)</div>
          </div>
          <div className="p-4 bg-surface-2 rounded-lg border border-border">
            <TrendingUp className="w-5 h-5 text-primary mb-2" />
            <div className="text-2xl font-bold text-foreground font-mono">{metrics.consistency_score.toFixed(0)}/100</div>
            <div className="text-xs text-muted-foreground">Consistency Score</div>
          </div>
          <div className="p-4 bg-surface-2 rounded-lg border border-border">
            <Layers className="w-5 h-5 text-primary mb-2" />
            <div className="text-2xl font-bold text-foreground font-mono">{metrics.num_repos}</div>
            <div className="text-xs text-muted-foreground">Repositories</div>
          </div>
        </div>
      </div>


      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Performance Metrics - Radar Chart */}
        <div className="card-terminal p-6">
          <h3 className="text-sm font-mono uppercase text-muted-foreground mb-6 flex items-center gap-2">
            <Brain className="w-4 h-4 text-primary" />
            Performance Metrics
          </h3>
          <div className="h-96">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart 
                data={prepareRadarData(metrics)}
                margin={{ top: 20, right: 30, bottom: 20, left: 30 }}
              >
                <PolarGrid 
                  stroke="hsl(var(--border))" 
                  strokeWidth={1}
                  strokeOpacity={0.3}
                />
                <PolarAngleAxis
                  dataKey="dimension"
                  tick={{ 
                    fill: 'hsl(var(--foreground))', 
                    fontSize: 12,
                    fontWeight: 500,
                    fontFamily: 'monospace'
                  }}
                  tickLine={{ stroke: 'hsl(var(--border))', strokeWidth: 1 }}
                />
                <PolarRadiusAxis
                  angle={90}
                  domain={[0, 100]}
                  tick={{ 
                    fill: 'hsl(var(--muted-foreground))', 
                    fontSize: 10,
                    fontFamily: 'monospace'
                  }}
                  tickCount={6}
                  tickFormatter={(value) => `${value}`}
                  axisLine={{ stroke: 'hsl(var(--border))', strokeWidth: 1 }}
                />
                <Radar
                  name="Score"
                  dataKey="value"
                  stroke="hsl(var(--primary))"
                  fill="hsl(var(--primary))"
                  fillOpacity={0.25}
                  strokeWidth={3}
                  dot={{ 
                    fill: 'hsl(var(--primary))', 
                    r: 4,
                    strokeWidth: 2,
                    stroke: 'hsl(var(--surface-1))'
                  }}
                  activeDot={{ 
                    r: 6,
                    fill: 'hsl(var(--primary))',
                    stroke: 'hsl(var(--surface-1))',
                    strokeWidth: 2
                  }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--surface-1))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px',
                    fontFamily: 'monospace',
                    padding: '12px',
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
                  }}
                  cursor={{ stroke: 'hsl(var(--primary))', strokeWidth: 2, strokeDasharray: '5 5' }}
                  formatter={(value: number, name: string, props: any) => {
                    const dimension = props.payload?.dimension || name;
                    const actualValue = props.payload?.actualValue;
                    
                    // For PRs Merged, show actual count instead of normalized value
                    if (dimension === 'PRs Merged') {
                      return [`${actualValue || value} PRs`, dimension];
                    }
                    
                    // Show formatted value with percentage
                    const percentage = Math.round(value);
                    return [`${percentage}%`, dimension];
                  }}
                  labelFormatter={(label) => (
                    <span className="font-semibold text-foreground">{label}</span>
                  )}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-4 pt-4 border-t border-border">
            <div className="flex flex-wrap gap-4 text-xs text-muted-foreground font-mono">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-primary/25 border border-primary"></div>
                <span>Performance Score</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-primary">●</span>
                <span>Scale: 0-100</span>
              </div>
            </div>
          </div>
        </div>

        {/* Heatmap */}
        {username && <ContributionHeatmap username={username} />}
      </div>

      {/* AI Summary */}
      <div className="card-terminal p-6">
        <h3 className="text-sm font-mono uppercase text-muted-foreground mb-4 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-primary" />
          AI-Generated Candidate Summary
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          {/* Strengths */}
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-terminal-green flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              Strengths
            </h4>
            {strengths.length > 0 ? (
              strengths.map((item) => (
                <div key={item.metric} className="p-3 bg-terminal-green/10 rounded-lg border border-terminal-green/20">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-mono text-foreground">{item.metric}</span>
                    <span className="text-sm font-bold text-terminal-green">{item.score}/100</span>
                  </div>
                  <p className="text-xs text-muted-foreground">{item.insight}</p>
                </div>
              ))
            ) : (
              <p className="text-xs text-muted-foreground italic">No strengths identified</p>
            )}
          </div>
          
          {/* Areas for Improvement */}
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-terminal-amber flex items-center gap-2">
              <Activity className="w-4 h-4" />
              Areas for Improvement
            </h4>
            {weaknesses.length > 0 ? (
              weaknesses.map((item) => (
                <div key={item.metric} className="p-3 bg-terminal-amber/10 rounded-lg border border-terminal-amber/20">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-mono text-foreground">{item.metric}</span>
                    <span className="text-sm font-bold text-terminal-amber">{item.score}/100</span>
                  </div>
                  <p className="text-xs text-muted-foreground">{item.insight}</p>
                </div>
              ))
            ) : (
              <p className="text-xs text-muted-foreground italic">No areas for improvement identified</p>
            )}
          </div>
        </div>
        
        {/* Overall Insight */}
        {summaries.overall_summary && (
          <div className="p-4 bg-primary/10 rounded-lg border border-primary/20">
            <h4 className="text-sm font-medium text-primary mb-2">Overall Assessment</h4>
            <p className="text-sm text-muted-foreground leading-relaxed">{summaries.overall_summary}</p>
          </div>
        )}
        
        {/* Features Implemented */}
        {features.length > 0 && (
          <div className="mt-6 space-y-2">
            <h4 className="text-sm font-medium text-foreground flex items-center gap-2">
              <Code className="w-4 h-4 text-primary" />
              Features Implemented
            </h4>
            <div className="flex flex-wrap gap-2">
              {features.map((feature, index) => (
                <span
                  key={index}
                  className="px-3 py-1.5 text-xs bg-surface-2 border border-border rounded-md text-foreground font-mono"
                >
                  {feature}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
