import { useState, useEffect } from 'react';
import { X, Plus, Trash2, CalendarIcon } from 'lucide-react';
import { Job, ChecklistItem } from './types';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { format, addWeeks } from 'date-fns';
import { cn } from '@/lib/utils';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface EditJobModalProps {
  job: Job | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: (job: Job) => void;
}

const categories: { value: Job['category']; label: string }[] = [
  { value: 'review', label: 'PR Review' },
  { value: 'testing', label: 'Testing' },
  { value: 'feature', label: 'Feature' },
  { value: 'bugfix', label: 'Bug Fix' },
  { value: 'documentation', label: 'Documentation' },
];

// Default due date is 2-3 weeks from now
const getDefaultDueDate = () => addWeeks(new Date(), 2);

export function EditJobModal({ job, isOpen, onClose, onSave }: EditJobModalProps) {
  const [formData, setFormData] = useState<Partial<Job>>(
    job || {
      title: '',
      description: '',
      guidelines: '',
      guidelinesUrl: '',
      githubPrUrl: '',
      award: 50,
      skills: [],
      dueDate: getDefaultDueDate().toISOString(),
      category: 'review',
      status: 'open',
      checklist: [],
      repoName: '',
      repoUrl: '',
    }
  );
  const [skillInput, setSkillInput] = useState('');
  const [checklistInput, setChecklistInput] = useState('');

  // Reset form data when job changes or modal opens
  useEffect(() => {
    if (isOpen) {
      setFormData(
        job || {
          title: '',
          description: '',
          guidelines: '',
          guidelinesUrl: '',
          githubPrUrl: '',
          award: 50,
          skills: [],
          dueDate: getDefaultDueDate().toISOString(),
          category: 'review',
          status: 'open',
          checklist: [],
          repoName: '',
          repoUrl: '',
        }
      );
      setSkillInput('');
      setChecklistInput('');
    }
  }, [job, isOpen]);

  if (!isOpen) return null;

  const handleAddSkill = () => {
    if (skillInput.trim() && !formData.skills?.includes(skillInput.trim())) {
      setFormData(prev => ({
        ...prev,
        skills: [...(prev.skills || []), skillInput.trim()],
      }));
      setSkillInput('');
    }
  };

  const handleRemoveSkill = (skill: string) => {
    setFormData(prev => ({
      ...prev,
      skills: prev.skills?.filter(s => s !== skill) || [],
    }));
  };

  const handleAddChecklistItem = () => {
    if (checklistInput.trim()) {
      const newItem: ChecklistItem = {
        id: crypto.randomUUID(),
        label: checklistInput.trim(),
        completed: false,
      };
      setFormData(prev => ({
        ...prev,
        checklist: [...(prev.checklist || []), newItem],
      }));
      setChecklistInput('');
    }
  };

  const handleRemoveChecklistItem = (id: string) => {
    setFormData(prev => ({
      ...prev,
      checklist: prev.checklist?.filter(item => item.id !== id) || [],
    }));
  };

  const handleDateSelect = (date: Date | undefined) => {
    if (date) {
      setFormData(prev => ({ ...prev, dueDate: date.toISOString() }));
    }
  };

  const handleSave = () => {
    const savedJob: Job = {
      id: job?.id || crypto.randomUUID(),
      title: formData.title || '',
      description: formData.description || '',
      guidelines: formData.guidelines || '',
      guidelinesUrl: formData.guidelinesUrl,
      githubPrUrl: formData.githubPrUrl,
      award: formData.award || 50,
      skills: formData.skills || [],
      dueDate: formData.dueDate || getDefaultDueDate().toISOString(),
      category: formData.category || 'review',
      status: formData.status || 'open',
      checklist: formData.checklist || [],
      repoName: formData.repoName || '',
      repoUrl: formData.repoUrl || '',
      createdAt: job?.createdAt || new Date().toISOString(),
    };
    onSave(savedJob);
    onClose();
  };

  const selectedDate = formData.dueDate ? new Date(formData.dueDate) : undefined;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-surface-1 border border-border rounded-xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-border">
          <h2 className="text-lg font-semibold text-foreground">
            {job ? 'Edit Job' : 'Create New Job'}
          </h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-surface-2 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-muted-foreground" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Title & Category */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Job Title</Label>
              <Input
                value={formData.title}
                onChange={e => setFormData(prev => ({ ...prev, title: e.target.value }))}
                placeholder="React repo PR review"
                className="bg-surface-2 border-border"
              />
            </div>
            <div className="space-y-2">
              <Label>Category</Label>
              <Select
                value={formData.category}
                onValueChange={value => setFormData(prev => ({ ...prev, category: value as Job['category'] }))}
              >
                <SelectTrigger className="bg-surface-2 border-border">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-surface-1 border-border">
                  {categories.map(cat => (
                    <SelectItem key={cat.value} value={cat.value}>
                      {cat.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Award & Due Date */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Award ($)</Label>
              <Input
                type="number"
                value={formData.award}
                onChange={e => setFormData(prev => ({ ...prev, award: Number(e.target.value) }))}
                className="bg-surface-2 border-border"
              />
            </div>
            <div className="space-y-2">
              <Label>Due Date</Label>
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className={cn(
                      "w-full justify-start text-left font-normal bg-surface-2 border-border",
                      !selectedDate && "text-muted-foreground"
                    )}
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {selectedDate ? format(selectedDate, "PPP") : <span>Pick a date</span>}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0 bg-surface-1 border-border" align="start">
                  <Calendar
                    mode="single"
                    selected={selectedDate}
                    onSelect={handleDateSelect}
                    initialFocus
                    disabled={(date) => date < new Date()}
                  />
                </PopoverContent>
              </Popover>
            </div>
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label>Description</Label>
            <p className="text-xs text-muted-foreground mb-1">
              Include repository and PR links directly in the description text.
            </p>
            <Textarea
              value={formData.description}
              onChange={e => setFormData(prev => ({ ...prev, description: e.target.value }))}
              placeholder="Describe the task in detail. Include links to the repository (https://github.com/org/repo) and specific PR (https://github.com/org/repo/pull/123) that needs attention..."
              rows={6}
              className="bg-surface-2 border-border resize-none"
            />
          </div>

          {/* Guidelines */}
          <div className="space-y-2">
            <Label>Guidelines</Label>
            <Textarea
              value={formData.guidelines}
              onChange={e => setFormData(prev => ({ ...prev, guidelines: e.target.value }))}
              placeholder="List the guidelines for completing this task..."
              rows={4}
              className="bg-surface-2 border-border resize-none"
            />
          </div>

          {/* Guidelines URL */}
          <div className="space-y-2">
            <Label>Design System / Guidelines URL (optional)</Label>
            <Input
              value={formData.guidelinesUrl}
              onChange={e => setFormData(prev => ({ ...prev, guidelinesUrl: e.target.value }))}
              placeholder="https://components-demo-nu.vercel.app/"
              className="bg-surface-2 border-border"
            />
          </div>

          {/* Skills */}
          <div className="space-y-2">
            <Label>Skills Required</Label>
            <div className="flex gap-2">
              <Input
                value={skillInput}
                onChange={e => setSkillInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), handleAddSkill())}
                placeholder="Add a skill..."
                className="bg-surface-2 border-border"
              />
              <Button type="button" variant="outline" onClick={handleAddSkill}>
                <Plus className="w-4 h-4" />
              </Button>
            </div>
            <div className="flex flex-wrap gap-2 mt-2">
              {formData.skills?.map(skill => (
                <span
                  key={skill}
                  className="inline-flex items-center gap-1 px-2 py-1 bg-surface-2 text-muted-foreground rounded text-sm font-mono"
                >
                  {skill}
                  <button onClick={() => handleRemoveSkill(skill)} className="hover:text-destructive">
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          </div>

          {/* Checklist */}
          <div className="space-y-2">
            <Label>Post-Completion Checklist</Label>
            <div className="flex gap-2">
              <Input
                value={checklistInput}
                onChange={e => setChecklistInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), handleAddChecklistItem())}
                placeholder="Add a checklist item..."
                className="bg-surface-2 border-border"
              />
              <Button type="button" variant="outline" onClick={handleAddChecklistItem}>
                <Plus className="w-4 h-4" />
              </Button>
            </div>
            <div className="space-y-2 mt-2">
              {formData.checklist?.map(item => (
                <div
                  key={item.id}
                  className="flex items-center gap-2 p-2 bg-surface-2 rounded-lg"
                >
                  <span className="flex-1 text-sm text-foreground">{item.label}</span>
                  <button
                    onClick={() => handleRemoveChecklistItem(item.id)}
                    className="p-1 hover:text-destructive transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-border">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSave}>
            {job ? 'Save Changes' : 'Create Job'}
          </Button>
        </div>
      </div>
    </div>
  );
}
