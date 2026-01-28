import { useState } from 'react';
import { Mail, Link } from 'lucide-react';
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

interface SendEmailModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  candidateEmail?: string;
  candidateName?: string;
}

const defaultEmailBody = `Hi there,

I hope this message finds you well! I came across your impressive work on GitHub and wanted to reach out about an exciting opportunity.

We're building a network of exceptional developers and engineers who work on cutting-edge projects with top tech companies. Based on your expertise, I believe you'd be a perfect fit for our community.

As a member, you'll get:
✨ Access to exclusive high-paying projects
🚀 Flexible remote work opportunities
🤝 Collaboration with talented peers globally
📈 Career growth and skill development

I'd love to learn more about your interests and discuss how we can work together.`;

export function SendEmailModal({ open, onOpenChange, candidateEmail = '', candidateName = '' }: SendEmailModalProps) {
  const [email, setEmail] = useState(candidateEmail);
  const [subject, setSubject] = useState(`${candidateName ? `${candidateName}, ` : ''}Join Our Elite Developer Network 🚀`);
  const [body, setBody] = useState(defaultEmailBody);
  const [interestFormLink] = useState('https://forms.example.com/join-network');

  const handleSend = () => {
    console.log('Sending email:', { email, subject, body, interestFormLink });
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl bg-surface-1 border-border">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg font-semibold">
            <Mail className="w-5 h-5 text-primary" />
            Send Email
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4 mt-4">
          <div className="space-y-2">
            <Label htmlFor="email">Candidate Email</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="candidate@example.com"
              className="bg-surface-2 border-border"
            />
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
              rows={10}
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
          <Button onClick={handleSend} disabled={!email || !subject}>
            <Mail className="w-4 h-4 mr-2" />
            Send Email
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
