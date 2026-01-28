import { useState } from 'react';
import { Video, Calendar, Clock } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface ScheduleInterviewModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  candidateName?: string;
}

const interviewers = [
  { id: 'john-doe', name: 'John Doe', role: 'Engineering Manager', avatar: '👨‍💼' },
  { id: 'jane-smith', name: 'Jane Smith', role: 'Senior Engineer', avatar: '👩‍💻' },
  { id: 'mike-johnson', name: 'Mike Johnson', role: 'Tech Lead', avatar: '👨‍💻' },
  { id: 'sarah-williams', name: 'Sarah Williams', role: 'Staff Engineer', avatar: '👩‍🔬' },
  { id: 'david-brown', name: 'David Brown', role: 'Principal Engineer', avatar: '🧑‍💼' },
];

const timeSlots = [
  '09:00 AM', '09:30 AM', '10:00 AM', '10:30 AM', '11:00 AM', '11:30 AM',
  '12:00 PM', '12:30 PM', '01:00 PM', '01:30 PM', '02:00 PM', '02:30 PM',
  '03:00 PM', '03:30 PM', '04:00 PM', '04:30 PM', '05:00 PM', '05:30 PM',
];

export function ScheduleInterviewModal({ open, onOpenChange, candidateName = '' }: ScheduleInterviewModalProps) {
  const [selectedInterviewer, setSelectedInterviewer] = useState('');
  const [selectedDate, setSelectedDate] = useState('');
  const [selectedTime, setSelectedTime] = useState('');
  
  const selectedInterviewerDetails = interviewers.find(i => i.id === selectedInterviewer);

  const handleSchedule = () => {
    console.log('Scheduling interview:', {
      candidate: candidateName,
      interviewer: selectedInterviewer,
      date: selectedDate,
      time: selectedTime,
    });
    onOpenChange(false);
  };

  // Get tomorrow's date as minimum
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const minDate = tomorrow.toISOString().split('T')[0];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md bg-surface-1 border-border">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg font-semibold">
            <Video className="w-5 h-5 text-primary" />
            Schedule Interview
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4 mt-4">
          {candidateName && (
            <p className="text-sm text-muted-foreground">
              Scheduling interview with: <span className="font-medium text-foreground">{candidateName}</span>
            </p>
          )}
          
          <div className="space-y-2">
            <Label>Select Interviewer</Label>
            <Select value={selectedInterviewer} onValueChange={setSelectedInterviewer}>
              <SelectTrigger className="bg-surface-2 border-border">
                <SelectValue placeholder="Choose an interviewer..." />
              </SelectTrigger>
              <SelectContent className="bg-surface-1 border-border">
                {interviewers.map((interviewer) => (
                  <SelectItem key={interviewer.id} value={interviewer.id} className="cursor-pointer">
                    <div className="flex items-center gap-2">
                      <span>{interviewer.avatar}</span>
                      <span>{interviewer.name}</span>
                      <span className="text-muted-foreground text-xs">({interviewer.role})</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          
          {selectedInterviewerDetails && (
            <div className="p-3 bg-surface-2 rounded-lg border border-border">
              <div className="flex items-center gap-3">
                <span className="text-2xl">{selectedInterviewerDetails.avatar}</span>
                <div>
                  <p className="font-medium text-foreground">{selectedInterviewerDetails.name}</p>
                  <p className="text-xs text-muted-foreground">{selectedInterviewerDetails.role}</p>
                </div>
              </div>
            </div>
          )}
          
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="date" className="flex items-center gap-2">
                <Calendar className="w-4 h-4" />
                Date
              </Label>
              <Input
                id="date"
                type="date"
                min={minDate}
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="bg-surface-2 border-border"
              />
            </div>
            
            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <Clock className="w-4 h-4" />
                Time
              </Label>
              <Select value={selectedTime} onValueChange={setSelectedTime}>
                <SelectTrigger className="bg-surface-2 border-border">
                  <SelectValue placeholder="Select time..." />
                </SelectTrigger>
                <SelectContent className="bg-surface-1 border-border max-h-48">
                  {timeSlots.map((time) => (
                    <SelectItem key={time} value={time} className="cursor-pointer">
                      {time}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>
        
        <DialogFooter className="mt-6">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button 
            onClick={handleSchedule} 
            disabled={!selectedInterviewer || !selectedDate || !selectedTime}
          >
            <Video className="w-4 h-4 mr-2" />
            Schedule Interview
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
