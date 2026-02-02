import { useState, useMemo, useEffect, useCallback, useRef } from 'react';
import { 
  Mail, 
  FileText, 
  Video, 
  FileSignature, 
  Wrench,
  Github,
  Slack,
  MoreHorizontal,
  User,
  Plus,
  Search,
  Filter,
  X,
  CheckCircle,
  Loader2
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { getGitGrade, getGradePillClass } from '@/lib/gitScore';
import { Checkbox } from '@/components/ui/checkbox';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuCheckboxItem,
} from '@/components/ui/dropdown-menu';
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from '@/components/ui/pagination';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import { CandidateProfile } from './CandidateProfile';
import { AddExpertsModal } from './modals/AddExpertsModal';
import { SendEmailModal } from './modals/SendEmailModal';
import { SendTestModal } from './modals/SendTestModal';
import { ScheduleInterviewModal } from './modals/ScheduleInterviewModal';
import { InterviewResultModal } from './modals/InterviewResultModal';
import { SendContractModal } from './modals/SendContractModal';
import { ProvisionToolsModal } from './modals/ProvisionToolsModal';
import { ProcessingNotification } from './modals/ProcessingNotification';
import { ThemeToggle } from '@/components/ThemeToggle';
import { Skeleton } from '@/components/ui/skeleton';
import { ExpertsFilters, defaultFilters, type FilterState } from './ExpertsFilters';
import type { ContributorAnalysis } from '@/lib/api';
import { useExperts, type MongoDBExpert, type ExpertWithDisplay } from '@/hooks/useExperts';
import { useToast } from '@/hooks/use-toast';

type Expert = ExpertWithDisplay;

const workflowLabels = {
  emailSent: {
    pending: { label: 'Not Sent', className: 'text-muted-foreground' },
    sent: { label: 'Sent', className: 'text-warning' },
    opened: { label: 'Opened', className: 'text-success' },
  },
  testSent: {
    pending: { label: 'Not Sent', className: 'text-muted-foreground' },
    sent: { label: 'Sent', className: 'text-warning' },
    completed: { label: 'Completed', className: 'text-info' },
    passed: { label: 'Passed', className: 'text-success' },
    failed: { label: 'Failed', className: 'text-danger' },
  },
  interview: {
    pending: { label: 'Not Set', className: 'text-muted-foreground' },
    scheduled: { label: 'Scheduled', className: 'text-warning' },
    completed: { label: 'Completed', className: 'text-success' },
  },
  interviewResult: {
    pending: { label: '—', className: 'text-muted-foreground' },
    pass: { label: 'Pass', className: 'text-success' },
    fail: { label: 'Fail', className: 'text-danger' },
    strong_pass: { label: 'Strong Pass', className: 'text-success font-bold' },
  },
};

// Extract all unique skills for the filter (will be computed from actual experts)

const statusConfig = {
  available: { label: 'Available', className: 'badge-success' },
  responded: { label: 'Responded', className: 'badge-responded' },
  assessment: { label: 'Assessment', className: 'badge-warning' },
  interviewing: { label: 'Interviewing', className: 'badge-warning' },
  onboarded: { label: 'Onboarded', className: 'badge-info' },
  contracted: { label: 'Contracted', className: 'badge-success' },
};

const ITEMS_PER_PAGE = 15;

/** Interview can only be scheduled when candidate has passed the test (or completed it). */
function canScheduleInterview(expert: Expert): boolean {
  const testSent = expert.workflow?.testSent ?? 'pending';
  return testSent === 'passed' || testSent === 'completed';
}

/** Contract can only be sent when interview result is pass or strong_pass. */
function canSendContract(expert: Expert): boolean {
  const result = expert.workflow?.interviewResult ?? 'pending';
  return result === 'pass' || result === 'strong_pass';
}

/** Expert has signed contract (status is contracted). */
function isContracted(expert: Expert): boolean {
  return (expert as any).status === 'contracted';
}

/** Send Email disabled when status is interviewing, assessment, contracted, or onboarded. */
function canSendEmail(expert: Expert): boolean {
  const s = (expert as any).status;
  return s !== 'interviewing' && s !== 'assessment' && s !== 'contracted' && s !== 'onboarded';
}

/** Provision Tools enabled only when status is contracted or onboarded. */
function canProvisionTools(expert: Expert): boolean {
  const s = (expert as any).status;
  return s === 'contracted' || s === 'onboarded';
}

export function ExpertsTable() {
  const { experts: allExperts, loading, error, refetch } = useExperts();
  const { toast } = useToast();
  const [selectedExperts, setSelectedExperts] = useState<Set<string>>(new Set());
  const [viewingProfile, setViewingProfile] = useState<Expert | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState<FilterState>(defaultFilters);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  
  // Modal states
  const [addExpertsOpen, setAddExpertsOpen] = useState(false);
  const [emailModalOpen, setEmailModalOpen] = useState(false);
  const [testModalOpen, setTestModalOpen] = useState(false);
  const [interviewModalOpen, setInterviewModalOpen] = useState(false);
  const [interviewResultModalOpen, setInterviewResultModalOpen] = useState(false);
  const [contractModalOpen, setContractModalOpen] = useState(false);
  const [provisionModalOpen, setProvisionModalOpen] = useState(false);
  const [selectedExpert, setSelectedExpert] = useState<Expert | null>(null);
  const [processingJobId, setProcessingJobId] = useState<string | null>(null);
  const tableScrollRef = useRef<HTMLDivElement>(null);

  // HRW score filter uses fixed 0–100 range (min and max set by slider thumbs)

  // Filter experts based on search and all filters
  const filteredExperts = useMemo(() => {
    return allExperts.filter(expert => {
      // Search filter
      const searchLower = searchQuery.toLowerCase();
      const matchesSearch = !searchQuery || 
        expert.name.toLowerCase().includes(searchLower) ||
        expert.email.toLowerCase().includes(searchLower) ||
        expert.skills.some(skill => skill.toLowerCase().includes(searchLower));
      
      // Location filter (case-insensitive comparison - both sides normalized)
      const matchesLocation = filters.locations.size === 0 || 
        (expert.location && filters.locations.has(expert.location.trim().toLowerCase()));
      
      // Skills filter
      const matchesSkills = filters.skills.size === 0 || 
        expert.skills.some(skill => filters.skills.has(skill));
      
      // Email found filter
      const matchesEmail = filters.emailFound === 'all' ||
        (filters.emailFound === 'found' && expert.email && expert.email.trim() !== '') ||
        (filters.emailFound === 'not-found' && (!expert.email || expert.email.trim() === ''));
      
      // Email status filter (sent / not sent)
      const emailSentStatus = expert.workflow?.emailSent ?? 'pending';
      const matchesEmailStatus = filters.emailStatus === 'all' ||
        (filters.emailStatus === 'sent' && (emailSentStatus === 'sent' || emailSentStatus === 'opened')) ||
        (filters.emailStatus === 'not_sent' && emailSentStatus === 'pending');
      
      // Status filter
      const matchesStatus = filters.status.size === 0 || 
        filters.status.has(expert.status);
      
      // Git grade filter
      const gitGrade = getGitGrade(expert.gitScore);
      const matchesGitGrade = filters.gitGrades.size === 0 || 
        filters.gitGrades.has(gitGrade);
      
      // Interview result filter
      const matchesInterviewResult = filters.interviewResult === 'all' ||
        expert.workflow.interviewResult === filters.interviewResult;
      
      // HRW score filter - filter scores within the range
      const hrwScore = (expert as any).hrwScore || (expert as any).hrw_score || 0;
      const minScore = Math.min(...filters.hrwScoreRange);
      const maxScore = Math.max(...filters.hrwScoreRange);
      const matchesHrwScore = hrwScore >= minScore && hrwScore <= maxScore;
      
      return matchesSearch && matchesLocation && matchesSkills && matchesEmail && 
             matchesEmailStatus && matchesStatus && matchesGitGrade && matchesInterviewResult && matchesHrwScore;
    });
  }, [allExperts, searchQuery, filters]);

  const clearFilters = () => {
    setSearchQuery('');
    setFilters({
      ...defaultFilters,
      hrwScoreRange: [0, 100],
    });
    setCurrentPage(1); // Reset to first page when clearing filters
  };

  // Pagination calculations
  const totalPages = Math.ceil(filteredExperts.length / ITEMS_PER_PAGE);
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
  const endIndex = startIndex + ITEMS_PER_PAGE;
  const paginatedExperts = filteredExperts.slice(startIndex, endIndex);

  // Reset to page 1 when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, filters]);

  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (filters.locations.size > 0) count++;
    if (filters.skills.size > 0) count++;
    if (filters.emailFound !== 'all') count++;
    if (filters.emailStatus !== 'all') count++;
    if (filters.status.size > 0) count++;
    if (filters.gitGrades.size > 0) count++;
    if (filters.interviewResult !== 'all') count++;
    // HRW filter is active when not the full 0–100 range
    const isDefaultHrwRange = filters.hrwScoreRange[0] === 0 && filters.hrwScoreRange[1] === 100;
    if (!isDefaultHrwRange) count++;
    return count;
  }, [filters]);

  const toggleSelection = (id: string) => {
    setSelectedExperts(prev => {
      const newSelection = new Set(prev);
      if (newSelection.has(id)) {
        newSelection.delete(id);
      } else {
        newSelection.add(id);
      }
      return newSelection;
    });
  };

  const toggleAll = () => {
    if (filteredExperts.length === 0) return;
    
    const allFilteredIds = filteredExperts
      .map(e => e.id || (e as any)._id || e.github_username)
      .filter(Boolean) as string[];
    
    const allSelected = allFilteredIds.length > 0 && 
      allFilteredIds.every(id => selectedExperts.has(id));
    
    setSelectedExperts(prev => {
      const newSelection = new Set(prev);
      
      if (allSelected) {
        // Deselect all filtered experts
        allFilteredIds.forEach(id => newSelection.delete(id));
      } else {
        // Select all filtered experts (across all pages)
        allFilteredIds.forEach(id => newSelection.add(id));
      }
      
      return newSelection;
    });
  };

  const hasSelection = selectedExperts.size > 0;

  // Helper to find expert by ID (use allExperts so selection works regardless of filters)
  const findExpertById = useCallback((id: string) =>
    allExperts.find((e) => String((e as any).id ?? (e as any)._id ?? e.github_username ?? '') === String(id)), [allExperts]);

  // Bulk interview: disabled when 1 selected but that expert hasn't passed the test or is contracted
  const bulkInterviewFirstExpert = useMemo(() => {
    if (selectedExperts.size !== 1) return null;
    const firstId = Array.from(selectedExperts)[0];
    return firstId ? findExpertById(firstId) : null;
  }, [selectedExperts, findExpertById]);
  const bulkInterviewDisabled = selectedExperts.size === 1 && (!bulkInterviewFirstExpert || isContracted(bulkInterviewFirstExpert) || !canScheduleInterview(bulkInterviewFirstExpert));

  // Bulk test: disabled when any selected expert is contracted
  const bulkTestDisabled = useMemo(() => {
    return Array.from(selectedExperts).some((id) => {
      const expert = findExpertById(id);
      return expert && isContracted(expert);
    });
  }, [selectedExperts, findExpertById]);

  // Bulk email: disabled when all selected experts have status interviewing/assessment/contracted/onboarded
  const bulkEmailDisabled = useMemo(() => {
    if (selectedExperts.size === 0) return true;
    const eligible = Array.from(selectedExperts)
      .map((id) => findExpertById(id))
      .filter((e): e is Expert => !!e && canSendEmail(e));
    return eligible.length === 0;
  }, [selectedExperts, findExpertById]);

  // Bulk contract: disabled when 1 selected but that expert can't receive contract (not pass/strong_pass or contracted)
  const bulkContractFirstExpert = useMemo(() => {
    if (selectedExperts.size !== 1) return null;
    const firstId = Array.from(selectedExperts)[0];
    return firstId ? findExpertById(firstId) : null;
  }, [selectedExperts, findExpertById]);
  const bulkContractDisabled = selectedExperts.size !== 1 || !bulkContractFirstExpert || isContracted(bulkContractFirstExpert) || !canSendContract(bulkContractFirstExpert);

  // Bulk provision: disabled when no selected expert has status contracted or onboarded
  const bulkProvisionDisabled = useMemo(() => {
    if (selectedExperts.size === 0) return true;
    const eligible = Array.from(selectedExperts)
      .map((id) => findExpertById(id))
      .filter((e): e is Expert => !!e && canProvisionTools(e));
    return eligible.length === 0;
  }, [selectedExperts, findExpertById]);

  // At least one selected expert has email — show Send Email only then
  const hasSelectedWithEmail = useMemo(() => {
    return Array.from(selectedExperts)
      .map((id) => findExpertById(id))
      .some((e) => !!e && !!e.email?.trim());
  }, [selectedExperts, findExpertById]);

  // Action handlers for individual expert
  const handleSendEmail = (expert: Expert) => {
    setSelectedExpert(expert);
    setEmailModalOpen(true);
  };

  const getEmailModalCandidates = (): Array<{ email: string; name?: string }> => {
    if (selectedExpert) {
      if (!selectedExpert.email || !canSendEmail(selectedExpert)) return [];
      return [{ email: selectedExpert.email, name: selectedExpert.name }];
    }
    const ids = Array.from(selectedExperts);
    return ids
      .map((id) => findExpertById(id))
      .filter((e): e is Expert => !!e && !!e.email && canSendEmail(e))
      .map((e) => ({ email: e.email, name: e.name }));
  };

  const getTestModalCandidates = (): Array<{ email: string; name?: string }> => {
    // Bulk: return all selected experts with email (exclude contracted)
    if (selectedExperts.size > 1) {
      return Array.from(selectedExperts)
        .map((id) => findExpertById(id))
        .filter((e): e is Expert => !!e && !!e.email && !isContracted(e))
        .map((e) => ({ email: e.email, name: e.name }));
    }
    // Single: use selectedExpert (exclude contracted)
    if (selectedExpert?.email && !isContracted(selectedExpert)) {
      return [{ email: selectedExpert.email, name: selectedExpert.name }];
    }
    return [];
  };

  const handleSendTest = (expert: Expert) => {
    if (isContracted(expert)) {
      toast({
        title: 'Cannot send test',
        description: 'This candidate has already signed the contract.',
        variant: 'destructive',
      });
      return;
    }
    setSelectedExpert(expert);
    setTestModalOpen(true);
  };

  const handleScheduleInterview = (expert: Expert) => {
    if (isContracted(expert)) {
      toast({
        title: 'Cannot schedule interview',
        description: 'This candidate has already signed the contract.',
        variant: 'destructive',
      });
      return;
    }
    if (!canScheduleInterview(expert)) {
      const testSent = expert.workflow?.testSent ?? 'pending';
      const reason = testSent === 'failed'
        ? 'This candidate failed the assessment.'
        : 'This candidate has not yet passed the assessment. Schedule an interview only after they pass.';
      toast({
        title: 'Cannot schedule interview',
        description: reason,
        variant: 'destructive',
      });
      return;
    }
    setSelectedExpert(expert);
    setInterviewModalOpen(true);
  };

  const handleSendContract = (expert: Expert) => {
    if (isContracted(expert)) {
      toast({
        title: 'Cannot send contract',
        description: 'This candidate has already signed the contract.',
        variant: 'destructive',
      });
      return;
    }
    if (!canSendContract(expert)) {
      toast({
        title: 'Cannot send contract',
        description: 'Candidate must pass the interview first (Result: Pass or Strong Pass).',
        variant: 'destructive',
      });
      return;
    }
    setSelectedExpert(expert);
    setContractModalOpen(true);
  };

  const handleSetInterviewResult = (expert: Expert) => {
    setSelectedExpert(expert);
    setInterviewResultModalOpen(true);
  };

  const handleProvisionTools = (expert: Expert) => {
    setSelectedExpert(expert);
    setProvisionModalOpen(true);
  };

  // Bulk action handlers
  const handleBulkEmail = () => {
    setSelectedExpert(null);
    setEmailModalOpen(true);
  };

  const handleBulkTest = () => {
    if (bulkTestDisabled) {
      toast({
        title: 'Cannot send test',
        description: 'One or more selected candidates have already signed the contract.',
        variant: 'destructive',
      });
      return;
    }
    const firstId = Array.from(selectedExperts)[0];
    const firstExpert = firstId ? findExpertById(firstId) : null;
    setSelectedExpert(firstExpert || null);
    setTestModalOpen(true);
  };

  const handleBulkInterview = () => {
    if (selectedExperts.size > 1) {
      toast({
        title: 'One candidate at a time',
        description: 'Interviews can only be scheduled for one candidate at a time. Please select a single expert.',
        variant: 'destructive',
      });
      return;
    }
    const firstId = Array.from(selectedExperts)[0];
    const firstExpert = firstId ? findExpertById(firstId) : null;
    if (!firstExpert) return;
    if (isContracted(firstExpert)) {
      toast({
        title: 'Cannot schedule interview',
        description: 'This candidate has already signed the contract.',
        variant: 'destructive',
      });
      return;
    }
    if (!canScheduleInterview(firstExpert)) {
      const testSent = firstExpert?.workflow?.testSent ?? 'pending';
      const reason = testSent === 'failed'
        ? 'This candidate failed the assessment.'
        : 'This candidate has not yet passed the assessment. Schedule an interview only after they pass.';
      toast({
        title: 'Cannot schedule interview',
        description: reason,
        variant: 'destructive',
      });
      return;
    }
    setSelectedExpert(firstExpert);
    setInterviewModalOpen(true);
  };

  const handleBulkContract = () => {
    if (bulkContractDisabled) {
      const first = bulkContractFirstExpert;
      if (!first) {
        toast({ title: 'Select one candidate', variant: 'destructive' });
        return;
      }
      if (isContracted(first)) {
        toast({
          title: 'Cannot send contract',
          description: 'This candidate has already signed the contract.',
          variant: 'destructive',
        });
        return;
      }
      if (!canSendContract(first)) {
        toast({
          title: 'Cannot send contract',
          description: 'Candidate must pass the interview first (Result: Pass or Strong Pass).',
          variant: 'destructive',
        });
        return;
      }
      return;
    }
    setSelectedExpert(bulkContractFirstExpert);
    setContractModalOpen(true);
  };

  const handleBulkProvision = () => {
    setSelectedExpert(null);
    setProvisionModalOpen(true);
  };

  // Show profile view if viewing a candidate
  if (viewingProfile) {
    return (
      <CandidateProfile
        expert={viewingProfile}
        onBack={() => setViewingProfile(null)}
      />
    );
  }

  // Loading: show only the loader, nothing else
  if (loading) {
    return (
      <div className="flex flex-col h-full min-h-0 flex-1 items-center justify-center gap-4">
        <Loader2 className="h-12 w-12 animate-spin text-primary" aria-hidden />
        <p className="text-base font-medium text-foreground">Loading experts</p>
        <p className="text-xs text-muted-foreground font-mono">Fetching your talent pool...</p>
        <div className="flex gap-2 mt-2">
          <Skeleton className="h-3 w-16 rounded-full" />
          <Skeleton className="h-3 w-20 rounded-full" />
          <Skeleton className="h-3 w-14 rounded-full" />
        </div>
      </div>
    );
  }

  // Error: show only error message
  if (error) {
    return (
      <div className="flex flex-col h-full min-h-0 flex-1 items-center justify-center p-8">
        <div className="text-center">
          <p className="text-danger font-medium">Error loading experts</p>
          <p className="text-sm text-muted-foreground mt-1">{error.message}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full min-h-0 w-full">
      {/* Header with actions - stays fixed while table scrolls */}
      <div className="flex flex-col gap-4 mb-4 shrink-0">
        <div className="flex flex-col gap-4">
          {/* Top Row: Title (left), Add Experts + Theme toggle (right, same line) */}
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <h2 className="text-xl sm:text-2xl font-semibold text-foreground">Experts</h2>
                {selectedExperts.size > 0 && (
                  <Badge variant="default" className="text-xs font-mono">
                    {selectedExperts.size} selected
                  </Badge>
                )}
              </div>
              <p className="text-xs sm:text-sm text-muted-foreground font-mono">
                Showing {paginatedExperts.length > 0 ? startIndex + 1 : 0}-{Math.min(endIndex, filteredExperts.length)} of {filteredExperts.length} experts
                {filteredExperts.length !== allExperts.length && ` (${allExperts.length} total)`}
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <Button 
                onClick={() => setAddExpertsOpen(true)}
                size="default"
                className="flex items-center gap-2 bg-primary hover:bg-primary/90 text-primary-foreground shadow-sm"
              >
                <Plus className="w-4 h-4" />
                Add Experts
              </Button>
              <ThemeToggle variant="icon" size="icon" className="shrink-0" />
            </div>
          </div>
          
          {/* Bulk Actions Bar */}
          {hasSelection && (
            <div className="flex flex-wrap items-center gap-2 p-3 bg-primary/5 border border-primary/20 rounded-lg animate-fade-in">
              <div className="flex items-center gap-2 text-xs sm:text-sm text-muted-foreground font-mono mr-2">
                <span className="text-primary font-semibold">{selectedExperts.size}</span>
                <span>expert{selectedExperts.size !== 1 ? 's' : ''} selected</span>
              </div>
              <div className="flex flex-wrap items-center gap-2 ml-auto">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleBulkEmail}
                  disabled={bulkEmailDisabled}
                  title={bulkEmailDisabled ? 'All selected candidates are in interviewing, assessment, contracted, or onboarded status' : undefined}
                  className="flex items-center gap-2 text-xs sm:text-sm h-8"
                >
                  <Mail className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Send Email</span>
                  <span className="sm:hidden">Email</span>
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleBulkTest}
                  disabled={bulkTestDisabled}
                  title={bulkTestDisabled ? 'One or more selected candidates have already signed the contract' : undefined}
                  className="flex items-center gap-2 text-xs sm:text-sm h-8"
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Send Test</span>
                  <span className="sm:hidden">Test</span>
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleBulkInterview}
                  className="flex items-center gap-2 text-xs sm:text-sm h-8"
                  disabled={bulkInterviewDisabled}
                  title={
                    selectedExperts.size > 1
                      ? 'Interviews can only be scheduled for one candidate at a time'
                      : bulkInterviewDisabled && bulkInterviewFirstExpert
                        ? isContracted(bulkInterviewFirstExpert)
                          ? 'Candidate has already signed the contract'
                          : 'Candidate must pass the assessment first'
                        : undefined
                  }
                >
                  <Video className="w-3.5 h-3.5" />
                  <span className="hidden lg:inline">Interview</span>
                  <span className="lg:hidden">Interview</span>
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleBulkContract}
                  disabled={bulkContractDisabled}
                  title={
                    bulkContractDisabled
                      ? selectedExperts.size !== 1
                        ? 'Select exactly one candidate'
                        : bulkContractFirstExpert && isContracted(bulkContractFirstExpert)
                          ? 'This candidate has already signed the contract'
                          : bulkContractFirstExpert && !canSendContract(bulkContractFirstExpert)
                            ? 'Candidate must pass the interview first (Result: Pass or Strong Pass)'
                            : undefined
                      : undefined
                  }
                  className="flex items-center gap-2 text-xs sm:text-sm h-8"
                >
                  <FileSignature className="w-3.5 h-3.5" />
                  <span className="hidden lg:inline">Contract</span>
                  <span className="lg:hidden">Contract</span>
                </Button>
                <Button
                  variant="default"
                  size="sm"
                  onClick={handleBulkProvision}
                  disabled={bulkProvisionDisabled}
                  title={bulkProvisionDisabled ? 'Provision Tools is only available for candidates with contracted or onboarded status' : undefined}
                  className="flex items-center gap-2 text-xs sm:text-sm h-8 bg-primary hover:bg-primary/90"
                >
                  <Wrench className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Provision</span>
                  <span className="sm:hidden">Provision</span>
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedExperts(new Set())}
                  className="flex items-center gap-2 text-xs sm:text-sm h-8 text-muted-foreground hover:text-foreground"
                >
                  <X className="w-3.5 h-3.5" />
                  Clear
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Search and Filter Bar */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
            <Input
              placeholder="Search by name, email, or skill..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 bg-surface-1 border-border h-10 focus:ring-2 focus:ring-primary/20"
            />
          </div>
          
          <div className="flex items-center gap-2">
            <Sheet open={filtersOpen} onOpenChange={setFiltersOpen}>
              <SheetTrigger asChild>
                <Button variant="outline" size="default" className="flex items-center gap-2 h-10">
                  <Filter className="w-4 h-4" />
                  <span className="hidden sm:inline">Filters</span>
                  {activeFilterCount > 0 && (
                    <Badge variant="default" className="ml-1 px-1.5 py-0.5 text-xs h-5 min-w-[1.25rem] flex items-center justify-center">
                      {activeFilterCount}
                    </Badge>
                  )}
                </Button>
              </SheetTrigger>
              <SheetContent side="right" className="w-[400px] sm:w-[450px] overflow-y-auto bg-surface-1 border-border">
                <SheetHeader>
                  <SheetTitle className="text-foreground">Filter Experts</SheetTitle>
                </SheetHeader>
                <div className="mt-6">
                  <ExpertsFilters
                    experts={allExperts}
                    filters={filters}
                    onFiltersChange={setFilters}
                    onClearFilters={clearFilters}
                  />
                </div>
              </SheetContent>
            </Sheet>

            {(searchQuery || activeFilterCount > 0) && (
              <Button 
                variant="ghost" 
                size="default" 
                onClick={clearFilters} 
                className="text-muted-foreground hover:text-foreground h-10"
              >
                <X className="w-4 h-4 mr-2" />
                Clear
              </Button>
            )}
          </div>
        </div>
        
        {/* Active Filter Badges */}
        {activeFilterCount > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            {filters.locations.size > 0 && (
              <Badge variant="secondary" className="text-xs">
                {filters.locations.size} location{filters.locations.size !== 1 ? 's' : ''}
              </Badge>
            )}
            {filters.skills.size > 0 && (
              <Badge variant="secondary" className="text-xs">
                {filters.skills.size} skill{filters.skills.size !== 1 ? 's' : ''}
              </Badge>
            )}
            {filters.emailFound !== 'all' && (
              <Badge variant="secondary" className="text-xs">
                Email: {filters.emailFound === 'found' ? 'Found' : 'Not Found'}
              </Badge>
            )}
            {filters.emailStatus !== 'all' && (
              <Badge variant="secondary" className="text-xs">
                Email: {filters.emailStatus === 'sent' ? 'Sent' : 'Not Sent'}
              </Badge>
            )}
            {filters.status.size > 0 && (
              <Badge variant="secondary" className="text-xs">
                {filters.status.size} status{filters.status.size !== 1 ? 'es' : ''}
              </Badge>
            )}
            {filters.gitGrades.size > 0 && (
              <Badge variant="secondary" className="text-xs">
                {Array.from(filters.gitGrades).join(', ')}
              </Badge>
            )}
            {filters.interviewResult !== 'all' && (
              <Badge variant="secondary" className="text-xs">
                Interview: {filters.interviewResult === 'pass' ? 'Pass' : filters.interviewResult === 'strong_pass' ? 'Strong Pass' : 'Fail'}
              </Badge>
            )}
            {!(filters.hrwScoreRange[0] === 0 && filters.hrwScoreRange[1] === 100) && (
              <Badge variant="secondary" className="text-xs">
                HRW: {Math.round(filters.hrwScoreRange[0])}-{Math.round(filters.hrwScoreRange[1])}
              </Badge>
            )}
          </div>
        )}
      </div>

      {/* Table – fixed width and height so list never shrinks when searching/filtering */}
      <div className="card-terminal flex-1 min-h-[60vh] w-full min-w-0 flex flex-col overflow-hidden">
        <div ref={tableScrollRef} className="flex-1 min-h-[50vh] w-full min-w-0 overflow-y-auto overflow-x-hidden">
          <table className="w-full min-w-full table-fixed border-collapse">
            <colgroup>
              <col className="w-[2.5%]" />
              <col className="w-[23%]" />
              <col className="w-[7%]" />
              <col className="w-[8%]" />
              <col className="w-[9%]" />
              <col className="w-[7%]" />
              <col className="w-[8%]" />
              <col className="w-[7%]" />
              <col className="w-[15%]" />
              <col className="w-[5%]" />
            </colgroup>
            <thead className="sticky top-0 bg-surface-1 z-10 border-b border-border">
              <tr>
                <th className="py-3 px-3 text-left align-middle">
                  <Checkbox
                    checked={filteredExperts.length > 0 && filteredExperts.every(e => {
                      const id = e.id || (e as any)._id || e.github_username;
                      return id && selectedExperts.has(id);
                    })}
                    onCheckedChange={toggleAll}
                    className="border-muted-foreground data-[state=checked]:bg-primary data-[state=checked]:border-primary cursor-pointer"
                    title={filteredExperts.length > 0 && filteredExperts.every(e => {
                      const id = e.id || (e as any)._id || e.github_username;
                      return id && selectedExperts.has(id);
                    }) ? "Deselect all filtered experts" : "Select all filtered experts"}
                  />
                </th>
                <th className="py-3 px-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground align-middle">Name</th>
                <th className="py-3 px-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground align-middle">Grade</th>
                <th className="py-3 px-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground align-middle">Status</th>
                <th className="py-3 px-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground align-middle">Email</th>
                <th className="py-3 px-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground align-middle">Test</th>
                <th className="py-3 px-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground align-middle">Interview</th>
                <th className="py-3 px-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground align-middle">Result</th>
                <th className="py-3 px-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground align-middle">Skills</th>
                <th className="py-3 px-2 w-12 min-w-[3rem] align-middle text-right" aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {paginatedExperts.length === 0 ? (
                <tr>
                  <td colSpan={10} className="py-16 px-6 text-center">
                    <div className="flex flex-col items-center gap-3">
                      <User className="w-12 h-12 text-muted-foreground/50" />
                      <p className="text-sm font-medium text-foreground">No experts found</p>
                      <p className="text-xs text-muted-foreground font-mono">
                        {filteredExperts.length === 0 && allExperts.length > 0
                          ? "Try adjusting your filters or search query"
                          : "Add experts to get started"}
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                paginatedExperts.map((expert) => {
                const gitGrade = getGitGrade(expert.gitScore);
                const expertId = expert.id || (expert as any)._id || expert.github_username || '';
                const isSelected = expertId && selectedExperts.has(expertId);
                const status = statusConfig[expert.status];
                
                return (
                  <tr
                    key={expertId}
                    onClick={(e) => {
                      // Don't open profile if clicking on checkbox or action buttons
                      const target = e.target as HTMLElement;
                      if (target.closest('input[type="checkbox"]') || 
                          target.closest('button') || 
                          target.closest('[role="button"]')) {
                        return;
                      }
                      setViewingProfile(expert);
                    }}
                    className={cn(
                      "group cursor-pointer border-b border-border/50 transition-all duration-150",
                      "hover:bg-surface-2/50",
                      isSelected && "bg-primary/10 hover:bg-primary/15"
                    )}
                  >
                    <td 
                      className="py-3 px-3 align-middle" 
                      onClick={(e) => {
                        e.stopPropagation();
                        if (expertId) {
                          toggleSelection(expertId);
                        }
                      }}
                    >
                      <Checkbox
                        checked={isSelected}
                        onCheckedChange={(checked) => {
                          if (expertId) {
                            toggleSelection(expertId);
                          }
                        }}
                        onClick={(e) => e.stopPropagation()}
                        className="border-muted-foreground data-[state=checked]:bg-primary data-[state=checked]:border-primary cursor-pointer"
                      />
                    </td>
                    <td className="py-3 px-3 align-middle min-w-0">
                      <div className="min-w-0">
                        <div className="font-medium text-foreground group-hover:text-primary transition-colors truncate" title={expert.name}>
                          {expert.name}
                        </div>
                        {expert.email && (
                          <div className="text-xs text-muted-foreground truncate" title={expert.email}>
                            {expert.email}
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-3 align-middle whitespace-nowrap">
                      <span className={getGradePillClass(gitGrade)}>
                        {gitGrade}
                      </span>
                    </td>
                    <td className="py-3 px-3 align-middle whitespace-nowrap">
                      <span className={`text-xs ${status?.className ?? 'text-muted-foreground'}`}>{status?.label ?? expert.status ?? '—'}</span>
                    </td>
                    <td className="py-3 px-3 align-middle whitespace-nowrap">
                      <span className={`text-xs ${workflowLabels.emailSent[expert.workflow?.emailSent as keyof typeof workflowLabels.emailSent]?.className ?? 'text-muted-foreground'}`}>
                        {workflowLabels.emailSent[expert.workflow?.emailSent as keyof typeof workflowLabels.emailSent]?.label ?? '—'}
                      </span>
                    </td>
                    <td className="p-4">
                      <span className={`text-xs font-mono ${workflowLabels.testSent[(expert.workflow?.testSent ?? 'pending') as keyof typeof workflowLabels.testSent]?.className ?? 'text-muted-foreground'}`}>
                        {workflowLabels.testSent[(expert.workflow?.testSent ?? 'pending') as keyof typeof workflowLabels.testSent]?.label ?? '—'}
                      </span>
                    </td>
                    <td className="py-3 px-3 align-middle whitespace-nowrap">
                      <span className={`text-xs ${workflowLabels.interview[expert.workflow?.interview as keyof typeof workflowLabels.interview]?.className ?? 'text-muted-foreground'}`}>
                        {workflowLabels.interview[expert.workflow?.interview as keyof typeof workflowLabels.interview]?.label ?? '—'}
                      </span>
                    </td>
                    <td className="py-3 px-3 align-middle whitespace-nowrap">
                      <span className={`text-xs ${workflowLabels.interviewResult[expert.workflow.interviewResult as keyof typeof workflowLabels.interviewResult]?.className ?? 'text-muted-foreground'}`}>
                        {workflowLabels.interviewResult[expert.workflow.interviewResult as keyof typeof workflowLabels.interviewResult]?.label ?? '—'}
                      </span>
                    </td>
                    <td className="py-3 px-3 align-middle min-w-0">
                      <div className="flex flex-wrap gap-1 min-w-0">
                        {expert.skills.slice(0, 2).map((skill) => (
                          <span key={skill} className="skill-tag truncate max-w-full inline-block">
                            {skill}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="py-3 px-2 align-middle overflow-visible">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <button 
                            onClick={(e) => e.stopPropagation()}
                            className="shrink-0 p-2 rounded-md bg-surface-2/60 hover:bg-surface-3 border border-border/50 hover:border-border transition-all opacity-60 group-hover:opacity-100 group-hover:bg-surface-3 group-hover:border-border inline-flex items-center justify-center"
                            aria-label="Row actions"
                          >
                            <MoreHorizontal className="w-5 h-5 text-muted-foreground group-hover:text-foreground transition-colors shrink-0" />
                          </button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="bg-surface-1 border-border w-48">
                          <DropdownMenuItem 
                            className="gap-2 cursor-pointer"
                            onClick={(e) => {
                              e.stopPropagation();
                              setViewingProfile(expert);
                            }}
                          >
                            <User className="w-4 h-4" />
                            <span>View Profile</span>
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem 
                            className={cn("gap-2", canSendEmail(expert) ? "cursor-pointer" : "cursor-not-allowed opacity-60")}
                            disabled={!canSendEmail(expert)}
                            onClick={(e) => {
                              e.stopPropagation();
                              if (canSendEmail(expert)) handleSendEmail(expert);
                            }}
                            title={!canSendEmail(expert) ? 'Send Email is disabled for candidates in interviewing, assessment, contracted, or onboarded status' : undefined}
                          >
                            <Mail className="w-4 h-4" />
                            <span>Send Email</span>
                          </DropdownMenuItem>
                          <DropdownMenuItem 
                            className={cn("gap-2", !isContracted(expert) ? "cursor-pointer" : "cursor-not-allowed opacity-60")}
                            disabled={isContracted(expert)}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleSendTest(expert);
                            }}
                            title={isContracted(expert) ? 'Candidate has already signed the contract' : undefined}
                          >
                            <FileText className="w-4 h-4" />
                            <span>Send Test</span>
                          </DropdownMenuItem>
                          <DropdownMenuItem 
                            className={cn("gap-2", !isContracted(expert) && canScheduleInterview(expert) ? "cursor-pointer" : "cursor-not-allowed opacity-60")}
                            disabled={isContracted(expert) || !canScheduleInterview(expert)}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleScheduleInterview(expert);
                            }}
                            title={
                              isContracted(expert)
                                ? 'Candidate has already signed the contract'
                                : !canScheduleInterview(expert)
                                  ? 'Candidate must pass the assessment first'
                                  : undefined
                            }
                          >
                            <Video className="w-4 h-4" />
                            <span>Schedule Interview</span>
                          </DropdownMenuItem>
                          {(expert.workflow.interview === 'scheduled' || expert.workflow.interview === 'completed') && (
                            <DropdownMenuItem 
                              className="gap-2 cursor-pointer"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleSetInterviewResult(expert);
                              }}
                            >
                              <CheckCircle className="w-4 h-4" />
                              <span>Set Interview Result</span>
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuItem 
                            className={cn("gap-2", !isContracted(expert) && canSendContract(expert) ? "cursor-pointer" : "cursor-not-allowed opacity-60")}
                            disabled={isContracted(expert) || !canSendContract(expert)}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleSendContract(expert);
                            }}
                            title={
                              isContracted(expert)
                                ? 'Candidate has already signed the contract'
                                : !canSendContract(expert)
                                  ? 'Candidate must pass the interview first (Result: Pass or Strong Pass)'
                                  : undefined
                            }
                          >
                            <FileSignature className="w-4 h-4" />
                            <span>Send Contract</span>
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem 
                            className={cn("gap-2", canProvisionTools(expert) ? "cursor-pointer" : "cursor-not-allowed opacity-60")}
                            disabled={!canProvisionTools(expert)}
                            onClick={(e) => {
                              e.stopPropagation();
                              if (canProvisionTools(expert)) handleProvisionTools(expert);
                            }}
                            title={!canProvisionTools(expert) ? 'Provision Tools is only available for candidates with contracted or onboarded status' : undefined}
                          >
                            <Wrench className="w-4 h-4" />
                            <span>Provision Tools</span>
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </td>
                  </tr>
                );
              })
              )}
            </tbody>
          </table>
        </div>
        
        {/* Pagination - stays fixed below scroll area */}
        {totalPages > 1 && (
          <div className="border-t border-border px-6 py-4 bg-surface-1/50 shrink-0">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-2 text-sm text-muted-foreground tabular-nums">
                <span className="inline-flex items-center gap-1.5 rounded-md bg-muted/80 px-2.5 py-1 text-foreground font-medium">
                  <span>Page</span>
                  <span className="font-semibold">{currentPage}</span>
                  <span className="text-muted-foreground font-normal">of</span>
                  <span className="font-semibold">{totalPages}</span>
                </span>
              </div>
              <Pagination>
                <PaginationContent>
                  <PaginationItem>
                    <PaginationPrevious
                      href="#"
                      onClick={(e) => {
                        e.preventDefault();
                        if (currentPage > 1) {
                          setCurrentPage(currentPage - 1);
                          tableScrollRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
                        }
                      }}
                      className={cn(
                        "cursor-pointer transition-opacity",
                        currentPage === 1 && "pointer-events-none opacity-50"
                      )}
                    />
                  </PaginationItem>
                  
                  {/* Page numbers with smart ellipsis */}
                  {(() => {
                    const pages: (number | 'ellipsis')[] = [];
                    
                    if (totalPages <= 7) {
                      // Show all pages if 7 or fewer
                      for (let i = 1; i <= totalPages; i++) {
                        pages.push(i);
                      }
                    } else {
                      // Always show first page
                      pages.push(1);
                      
                      if (currentPage > 3) {
                        pages.push('ellipsis');
                      }
                      
                      // Show pages around current
                      const start = Math.max(2, currentPage - 1);
                      const end = Math.min(totalPages - 1, currentPage + 1);
                      
                      for (let i = start; i <= end; i++) {
                        if (i !== 1 && i !== totalPages) {
                          pages.push(i);
                        }
                      }
                      
                      if (currentPage < totalPages - 2) {
                        pages.push('ellipsis');
                      }
                      
                      // Always show last page
                      pages.push(totalPages);
                    }
                    
                    return pages.map((page, index) => {
                      if (page === 'ellipsis') {
                        return (
                          <PaginationItem key={`ellipsis-${index}`}>
                            <PaginationEllipsis />
                          </PaginationItem>
                        );
                      }
                      
                      return (
                        <PaginationItem key={page}>
                          <PaginationLink
                            href="#"
                            onClick={(e) => {
                              e.preventDefault();
                              setCurrentPage(page);
                              tableScrollRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
                            }}
                            isActive={currentPage === page}
                            className="cursor-pointer min-w-[2.5rem] transition-all"
                          >
                            {page}
                          </PaginationLink>
                        </PaginationItem>
                      );
                    });
                  })()}
                  
                  <PaginationItem>
                    <PaginationNext
                      href="#"
                      onClick={(e) => {
                        e.preventDefault();
                        if (currentPage < totalPages) {
                          setCurrentPage(currentPage + 1);
                          tableScrollRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
                        }
                      }}
                      className={cn(
                        "cursor-pointer transition-opacity",
                        currentPage === totalPages && "pointer-events-none opacity-50"
                      )}
                    />
                  </PaginationItem>
                </PaginationContent>
              </Pagination>
            </div>
          </div>
        )}
      </div>

      {/* Modals */}
      <AddExpertsModal 
        open={addExpertsOpen} 
        onOpenChange={setAddExpertsOpen}
        onContributorsAnalyzed={(analyses: ContributorAnalysis[]) => {
          console.log('Contributors analyzed:', analyses);
          // TODO: Save to database or update UI
        }}
        onJobStarted={(jobId: string) => {
          setProcessingJobId(jobId);
        }}
      />
      
      {/* Processing Notification */}
      {processingJobId && (
        <ProcessingNotification
          jobId={processingJobId}
          onComplete={(status) => {
            console.log('Analysis completed:', status);
            setProcessingJobId(null);
          }}
          onDismiss={() => setProcessingJobId(null)}
        />
      )}
      <SendEmailModal 
        open={emailModalOpen} 
        onOpenChange={setEmailModalOpen}
        candidates={getEmailModalCandidates()}
        onEmailSent={() => refetch()}
      />
      <SendTestModal 
        open={testModalOpen} 
        onOpenChange={setTestModalOpen}
        candidates={getTestModalCandidates()}
        onTestSent={() => {
          refetch(); // Refresh experts list after test is sent
        }}
      />
      <ScheduleInterviewModal 
        open={interviewModalOpen} 
        onOpenChange={setInterviewModalOpen}
        candidateName={selectedExpert?.name}
        candidateEmail={selectedExpert?.email}
      />
      <InterviewResultModal
        open={interviewResultModalOpen}
        onOpenChange={setInterviewResultModalOpen}
        candidateEmail={selectedExpert?.email || ''}
        candidateName={selectedExpert?.name}
        currentStatus={selectedExpert?.workflow?.interview}
        currentResult={selectedExpert?.workflow?.interviewResult}
        onUpdate={() => {
          // Refresh experts list
          refetch();
        }}
      />
      <SendContractModal 
        open={contractModalOpen} 
        onOpenChange={setContractModalOpen}
        candidateName={selectedExpert?.name}
        candidateEmail={selectedExpert?.email}
        candidatePhone={(selectedExpert as any)?.phone ?? ''}
        candidateAddress={(selectedExpert as any)?.location ?? ''}
      />
      <ProvisionToolsModal 
        open={provisionModalOpen} 
        onOpenChange={setProvisionModalOpen}
        candidateName={selectedExpert?.name}
      />
    </div>
  );
}