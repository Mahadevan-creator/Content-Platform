import { useState, useEffect } from 'react';
import { Mail, Link, X, Plus } from 'lucide-react';
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
import { Badge } from '@/components/ui/badge';

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
      <DialogContent className="sm:max-w-xl bg-surface-1 border-border">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg font-semibold">
            <Mail className="w-5 h-5 text-primary" />
            Send Email {recipients.length > 1 && `(${recipients.length} recipients)`}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 mt-4">
          <div className="space-y-2">
            <Label>Recipients</Label>
            <div className="flex flex-wrap gap-2 p-2 rounded-lg bg-surface-2 border border-border min-h-[44px]">
              {recipients.map((r) => (
                <Badge
                  key={r.email}
                  variant="secondary"
                  className="flex items-center gap-1 pr-1 font-mono text-xs"
                >
                  {r.name ? `${r.name} ` : ''}
                  <span className="text-muted-foreground">{r.email}</span>
                  <button
                    type="button"
                    onClick={() => removeRecipient(r.email)}
                    className="ml-1 rounded hover:bg-muted p-0.5"
                    aria-label={`Remove ${r.email}`}
                  >
                    <X className="w-3 h-3" />
                  </button>
                </Badge>
              ))}
            </div>
            <div className="flex gap-2">
              <Input
                type="email"
                placeholder="Add email (e.g. candidate@example.com)"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addRecipient())}
                className="bg-surface-2 border-border flex-1"
              />
              <Button type="button" variant="outline" size="icon" onClick={addRecipient} disabled={!newEmail.trim().includes('@')}>
                <Plus className="w-4 h-4" />
              </Button>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="subject">Subject</Label>
            <Input
              id="subject"
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="bg-surface-2 border-border"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="body">Email Body</Label>
            <Textarea
              id="body"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={8}
              className="bg-surface-2 border-border font-mono text-sm resize-none"
            />
          </div>

          <div className="p-3 bg-surface-2 rounded-lg border border-border">
            <div className="flex items-center gap-2 mb-2">
              <Link className="w-4 h-4 text-primary" />
              <span className="text-sm font-medium text-foreground">Interest Form Link</span>
            </div>
            <p className="text-xs text-muted-foreground mb-1">
              This link will be included at the bottom of the email:
            </p>
            <code className="text-xs font-mono text-primary bg-surface-3 px-2 py-1 rounded">
              {interestFormLink}
            </code>
          </div>
        </div>

        <DialogFooter className="mt-6">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSend} disabled={!canSend || loading}>
            <Mail className="w-4 h-4 mr-2" />
            {loading ? 'Sending...' : `Send to ${emailList.length} recipient(s)`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
