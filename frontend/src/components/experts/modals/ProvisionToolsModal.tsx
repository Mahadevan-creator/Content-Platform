import { useState } from 'react';
import { Wrench, Github, Mail, Check } from 'lucide-react';
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

interface ProvisionToolsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  candidateName?: string;
}

const availableTools = [
  { 
    id: 'slack', 
    name: 'Slack', 
    description: 'Team communication and collaboration',
    icon: '💬',
    color: '#4A154B'
  },
  { 
    id: 'github', 
    name: 'GitHub', 
    description: 'Code repository and version control',
    icon: '🐙',
    color: '#24292F'
  },
  { 
    id: 'zoho', 
    name: 'Zoho', 
    description: 'Project management and CRM',
    icon: '📊',
    color: '#C8202F'
  },
  { 
    id: 'email', 
    name: 'Company Email', 
    description: 'Corporate email account setup',
    icon: '📧',
    color: '#0078D4'
  },
  { 
    id: 'jira', 
    name: 'Jira', 
    description: 'Issue tracking and project management',
    icon: '📋',
    color: '#0052CC'
  },
  { 
    id: 'notion', 
    name: 'Notion', 
    description: 'Documentation and knowledge base',
    icon: '📝',
    color: '#000000'
  },
];

export function ProvisionToolsModal({ open, onOpenChange, candidateName = '' }: ProvisionToolsModalProps) {
  const [selectedTools, setSelectedTools] = useState<Set<string>>(new Set());

  const toggleTool = (toolId: string) => {
    const newSelection = new Set(selectedTools);
    if (newSelection.has(toolId)) {
      newSelection.delete(toolId);
    } else {
      newSelection.add(toolId);
    }
    setSelectedTools(newSelection);
  };

  const handleProvision = () => {
    console.log('Provisioning tools:', Array.from(selectedTools), 'for:', candidateName);
    onOpenChange(false);
  };

  const selectAll = () => {
    setSelectedTools(new Set(availableTools.map(t => t.id)));
  };

  const deselectAll = () => {
    setSelectedTools(new Set());
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md bg-surface-1 border-border">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg font-semibold">
            <Wrench className="w-5 h-5 text-primary" />
            Provision Tools
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4 mt-4">
          {candidateName && (
            <p className="text-sm text-muted-foreground">
              Provisioning tools for: <span className="font-medium text-foreground">{candidateName}</span>
            </p>
          )}
          
          <div className="flex items-center justify-between">
            <Label className="text-sm font-medium">Available Tools</Label>
            <div className="flex gap-2">
              <button 
                onClick={selectAll}
                className="text-xs text-primary hover:underline"
              >
                Select all
              </button>
              <span className="text-muted-foreground">|</span>
              <button 
                onClick={deselectAll}
                className="text-xs text-muted-foreground hover:text-foreground"
              >
                Clear
              </button>
            </div>
          </div>
          
          <div className="grid grid-cols-1 gap-3 max-h-64 overflow-y-auto">
            {availableTools.map((tool) => {
              const isSelected = selectedTools.has(tool.id);
              return (
                <button
                  key={tool.id}
                  type="button"
                  onClick={() => toggleTool(tool.id)}
                  className={`flex items-center gap-4 p-4 rounded-lg border-2 cursor-pointer transition-all text-left hover:scale-[1.01] active:scale-[0.99] ${
                    isSelected 
                      ? 'bg-primary/10 border-primary shadow-[0_0_12px_rgba(var(--primary),0.3)]' 
                      : 'bg-surface-2 border-border hover:border-primary/50 hover:bg-surface-3'
                  }`}
                >
                  <Checkbox
                    checked={isSelected}
                    className="border-muted-foreground data-[state=checked]:bg-primary data-[state=checked]:border-primary"
                  />
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-base transition-all ${
                    isSelected ? 'bg-primary text-primary-foreground' : 'bg-surface-3'
                  }`}>
                    {tool.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`font-medium text-sm ${isSelected ? 'text-primary' : 'text-foreground'}`}>{tool.name}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{tool.description}</p>
                  </div>
                </button>
              );
            })}
          </div>
          
          {selectedTools.size > 0 && (
            <p className="text-xs text-muted-foreground text-center">
              {selectedTools.size} tool{selectedTools.size !== 1 ? 's' : ''} selected
            </p>
          )}
        </div>
        
        <DialogFooter className="mt-6">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button 
            onClick={handleProvision} 
            disabled={selectedTools.size === 0}
          >
            <Wrench className="w-4 h-4 mr-2" />
            Provision
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
