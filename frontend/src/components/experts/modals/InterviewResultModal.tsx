import { useState } from 'react';
import { CheckCircle, XCircle, RefreshCw, Loader2, AlertCircle } from 'lucide-react';
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
import { checkInterviewStatus, updateInterviewCompletion } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

interface InterviewResultModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  candidateEmail: string;
  candidateName?: string;
  currentStatus?: string;
  currentResult?: string;
  onUpdate?: () => void;
}

export function InterviewResultModal({
  open,
  onOpenChange,
  candidateEmail,
  candidateName = '',
  currentStatus,
  currentResult,
  onUpdate,
}: InterviewResultModalProps) {
  const [selectedResult, setSelectedResult] = useState<string>(currentResult || '');
  const [isChecking, setIsChecking] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [checkResult, setCheckResult] = useState<{
    status?: string;
    result?: string;
    message?: string;
  } | null>(null);
  const { toast } = useToast();

  const handleCheckStatus = async () => {
    if (!candidateEmail) {
      toast({
        title: 'Error',
        description: 'Candidate email is required',
        variant: 'destructive',
      });
      return;
    }

    setIsChecking(true);
    setCheckResult(null);

    try {
      const response = await checkInterviewStatus(candidateEmail);
      setCheckResult({
        status: response.interview_status,
        result: response.interview_result || undefined,
        message: response.updated ? 'Status updated from HackerRank' : 'Status checked',
      });

      // Update selected result if we got one from HackerRank
      if (response.interview_result) {
        setSelectedResult(response.interview_result);
      }

      toast({
        title: 'Status Checked',
        description: `Interview status: ${response.interview_status}${response.interview_result ? `, Result: ${response.interview_result}` : ''}`,
      });

      if (onUpdate) {
        onUpdate();
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to check interview status';
      setCheckResult({
        message: errorMessage,
      });
      toast({
        title: 'Error Checking Status',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setIsChecking(false);
    }
  };

  const handleUpdateResult = async () => {
    if (!selectedResult) {
      toast({
        title: 'Error',
        description: 'Please select a result',
        variant: 'destructive',
      });
      return;
    }

    setIsUpdating(true);

    try {
      await updateInterviewCompletion({
        email: candidateEmail,
        interview_result: selectedResult as 'pass' | 'fail' | 'strong_pass',
        interview_status: 'completed',
      });

      toast({
        title: 'Result Updated',
        description: `Interview result set to: ${selectedResult}`,
      });

      if (onUpdate) {
        onUpdate();
      }

      onOpenChange(false);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update interview result';
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setIsUpdating(false);
    }
  };

  const handleClose = () => {
    setSelectedResult(currentResult || '');
    setCheckResult(null);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md bg-surface-1 border-border">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg font-semibold">
            <CheckCircle className="w-5 h-5 text-primary" />
            Interview Result
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 mt-4">
          {candidateName && (
            <p className="text-sm text-muted-foreground">
              Candidate: <span className="font-medium text-foreground">{candidateName}</span>
            </p>
          )}

          <div className="p-3 bg-surface-2 rounded-lg border border-border">
            <p className="text-xs text-muted-foreground mb-1">Email</p>
            <p className="text-sm font-medium text-foreground">{candidateEmail}</p>
          </div>

          {/* Current Status Display */}
          {(currentStatus || checkResult?.status) && (
            <div className="p-3 bg-surface-2 rounded-lg border border-border">
              <p className="text-xs text-muted-foreground mb-1">Current Status</p>
              <p className="text-sm font-medium text-foreground">
                {checkResult?.status || currentStatus || 'Unknown'}
              </p>
              {checkResult?.result && (
                <p className="text-xs text-muted-foreground mt-1">
                  Result: <span className="font-medium">{checkResult.result}</span>
                </p>
              )}
            </div>
          )}

          {/* Check Status Button */}
          <div className="space-y-2">
            <Button
              onClick={handleCheckStatus}
              disabled={isChecking}
              variant="outline"
              className="w-full"
            >
              {isChecking ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Checking...
                </>
              ) : (
                <>
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Check Status from HackerRank
                </>
              )}
            </Button>
            {checkResult?.message && (
              <p className="text-xs text-muted-foreground">{checkResult.message}</p>
            )}
          </div>

          {/* Result Selection */}
          <div className="space-y-2">
            <Label>Interview Result</Label>
            <Select value={selectedResult} onValueChange={setSelectedResult}>
              <SelectTrigger className="bg-surface-2 border-border">
                <SelectValue placeholder="Select result..." />
              </SelectTrigger>
              <SelectContent className="bg-surface-1 border-border">
                <SelectItem value="pass" className="cursor-pointer">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-terminal-green" />
                    <span>Pass</span>
                  </div>
                </SelectItem>
                <SelectItem value="strong_pass" className="cursor-pointer">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-terminal-green" />
                    <span>Strong Pass</span>
                  </div>
                </SelectItem>
                <SelectItem value="fail" className="cursor-pointer">
                  <div className="flex items-center gap-2">
                    <XCircle className="w-4 h-4 text-terminal-red" />
                    <span>Fail</span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Select the interview result or check status from HackerRank first
            </p>
          </div>

          {checkResult?.message && checkResult.message.includes('Error') && (
            <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-destructive" />
                <p className="text-sm text-destructive">{checkResult.message}</p>
              </div>
            </div>
          )}
        </div>

        <DialogFooter className="mt-6">
          <Button variant="outline" onClick={handleClose} disabled={isUpdating || isChecking}>
            Cancel
          </Button>
          <Button
            onClick={handleUpdateResult}
            disabled={!selectedResult || isUpdating || isChecking}
          >
            {isUpdating ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Updating...
              </>
            ) : (
              <>
                <CheckCircle className="w-4 h-4 mr-2" />
                Update Result
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
