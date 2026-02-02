import { useState, useEffect } from 'react';
import { FileSignature, FileText, Shield, Send, Loader2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { sendContractToCandidate } from '@/lib/api';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';

interface SendContractModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  candidateName?: string;
  candidateEmail?: string;
  candidatePhone?: string;
  candidateAddress?: string;
}

export function SendContractModal({ open, onOpenChange, candidateName = '', candidateEmail = '', candidatePhone = '', candidateAddress = '' }: SendContractModalProps) {
  const [includeNda, setIncludeNda] = useState(true);
  const [includeContract, setIncludeContract] = useState(true);
  const [sending, setSending] = useState(false);
  const [phone, setPhone] = useState(candidatePhone);
  const [address, setAddress] = useState(candidateAddress);

  useEffect(() => {
    setPhone(candidatePhone);
    setAddress(candidateAddress);
  }, [candidatePhone, candidateAddress, open]);

  const handleSendDocuSign = async () => {
    if (!candidateEmail?.trim()) {
      toast.error('Candidate email is required');
      return;
    }
    setSending(true);
    try {
      await sendContractToCandidate({
        candidate_email: candidateEmail.trim(),
        candidate_name: candidateName?.trim() || undefined,
        candidate_phone: phone?.trim() || undefined,
        candidate_address: address?.trim() || undefined,
        include_nda: includeNda,
        include_contract: includeContract,
      });
      toast.success('Contract sent! The candidate will receive an email from DocuSign.');
      onOpenChange(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to send contract');
    } finally {
      setSending(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md bg-surface-1 border-border">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg font-semibold">
            <FileSignature className="w-5 h-5 text-primary" />
            Send Contract
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4 mt-4">
          {candidateName && (
            <div className="p-3 bg-surface-2 rounded-lg border border-border">
              <p className="text-sm text-muted-foreground">Sending to:</p>
              <p className="font-medium text-foreground">{candidateName}</p>
              {candidateEmail && (
                <p className="text-xs text-muted-foreground font-mono">{candidateEmail}</p>
              )}
            </div>
          )}

          <div className="space-y-2">
            <Label className="text-sm font-medium">Personal details (pre-filled in document)</Label>
            <Input
              placeholder="Phone number"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="bg-surface-2 border-border"
            />
            <Input
              placeholder="Address"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              className="bg-surface-2 border-border"
            />
          </div>
          
          <div className="space-y-3">
            <Label className="text-sm font-medium">Select Documents</Label>
            
            <div 
              className={`flex items-start gap-3 p-4 rounded-lg border transition-colors cursor-pointer ${
                includeNda ? 'bg-primary/5 border-primary/30' : 'bg-surface-2 border-border hover:border-primary/20'
              }`}
              onClick={() => setIncludeNda(!includeNda)}
            >
              <Checkbox 
                checked={includeNda} 
                onCheckedChange={(checked) => setIncludeNda(checked as boolean)}
                className="mt-0.5"
              />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <Shield className="w-4 h-4 text-warning" />
                  <span className="font-medium text-foreground">Non-Disclosure Agreement (NDA)</span>
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Confidentiality agreement to protect sensitive information
                </p>
              </div>
            </div>
            
            <div 
              className={`flex items-start gap-3 p-4 rounded-lg border transition-colors cursor-pointer ${
                includeContract ? 'bg-primary/5 border-primary/30' : 'bg-surface-2 border-border hover:border-primary/20'
              }`}
              onClick={() => setIncludeContract(!includeContract)}
            >
              <Checkbox 
                checked={includeContract} 
                onCheckedChange={(checked) => setIncludeContract(checked as boolean)}
                className="mt-0.5"
              />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-success" />
                  <span className="font-medium text-foreground">Contractor Agreement</span>
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Terms and conditions for the engagement
                </p>
              </div>
            </div>
          </div>
          
          {(!includeNda && !includeContract) && (
            <p className="text-sm text-danger">
              Please select at least one document to send
            </p>
          )}
          {!candidateEmail?.trim() && (
            <p className="text-sm text-danger">
              Candidate email is required to send a contract
            </p>
          )}
        </div>
        
        <DialogFooter className="mt-6">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button 
            onClick={handleSendDocuSign} 
            disabled={(!includeNda && !includeContract) || !candidateEmail?.trim() || sending}
            className="bg-[#FFD700] hover:bg-[#FFD700]/90 text-black"
          >
            {sending ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Send className="w-4 h-4 mr-2" />
            )}
            {sending ? 'Sending...' : 'Send DocuSign'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
