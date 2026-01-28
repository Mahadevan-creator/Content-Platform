import { useState } from 'react';
import { FileText, ChevronDown } from 'lucide-react';
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

interface SendTestModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  candidateName?: string;
}

const availableTests = [
  { id: 'hackerrank-frontend', name: 'HackerRank - Frontend Developer', duration: '90 mins', difficulty: 'Medium' },
  { id: 'hackerrank-backend', name: 'HackerRank - Backend Developer', duration: '90 mins', difficulty: 'Medium' },
  { id: 'hackerrank-fullstack', name: 'HackerRank - Full Stack Developer', duration: '120 mins', difficulty: 'Hard' },
  { id: 'hackerrank-ml', name: 'HackerRank - ML Engineer', duration: '120 mins', difficulty: 'Hard' },
  { id: 'hackerrank-devops', name: 'HackerRank - DevOps Engineer', duration: '90 mins', difficulty: 'Medium' },
  { id: 'leetcode-coding', name: 'LeetCode - Coding Challenge', duration: '75 mins', difficulty: 'Medium' },
  { id: 'custom-system-design', name: 'Custom - System Design Interview', duration: '45 mins', difficulty: 'Hard' },
];

export function SendTestModal({ open, onOpenChange, candidateName = '' }: SendTestModalProps) {
  const [selectedTest, setSelectedTest] = useState('');
  
  const selectedTestDetails = availableTests.find(t => t.id === selectedTest);

  const handleSend = () => {
    console.log('Sending test:', selectedTest, 'to:', candidateName);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md bg-surface-1 border-border">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg font-semibold">
            <FileText className="w-5 h-5 text-primary" />
            Send Technical Test
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4 mt-4">
          {candidateName && (
            <p className="text-sm text-muted-foreground">
              Sending test to: <span className="font-medium text-foreground">{candidateName}</span>
            </p>
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
                      <span>{test.name}</span>
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
                    selectedTestDetails.difficulty === 'Hard' ? 'text-terminal-red' :
                    selectedTestDetails.difficulty === 'Medium' ? 'text-terminal-amber' :
                    'text-terminal-green'
                  }`}>{selectedTestDetails.difficulty}</span>
                </span>
              </div>
            </div>
          )}
        </div>
        
        <DialogFooter className="mt-6">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSend} disabled={!selectedTest}>
            <FileText className="w-4 h-4 mr-2" />
            Send Test
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
