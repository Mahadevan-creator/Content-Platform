import { useEffect, useState } from 'react';
import { Loader2, X, CheckCircle2, AlertCircle } from 'lucide-react';
import { Progress } from '@/components/ui/progress';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { getJobStatus, type JobStatus } from '@/lib/api';

interface ProcessingNotificationProps {
  jobId: string;
  onComplete?: (status: JobStatus) => void;
  onDismiss?: () => void;
}

export function ProcessingNotification({ jobId, onComplete, onDismiss }: ProcessingNotificationProps) {
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [isPolling, setIsPolling] = useState(true);

  useEffect(() => {
    if (!isPolling) return;

    const pollStatus = async () => {
      try {
        const jobStatus = await getJobStatus(jobId);
        setStatus(jobStatus);

        if (jobStatus.status === 'completed') {
          setIsPolling(false);
          if (onComplete) {
            onComplete(jobStatus);
          }
        } else if (jobStatus.status === 'failed') {
          setIsPolling(false);
        }
      } catch (error) {
        console.error('Error polling job status:', error);
      }
    };

    // Initial poll
    pollStatus();

    // Poll every 2 seconds
    const interval = setInterval(pollStatus, 2000);

    return () => clearInterval(interval);
  }, [jobId, isPolling, onComplete]);

  if (!status) {
    return null;
  }

  const isCompleted = status.status === 'completed';
  const isFailed = status.status === 'failed';
  const isProcessing = status.status === 'processing' || status.status === 'pending';

  return (
    <Card className="fixed bottom-4 right-4 w-96 z-50 shadow-lg border-border bg-surface-1">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 space-y-2">
            <div className="flex items-center gap-2">
              {isProcessing && <Loader2 className="w-4 h-4 animate-spin text-primary" />}
              {isCompleted && <CheckCircle2 className="w-4 h-4 text-terminal-green" />}
              {isFailed && <AlertCircle className="w-4 h-4 text-terminal-red" />}
              <span className="text-sm font-medium text-foreground">
                {isProcessing && 'Adding experts...'}
                {isCompleted && 'Complete'}
                {isFailed && 'Failed'}
              </span>
            </div>

            {status.message && (
              <p className="text-xs text-muted-foreground">
                {status.message}
              </p>
            )}

            {status.current_repo && (
              <p className="text-xs text-primary font-mono truncate">
                {status.current_repo}
              </p>
            )}

            {isProcessing && (
              <div className="space-y-1">
                <Progress value={status.progress || 0} className="h-1.5" />
                <p className="text-xs text-muted-foreground text-right">
                  {Math.round(status.progress || 0)}%
                </p>
              </div>
            )}

            {isFailed && status.error && (
              <p className="text-xs text-terminal-red">
                {status.error}
              </p>
            )}
          </div>

          {(isCompleted || isFailed) && onDismiss && (
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={onDismiss}
            >
              <X className="w-4 h-4" />
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
