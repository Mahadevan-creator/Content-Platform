import { useState } from 'react';
import { FileText, CheckCircle2, ExternalLink } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { sendTestToCandidate } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

export interface TestCandidate {
  email: string;
  name?: string;
}

interface SendTestModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Single candidate (from row) or multiple (from bulk) */
  candidates?: TestCandidate[];
  /** @deprecated Use candidates instead */
  candidateName?: string;
  /** @deprecated Use candidates instead */
  candidateEmail?: string;
  onTestSent?: () => void;
}

// HackerRank Test IDs and links (SME hiring tests)
const availableTests = [
  { 
    id: '2291170', 
    name: 'Django', 
    publicLink: 'https://hr.gs/django-sme-hiring-test',
    privateLink: 'https://www.hackerrank.com/work/tests/2291170/questions',
    duration: '90 mins', 
    difficulty: 'Medium' 
  },
  { 
    id: '2288233', 
    name: 'Spring Boot', 
    publicLink: 'https://hr.gs/springboot-sme-hiring-test',
    privateLink: 'https://www.hackerrank.com/work/tests/2288233/questions',
    duration: '90 mins', 
    difficulty: 'Medium' 
  },
  { 
    id: '2291652', 
    name: 'Go', 
    publicLink: 'https://hr.gs/go-sme-hiring-test',
    privateLink: 'https://www.hackerrank.com/work/tests/2291652/questions',
    duration: '90 mins', 
    difficulty: 'Medium' 
  },
  { 
    id: '2291659', 
    name: '.NET', 
    publicLink: 'https://hr.gs/dotnet-sme-hiring-test',
    privateLink: 'https://www.hackerrank.com/work/tests/2291659/questions',
    duration: '90 mins', 
    difficulty: 'Medium' 
  },
  { 
    id: '2291661', 
    name: 'Angular', 
    publicLink: 'https://hr.gs/angular-sme-hiring-test',
    privateLink: 'https://www.hackerrank.com/work/tests/2291661/questions',
    duration: '90 mins', 
    difficulty: 'Medium' 
  },
];

export function SendTestModal({ 
  open, 
  onOpenChange, 
  candidates = [],
  candidateName = '',
  candidateEmail = '',
  onTestSent
}: SendTestModalProps) {
  const { toast } = useToast();
  const [selectedTest, setSelectedTest] = useState('');
  const [loading, setLoading] = useState(false);
  const [successResult, setSuccessResult] = useState<{ test_link?: string; sent?: number; failed?: string[] } | null>(null);
  
  // Support both candidates array and legacy single candidate props
  const candidateList: TestCandidate[] = candidates.length > 0
    ? candidates
    : candidateEmail ? [{ email: candidateEmail, name: candidateName || undefined }] : [];
  
  const isBulk = candidateList.length > 1;
  const selectedTestDetails = availableTests.find(t => t.id === selectedTest);

  const handleSend = async () => {
    if (!selectedTest || candidateList.length === 0) {
      toast({
        title: 'Missing information',
        description: 'Please select a test and ensure at least one candidate email is provided',
        variant: 'destructive',
      });
      return;
    }

    setLoading(true);
    let sentCount = 0;
    const failed: string[] = [];
    try {
      for (const c of candidateList) {
        const email = (c.email ?? '').trim();
        if (!email) continue;
        try {
          await sendTestToCandidate({
            test_id: selectedTest,
            candidate_email: email,
            candidate_name: isBulk ? 'Candidate' : ((c.name ?? '').trim() || undefined),
            send_email: true,
          });
          sentCount += 1;
        } catch (err) {
          failed.push(`${email}: ${err instanceof Error ? err.message : 'Unknown error'}`);
        }
      }
      
      setSuccessResult({ sent: sentCount, failed: failed.length > 0 ? failed : undefined });
      if (sentCount > 0) {
        toast({
          title: 'Test sent',
          description: failed.length > 0
            ? `Sent to ${sentCount} recipient(s). Failed: ${failed.length}`
            : `Test invite sent to ${sentCount} recipient(s)`,
        });
        if (onTestSent) onTestSent();
      }
      if (failed.length > 0 && sentCount === 0) {
        toast({
          title: 'Failed to send test',
          description: failed[0],
          variant: 'destructive',
        });
      }
    } catch (error) {
      toast({
        title: 'Failed to send test',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleClose = (open: boolean) => {
    if (!open) {
      setSuccessResult(null);
      setSelectedTest('');
    }
    onOpenChange(open);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md bg-surface-1 border-border">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg font-semibold">
            <FileText className="w-5 h-5 text-primary" />
            {successResult ? 'Test sent successfully' : 'Send Technical Test'}
          </DialogTitle>
        </DialogHeader>
        
        {successResult ? (
          <div className="space-y-4 mt-2">
            <div className="flex items-center gap-3 p-4 rounded-lg bg-primary/10 border border-primary/20">
              <CheckCircle2 className="w-8 h-8 text-primary shrink-0" />
              <div>
                <p className="font-medium text-foreground">Test invite sent successfully</p>
                <p className="text-sm text-muted-foreground mt-1">
                  {successResult.sent && successResult.sent > 1
                    ? `${successResult.sent} candidates will receive an email with the test link.`
                    : 'The candidate will receive an email with the test link.'}
                  {successResult.failed && successResult.failed.length > 0 && (
                    <span className="block mt-1 text-destructive">Failed: {successResult.failed.length}</span>
                  )}
                </p>
              </div>
            </div>
            
            {selectedTestDetails && (
              <div className="space-y-2">
                <Label className="text-muted-foreground">Public Test Link</Label>
                <a
                  href={selectedTestDetails.publicLink}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-sm text-primary hover:underline break-all"
                >
                  {selectedTestDetails.publicLink}
                  <ExternalLink className="w-4 h-4 shrink-0" />
                </a>
              </div>
            )}
            
            {successResult.test_link && (
              <div className="space-y-2">
                <Label className="text-muted-foreground">Candidate Test Link</Label>
                <a
                  href={successResult.test_link.startsWith('http') ? successResult.test_link : `https://${successResult.test_link}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-sm text-primary hover:underline break-all"
                >
                  {successResult.test_link}
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
              {candidateList.length > 0 && (
                <div className="p-3 rounded-lg bg-surface-2 border border-border">
                  <Label className="text-muted-foreground text-xs">
                    {candidateList.length === 1 ? 'Candidate' : `Candidates (${candidateList.length})`}
                  </Label>
                  {candidateList.length === 1 ? (
                    <>
                      <p className="font-medium text-foreground mt-0.5">{candidateList[0].name || candidateList[0].email}</p>
                      <p className="text-sm text-muted-foreground font-mono">{candidateList[0].email}</p>
                    </>
                  ) : (
                    <p className="text-sm text-muted-foreground mt-0.5 font-mono">
                      {candidateList.map((c) => c.email).join(', ')}
                    </p>
                  )}
                </div>
              )}
              
              {candidateList.length === 0 && (
                <p className="text-xs text-destructive font-medium">⚠️ At least one candidate email is required</p>
              )}
              
              <div className="space-y-2">
                <Label>Select Test</Label>
                <Select value={selectedTest} onValueChange={setSelectedTest}>
                  <SelectTrigger className="bg-surface-2 border-border">
                    <SelectValue placeholder="Choose a test to send..." />
                  </SelectTrigger>
                  <SelectContent className="bg-surface-1 border-border">
                    {availableTests.map((test) => (
                      <SelectItem key={test.id} value={test.id} className="cursor-pointer">
                        <div className="flex flex-col">
                          <span className="font-medium">{test.name}</span>
                          <span className="text-xs text-muted-foreground">{test.publicLink}</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              {selectedTestDetails && (
                <div className="p-4 bg-surface-2 rounded-lg border border-border space-y-2">
                  <h4 className="font-medium text-foreground">{selectedTestDetails.name}</h4>
                  <div className="flex gap-4 text-sm">
                    <span className="text-muted-foreground">
                      Duration: <span className="text-foreground font-mono">{selectedTestDetails.duration}</span>
                    </span>
                    <span className="text-muted-foreground">
                      Difficulty: <span className={`font-mono ${
                        selectedTestDetails.difficulty === 'Hard' ? 'text-danger' :
                        selectedTestDetails.difficulty === 'Medium' ? 'text-warning' :
                        'text-success'
                      }`}>{selectedTestDetails.difficulty}</span>
                    </span>
                  </div>
                  <div className="mt-2 space-y-2">
                    <div>
                      <Label className="text-xs text-muted-foreground">Public Link:</Label>
                      <a
                        href={selectedTestDetails.publicLink}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-primary hover:underline block mt-1"
                      >
                        {selectedTestDetails.publicLink}
                      </a>
                    </div>
                    {selectedTestDetails.privateLink && (
                      <div>
                        <Label className="text-xs text-muted-foreground">Private Link:</Label>
                        <a
                          href={selectedTestDetails.privateLink}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-primary hover:underline block mt-1"
                        >
                          {selectedTestDetails.privateLink}
                        </a>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
            
            <DialogFooter className="mt-6">
              <Button variant="outline" onClick={() => handleClose(false)}>
                Cancel
              </Button>
              <Button onClick={handleSend} disabled={!selectedTest || candidateList.length === 0 || loading}>
                {loading ? 'Sending...' : (
                  <>
                    <FileText className="w-4 h-4 mr-2" />
                    Send Test{candidateList.length > 1 ? ` to ${candidateList.length} candidates` : ''}
                  </>
                )}
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
