// Main index page component
import { useState, useEffect } from 'react';
import { Menu } from 'lucide-react';
import { AppSidebar } from '@/components/layout/AppSidebar';
import { ExpertsTable } from '@/components/experts/ExpertsTable';
import { IdeaGeneration } from '@/components/ideas/IdeaGeneration';
import { JobBoardSection } from '@/components/sections/JobBoardSection';
import { cn } from '@/lib/utils';

type SectionKey = 'experts' | 'builder' | 'jobs';

const sectionComponents: Record<SectionKey, React.ComponentType> = {
  experts: ExpertsTable,
  builder: IdeaGeneration,
  jobs: JobBoardSection,
};

export default function Index() {
  const [activeSection, setActiveSection] = useState<SectionKey>('experts');
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // Detect mobile viewport
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
      if (window.innerWidth < 768) {
        setIsCollapsed(true);
      }
    };
    
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Close mobile menu when section changes
  const handleSectionChange = (section: SectionKey) => {
    setActiveSection(section);
    if (isMobile) {
      setIsMobileMenuOpen(false);
    }
  };

  const ActiveComponent = sectionComponents[activeSection];

  return (
    <div className="flex min-h-screen w-full bg-background">
      {/* Mobile menu overlay */}
      {isMobile && isMobileMenuOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar - hidden on mobile unless menu is open */}
      <div className={cn(
        "md:relative md:block",
        isMobile && "fixed inset-y-0 left-0 z-50 transition-transform duration-300",
        isMobile && !isMobileMenuOpen && "-translate-x-full"
      )}>
        <AppSidebar
          activeSection={activeSection}
          onSectionChange={handleSectionChange}
          isCollapsed={isMobile ? false : isCollapsed}
          onToggleCollapse={() => isMobile ? setIsMobileMenuOpen(false) : setIsCollapsed(!isCollapsed)}
        />
      </div>
      
      <main className="flex-1 overflow-auto">
        {/* Mobile header */}
        {isMobile && (
          <div className="sticky top-0 z-30 bg-background border-b border-border p-4 flex items-center gap-3">
            <button
              onClick={() => setIsMobileMenuOpen(true)}
              className="p-2 rounded-lg bg-surface-2 hover:bg-surface-3 transition-colors"
            >
              <Menu className="w-5 h-5 text-foreground" />
            </button>
            <h1 className="font-mono font-semibold text-foreground">
              {activeSection === 'experts' ? 'Experts' : activeSection === 'builder' ? 'Builder' : 'Job Board'}
            </h1>
          </div>
        )}
        
        <div className="p-4 md:p-8">
          <div className="max-w-7xl mx-auto h-full">
            <ActiveComponent key={activeSection} />
          </div>
        </div>
      </main>
    </div>
  );
}
