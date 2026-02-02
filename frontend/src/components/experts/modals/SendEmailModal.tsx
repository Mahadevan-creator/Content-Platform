import { useState, useEffect } from 'react';
import { Mail, Link2, X, Plus, Loader2, Users } from 'lucide-react';
import { sendEmailToCandidate, getEmailConfig } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';

export interface EmailCandidate {
  email: string;
  name?: string;
}

interface SendEmailModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Single candidate (from row action) or multiple (from bulk) */
  candidates?: EmailCandidate[];
  onEmailSent?: () => void;
}

const EMAIL_TEMPLATE = `Hi {candidateName},

At HackerRank, we're moving beyond LeetCode-style questions and algorithm memorization.

We want to assess real engineering skills and how candidates work in existing codebases, understand requirements, make design trade-offs, write tests, and deliver production-quality code. We're building interview and take-home tasks based on real-world repositories, where candidates contribute to production-style codebases instead of solving isolated problems.

We're looking to collaborate with experienced engineers like you to help design these repo-based tasks.
I think your work aligns well with this direction, and we'd love to explore a collaboration. Would you be open to a short conversation?

Please check & fill the google form by clicking the link below so that my team can reach out to you for taking things forward.

Best,

{senderName}
HackerRank`;

const DEFAULT_INTEREST_FORM_LINK = 'https://forms.gle/eAoqLZERuaeBtpzEA';

function buildEmailBody(candidateName: string, senderName: string): string {
  return EMAIL_TEMPLATE
    .replace(/{candidateName}/g, candidateName)
    .replace(/{senderName}/g, senderName);
}

export function SendEmailModal({ open, onOpenChange, candidates = [], onEmailSent }: SendEmailModalProps) {
  const [recipients, setRecipients] = useState<EmailCandidate[]>([]);
  const [newEmail, setNewEmail] = useState('');
  const [subject, setSubject] = useState('Opportunity to Design Real-World, Repo-Based Interview Tasks at HackerRank');
  const [body, setBody] = useState('');
  const [senderName, setSenderName] = useState('');
  const [interestFormLink] = useState(DEFAULT_INTEREST_FORM_LINK);
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  // Sync recipients, subject, and build body when modal opens or candidates change
  useEffect(() => {
    if (open) {
      const withEmail = (candidates || []).filter((c) => c?.email?.trim());
      setRecipients(withEmail);
      setNewEmail('');
      // Subject: single recipient with name → personalized; multiple → generic
      if (withEmail.length === 1 && withEmail[0].name) {
        setSubject(`${withEmail[0].name} – Opportunity to Design Real-World, Repo-Based Interview Tasks at HackerRank`);
      } else {
        setSubject('Opportunity to Design Real-World, Repo-Based Interview Tasks at HackerRank');
      }
      // Build body: single recipient with name → use name; multiple → "Candidate"
      const candidateName = withEmail.length === 1 && withEmail[0].name
        ? withEmail[0].name
        : 'Candidate';
      getEmailConfig().then((config) => {
        const displayName = config.sender_name || 'HackerRank Team';
        setSenderName(displayName);
        setBody(buildEmailBody(candidateName, displayName));
      });
    }
  }, [open, candidates]);

  const addRecipient = () => {
    const email = newEmail.trim();
    if (!email || !email.includes('@')) return;
    if (recipients.some((r) => r.email.toLowerCase() === email.toLowerCase())) return;
    setRecipients((prev) => [...prev, { email }]);
    setNewEmail('');
  };

  const removeRecipient = (email: string) => {
    setRecipients((prev) => prev.filter((r) => r.email !== email));
  };

  const emailList = recipients.map((r) => r.email).filter(Boolean);
  const canSend = emailList.length > 0 && subject.trim().length > 0;
  const isBulk = recipients.length > 1;

  const handleSend = async () => {
    if (!canSend) return;
    setLoading(true);
    try {
      const result = await sendEmailToCandidate({
        to: emailList,
        subject: subject.trim(),
        body: body.trim(),
        interest_form_link: interestFormLink,
      });
      const count = result.sent ?? emailList.length;
      toast({
        title: 'Email sent',
        description: result.failed?.length
          ? `Sent to ${count}. Failed: ${result.failed.length}`
          : `Email sent to ${count} recipient(s)`,
      });
      onEmailSent?.();
      onOpenChange(false);
    } catch (err) {
      toast({
        title: 'Failed to send email',
        description: err instanceof Error ? err.message : 'Unknown error',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] flex flex-col bg-surface-1 border-border p-0 gap-0 overflow-hidden">
        {/* Header */}
        <DialogHeader className="shrink-0 px-6 pt-6 pb-4 border-b border-border bg-surface-1">
          <DialogTitle className="flex items-center gap-3 text-xl font-semibold tracking-tight">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Mail className="h-5 w-5" />
            </div>
            <div>
              <span>Send Email</span>
              {isBulk && (
                <span className="ml-2 text-sm font-normal text-muted-foreground">
                  to {recipients.length} recipients
                </span>
              )}
            </div>
          </DialogTitle>
        </DialogHeader>

        {/* Scrollable body — native overflow so whole popup scrolls reliably */}
        <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden overscroll-contain">
          <div className="space-y-5 py-5 px-6 pb-6">
            {/* Recipients section — scrollable list */}
            <section className="space-y-3">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Users className="h-4 w-4 text-muted-foreground" />
                  <Label className="text-sm font-medium text-foreground">Recipients</Label>
                  {recipients.length > 0 && (
                    <span className="text-xs text-muted-foreground font-normal">
                      {recipients.length} {recipients.length === 1 ? 'recipient' : 'recipients'}
                    </span>
                  )}
                </div>
              </div>
              <div className="rounded-lg border border-border bg-surface-2/50 overflow-hidden flex flex-col">
                {recipients.length > 0 ? (
                  <ScrollArea className="h-[180px] w-full shrink-0 border-b border-border">
                    <ul className="p-2 space-y-1" role="list">
                      {recipients.map((r) => (
                        <li
                          key={r.email}
                          className="flex items-center gap-2 rounded-md px-3 py-2 bg-background/60 hover:bg-background/80 border border-transparent hover:border-border/50 transition-colors group"
                        >
                          <div className="flex-1 min-w-0">
                            {r.name && (
                              <p className="text-sm font-medium text-foreground truncate">{r.name}</p>
                            )}
                            <p className="text-xs font-mono text-muted-foreground truncate" title={r.email}>
                              {r.email}
                            </p>
                          </div>
                          <button
                            type="button"
                            onClick={() => removeRecipient(r.email)}
                            className="shrink-0 rounded p-1.5 text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1 opacity-70 group-hover:opacity-100"
                            aria-label={`Remove ${r.email}`}
                          >
                            <X className="h-4 w-4" />
                          </button>
                        </li>
                      ))}
                    </ul>
                  </ScrollArea>
                ) : (
                  <div className="h-[100px] flex items-center justify-center text-sm text-muted-foreground border-b border-border">
                    No recipients yet. Add an email below.
                  </div>
                )}
                <div className="flex gap-2 p-3">
                  <Input
                    type="email"
                    placeholder="Add another email..."
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addRecipient())}
                    className="flex-1 h-9 bg-background border-border text-sm placeholder:text-muted-foreground transition-[box-shadow,border-color] duration-200 focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2 focus-visible:border-primary/40"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={addRecipient}
                    disabled={!newEmail.trim().includes('@')}
                    className="shrink-0"
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    Add
                  </Button>
                </div>
              </div>
            </section>

            <Separator className="bg-border" />

            {/* Subject */}
            <section className="space-y-2">
              <Label htmlFor="email-subject" className="text-sm font-medium">Subject</Label>
              <Input
                id="email-subject"
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="h-10 bg-surface-2/50 border-border text-sm transition-[box-shadow,border-color] duration-200 focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2 focus-visible:border-primary/40"
                placeholder="Email subject"
              />
            </section>

            {/* Email body */}
            <section className="space-y-2">
              <Label htmlFor="email-body" className="text-sm font-medium">Message</Label>
              <Textarea
                id="email-body"
                value={body}
                onChange={(e) => setBody(e.target.value)}
                rows={10}
                className="min-h-[200px] max-h-[280px] resize-y bg-surface-2/50 border-border text-sm font-sans leading-relaxed transition-[box-shadow,border-color] duration-200 focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2 focus-visible:border-primary/40"
                placeholder="Email body..."
              />
            </section>

            {/* Interest form link */}
            <section className="rounded-lg border border-border bg-surface-2/30 p-4 space-y-2">
              <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                <Link2 className="h-4 w-4 text-primary shrink-0" />
                Interest form link
              </div>
              <p className="text-xs text-muted-foreground">
                This link will be appended to the email.
              </p>
              <code className="block text-xs font-mono text-primary bg-surface-1 px-3 py-2 rounded border border-border break-all">
                {interestFormLink}
              </code>
            </section>
          </div>
        </div>

        {/* Sticky footer */}
        <DialogFooter className="shrink-0 flex-row justify-end gap-2 px-6 py-4 border-t border-border bg-surface-1">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={handleSend} disabled={!canSend || loading}>
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Sending...
              </>
            ) : (
              <>
                <Mail className="h-4 w-4 mr-2" />
                Send to {emailList.length} {emailList.length === 1 ? 'recipient' : 'recipients'}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
