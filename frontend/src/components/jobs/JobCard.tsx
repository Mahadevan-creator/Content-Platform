import { DollarSign, Calendar, Clock } from 'lucide-react';
import { Job } from './types';
import { format } from 'date-fns';

interface JobCardProps {
  job: Job;
  onClick: () => void;
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

export function JobCard({ job, onClick }: JobCardProps) {
  const formattedDueDate = job.dueDate ? format(new Date(job.dueDate), 'MMM d') : 'No date';
  
  return (
    <div
      onClick={onClick}
      className="card-terminal p-5 cursor-pointer hover:border-primary/50 transition-all duration-200 group"
    >
      <div className="flex items-start justify-between mb-3">
        <span className={`px-2 py-1 text-xs font-mono rounded border ${categoryColors[job.category]}`}>
          {categoryLabels[job.category]}
        </span>
        <div className="flex items-center gap-1 text-terminal-green font-mono font-bold">
          <DollarSign className="w-4 h-4" />
          <span>{job.award}</span>
        </div>
      </div>
      
      <h3 className="text-lg font-semibold text-foreground mb-2 group-hover:text-primary transition-colors">
        {job.title}
      </h3>
      
      <p className="text-sm text-muted-foreground line-clamp-2 mb-4">
        {job.description}
      </p>
      
      <div className="flex items-center gap-4 text-xs text-muted-foreground mb-3">
        <span className="flex items-center gap-1">
          <Calendar className="w-3.5 h-3.5" />
          Due {formattedDueDate}
        </span>
      </div>
      
      <div className="flex flex-wrap gap-1.5">
        {job.skills.slice(0, 4).map((skill) => (
          <span
            key={skill}
            className="px-2 py-0.5 text-xs bg-surface-2 text-muted-foreground rounded font-mono"
          >
            {skill}
          </span>
        ))}
        {job.skills.length > 4 && (
          <span className="px-2 py-0.5 text-xs bg-surface-2 text-muted-foreground rounded font-mono">
            +{job.skills.length - 4}
          </span>
        )}
      </div>
    </div>
  );
}
