import { useState, useEffect } from 'react';
import { Video, Calendar, Clock, CheckCircle2, ExternalLink, Mail } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { createInterview, type CreateInterviewResponse } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

export const HACKERRANK_INTERVIEWERS = [
  { name: 'Mahadevan M', email: 'mahadevan.m@hackerrank.com' },
  { name: 'Dhruvi Shah', email: 'dhruvi.shah@hackerrank.com' },
  { name: 'Anshu Pandey', email: 'anshu.pandey@hackerrank.com' },
  { name: 'Sahil Phulwani', email: 'sahil.phulwani@hackerrank.com' },
  { name: 'Adhiraj Cheema', email: 'adhiraj.cheema@hackerrank.com' },
  { name: 'Aaryan Ghosh', email: 'aaryan.ghosh@hackerrank.com' },
  { name: 'Darshan Suresh', email: 'darshan@hackerrank.com' },
];

interface ScheduleInterviewModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  candidateName?: string;
  candidateEmail?: string;
}

const timeSlots = [
  '09:00 AM', '09:30 AM', '10:00 AM', '10:30 AM', '11:00 AM', '11:30 AM',
  '12:00 PM', '12:30 PM', '01:00 PM', '01:30 PM', '02:00 PM', '02:30 PM',
  '03:00 PM', '03:30 PM', '04:00 PM', '04:30 PM', '05:00 PM', '05:30 PM',
  '06:00 PM', '06:30 PM', '07:00 PM', '07:30 PM', '08:00 PM', '08:30 PM',
  '09:00 PM', '09:30 PM', '10:00 PM', '10:30 PM',
];

function toISO(fromDate: string, fromTime: string, durationMinutes = 60): { from: string; to: string } {
  if (!fromDate || !fromTime) return { from: '', to: '' };
  const [h, m] = (() => {
    const match = fromTime.match(/^(\d{1,2}):(\d{2})\s*(AM|PM)$/i);
    if (!match) return [9, 0];
    let hour = parseInt(match[1], 10);
    const min = parseInt(match[2], 10);
    if (match[3].toUpperCase() === 'PM' && hour !== 12) hour += 12;
    if (match[3].toUpperCase() === 'AM' && hour === 12) hour = 0;
    return [hour, min];
  })();
  const from = new Date(fromDate);
  from.setHours(h, m, 0, 0);
  const to = new Date(from.getTime() + durationMinutes * 60 * 1000);
  return {
    from: from.toISOString(),
    to: to.toISOString(),
  };
}

export function ScheduleInterviewModal({
  open,
  onOpenChange,
  candidateName = '',
  candidateEmail = '',
}: ScheduleInterviewModalProps) {
  const { toast } = useToast();
  const [selectedInterviewerEmails, setSelectedInterviewerEmails] = useState<Set<string>>(new Set());
  const [selectedDate, setSelectedDate] = useState('');
  const [selectedTime, setSelectedTime] = useState('');
  const [title, setTitle] = useState('');
  const [notes, setNotes] = useState('');
  const [resumeUrl, setResumeUrl] = useState('');
  const [resultUrl, setResultUrl] = useState('');
  const [sendEmail, setSendEmail] = useState(true);
  const [loading, setLoading] = useState(false);
  const [successResult, setSuccessResult] = useState<CreateInterviewResponse | null>(null);

  useEffect(() => {
    if (open) setSuccessResult(null);
  }, [open]);

  const toggleInterviewer = (email: string) => {
    setSelectedInterviewerEmails((prev) => {
      const next = new Set(prev);
      if (next.has(email)) next.delete(email);
      else next.add(email);
      return next;
    });
  };

  const handleSchedule = async () => {
    const email = (candidateEmail || '').trim();
    if (!email) {
      toast({ title: 'Candidate email is required', variant: 'destructive' });
      return;
    }
    if (selectedInterviewerEmails.size === 0) {
      toast({ title: 'Select at least one interviewer', variant: 'destructive' });
      return;
    }
    if (!selectedDate || !selectedTime) {
      toast({ title: 'Date and time are required', variant: 'destructive' });
      return;
    }
    const { from: fromISO, to: toISOStr } = toISO(selectedDate, selectedTime);
    if (!fromISO) {
      toast({ title: 'Invalid date or time', variant: 'destructive' });
      return;
    }
    const interviewTitle = title.trim() || `Interview with ${(candidateName || 'Candidate').trim() || 'Candidate'}`;

    setLoading(true);
    try {
      const payload = {
        from: fromISO,
        to: toISOStr,
        title: interviewTitle,
        notes: notes.trim() || undefined,
        resume_url: resumeUrl.trim() || undefined,
        result_url: resultUrl.trim() || undefined,
        interviewers: HACKERRANK_INTERVIEWERS.filter((i) => selectedInterviewerEmails.has(i.email)),
        candidate: {
          name: (candidateName || '').trim() || undefined,
          email,
        },
        send_email: sendEmail,
        metadata: {},
      };
      const result = await createInterview(payload);
      setSuccessResult(result);
      toast({
        title: 'Interview created',
        description: 'Calendar invites will be sent to the candidate and interviewers.',
      });
    } catch (e) {
      toast({
        title: 'Failed to create interview',
        description: e instanceof Error ? e.message : 'Unknown error',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleClose = (open: boolean) => {
    if (!open) setSuccessResult(null);
    onOpenChange(open);
  };

  const hasValidEmail = candidateEmail && candidateEmail.trim().length > 0;
  const canSubmit =
    hasValidEmail &&
    selectedInterviewerEmails.size > 0 &&
    selectedDate &&
    selectedTime &&
    !loading;

  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const minDate = tomorrow.toISOString().split('T')[0];

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-lg bg-surface-1 border-border max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg font-semibold">
            <Video className="w-5 h-5 text-primary" />
            {successResult ? 'Interview scheduled' : 'Schedule Interview'}
          </DialogTitle>
        </DialogHeader>

        {successResult ? (
          <div className="space-y-4 mt-2">
            <div className="flex items-center gap-3 p-4 rounded-lg bg-primary/10 border border-primary/20">
              <CheckCircle2 className="w-8 h-8 text-primary shrink-0" />
              <div>
                <p className="font-medium text-foreground">Interview created successfully</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Calendar invites have been sent to the candidate and selected interviewers.
                </p>
              </div>
            </div>
            <div className="space-y-2">
              <Label className="text-muted-foreground">Interview link</Label>
              <a
                href={successResult.url?.startsWith('http') ? successResult.url : `https://${successResult.url}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-sm text-primary hover:underline break-all"
              >
                {successResult.url}
                <ExternalLink className="w-4 h-4 shrink-0" />
              </a>
            </div>
            {successResult.report_url && (
              <div className="space-y-2">
                <Label className="text-muted-foreground">Report URL</Label>
                <a
                  href={successResult.report_url?.startsWith('http') ? successResult.report_url : `https://${successResult.report_url}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-sm text-primary hover:underline break-all"
                >
                  {successResult.report_url}
                  <ExternalLink className="w-4 h-4 shrink-0" />
                </a>
              </div>
            )}
            <DialogFooter className="mt-6">
              <Button onClick={() => handleClose(false)}>Done</Button>
            </DialogFooter>
          </div>
        ) : (
          <>
            <div className="space-y-4 mt-2">
            <div className="p-3 rounded-lg bg-surface-2 border border-border">
              <Label className="text-muted-foreground text-xs">Candidate (from selection)</Label>
              <p className="font-medium text-foreground mt-0.5">{candidateName || '—'}</p>
              <p className="text-sm text-muted-foreground font-mono">{candidateEmail || '—'}</p>
              {!hasValidEmail && (
                <p className="text-xs text-destructive mt-1 font-medium">⚠️ Email required to schedule interview</p>
              )}
            </div>

              <div className="space-y-2">
                <Label>Select interviewers</Label>
                <div className="border border-border rounded-lg bg-surface-2/50 max-h-44 overflow-y-auto p-2 space-y-2">
                  {HACKERRANK_INTERVIEWERS.map((inv) => (
                    <label
                      key={inv.email}
                      className="flex items-center gap-3 p-2 rounded-md hover:bg-surface-2 cursor-pointer"
                    >
                      <Checkbox
                        checked={selectedInterviewerEmails.has(inv.email)}
                        onCheckedChange={() => toggleInterviewer(inv.email)}
                      />
                      <span className="text-sm font-medium text-foreground">{inv.name}</span>
                      <span className="text-xs text-muted-foreground truncate">({inv.email})</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Calendar className="w-4 h-4" />
                    Date
                  </Label>
                  <Input
                    type="date"
                    min={minDate}
                    value={selectedDate}
                    onChange={(e) => setSelectedDate(e.target.value)}
                    className="bg-surface-2 border-border"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Clock className="w-4 h-4" />
                    Time
                  </Label>
                  <Select value={selectedTime} onValueChange={setSelectedTime}>
                    <SelectTrigger className="bg-surface-2 border-border">
                      <SelectValue placeholder="Select time..." />
                    </SelectTrigger>
                    <SelectContent className="bg-surface-1 border-border max-h-48">
                      {timeSlots.map((t) => (
                        <SelectItem key={t} value={t} className="cursor-pointer">
                          {t}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Title</Label>
                <Input
                  placeholder="e.g. Interview with Mark"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="bg-surface-2 border-border"
                />
              </div>

              <div className="space-y-2">
                <Label>Notes (optional)</Label>
                <Textarea
                  placeholder="e.g. Assess system design concepts"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={2}
                  className="bg-surface-2 border-border resize-none"
                />
              </div>

              <div className="space-y-2">
                <Label>Resume URL (optional)</Label>
                <Input
                  placeholder="https://..."
                  value={resumeUrl}
                  onChange={(e) => setResumeUrl(e.target.value)}
                  className="bg-surface-2 border-border"
                />
              </div>

              <div className="space-y-2">
                <Label>Result webhook URL (optional)</Label>
                <Input
                  placeholder="https://..."
                  value={resultUrl}
                  onChange={(e) => setResultUrl(e.target.value)}
                  className="bg-surface-2 border-border"
                />
              </div>

              <label className="flex items-center gap-2 cursor-pointer">
                <Checkbox
                  checked={sendEmail}
                  onCheckedChange={(v) => setSendEmail(v === true)}
                />
                <span className="text-sm flex items-center gap-1.5">
                  <Mail className="w-4 h-4" />
                  Send calendar invite to candidate and interviewers
                </span>
              </label>
            </div>

            <DialogFooter className="mt-6">
              <Button variant="outline" onClick={() => handleClose(false)}>
                Cancel
              </Button>
              <Button onClick={handleSchedule} disabled={!canSubmit}>
                {loading ? 'Scheduling...' : (
                  <>
                    <Video className="w-4 h-4 mr-2" />
                    Schedule Interview
                  </>
                )}
              </Button>
            </DialogFooter>
            {!canSubmit && (
              <div className="text-xs text-muted-foreground mt-2 px-1">
                {!hasValidEmail && <div>• Candidate email is required</div>}
                {selectedInterviewerEmails.size === 0 && <div>• Select at least one interviewer</div>}
                {!selectedDate && <div>• Date is required</div>}
                {!selectedTime && <div>• Time is required</div>}
              </div>
            )}
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
