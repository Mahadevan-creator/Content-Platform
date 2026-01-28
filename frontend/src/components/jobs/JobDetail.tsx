import { useState } from 'react';
import { 
  ArrowLeft, 
  DollarSign, 
  Calendar,
  CheckCircle2, 
  Circle,
  Pencil,
  Layers,
  FileText,
  ListChecks,
  Target,
  Send
} from 'lucide-react';
import { Job, ChecklistItem } from './types';
import { Button } from '@/components/ui/button';
import { format } from 'date-fns';

interface JobDetailProps {
  job: Job;
  onBack: () => void;
  onEdit: () => void;
  onApply?: (jobId: string) => void;
  userSkills?: string[];
}

const categoryColors: Record<Job['category'], string> = {
  review: 'bg-terminal-cyan/10 text-terminal-cyan border-terminal-cyan/20',
  testing: 'bg-terminal-amber/10 text-terminal-amber border-terminal-amber/20',
  feature: 'bg-primary/10 text-primary border-primary/20',
  bugfix: 'bg-terminal-red/10 text-terminal-red border-terminal-red/20',
  documentation: 'bg-muted/20 text-muted-foreground border-muted/30',
};

const categoryLabels: Record<Job['category'], string> = {
  review: 'PR Review',
  testing: 'Testing',
  feature: 'Feature',
  bugfix: 'Bug Fix',
  documentation: 'Docs',
};

export function JobDetail({ job, onBack, onEdit, onApply, userSkills = [] }: JobDetailProps) {
  const [checklist, setChecklist] = useState<ChecklistItem[]>(job.checklist);
  const [hasApplied, setHasApplied] = useState(false);
  
  const matchingSkills = job.skills.filter(skill => 
    userSkills.some(us => us.toLowerCase() === skill.toLowerCase())
  );
  const matchPercentage = job.skills.length > 0 
    ? Math.round((matchingSkills.length / job.skills.length) * 100)
    : 0;

  const toggleChecklistItem = (itemId: string) => {
    setChecklist(prev => 
      prev.map(item => 
        item.id === itemId ? { ...item, completed: !item.completed } : item
      )
    );
  };

  const handleApply = () => {
    setHasApplied(true);
    onApply?.(job.id);
  };

  const completedCount = checklist.filter(item => item.completed).length;

  const formattedDueDate = job.dueDate ? format(new Date(job.dueDate), 'MMMM d, yyyy') : 'Not set';

  return (
    <div className="flex flex-col h-full gap-4 sm:gap-6 overflow-y-auto">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="flex flex-col sm:flex-row sm:items-center gap-4">
          <button
            onClick={onBack}
            className="p-2 rounded-lg hover:bg-surface-2 transition-colors w-fit"
          >
            <ArrowLeft className="w-5 h-5 text-muted-foreground" />
          </button>
          <div>
            <div className="flex flex-wrap items-center gap-2 sm:gap-3 mb-1">
              <h2 className="text-lg sm:text-xl font-semibold text-foreground">{job.title}</h2>
              <span className={`px-2 py-1 text-xs font-mono rounded border ${categoryColors[job.category]}`}>
                {categoryLabels[job.category]}
              </span>
            </div>
            <div className="flex items-center gap-4 text-xs sm:text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                <Calendar className="w-4 h-4" />
                Due: {formattedDueDate}
              </span>
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 sm:px-4 py-2 bg-terminal-green/10 rounded-lg border border-terminal-green/20">
            <DollarSign className="w-4 sm:w-5 h-4 sm:h-5 text-terminal-green" />
            <span className="text-lg sm:text-xl font-bold text-terminal-green font-mono">{job.award}</span>
          </div>
          <Button variant="outline" size="sm" onClick={onEdit}>
            <Pencil className="w-4 h-4 mr-2" />
            Edit
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Description */}
          <div className="card-terminal p-6">
            <h3 className="text-sm font-mono uppercase text-muted-foreground mb-4 flex items-center gap-2">
              <FileText className="w-4 h-4 text-primary" />
              Description
            </h3>
            <div className="text-foreground leading-relaxed whitespace-pre-wrap prose prose-invert max-w-none">
              {job.description}
            </div>
          </div>

          {/* Guidelines */}
          <div className="card-terminal p-6">
            <h3 className="text-sm font-mono uppercase text-muted-foreground mb-4 flex items-center gap-2">
              <ListChecks className="w-4 h-4 text-primary" />
              Guidelines
            </h3>
            <p className="text-foreground leading-relaxed whitespace-pre-wrap mb-4">
              {job.guidelines}
            </p>
            {job.guidelinesUrl && (
              <a
                href={job.guidelinesUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 bg-primary/10 text-primary rounded-lg hover:bg-primary/20 transition-colors text-sm font-medium"
              >
                View Design System
              </a>
            )}
          </div>

          {/* Post-Completion Checklist */}
          <div className="card-terminal p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-mono uppercase text-muted-foreground flex items-center gap-2">
                <Target className="w-4 h-4 text-primary" />
                Post-Completion Checklist
              </h3>
              <span className="text-xs text-muted-foreground font-mono">
                {completedCount}/{checklist.length} completed
              </span>
            </div>
            <div className="space-y-3">
              {checklist.map((item) => (
                <button
                  key={item.id}
                  onClick={() => toggleChecklistItem(item.id)}
                  className="w-full flex items-center gap-3 p-3 bg-surface-2 rounded-lg hover:bg-surface-3 transition-colors text-left"
                >
                  {item.completed ? (
                    <CheckCircle2 className="w-5 h-5 text-terminal-green flex-shrink-0" />
                  ) : (
                    <Circle className="w-5 h-5 text-muted-foreground flex-shrink-0" />
                  )}
                  <span className={`text-sm ${item.completed ? 'text-muted-foreground line-through' : 'text-foreground'}`}>
                    {item.label}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Apply Button */}
          <div className="card-terminal p-6">
            <Button 
              className="w-full" 
              size="lg"
              onClick={handleApply}
              disabled={hasApplied}
            >
              <Send className="w-4 h-4 mr-2" />
              {hasApplied ? 'Application Submitted' : 'Apply for this Job'}
            </Button>
            {hasApplied && (
              <p className="text-xs text-muted-foreground text-center mt-3">
                We'll notify you once your application is reviewed.
              </p>
            )}
          </div>

          {/* Skills Required */}
          <div className="card-terminal p-6">
            <h3 className="text-sm font-mono uppercase text-muted-foreground mb-4 flex items-center gap-2">
              <Layers className="w-4 h-4 text-primary" />
              Skills Required
            </h3>
            <div className="flex flex-wrap gap-2">
              {job.skills.map((skill) => {
                const isMatched = matchingSkills.includes(skill);
                return (
                  <span
                    key={skill}
                    className={`px-3 py-1.5 text-xs rounded-lg font-mono border ${
                      isMatched 
                        ? 'bg-terminal-green/10 text-terminal-green border-terminal-green/20' 
                        : 'bg-surface-2 text-muted-foreground border-border'
                    }`}
                  >
                    {skill}
                  </span>
                );
              })}
            </div>
          </div>

          {/* Skill Match */}
          {userSkills.length > 0 && (
            <div className="card-terminal p-6">
              <h3 className="text-sm font-mono uppercase text-muted-foreground mb-4">
                Your Skill Match
              </h3>
              <div className="flex items-center gap-4">
                <div className="relative w-20 h-20">
                  <svg className="w-full h-full transform -rotate-90">
                    <circle
                      cx="40"
                      cy="40"
                      r="36"
                      stroke="hsl(var(--surface-2))"
                      strokeWidth="8"
                      fill="none"
                    />
                    <circle
                      cx="40"
                      cy="40"
                      r="36"
                      stroke="hsl(var(--primary))"
                      strokeWidth="8"
                      fill="none"
                      strokeDasharray={`${(matchPercentage / 100) * 226.2} 226.2`}
                      strokeLinecap="round"
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-lg font-bold text-foreground font-mono">{matchPercentage}%</span>
                  </div>
                </div>
                <div className="flex-1">
                  <p className="text-sm text-muted-foreground">
                    {matchingSkills.length} of {job.skills.length} skills matched
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {matchPercentage >= 80 
                      ? 'Great fit!' 
                      : matchPercentage >= 50 
                        ? 'Good match' 
                        : 'Consider learning more skills'}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Due Date */}
          <div className="card-terminal p-6">
            <h3 className="text-sm font-mono uppercase text-muted-foreground mb-4 flex items-center gap-2">
              <Calendar className="w-4 h-4 text-primary" />
              Due Date
            </h3>
            <div className="flex items-center gap-3 p-3 bg-surface-2 rounded-lg">
              <Calendar className="w-5 h-5 text-terminal-amber" />
              <div>
                <p className="text-foreground font-medium">{formattedDueDate}</p>
                <p className="text-xs text-muted-foreground">Complete by this date</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
