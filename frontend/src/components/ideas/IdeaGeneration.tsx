import { useState, useMemo } from 'react';
import { 
  GitBranch, 
  Loader2, 
  ExternalLink, 
  Lightbulb,
  CheckCircle2,
  AlertCircle,
  ArrowLeft,
  Code,
  Users,
  Target,
  Check,
  X,
  Filter,
  Layers,
  Search,
  ChevronDown,
  Hammer,
  XCircle
} from 'lucide-react';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { Checkbox } from '@/components/ui/checkbox';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';

interface TaskIdea {
  id: string;
  title: string;
  description: string;
  difficulty: 'easy' | 'medium' | 'hard';
  category: 'bug_fix' | 'feature' | 'system_design' | 'code_review';
  stack: string[];
  status: 'pending' | 'approved' | 'rejected';
  builtLink?: string;
}

interface RepoAnalysis {
  id: string;
  repoUrl: string;
  repoName: string;
  status: 'analyzing' | 'completed' | 'error';
  taskIdeas: TaskIdea[];
}

const mockAnalyses: RepoAnalysis[] = [
  {
    id: '1',
    repoUrl: 'https://github.com/calcom/cal.com',
    repoName: 'calcom/cal.com',
    status: 'completed',
    taskIdeas: [
      {
        id: 't1',
        title: 'Implement recurring availability patterns',
        description: 'Build a system that allows users to define complex recurring availability patterns, such as "available every Monday and Wednesday from 9am-12pm, except the first Monday of each month." This requires understanding the existing availability data model and extending it to support recurring rules with exceptions.',
        difficulty: 'hard',
        category: 'feature',
        stack: ['TypeScript', 'Next.js', 'Prisma', 'PostgreSQL'],
        status: 'pending'
      },
      {
        id: 't2',
        title: 'Design a multi-tenant booking architecture',
        description: 'Create a system design proposal for handling multi-tenant booking scenarios where organizations can have sub-teams with different availability rules, permissions, and branding. Consider data isolation, performance, and scalability.',
        difficulty: 'hard',
        category: 'system_design',
        stack: ['PostgreSQL', 'Redis', 'TypeScript'],
        status: 'approved'
      },
      {
        id: 't3',
        title: 'Review calendar sync implementation',
        description: 'Conduct a thorough code review of the calendar synchronization mechanism. Identify potential race conditions, error handling gaps, and suggest improvements for reliability and maintainability.',
        difficulty: 'medium',
        category: 'code_review',
        stack: ['TypeScript', 'Node.js', 'Google Calendar API'],
        status: 'pending'
      },
      {
        id: 't4',
        title: 'Fix timezone edge cases in recurring events',
        description: 'Investigate and fix bugs related to DST transitions in recurring events. Events scheduled during DST change periods may show incorrect times or be skipped entirely.',
        difficulty: 'medium',
        category: 'bug_fix',
        stack: ['TypeScript', 'Day.js', 'Next.js'],
        status: 'rejected'
      },
      {
        id: 't5',
        title: 'Build a booking widget customization API',
        description: 'Design and implement an API that allows users to programmatically customize their booking widget\'s appearance and behavior. This should support theming, custom fields, and conditional logic.',
        difficulty: 'medium',
        category: 'feature',
        stack: ['TypeScript', 'React', 'tRPC'],
        status: 'approved'
      },
      {
        id: 't6',
        title: 'Design webhook delivery system architecture',
        description: 'Create a comprehensive system design for a reliable webhook delivery system with exponential backoff, dead letter queues, monitoring dashboard, and configurable retry policies.',
        difficulty: 'hard',
        category: 'system_design',
        stack: ['Node.js', 'Redis', 'PostgreSQL', 'Bull'],
        status: 'pending'
      }
    ]
  },
  {
    id: '2',
    repoUrl: 'https://github.com/formbricks/formbricks',
    repoName: 'formbricks/formbricks',
    status: 'completed',
    taskIdeas: [
      {
        id: 'fb1',
        title: 'Implement branching logic for surveys',
        description: 'Build a feature that allows survey creators to define conditional branching based on previous answers. Users should be able to skip questions, redirect to different paths, or end the survey early based on responses.',
        difficulty: 'hard',
        category: 'feature',
        stack: ['TypeScript', 'React', 'Next.js', 'Prisma'],
        status: 'pending'
      },
      {
        id: 'fb2',
        title: 'Design real-time response analytics pipeline',
        description: 'Architect a system that processes survey responses in real-time, aggregates metrics, and pushes updates to dashboards. Consider scalability for high-volume surveys and data consistency.',
        difficulty: 'hard',
        category: 'system_design',
        stack: ['PostgreSQL', 'Redis', 'WebSocket', 'TypeScript'],
        status: 'approved'
      },
      {
        id: 'fb3',
        title: 'Review survey rendering performance',
        description: 'Analyze the survey rendering code for performance bottlenecks. Look for unnecessary re-renders, large bundle sizes, and opportunities for lazy loading or code splitting.',
        difficulty: 'medium',
        category: 'code_review',
        stack: ['React', 'TypeScript', 'Webpack'],
        status: 'pending'
      },
      {
        id: 'fb4',
        title: 'Fix partial response persistence bug',
        description: 'Investigate reports of partial survey responses not being saved when users navigate away. Implement proper autosave and recovery mechanisms.',
        difficulty: 'medium',
        category: 'bug_fix',
        stack: ['React', 'TypeScript', 'IndexedDB'],
        status: 'pending'
      },
      {
        id: 'fb5',
        title: 'Build embeddable survey widget',
        description: 'Create a lightweight, embeddable survey widget that can be integrated into any website with minimal code. Support customization and event callbacks.',
        difficulty: 'medium',
        category: 'feature',
        stack: ['TypeScript', 'Preact', 'Rollup'],
        status: 'pending'
      }
    ]
  },
  {
    id: '3',
    repoUrl: 'https://github.com/asyncapi/asyncapi',
    repoName: 'asyncapi/asyncapi',
    status: 'completed',
    taskIdeas: [
      {
        id: 'aa1',
        title: 'Design spec validation architecture',
        description: 'Create a system design for a comprehensive AsyncAPI specification validator that supports custom rules, plugins, and integration with CI/CD pipelines. Consider performance for large specs.',
        difficulty: 'hard',
        category: 'system_design',
        stack: ['TypeScript', 'JSON Schema', 'Node.js'],
        status: 'pending'
      },
      {
        id: 'aa2',
        title: 'Implement schema registry integration',
        description: 'Build a feature that allows AsyncAPI documents to reference schemas from external registries like Confluent Schema Registry or AWS Glue.',
        difficulty: 'hard',
        category: 'feature',
        stack: ['TypeScript', 'Avro', 'Kafka', 'Node.js'],
        status: 'pending'
      },
      {
        id: 'aa3',
        title: 'Review parser error handling',
        description: 'Conduct a code review of the spec parser focusing on error handling and error messages. Ensure errors are descriptive, actionable, and help users fix their specifications.',
        difficulty: 'medium',
        category: 'code_review',
        stack: ['TypeScript', 'YAML', 'JSON Schema'],
        status: 'approved'
      },
      {
        id: 'aa4',
        title: 'Fix circular reference resolution',
        description: 'Debug and fix issues with circular $ref references causing infinite loops or incorrect schema resolution in certain edge cases.',
        difficulty: 'hard',
        category: 'bug_fix',
        stack: ['TypeScript', 'JSON Schema', 'Node.js'],
        status: 'pending'
      },
      {
        id: 'aa5',
        title: 'Build interactive documentation generator',
        description: 'Create a tool that generates interactive API documentation from AsyncAPI specs, including live examples, try-it-out features, and code generation.',
        difficulty: 'medium',
        category: 'feature',
        stack: ['React', 'TypeScript', 'MDX'],
        status: 'pending'
      }
    ]
  },
  {
    id: '4',
    repoUrl: 'https://github.com/sveltejs/svelte',
    repoName: 'sveltejs/svelte',
    status: 'completed',
    taskIdeas: [
      {
        id: 'sv1',
        title: 'Design incremental compilation system',
        description: 'Architect an incremental compilation system that only recompiles changed components and their dependents. Consider cache invalidation, dependency tracking, and integration with bundlers.',
        difficulty: 'hard',
        category: 'system_design',
        stack: ['TypeScript', 'Svelte', 'Vite', 'Rollup'],
        status: 'pending'
      },
      {
        id: 'sv2',
        title: 'Implement fine-grained reactivity debugging',
        description: 'Build developer tools that visualize the reactivity graph, showing which state changes trigger which updates. Help developers identify unnecessary re-renders.',
        difficulty: 'hard',
        category: 'feature',
        stack: ['Svelte', 'TypeScript', 'Chrome DevTools API'],
        status: 'approved'
      },
      {
        id: 'sv3',
        title: 'Review transition system implementation',
        description: 'Perform a deep code review of the transition/animation system. Analyze the implementation for edge cases, browser compatibility issues, and potential optimizations.',
        difficulty: 'medium',
        category: 'code_review',
        stack: ['Svelte', 'TypeScript', 'CSS'],
        status: 'pending'
      },
      {
        id: 'sv4',
        title: 'Fix SSR hydration mismatch warnings',
        description: 'Investigate and fix false-positive hydration mismatch warnings that occur with certain component patterns. Improve error messages to be more actionable.',
        difficulty: 'medium',
        category: 'bug_fix',
        stack: ['Svelte', 'TypeScript', 'Node.js'],
        status: 'pending'
      },
      {
        id: 'sv5',
        title: 'Design component lazy loading strategy',
        description: 'Create a system design for built-in component lazy loading that integrates seamlessly with Svelte\'s compilation model. Consider code splitting, prefetching, and loading states.',
        difficulty: 'hard',
        category: 'system_design',
        stack: ['Svelte', 'Vite', 'TypeScript'],
        status: 'pending'
      },
      {
        id: 'sv6',
        title: 'Implement TypeScript generic component support',
        description: 'Add support for generic type parameters in Svelte components, allowing components to be type-safe while remaining flexible for different data types.',
        difficulty: 'hard',
        category: 'feature',
        stack: ['TypeScript', 'Svelte', 'LSP'],
        status: 'pending'
      }
    ]
  }
];

type ViewMode = 'repos' | 'taskList' | 'taskDetail';

export function IdeaGeneration() {
  const { toast } = useToast();
  const [repoUrl, setRepoUrl] = useState('');
  const [analyses, setAnalyses] = useState<RepoAnalysis[]>(mockAnalyses);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('repos');
  const [selectedRepo, setSelectedRepo] = useState<RepoAnalysis | null>(null);
  const [selectedTask, setSelectedTask] = useState<TaskIdea | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedStacks, setSelectedStacks] = useState<string[]>([]);
  const [selectedTaskIds, setSelectedTaskIds] = useState<Set<string>>(new Set());

  const toggleTaskSelection = (taskId: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    // Only allow selection of approved tasks
    const task = selectedRepo?.taskIdeas.find(t => t.id === taskId);
    if (task?.status !== 'approved') return;
    
    setSelectedTaskIds(prev => {
      const next = new Set(prev);
      if (next.has(taskId)) {
        next.delete(taskId);
      } else {
        next.add(taskId);
      }
      return next;
    });
  };

  const selectAllTasks = () => {
    if (selectedRepo) {
      // Only select approved tasks
      const approvedIds = selectedRepo.taskIdeas.filter(t => t.status === 'approved').map(t => t.id);
      setSelectedTaskIds(new Set(approvedIds));
    }
  };

  const clearSelection = () => {
    setSelectedTaskIds(new Set());
  };

  const handleBuildSelected = () => {
    if (selectedTaskIds.size === 0) return;
    
    // Generate a mock GitHub link for each selected task
    const builtLink = `https://github.com/built-tasks/repo-${Date.now()}`;
    
    setAnalyses(prev => prev.map(repo => ({
      ...repo,
      taskIdeas: repo.taskIdeas.map(task => 
        selectedTaskIds.has(task.id) ? { ...task, builtLink } : task
      )
    })));
    
    if (selectedRepo) {
      setSelectedRepo(prev => prev ? {
        ...prev,
        taskIdeas: prev.taskIdeas.map(task =>
          selectedTaskIds.has(task.id) ? { ...task, builtLink } : task
        )
      } : null);
    }
    
    toast({
      title: "Build Started",
      description: `Building ${selectedTaskIds.size} task(s). GitHub repo link will be available shortly.`,
    });
    
    setSelectedTaskIds(new Set());
  };

  // Get all unique stacks from all repos
  const allStacks = useMemo(() => {
    const stacks = new Set<string>();
    analyses.forEach(repo => {
      repo.taskIdeas.forEach(task => {
        task.stack.forEach(s => stacks.add(s));
      });
    });
    return Array.from(stacks).sort();
  }, [analyses]);

  // Filter repos by search query and stacks
  const filteredAnalyses = useMemo(() => {
    return analyses.filter(repo => {
      const matchesSearch = !searchQuery || 
        repo.repoName.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStack = selectedStacks.length === 0 || 
        repo.taskIdeas.some(task => task.stack.some(s => selectedStacks.includes(s)));
      return matchesSearch && matchesStack;
    });
  }, [analyses, searchQuery, selectedStacks]);

  const toggleStack = (stack: string) => {
    setSelectedStacks(prev => 
      prev.includes(stack) 
        ? prev.filter(s => s !== stack)
        : [...prev, stack]
    );
  };

  const clearStackFilter = () => {
    setSelectedStacks([]);
  };

  const handleAnalyze = () => {
    if (!repoUrl.trim()) return;
    
    setIsAnalyzing(true);
    
    const repoName = repoUrl.replace('https://github.com/', '').replace('.git', '');
    const newAnalysis: RepoAnalysis = {
      id: Date.now().toString(),
      repoUrl,
      repoName,
      status: 'analyzing',
      taskIdeas: []
    };
    
    setAnalyses(prev => [newAnalysis, ...prev]);
    setRepoUrl('');
    
    setTimeout(() => {
      setAnalyses(prev => prev.map(a => 
        a.id === newAnalysis.id 
          ? {
              ...a,
              status: 'completed' as const,
              taskIdeas: [
                {
                  id: 'new1',
                  title: 'Implement feature flag system',
                  description: 'Build a comprehensive feature flag system that allows for gradual rollouts, A/B testing, and emergency kill switches. This should integrate with the existing configuration management.',
                  difficulty: 'medium' as const,
                  category: 'feature' as const,
                  stack: ['TypeScript', 'React', 'Node.js'],
                  status: 'pending' as const
                },
                {
                  id: 'new2',
                  title: 'Design scalable caching architecture',
                  description: 'Create a system design for a multi-layer caching strategy that improves performance while maintaining data consistency. Consider cache invalidation, distributed caching, and monitoring.',
                  difficulty: 'hard' as const,
                  category: 'system_design' as const,
                  stack: ['Redis', 'Node.js', 'PostgreSQL'],
                  status: 'pending' as const
                },
                {
                  id: 'new3',
                  title: 'Review database query patterns',
                  description: 'Conduct a code review of the database access layer. Identify N+1 problems, missing indexes, and opportunities for query optimization.',
                  difficulty: 'medium' as const,
                  category: 'code_review' as const,
                  stack: ['PostgreSQL', 'TypeScript', 'Prisma'],
                  status: 'pending' as const
                },
                {
                  id: 'new4',
                  title: 'Fix race condition in concurrent updates',
                  description: 'Debug and fix a race condition that occurs when multiple users update the same resource simultaneously. Implement proper locking or optimistic concurrency.',
                  difficulty: 'hard' as const,
                  category: 'bug_fix' as const,
                  stack: ['TypeScript', 'PostgreSQL', 'Node.js'],
                  status: 'pending' as const
                }
              ]
            }
          : a
      ));
      setIsAnalyzing(false);
    }, 3000);
  };

  const handleRepoClick = (analysis: RepoAnalysis) => {
    if (analysis.status === 'completed') {
      setSelectedRepo(analysis);
      setViewMode('taskList');
    }
  };

  const handleTaskClick = (task: TaskIdea) => {
    setSelectedTask(task);
    setViewMode('taskDetail');
  };

  const handleBackToRepos = () => {
    setViewMode('repos');
    setSelectedRepo(null);
    setSelectedTask(null);
  };

  const handleBackToTasks = () => {
    setViewMode('taskList');
    setSelectedTask(null);
  };

  const handleApproveTask = (taskId: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    setAnalyses(prev => prev.map(repo => ({
      ...repo,
      taskIdeas: repo.taskIdeas.map(task => 
        task.id === taskId ? { ...task, status: 'approved' as const } : task
      )
    })));
    // Update selectedRepo if we're viewing it
    if (selectedRepo) {
      setSelectedRepo(prev => prev ? {
        ...prev,
        taskIdeas: prev.taskIdeas.map(task =>
          task.id === taskId ? { ...task, status: 'approved' as const } : task
        )
      } : null);
    }
    // Update selectedTask if we're viewing it
    if (selectedTask?.id === taskId) {
      setSelectedTask(prev => prev ? { ...prev, status: 'approved' as const } : null);
    }
    toast({
      title: "Task Approved",
      description: "This task idea has been approved for building.",
    });
  };

  const handleRejectTask = (taskId: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    setAnalyses(prev => prev.map(repo => ({
      ...repo,
      taskIdeas: repo.taskIdeas.map(task => 
        task.id === taskId ? { ...task, status: 'rejected' as const } : task
      )
    })));
    // Update selectedRepo if we're viewing it
    if (selectedRepo) {
      setSelectedRepo(prev => prev ? {
        ...prev,
        taskIdeas: prev.taskIdeas.map(task =>
          task.id === taskId ? { ...task, status: 'rejected' as const } : task
        )
      } : null);
    }
    // Update selectedTask if we're viewing it
    if (selectedTask?.id === taskId) {
      setSelectedTask(prev => prev ? { ...prev, status: 'rejected' as const } : null);
    }
    toast({
      title: "Task Rejected",
      description: "This task idea has been marked as rejected.",
      variant: "destructive",
    });
  };

  const statusConfig = {
    analyzing: { icon: Loader2, label: 'Analyzing...', className: 'text-terminal-amber animate-spin' },
    completed: { icon: CheckCircle2, label: 'Completed', className: 'text-terminal-green' },
    error: { icon: AlertCircle, label: 'Error', className: 'text-terminal-red' },
  };

  const difficultyConfig = {
    easy: { label: 'Easy', className: 'text-terminal-green bg-terminal-green/10' },
    medium: { label: 'Medium', className: 'text-terminal-amber bg-terminal-amber/10' },
    hard: { label: 'Hard', className: 'text-terminal-red bg-terminal-red/10' },
  };

  const categoryConfig: Record<string, { label: string; className: string }> = {
    bug_fix: { label: 'Bug Fix', className: 'text-terminal-red bg-terminal-red/10' },
    feature: { label: 'Feature', className: 'text-primary bg-primary/10' },
    system_design: { label: 'System Design', className: 'text-terminal-cyan bg-terminal-cyan/10' },
    code_review: { label: 'Code Review', className: 'text-terminal-amber bg-terminal-amber/10' },
  };

  const getCategory = (category: string) => categoryConfig[category] || { label: category, className: 'text-muted-foreground bg-surface-2' };
  const getDifficulty = (difficulty: string) => difficultyConfig[difficulty as keyof typeof difficultyConfig] || { label: difficulty, className: 'text-muted-foreground bg-surface-2' };

  // Task Detail View
  if (viewMode === 'taskDetail' && selectedTask && selectedRepo) {
    return (
      <div className="flex flex-col h-full min-h-[60vh]">
        <div className="flex items-center gap-5 mb-8">
          <button
            onClick={handleBackToTasks}
            className="p-2.5 rounded-lg hover:bg-surface-2 transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-muted-foreground" />
          </button>
          <div className="flex-1">
            <h2 className="text-2xl font-semibold text-foreground">Task Idea</h2>
            <p className="text-sm text-muted-foreground font-mono mt-0.5">
              From {selectedRepo.repoName}
            </p>
          </div>
          
          {/* Action Buttons */}
          {selectedTask.status === 'pending' && (
            <div className="flex items-center gap-2">
              <button
                onClick={(e) => handleApproveTask(selectedTask.id, e)}
                className="flex items-center gap-2 px-4 py-2 bg-terminal-green/10 text-terminal-green rounded-lg hover:bg-terminal-green/20 transition-colors"
              >
                <Check className="w-4 h-4" />
                Approve
              </button>
              <button
                onClick={(e) => handleRejectTask(selectedTask.id, e)}
                className="flex items-center gap-2 px-4 py-2 bg-terminal-red/10 text-terminal-red rounded-lg hover:bg-terminal-red/20 transition-colors"
              >
                <X className="w-4 h-4" />
                Reject
              </button>
            </div>
          )}
          {selectedTask.status === 'approved' && (
            <span className="px-3 py-1 bg-terminal-green/20 text-terminal-green text-sm font-medium rounded-full">
              ✓ Approved
            </span>
          )}
          {selectedTask.status === 'rejected' && (
            <span className="px-3 py-1 bg-terminal-red/20 text-terminal-red text-sm font-medium rounded-full">
              ✗ Rejected
            </span>
          )}
        </div>

        <div className="card-terminal p-6 sm:p-8 flex-1 overflow-y-auto min-h-[50vh]">
          {/* Source Repo Banner */}
          <div className="bg-primary/10 border border-primary/20 rounded-xl p-5 mb-8">
            <div className="flex items-center gap-3 mb-2">
              <GitBranch className="w-5 h-5 text-primary" />
              <span className="text-sm font-medium text-primary">Inspiration Source</span>
            </div>
            <a
              href={selectedRepo.repoUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-foreground font-mono text-sm hover:text-primary transition-colors"
            >
              {selectedRepo.repoName}
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>

          {/* Task Title & Badges */}
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-4">
              <h3 className="text-2xl sm:text-3xl font-semibold text-foreground">{selectedTask.title}</h3>
              {selectedTask.status === 'approved' && (
                <span className="px-2 py-1 bg-terminal-green/20 text-terminal-green text-xs font-medium rounded">
                  Approved
                </span>
              )}
              {selectedTask.status === 'rejected' && (
                <span className="px-2 py-1 bg-terminal-red/20 text-terminal-red text-xs font-medium rounded">
                  Rejected
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className={cn("px-2 py-1 rounded text-xs font-mono", getDifficulty(selectedTask.difficulty).className)}>
                {getDifficulty(selectedTask.difficulty).label}
              </span>
              <span className={cn("px-2 py-1 rounded text-xs font-mono", getCategory(selectedTask.category).className)}>
                {getCategory(selectedTask.category).label}
              </span>
            </div>
          </div>

          {/* Stack */}
          <div className="mb-8">
            <h4 className="text-sm font-mono uppercase text-muted-foreground mb-3 flex items-center gap-2">
              <Layers className="w-4 h-4" />
              Tech Stack
            </h4>
            <div className="flex flex-wrap gap-2.5">
              {selectedTask.stack.map(tech => (
                <span key={tech} className="px-3 py-1.5 bg-surface-2 text-foreground text-sm font-mono rounded-lg">
                  {tech}
                </span>
              ))}
            </div>
          </div>

          {/* Task Description */}
          <div className="mb-10">
            <h4 className="text-sm font-mono uppercase text-muted-foreground mb-3 flex items-center gap-2">
              <Target className="w-4 h-4" />
              Task Description
            </h4>
            <p className="text-foreground leading-relaxed text-base">{selectedTask.description}</p>
          </div>

          {/* Interview Context */}
          <div className="bg-terminal-amber/10 border border-terminal-amber/20 rounded-xl p-5">
            <div className="flex items-center gap-3 mb-3">
              <Users className="w-5 h-5 text-terminal-amber" />
              <span className="text-sm font-medium text-terminal-amber">Live Interview Task</span>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed">
              This task is designed for use in actual live interviews with candidates or developers. 
              It tests real-world problem-solving skills based on patterns observed in production-grade 
              open source projects. The candidate should be able to discuss their approach, trade-offs, 
              and implementation strategy.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Task List View
  if (viewMode === 'taskList' && selectedRepo) {
    const allSelected = selectedRepo.taskIdeas.length > 0 && selectedRepo.taskIdeas.every(t => selectedTaskIds.has(t.id));
    const someSelected = selectedTaskIds.size > 0;
    
    return (
      <div className="flex flex-col h-full min-h-[60vh]">
        <div className="flex flex-col sm:flex-row sm:items-center gap-5 mb-8">
          <button
            onClick={handleBackToRepos}
            className="p-2.5 rounded-lg hover:bg-surface-2 transition-colors w-fit"
          >
            <ArrowLeft className="w-5 h-5 text-muted-foreground" />
          </button>
          <div className="flex-1">
            <h2 className="text-xl sm:text-2xl font-semibold text-foreground">Task Ideas</h2>
            <div className="flex items-center gap-2 text-xs sm:text-sm text-muted-foreground font-mono">
              <GitBranch className="w-3.5 h-3.5" />
              <span className="truncate max-w-[200px] sm:max-w-none">{selectedRepo.repoName}</span>
              <a
                href={selectedRepo.repoUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-primary transition-colors"
              >
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>
          <span className="text-xs sm:text-sm text-muted-foreground">
            {selectedRepo.taskIdeas.length} task ideas
          </span>
        </div>

        {/* Build Action Bar */}
        <div className="card-terminal p-4 sm:p-5 mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <Checkbox
              checked={allSelected}
              onCheckedChange={() => allSelected ? clearSelection() : selectAllTasks()}
              className="border-muted-foreground data-[state=checked]:bg-primary data-[state=checked]:border-primary"
            />
            <span className="text-sm text-muted-foreground">
              {selectedTaskIds.size > 0 ? `${selectedTaskIds.size} selected` : 'Select approved tasks to build'}
            </span>
            {someSelected && (
              <button
                onClick={clearSelection}
                className="text-xs text-primary hover:underline"
              >
                Clear
              </button>
            )}
          </div>
          <button
            onClick={handleBuildSelected}
            disabled={!someSelected}
            className={cn(
              "flex items-center justify-center gap-2 px-5 py-3 rounded-lg font-medium text-sm transition-colors w-full sm:w-auto",
              someSelected
                ? "bg-primary text-primary-foreground hover:bg-primary/90"
                : "bg-surface-2 text-muted-foreground cursor-not-allowed"
            )}
          >
            <Hammer className="w-4 h-4" />
            Build {selectedTaskIds.size > 0 ? `(${selectedTaskIds.size})` : ''}
          </button>
        </div>

        <div className="card-terminal flex-1 overflow-hidden min-h-[50vh]">
          <div className="overflow-x-auto h-full">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="p-5 w-14"></th>
                  <th className="p-5 text-left text-xs font-mono uppercase tracking-wider text-muted-foreground">Task</th>
                  <th className="p-5 text-left text-xs font-mono uppercase tracking-wider text-muted-foreground">Status</th>
                  <th className="p-5 text-left text-xs font-mono uppercase tracking-wider text-muted-foreground">Difficulty</th>
                  <th className="p-5 text-left text-xs font-mono uppercase tracking-wider text-muted-foreground">Category</th>
                  <th className="p-5 text-left text-xs font-mono uppercase tracking-wider text-muted-foreground">Actions</th>
                  <th className="p-5 text-left text-xs font-mono uppercase tracking-wider text-muted-foreground">Built Link</th>
                </tr>
              </thead>
              <tbody>
                {selectedRepo.taskIdeas.map((task) => (
                  <tr
                    key={task.id}
                    onClick={() => handleTaskClick(task)}
                    className="table-row-hover cursor-pointer border-b border-border/50"
                  >
                    <td className="p-5" onClick={(e) => e.stopPropagation()}>
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span className={cn(task.status !== 'approved' && "cursor-not-allowed")}>
                              <Checkbox
                                checked={selectedTaskIds.has(task.id)}
                                onCheckedChange={() => toggleTaskSelection(task.id)}
                                disabled={task.status !== 'approved'}
                                className={cn(
                                  "border-muted-foreground data-[state=checked]:bg-primary data-[state=checked]:border-primary",
                                  task.status !== 'approved' && "opacity-50 cursor-not-allowed"
                                )}
                              />
                            </span>
                          </TooltipTrigger>
                          {task.status !== 'approved' && (
                            <TooltipContent>
                              <p>First approve or reject before building.</p>
                            </TooltipContent>
                          )}
                        </Tooltip>
                      </TooltipProvider>
                    </td>
                    <td className="p-5">
                      <div className="flex items-start gap-3">
                        <Code className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
                        <div>
                          <span className="font-medium text-foreground text-sm">{task.title}</span>
                          <div className="text-xs text-muted-foreground line-clamp-1 mt-1">
                            {task.description}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="p-5">
                      {task.status === 'approved' ? (
                        <span className="px-2 py-1 bg-terminal-green/20 text-terminal-green text-xs font-medium rounded">
                          Approved
                        </span>
                      ) : task.status === 'rejected' ? (
                        <span className="px-2 py-1 bg-terminal-red/20 text-terminal-red text-xs font-medium rounded">
                          Rejected
                        </span>
                      ) : (
                        <span className="px-2 py-1 bg-terminal-amber/20 text-terminal-amber text-xs font-medium rounded">
                          To be Reviewed
                        </span>
                      )}
                    </td>
                    <td className="p-5">
                      <span className={cn("px-2.5 py-1 rounded text-xs font-mono", getDifficulty(task.difficulty).className)}>
                        {getDifficulty(task.difficulty).label}
                      </span>
                    </td>
                    <td className="p-5">
                      <span className={cn("px-2.5 py-1 rounded text-xs font-mono", getCategory(task.category).className)}>
                        {getCategory(task.category).label}
                      </span>
                    </td>
                    <td className="p-5" onClick={(e) => e.stopPropagation()}>
                      {task.status === 'pending' ? (
                        <div className="flex items-center gap-1">
                          <button
                            onClick={(e) => handleApproveTask(task.id, e)}
                            className="p-1.5 rounded hover:bg-terminal-green/20 text-terminal-green transition-colors"
                            title="Approve"
                          >
                            <CheckCircle2 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={(e) => handleRejectTask(task.id, e)}
                            className="p-1.5 rounded hover:bg-terminal-red/20 text-terminal-red transition-colors"
                            title="Reject"
                          >
                            <XCircle className="w-4 h-4" />
                          </button>
                        </div>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </td>
                    <td className="p-5" onClick={(e) => e.stopPropagation()}>
                      {task.builtLink ? (
                        <a
                          href={task.builtLink}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1.5 text-primary hover:underline text-sm font-mono"
                        >
                          <GitBranch className="w-3.5 h-3.5" />
                          View Repo
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  }

  // Repos View (default)
  return (
    <div className="flex flex-col h-full min-h-[60vh]">
      {/* Header */}
      <div className="mb-6 sm:mb-8">
        <h2 className="text-xl sm:text-2xl font-semibold text-foreground">Builder</h2>
        <p className="text-sm text-muted-foreground font-mono mt-1">
          Analyze GitHub repos to generate task ideas
        </p>
      </div>

      {/* Input Section */}
      <div className="card-terminal p-5 sm:p-6 mb-6">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
          <div className="flex-1 relative">
            <GitBranch className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
            <input
              type="text"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAnalyze()}
              placeholder="https://github.com/username/repository"
              className="input-terminal w-full pl-12 py-3 text-base"
            />
          </div>
          <button
            onClick={handleAnalyze}
            disabled={!repoUrl.trim() || isAnalyzing}
            className={cn(
              "action-btn action-btn-primary px-5 sm:px-6 py-3.5 flex items-center justify-center gap-2 w-full sm:w-auto text-sm font-medium",
              (!repoUrl.trim() || isAnalyzing) && "opacity-50 cursor-not-allowed"
            )}
          >
            {isAnalyzing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Analyzing...</span>
              </>
            ) : (
              <>
                <Lightbulb className="w-4 h-4" />
                <span>Analyze Repo</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Search and Stack Filter */}
      <div className="card-terminal p-5 sm:p-6 mb-6">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
          {/* Search */}
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search repositories..."
              className="input-terminal w-full pl-12 py-3 text-base"
            />
          </div>
          
          {/* Stack Filter Dropdown */}
          <Popover>
            <PopoverTrigger asChild>
              <button className="flex items-center justify-center gap-2 px-5 py-3 bg-surface-2 hover:bg-surface-3 rounded-lg text-sm font-medium transition-colors w-full sm:w-auto">
                <Layers className="w-4 h-4 text-muted-foreground" />
                <span className="text-foreground">
                  {selectedStacks.length === 0 
                    ? 'Filter by Stack' 
                    : `${selectedStacks.length} stack${selectedStacks.length > 1 ? 's' : ''}`}
                </span>
                <ChevronDown className="w-4 h-4 text-muted-foreground" />
              </button>
            </PopoverTrigger>
            <PopoverContent className="w-64 p-2 bg-surface-1 border-border" align="end">
              <div className="flex items-center justify-between mb-2 pb-2 border-b border-border">
                <span className="text-xs font-mono text-muted-foreground uppercase">Select Stacks</span>
                {selectedStacks.length > 0 && (
                  <button 
                    onClick={clearStackFilter}
                    className="text-xs text-primary hover:underline"
                  >
                    Clear all
                  </button>
                )}
              </div>
              <div className="max-h-64 overflow-y-auto space-y-1">
                {allStacks.map(stack => (
                  <label
                    key={stack}
                    className="flex items-center gap-3 px-2 py-1.5 rounded hover:bg-surface-2 cursor-pointer transition-colors"
                  >
                    <Checkbox
                      checked={selectedStacks.includes(stack)}
                      onCheckedChange={() => toggleStack(stack)}
                      className="border-muted-foreground data-[state=checked]:bg-primary data-[state=checked]:border-primary"
                    />
                    <span className="text-sm font-mono text-foreground">{stack}</span>
                  </label>
                ))}
              </div>
            </PopoverContent>
          </Popover>
        </div>
      </div>

      {/* Results Table */}
      <div className="card-terminal flex-1 overflow-hidden min-h-[50vh]">
        <div className="overflow-x-auto h-full">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="p-5 text-left text-xs font-mono uppercase tracking-wider text-muted-foreground">Repository</th>
                <th className="p-5 text-left text-xs font-mono uppercase tracking-wider text-muted-foreground">Stacks</th>
                <th className="p-5 text-left text-xs font-mono uppercase tracking-wider text-muted-foreground">Task Ideas</th>
              </tr>
            </thead>
            <tbody>
              {filteredAnalyses.map((analysis) => {
                const approvedCount = analysis.taskIdeas.filter(t => t.status === 'approved').length;
                // Get unique stacks for this repo
                const repoStacks = Array.from(new Set(analysis.taskIdeas.flatMap(t => t.stack))).slice(0, 4);
                
                return (
                  <tr
                    key={analysis.id}
                    onClick={() => handleRepoClick(analysis)}
                    className={cn(
                      "table-row-hover border-b border-border/50",
                      analysis.status === 'completed' && "cursor-pointer"
                    )}
                  >
                    <td className="p-5">
                      <div className="flex items-center gap-3">
                        <GitBranch className="w-5 h-5 text-muted-foreground" />
                        <span className="font-mono text-base text-foreground">{analysis.repoName}</span>
                        <a
                          href={analysis.repoUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="text-muted-foreground hover:text-primary transition-colors"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      </div>
                    </td>
                    <td className="p-5">
                      <div className="flex flex-wrap gap-2">
                        {repoStacks.map(stack => (
                          <span key={stack} className="px-2.5 py-1 bg-surface-2 text-muted-foreground text-xs font-mono rounded">
                            {stack}
                          </span>
                        ))}
                        {analysis.taskIdeas.flatMap(t => t.stack).length > 4 && (
                          <span className="px-2.5 py-1 bg-surface-2 text-muted-foreground text-xs font-mono rounded">
                            +more
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="p-5">
                      <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2">
                          <Lightbulb className="w-5 h-5 text-terminal-amber" />
                          <span className="text-base font-mono">{analysis.taskIdeas.length}</span>
                        </div>
                        {approvedCount > 0 && (
                          <span className="px-2 py-0.5 bg-terminal-green/20 text-terminal-green text-xs font-mono rounded">
                            {approvedCount} approved
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
