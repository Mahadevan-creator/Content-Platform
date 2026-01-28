import { useState, useMemo } from 'react';
import { Plus, Search, Filter } from 'lucide-react';
import { addWeeks, format } from 'date-fns';
import { Job } from './types';
import { JobCard } from './JobCard';
import { JobDetail } from './JobDetail';
import { EditJobModal } from './EditJobModal';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from '@/hooks/use-toast';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';

// Helper to generate due dates 2-3 weeks from reference dates
const getDueDate = (weeksFromNow: number) => addWeeks(new Date(), weeksFromNow).toISOString();

// Mock data
const mockJobs: Job[] = [
  {
    id: '1',
    title: 'React repo that needs review',
    description: `Review a comprehensive PR that adds a new dashboard feature to the Cal.com platform. The PR includes new React components, state management changes, and API integrations.

You need to review the code quality, ensure best practices are followed, and check for potential bugs or performance issues.

📦 Repository: https://github.com/calcom/cal.com
🔗 PR to Review: https://github.com/calcom/cal.com/pull/1234`,
    guidelines: 'Follow the Cal.com contribution guidelines. Ensure all components follow the existing design patterns. Check for proper TypeScript types and error handling.',
    guidelinesUrl: 'https://components-demo-nu.vercel.app/',
    award: 80,
    skills: ['React', 'TypeScript', 'Code Review', 'Jest'],
    dueDate: getDueDate(2),
    category: 'review',
    status: 'open',
    checklist: [
      { id: '1', label: 'Reviewed all changed files', completed: false },
      { id: '2', label: 'Tested locally', completed: false },
      { id: '3', label: 'Left constructive comments', completed: false },
      { id: '4', label: 'Approved or requested changes', completed: false },
    ],
    repoName: 'cal.com',
    repoUrl: 'https://github.com/calcom/cal.com',
    createdAt: '2024-01-15',
  },
  {
    id: '2',
    title: 'Svelte repo test cases',
    description: `Write comprehensive test cases for a particular PR in the Svelte repository. The PR introduces new reactive features that need thorough testing to ensure backward compatibility and correct behavior.

📦 Repository: https://github.com/sveltejs/svelte
🔗 PR to Test: https://github.com/sveltejs/svelte/pull/567`,
    guidelines: 'Use Vitest for testing. Cover edge cases and error scenarios. Ensure tests are readable and maintainable.',
    award: 100,
    skills: ['Svelte', 'Vitest', 'Testing', 'JavaScript'],
    dueDate: getDueDate(3),
    category: 'testing',
    status: 'open',
    checklist: [
      { id: '1', label: 'Unit tests written', completed: false },
      { id: '2', label: 'Integration tests written', completed: false },
      { id: '3', label: 'Edge cases covered', completed: false },
      { id: '4', label: 'All tests passing', completed: false },
      { id: '5', label: 'Test documentation added', completed: false },
    ],
    repoName: 'svelte',
    repoUrl: 'https://github.com/sveltejs/svelte',
    createdAt: '2024-01-14',
  },
  {
    id: '3',
    title: 'Vue.js documentation update',
    description: `Update the Vue.js documentation to reflect recent API changes. This includes updating code examples, adding new sections, and ensuring all links are working correctly.

📦 Repository: https://github.com/vuejs/vue
🔗 Documentation PR: https://github.com/vuejs/vue/pull/890`,
    guidelines: 'Follow the Vue.js documentation style guide. Use clear and concise language. Include working code examples.',
    award: 60,
    skills: ['Vue.js', 'Technical Writing', 'Markdown'],
    dueDate: getDueDate(2),
    category: 'documentation',
    status: 'open',
    checklist: [
      { id: '1', label: 'All examples updated', completed: false },
      { id: '2', label: 'Links verified', completed: false },
      { id: '3', label: 'Spell check completed', completed: false },
    ],
    repoName: 'vue.js',
    repoUrl: 'https://github.com/vuejs/vue',
    createdAt: '2024-01-13',
  },
  {
    id: '4',
    title: 'Next.js performance fix',
    description: `Fix a performance regression in the Next.js image optimization pipeline. The issue causes slow load times for pages with multiple optimized images.

📦 Repository: https://github.com/vercel/next.js
🔗 Issue to Fix: https://github.com/vercel/next.js/issues/456
🔗 Related PR: https://github.com/vercel/next.js/pull/789`,
    guidelines: 'Profile before and after changes. Ensure backward compatibility. Add regression tests.',
    award: 150,
    skills: ['Next.js', 'Node.js', 'Performance', 'React'],
    dueDate: getDueDate(3),
    category: 'bugfix',
    status: 'open',
    checklist: [
      { id: '1', label: 'Root cause identified', completed: false },
      { id: '2', label: 'Fix implemented', completed: false },
      { id: '3', label: 'Performance benchmarks show improvement', completed: false },
      { id: '4', label: 'Regression tests added', completed: false },
      { id: '5', label: 'Documentation updated', completed: false },
    ],
    repoName: 'next.js',
    repoUrl: 'https://github.com/vercel/next.js',
    createdAt: '2024-01-12',
  },
  {
    id: '5',
    title: 'Add dark mode to component library',
    description: `Implement a complete dark mode theme for the Shadcn component library fork. This includes updating all color tokens, adding theme switching logic, and ensuring accessibility.

📦 Repository: https://github.com/shadcn/ui
🔗 Feature PR: https://github.com/shadcn/ui/pull/234`,
    guidelines: 'Use CSS custom properties for theming. Ensure WCAG AA contrast ratios. Test with screen readers.',
    guidelinesUrl: 'https://components-demo-nu.vercel.app/',
    award: 120,
    skills: ['React', 'CSS', 'Tailwind CSS', 'Accessibility'],
    dueDate: getDueDate(2),
    category: 'feature',
    status: 'open',
    checklist: [
      { id: '1', label: 'Color tokens defined', completed: false },
      { id: '2', label: 'Theme switcher implemented', completed: false },
      { id: '3', label: 'All components themed', completed: false },
      { id: '4', label: 'Accessibility tested', completed: false },
      { id: '5', label: 'Documentation updated', completed: false },
    ],
    repoName: 'ui-components',
    repoUrl: 'https://github.com/shadcn/ui',
    createdAt: '2024-01-11',
  },
];

const allCategories: Job['category'][] = ['review', 'testing', 'feature', 'bugfix', 'documentation'];

const categoryLabels: Record<Job['category'], string> = {
  review: 'PR Review',
  testing: 'Testing',
  feature: 'Feature',
  bugfix: 'Bug Fix',
  documentation: 'Docs',
};

// Mock user skills for skill matching
const userSkills = ['React', 'TypeScript', 'Node.js', 'Testing', 'CSS', 'Tailwind CSS'];

export function JobBoard() {
  const [jobs, setJobs] = useState<Job[]>(mockJobs);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [editingJob, setEditingJob] = useState<Job | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategories, setSelectedCategories] = useState<Job['category'][]>([]);

  const filteredJobs = useMemo(() => {
    return jobs.filter(job => {
      const matchesSearch = !searchQuery || 
        job.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        job.repoName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        job.skills.some(s => s.toLowerCase().includes(searchQuery.toLowerCase()));
      
      const matchesCategory = selectedCategories.length === 0 || 
        selectedCategories.includes(job.category);
      
      return matchesSearch && matchesCategory;
    });
  }, [jobs, searchQuery, selectedCategories]);

  const handleCategoryToggle = (category: Job['category']) => {
    setSelectedCategories(prev =>
      prev.includes(category)
        ? prev.filter(c => c !== category)
        : [...prev, category]
    );
  };

  const handleSaveJob = (job: Job) => {
    setJobs(prev => {
      const existing = prev.find(j => j.id === job.id);
      if (existing) {
        return prev.map(j => j.id === job.id ? job : j);
      }
      return [...prev, job];
    });
    if (selectedJob?.id === job.id) {
      setSelectedJob(job);
    }
  };

  const handleCreateNew = () => {
    setEditingJob(null);
    setIsEditModalOpen(true);
  };

  const handleEditJob = () => {
    if (selectedJob) {
      setEditingJob(selectedJob);
      setIsEditModalOpen(true);
    }
  };

  const handleCloseModal = () => {
    setIsEditModalOpen(false);
    setEditingJob(null);
  };

  const handleApply = (jobId: string) => {
    toast({
      title: "Application Submitted!",
      description: "Your application has been sent. We'll notify you once it's reviewed.",
    });
  };

  if (selectedJob) {
    return (
      <JobDetail
        job={selectedJob}
        onBack={() => setSelectedJob(null)}
        onEdit={handleEditJob}
        onApply={handleApply}
        userSkills={userSkills}
      />
    );
  }

  return (
    <div className="flex flex-col h-full gap-4 sm:gap-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-semibold text-foreground">Job Board</h1>
          <p className="text-xs sm:text-sm text-muted-foreground mt-1">
            Find tasks, contribute to open source, and earn rewards
          </p>
        </div>
        <Button onClick={handleCreateNew} className="w-fit">
          <Plus className="w-4 h-4 mr-2" />
          Create Job
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 sm:gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search jobs, repos, or skills..."
            className="pl-10 bg-surface-1 border-border"
          />
        </div>
        
        <Popover>
          <PopoverTrigger asChild>
            <Button variant="outline" className="gap-2 w-full sm:w-auto">
              <Filter className="w-4 h-4" />
              Categories
              {selectedCategories.length > 0 && (
                <span className="ml-1 px-1.5 py-0.5 bg-primary/20 text-primary rounded text-xs">
                  {selectedCategories.length}
                </span>
              )}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-56 bg-surface-1 border-border" align="end">
            <div className="space-y-3">
              <h4 className="text-sm font-medium text-foreground">Filter by Category</h4>
              {allCategories.map(category => (
                <div key={category} className="flex items-center gap-2">
                  <Checkbox
                    id={category}
                    checked={selectedCategories.includes(category)}
                    onCheckedChange={() => handleCategoryToggle(category)}
                  />
                  <Label htmlFor={category} className="text-sm text-muted-foreground cursor-pointer">
                    {categoryLabels[category]}
                  </Label>
                </div>
              ))}
            </div>
          </PopoverContent>
        </Popover>
      </div>

      {/* Jobs Grid */}
      {filteredJobs.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredJobs.map(job => (
            <JobCard
              key={job.id}
              job={job}
              onClick={() => setSelectedJob(job)}
            />
          ))}
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <p className="text-muted-foreground">No jobs found matching your criteria</p>
            <Button variant="link" onClick={() => { setSearchQuery(''); setSelectedCategories([]); }}>
              Clear filters
            </Button>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      <EditJobModal
        job={editingJob}
        isOpen={isEditModalOpen}
        onClose={handleCloseModal}
        onSave={handleSaveJob}
      />
    </div>
  );
}
