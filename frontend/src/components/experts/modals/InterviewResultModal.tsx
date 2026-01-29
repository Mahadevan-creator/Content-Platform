import { useState } from 'react';
import { CheckCircle, XCircle, RefreshCw, Loader2 } from 'lucide-react';
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
import { updateInterviewCompletion } from '@/lib/api';
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
  const [isUpdating, setIsUpdating] = useState(false);
  const { toast } = useToast();

  // Interview status is updated by the separate interview_poller; refresh expert list to get latest
  const handleRefresh = () => {
    if (onUpdate) onUpdate();
    toast({
      title: 'Refreshing',
      description: 'Expert list will update with latest interview status from server.',
    });
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

          {/* Current Status (from expert data; updated by interview_poller) */}
          {currentStatus && (
            <div className="p-3 bg-surface-2 rounded-lg border border-border">
              <p className="text-xs text-muted-foreground mb-1">Current Status</p>
              <p className="text-sm font-medium text-foreground">{currentStatus}</p>
              {currentResult && (
                <p className="text-xs text-muted-foreground mt-1">
                  Result: <span className="font-medium">{currentResult}</span>
                </p>
              )}
            </div>
          )}

          {/* Refresh to get latest status from server (interview_poller updates MongoDB) */}
          <div className="space-y-2">
            <Button
              onClick={handleRefresh}
              variant="outline"
              className="w-full"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh (get latest status from server)
            </Button>
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
              Select the interview result. Status is updated by the server every 30 min; use Refresh to get latest.
            </p>
          </div>
        </div>

        <DialogFooter className="mt-6">
          <Button variant="outline" onClick={handleClose} disabled={isUpdating}>
            Cancel
          </Button>
          <Button
            onClick={handleUpdateResult}
            disabled={!selectedResult || isUpdating}
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
