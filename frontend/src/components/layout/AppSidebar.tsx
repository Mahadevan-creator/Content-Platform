import { useState } from 'react';
import { Users, Hammer, Briefcase, ChevronRight, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';

type SectionKey = 'experts' | 'builder' | 'jobs';

interface AppSidebarProps {
  activeSection: SectionKey;
  onSectionChange: (section: SectionKey) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

const sections = [
  { key: 'experts' as const, label: 'Experts', icon: Users, description: 'Manage your talent pool' },
  { key: 'builder' as const, label: 'Builder', icon: Hammer, description: 'Powered by Agent Fleet' },
  { key: 'jobs' as const, label: 'Job Board', icon: Briefcase, description: 'Post and manage jobs' },
];

export function AppSidebar({ activeSection, onSectionChange, isCollapsed, onToggleCollapse }: AppSidebarProps) {
  const [hoveredSection, setHoveredSection] = useState<SectionKey | null>(null);

  return (
    <aside
      className={cn(
        "h-screen bg-sidebar border-r border-sidebar-border flex flex-col transition-all duration-300",
        isCollapsed ? "w-16" : "w-64",
        "flex-shrink-0"
      )}
    >
      {/* Header: logo and title only */}
      <div className="p-4 border-b border-sidebar-border">
        <div className={cn(
          "flex items-center gap-3",
          isCollapsed && "justify-center"
        )}>
          <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center glow-green-subtle shrink-0">
            <Sparkles className="w-4 h-4 text-primary" />
          </div>
          {!isCollapsed && (
            <div className="animate-fade-in flex-1 min-w-0">
              <h1 className="font-mono font-semibold text-foreground tracking-tight">Content Platform</h1>
              <p className="text-[10px] text-muted-foreground font-mono">AI-Powered Creation</p>
            </div>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4">
        <div className="px-3 mb-2">
          {!isCollapsed && (
            <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
              Workspace
            </span>
          )}
        </div>
        
        {sections.map((section) => {
          const isActive = activeSection === section.key;
          const isHovered = hoveredSection === section.key;
          
          return (
            <button
              key={section.key}
              onClick={() => onSectionChange(section.key)}
              onMouseEnter={() => setHoveredSection(section.key)}
              onMouseLeave={() => setHoveredSection(null)}
              className={cn(
                "w-full sidebar-item flex items-center gap-3",
                isActive && "active"
              )}
            >
              <div className={cn(
                "w-8 h-8 rounded-lg flex items-center justify-center transition-all duration-200",
                isActive 
                  ? "bg-primary/20 text-primary" 
                  : "bg-surface-2 text-muted-foreground",
                isHovered && !isActive && "bg-surface-3 text-foreground"
              )}>
                <section.icon className="w-4 h-4" />
              </div>
              
              {!isCollapsed && (
                <div className="flex-1 text-left animate-fade-in">
                  <div className={cn(
                    "text-sm font-medium transition-colors",
                    isActive ? "text-foreground" : "text-muted-foreground"
                  )}>
                    {section.label}
                  </div>
                  <div className="text-[10px] text-muted-foreground">
                    {section.description}
                  </div>
                </div>
              )}
              
              {!isCollapsed && (
                <ChevronRight className={cn(
                  "w-4 h-4 text-muted-foreground transition-all duration-200",
                  isActive && "text-primary rotate-90"
                )} />
              )}
            </button>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-sidebar-border">
        <button
          onClick={onToggleCollapse}
          className="w-full p-2 rounded-lg bg-surface-2 hover:bg-surface-3 transition-colors flex items-center justify-center gap-2"
        >
          <ChevronRight className={cn(
            "w-4 h-4 text-muted-foreground transition-transform duration-300",
            isCollapsed ? "rotate-0" : "rotate-180"
          )} />
          {!isCollapsed && (
            <span className="text-xs text-muted-foreground font-mono">Collapse</span>
          )}
        </button>
      </div>
    </aside>
  );
}
