import { useState, useRef } from 'react';
import { Upload, Github, X, Users, Plus, Trash2, Loader2, CheckCircle2, AlertCircle, FileText } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { analyzeRepositories, pollJobStatus, uploadCsvCandidates, addUsernamesCandidates, type JobStatus, type ContributorAnalysis } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import { ProcessingNotification } from './ProcessingNotification';

interface AddExpertsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onContributorsAnalyzed?: (analyses: ContributorAnalysis[]) => void;
  onJobStarted?: (jobId: string) => void;
}

export function AddExpertsModal({ open, onOpenChange, onContributorsAnalyzed, onJobStarted }: AddExpertsModalProps) {
  const { toast } = useToast();
  const [usernames, setUsernames] = useState('');
  const [repoUrls, setRepoUrls] = useState<string[]>(['']);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleAddRepo = () => {
    setRepoUrls([...repoUrls, '']);
  };

  const handleRemoveRepo = (index: number) => {
    if (repoUrls.length > 1) {
      setRepoUrls(repoUrls.filter((_, i) => i !== index));
    }
  };

  const handleRepoChange = (index: number, value: string) => {
    const updated = [...repoUrls];
    updated[index] = value;
    setRepoUrls(updated);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.name.endsWith('.csv')) {
        toast({
          title: 'Invalid file type',
          description: 'Please upload a CSV file',
          variant: 'destructive',
        });
        return;
      }
      setCsvFile(file);
      setError(null);
    }
  };

  const handleRemoveFile = () => {
    setCsvFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSubmitCsv = async () => {
    if (!csvFile) return;

    setIsAnalyzing(true);
    setError(null);

    try {
      // Upload CSV and start processing
      const jobStatus = await uploadCsvCandidates(csvFile);
      
      // Notify parent component about the job
      if (onJobStarted) {
        onJobStarted(jobStatus.job_id);
      }
      
      toast({
        title: 'CSV upload started',
        description: 'Processing candidates from CSV. You can continue working...',
      });

      // Close modal immediately so user can continue working
      onOpenChange(false);
      setCsvFile(null);
      setIsAnalyzing(false);

      // Poll for job status in background
      pollJobStatus(
        jobStatus.job_id,
        () => {
          // Progress updates handled by ProcessingNotification
        },
        2000 // Poll every 2 seconds
      ).then((finalStatus) => {
        if (finalStatus.status === 'completed' && finalStatus.result) {
          const count = finalStatus.result.processed ?? finalStatus.result.total_candidates ?? finalStatus.result.candidates?.length ?? 0;
          toast({
            title: 'CSV processing complete',
            description: count > 0
              ? `Successfully processed ${count} candidate${count === 1 ? '' : 's'} from CSV. PR analysis and git scores are running in background.`
              : 'CSV processing finished. Check the experts list for updates.',
          });
        }
      }).catch((error) => {
        const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred';
        toast({
          title: 'CSV processing failed',
          description: errorMessage,
          variant: 'destructive',
        });
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred';
      setError(errorMessage);
      toast({
        title: 'CSV upload failed',
        description: errorMessage,
        variant: 'destructive',
      });
      setIsAnalyzing(false);
    }
  };

  const handleSubmitUsernames = async () => {
    const parsedUsernames = usernames
      .split(',')
      .map(u => u.trim())
      .filter(u => u.length > 0);
    if (parsedUsernames.length === 0) return;

    setIsAnalyzing(true);
    setError(null);

    try {
      const jobStatus = await addUsernamesCandidates(parsedUsernames);
      if (onJobStarted) {
        onJobStarted(jobStatus.job_id);
      }
      toast({
        title: 'Usernames import started',
        description: 'Processing candidates from GitHub usernames. You can continue working...',
      });
      onOpenChange(false);
      setUsernames('');
      setIsAnalyzing(false);

      pollJobStatus(jobStatus.job_id, () => {}, 2000)
        .then((finalStatus) => {
          if (finalStatus.status === 'completed' && finalStatus.result) {
            const count = finalStatus.result.processed ?? finalStatus.result.total_candidates ?? finalStatus.result.candidates?.length ?? 0;
            toast({
              title: 'Usernames processing complete',
              description: count > 0
                ? `Successfully processed ${count} candidate${count === 1 ? '' : 's'} from GitHub usernames. PR analysis and git scores are running in background.`
                : 'Usernames processing finished. Check the experts list for updates.',
            });
          }
        })
        .catch((err) => {
          const msg = err instanceof Error ? err.message : 'An unexpected error occurred';
          toast({
            title: 'Usernames processing failed',
            description: msg,
            variant: 'destructive',
          });
        });
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'An unexpected error occurred';
      setError(msg);
      toast({
        title: 'Usernames import failed',
        description: msg,
        variant: 'destructive',
      });
      setIsAnalyzing(false);
    }
  };

  const handleSubmitRepos = async () => {
    const validUrls = repoUrls.filter(url => url.trim().length > 0);
    if (validUrls.length === 0) return;

    setIsAnalyzing(true);
    setError(null);

    try {
      // Start analysis job on backend
      const jobStatus = await analyzeRepositories(validUrls);
      
      // Notify parent component about the job
      if (onJobStarted) {
        onJobStarted(jobStatus.job_id);
      }
      
      toast({
        title: 'Analysis started',
        description: 'Processing in background. You can continue working...',
      });

      // Close modal immediately so user can continue working
      onOpenChange(false);
      setRepoUrls(['']);
      setIsAnalyzing(false);

      // Poll for job status in background (don't await, let it run async)
      pollJobStatus(
        jobStatus.job_id,
        () => {
          // Progress updates handled by ProcessingNotification
        },
        2000 // Poll every 2 seconds
      ).then((finalStatus) => {
        if (finalStatus.status === 'completed' && finalStatus.result) {
          const analyses = finalStatus.result.analyses;
          const count = finalStatus.result.total_contributors ?? analyses?.length ?? 0;
          if (onContributorsAnalyzed && analyses?.length) {
            onContributorsAnalyzed(analyses);
          }
          toast({
            title: 'Repo analysis complete',
            description: count > 0
              ? `Successfully analyzed ${count} contributor${count === 1 ? '' : 's'} from ${validUrls.length} repo${validUrls.length === 1 ? '' : 's'}. PR analysis and git scores are running in background.`
              : 'Repo analysis finished. Check the experts list for updates.',
          });
        }
      }).catch((error) => {
        const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred';
        toast({
          title: 'Analysis failed',
          description: errorMessage,
          variant: 'destructive',
        });
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred';
      setError(errorMessage);
      toast({
        title: 'Analysis failed',
        description: errorMessage,
        variant: 'destructive',
      });
      setIsAnalyzing(false);
    }
  };

  const validRepoCount = repoUrls.filter(url => url.trim().length > 0).length;

  const handleClose = (open: boolean) => {
    if (!isAnalyzing) {
      onOpenChange(open);
      if (!open) {
        // Reset state when closing
        setError(null);
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-lg bg-surface-1 border-border">
        <DialogHeader>
          <DialogTitle className="text-lg font-semibold">Add Experts</DialogTitle>
        </DialogHeader>
        
        <Tabs defaultValue="csv" className="mt-4">
          <TabsList className="grid w-full grid-cols-3 bg-surface-2">
            <TabsTrigger value="csv" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
              <FileText className="w-4 h-4 mr-2" />
              Upload CSV
            </TabsTrigger>
            <TabsTrigger value="usernames" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
              <Users className="w-4 h-4 mr-2" />
              GitHub Users
            </TabsTrigger>
            <TabsTrigger value="repos" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
              <Github className="w-4 h-4 mr-2" />
              From Repos
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="csv" className="mt-4 space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">
                Upload CSV File
              </label>
              <div className="border-2 border-dashed border-border rounded-lg p-6 bg-surface-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv"
                  onChange={handleFileSelect}
                  className="hidden"
                  id="csv-upload"
                  disabled={isAnalyzing}
                />
                <label
                  htmlFor="csv-upload"
                  className="flex flex-col items-center justify-center cursor-pointer"
                >
                  {csvFile ? (
                    <div className="flex items-center gap-2 text-sm">
                      <FileText className="w-5 h-5 text-primary" />
                      <span className="font-medium">{csvFile.name}</span>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 text-muted-foreground hover:text-terminal-red"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRemoveFile();
                        }}
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    </div>
                  ) : (
                    <>
                      <Upload className="w-8 h-8 text-muted-foreground mb-2" />
                      <span className="text-sm font-medium text-foreground mb-1">
                        Click to upload CSV file
                      </span>
                      <span className="text-xs text-muted-foreground">
                        CSV must have a "Username" column
                      </span>
                    </>
                  )}
                </label>
              </div>
              <p className="text-xs text-muted-foreground">
                Upload a CSV file with a "Username" column. We'll process up to 10 candidates, analyze their top 3 PRs, and calculate their git scores.
              </p>
            </div>
            
            {error && (
              <Alert variant="destructive" className="bg-terminal-red/10 border-terminal-red/20">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription className="text-sm">{error}</AlertDescription>
              </Alert>
            )}

            <Button
              onClick={handleSubmitCsv}
              disabled={!csvFile || isAnalyzing}
              className="w-full"
            >
              {isAnalyzing ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4 mr-2" />
                  Upload & Process CSV
                </>
              )}
            </Button>
          </TabsContent>
          
          <TabsContent value="usernames" className="mt-4 space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">
                GitHub Usernames
              </label>
              <Textarea
                placeholder="Enter GitHub usernames separated by commas&#10;e.g., octocat, torvalds, gaearon"
                value={usernames}
                onChange={(e) => setUsernames(e.target.value)}
                className="min-h-[120px] bg-surface-2 border-border font-mono text-sm resize-none"
              />
              <p className="text-xs text-muted-foreground">
                Enter GitHub usernames separated by commas. We'll process up to 10 candidates, analyze their top 3 PRs, and calculate their git scores (same flow as CSV and repos).
              </p>
            </div>
            {error && (
              <Alert variant="destructive" className="bg-terminal-red/10 border-terminal-red/20">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription className="text-sm">{error}</AlertDescription>
              </Alert>
            )}
            <Button
              onClick={handleSubmitUsernames}
              disabled={!usernames.trim() || isAnalyzing}
              className="w-full"
            >
              {isAnalyzing ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Users className="w-4 h-4 mr-2" />
                  Import {usernames.split(',').filter(u => u.trim()).length || 0} Expert(s)
                </>
              )}
            </Button>
          </TabsContent>
          
          <TabsContent value="repos" className="mt-4 space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-foreground">
                  GitHub Repository URLs
                </label>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleAddRepo}
                  disabled={isAnalyzing}
                  className="h-7 px-2 text-xs text-primary hover:text-primary hover:bg-primary/10"
                >
                  <Plus className="w-3 h-3 mr-1" />
                  Add Repo
                </Button>
              </div>
              
              <div className="space-y-2 max-h-[200px] overflow-y-auto">
                {repoUrls.map((url, index) => (
                  <div key={index} className="flex items-center gap-2">
                    <div className="relative flex-1">
                      <Github className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input
                        type="url"
                        placeholder="https://github.com/owner/repo"
                        value={url}
                        onChange={(e) => handleRepoChange(index, e.target.value)}
                        disabled={isAnalyzing}
                        className="pl-10 bg-surface-2 border-border"
                      />
                    </div>
                    {repoUrls.length > 1 && !isAnalyzing && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleRemoveRepo(index)}
                        className="h-9 w-9 text-muted-foreground hover:text-terminal-red hover:bg-terminal-red/10"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                ))}
              </div>
              
              {error && (
                <Alert variant="destructive" className="bg-terminal-red/10 border-terminal-red/20">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription className="text-sm">{error}</AlertDescription>
                </Alert>
              )}

              {!isAnalyzing && (
                <div className="p-3 bg-primary/10 border border-primary/20 rounded-lg">
                  <p className="text-sm text-primary font-medium">
                    ✨ We'll gather top 25 contributors from {validRepoCount === 1 ? 'this repo' : `these ${validRepoCount} repos`} and analyze their top 3 merged PRs
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    PRs are scored based on: priority labels (feature, high priority, bounty, $, money, reward, points), files changed, lines of code, and number of commits
                  </p>
                </div>
              )}
            </div>
            <Button
              onClick={handleSubmitRepos}
              disabled={validRepoCount === 0 || isAnalyzing}
              className="w-full"
            >
              {isAnalyzing ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Github className="w-4 h-4 mr-2" />
                  Fetch Contributors from {validRepoCount} Repo{validRepoCount !== 1 ? 's' : ''}
                </>
              )}
            </Button>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
