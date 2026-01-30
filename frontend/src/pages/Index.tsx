// Main index page component
import { useState, useEffect } from 'react';
import { Menu } from 'lucide-react';
import { AppSidebar } from '@/components/layout/AppSidebar';
import { ThemeToggle } from '@/components/ThemeToggle';
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
    <div className="flex h-screen w-full bg-background overflow-hidden">
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
      
      <main className="flex-1 min-h-0 overflow-auto flex flex-col">
        {/* Desktop: top bar with theme toggle (only for Builder/Job Board; Experts has it in header) */}
        {!isMobile && activeSection !== 'experts' && (
          <div className="app-bar sticky top-0 z-20 flex items-center justify-end h-10 px-4 md:px-6 shrink-0 backdrop-blur-md bg-background/80">
            <ThemeToggle variant="icon" size="icon" className="shrink-0" />
          </div>
        )}
        {/* Mobile header */}
        {isMobile && (
          <div className="sticky top-0 z-30 bg-background p-3 flex items-center justify-between gap-3 shrink-0">
            <div className="flex items-center gap-3">
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
            <ThemeToggle variant="icon" size="icon" />
          </div>
        )}
        
        <div className="pt-8 px-4 pb-4 md:pt-10 md:px-8 md:pb-8 flex-1 min-h-0 flex flex-col">
          <div className={cn(
            "mx-auto flex-1 min-h-0 flex flex-col w-full",
            activeSection === 'experts' ? "max-w-7xl" : "max-w-[90rem]"
          )}>
            <ActiveComponent key={activeSection} />
          </div>
        </div>
      </main>
    </div>
  );
}
