import { useState, useMemo } from 'react';
import { X, Check, ChevronDown, MapPin, Code, Mail, UserCheck, Award, FileCheck, TrendingUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import * as SliderPrimitive from '@radix-ui/react-slider';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import type { ExpertWithDisplay } from '@/hooks/useExperts';
import { getGitGrade } from '@/lib/gitScore';

export interface FilterState {
  locations: Set<string>;
  skills: Set<string>;
  emailFound: 'all' | 'found' | 'not-found';
  status: Set<'available' | 'interviewing' | 'onboarded' | 'contracted'>;
  gitGrades: Set<string>;
  interviewResult: 'all' | 'pass' | 'fail' | 'strong_pass';
  hrwScoreRange: [number, number];
}

const defaultFilters: FilterState = {
  locations: new Set(),
  skills: new Set(),
  emailFound: 'all',
  status: new Set(),
  gitGrades: new Set(),
  interviewResult: 'all',
  hrwScoreRange: [0, 100],
};

interface ExpertsFiltersProps {
  experts: ExpertWithDisplay[];
  filters: FilterState;
  onFiltersChange: (filters: FilterState) => void;
  onClearFilters: () => void;
}

const gitGradeOptions = ['A+', 'A', 'B+', 'B', 'C+', 'C', 'D+', 'D', 'F'];
const statusOptions = [
  { value: 'available' as const, label: 'Available' },
  { value: 'interviewing' as const, label: 'Interviewing' },
  { value: 'onboarded' as const, label: 'Onboarded' },
  { value: 'contracted' as const, label: 'Contracted' },
];

export function ExpertsFilters({ experts, filters, onFiltersChange, onClearFilters }: ExpertsFiltersProps) {
  const [skillsPopoverOpen, setSkillsPopoverOpen] = useState(false);
  const [skillsSearch, setSkillsSearch] = useState('');

  // Intelligently normalize locations to merge variants like "New Delhi" and "New Delhi, India"
  const allLocations = useMemo(() => {
    // Helper function to extract base location (before first comma)
    const getBaseLocation = (location: string): string => {
      return location.split(',')[0].trim().toLowerCase();
    };
    
    // Helper function to check if one location contains another as a complete word/phrase
    const isContainedLocation = (shorter: string, longer: string): boolean => {
      const shorterNorm = shorter.toLowerCase();
      const longerNorm = longer.toLowerCase();
      
      if (shorterNorm === longerNorm) return false;
      
      // Check if shorter is at the start of longer (e.g., "new delhi" in "new delhi, india")
      if (longerNorm.startsWith(shorterNorm + ',')) return true;
      if (longerNorm.startsWith(shorterNorm + ' ')) return true;
      
      // Check if shorter is the base location of longer
      const longerBase = getBaseLocation(longer);
      if (shorterNorm === longerBase) return true;
      
      // Check if shorter is a word in longer (word boundary match)
      const longerWords = longerNorm.split(/[\s,]+/);
      const shorterWords = shorterNorm.split(/[\s,]+/);
      
      // Check if all words of shorter appear consecutively in longer
      if (shorterWords.length > 0) {
        for (let i = 0; i <= longerWords.length - shorterWords.length; i++) {
          const matches = shorterWords.every((word, idx) => longerWords[i + idx] === word);
          if (matches) return true;
        }
      }
      
      return false;
    };
    
    // Step 1: Collect all unique locations (case-insensitive exact matches)
    const locationMap = new Map<string, string>(); // normalized -> original
    
    experts.forEach(e => {
      if (e.location) {
        const trimmed = e.location.trim();
        if (trimmed) {
          const normalized = trimmed.toLowerCase();
          // Keep the longest version if we see the same normalized location
          if (!locationMap.has(normalized) || trimmed.length > locationMap.get(normalized)!.length) {
            locationMap.set(normalized, trimmed);
          }
        }
      }
    });

    // Step 2: Merge locations where one contains another
    // Sort by length (longest first) to process more specific locations first
    const entries = Array.from(locationMap.entries())
      .map(([normalized, original]) => ({ normalized, original }))
      .sort((a, b) => {
        // Sort by: 1) length (longest first), 2) alphabetically
        if (b.normalized.length !== a.normalized.length) {
          return b.normalized.length - a.normalized.length;
        }
        return a.normalized.localeCompare(b.normalized);
      });
    
    const result: Array<{ normalized: string; original: string }> = [];
    
    for (const entry of entries) {
      let shouldAdd = true;
      
      // Check if this location is contained in any already-added location
      for (const existing of result) {
        if (isContainedLocation(entry.normalized, existing.normalized)) {
          shouldAdd = false;
          break;
        }
      }
      
      if (shouldAdd) {
        // Remove any existing locations that are contained in this one
        for (let i = result.length - 1; i >= 0; i--) {
          if (isContainedLocation(result[i].normalized, entry.normalized)) {
            result.splice(i, 1);
          }
        }
        result.push(entry);
      }
    }
    
    // Sort final results alphabetically
    return result.map(e => e.original).sort();
  }, [experts]);

  const allSkills = useMemo(() => {
    return Array.from(new Set(experts.flatMap(e => e.skills))).sort();
  }, [experts]);

  const filteredSkills = useMemo(() => {
    if (!skillsSearch) return allSkills;
    const searchLower = skillsSearch.toLowerCase();
    return allSkills.filter(skill => skill.toLowerCase().includes(searchLower));
  }, [allSkills, skillsSearch]);

  // Calculate HRW score range from actual data
  const hrwScoreRange = useMemo(() => {
    const scores = experts
      .map(e => (e as any).hrwScore || (e as any).hrw_score)
      .filter((score): score is number => typeof score === 'number');
    if (scores.length === 0) return [0, 100];
    return [Math.min(...scores), Math.max(...scores)];
  }, [experts]);

  const updateFilters = (updates: Partial<FilterState>) => {
    onFiltersChange({ ...filters, ...updates });
  };

  const toggleLocation = (location: string) => {
    const newLocations = new Set(filters.locations);
    // Store normalized (lowercase) for comparison, but display original case
    const normalized = location.toLowerCase();
    if (newLocations.has(normalized)) {
      newLocations.delete(normalized);
    } else {
      newLocations.add(normalized);
    }
    updateFilters({ locations: newLocations });
  };

  const toggleSkill = (skill: string) => {
    const newSkills = new Set(filters.skills);
    if (newSkills.has(skill)) {
      newSkills.delete(skill);
    } else {
      newSkills.add(skill);
    }
    updateFilters({ skills: newSkills });
  };

  const toggleStatus = (status: 'available' | 'interviewing' | 'onboarded' | 'contracted') => {
    const newStatus = new Set(filters.status);
    if (newStatus.has(status)) {
      newStatus.delete(status);
    } else {
      newStatus.add(status);
    }
    updateFilters({ status: newStatus });
  };

  const toggleGitGrade = (grade: string) => {
    const newGrades = new Set(filters.gitGrades);
    if (newGrades.has(grade)) {
      newGrades.delete(grade);
    } else {
      newGrades.add(grade);
    }
    updateFilters({ gitGrades: newGrades });
  };

  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (filters.locations.size > 0) count++;
    if (filters.skills.size > 0) count++;
    if (filters.emailFound !== 'all') count++;
    if (filters.status.size > 0) count++;
    if (filters.gitGrades.size > 0) count++;
    if (filters.interviewResult !== 'all') count++;
    // Check if HRW range is different from the full data range
    const isDefaultRange = filters.hrwScoreRange[0] === hrwScoreRange[0] && 
                          filters.hrwScoreRange[1] === hrwScoreRange[1];
    if (!isDefaultRange) count++;
    return count;
  }, [filters, hrwScoreRange]);

  const hasActiveFilters = activeFilterCount > 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-foreground">Filters</h3>
          {hasActiveFilters && (
            <p className="text-xs text-muted-foreground mt-1">
              {activeFilterCount} active filter{activeFilterCount !== 1 ? 's' : ''}
            </p>
          )}
        </div>
        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onClearFilters}
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            Clear all
          </Button>
        )}
      </div>

      {/* Location Filter */}
      <div className="space-y-3">
        <Label className="text-sm font-medium flex items-center gap-2">
          <MapPin className="w-4 h-4" />
          Location
        </Label>
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {allLocations.length === 0 ? (
            <p className="text-xs text-muted-foreground">No locations available</p>
          ) : (
            allLocations.map(location => (
              <div key={location} className="flex items-center space-x-2">
                <Checkbox
                  id={`location-${location}`}
                  checked={filters.locations.has(location.toLowerCase())}
                  onCheckedChange={() => toggleLocation(location)}
                />
                <Label
                  htmlFor={`location-${location}`}
                  className="text-sm cursor-pointer flex-1"
                >
                  {location}
                </Label>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Skills Filter - Multi-select with search */}
      <div className="space-y-3">
        <Label className="text-sm font-medium flex items-center gap-2">
          <Code className="w-4 h-4" />
          Skills
        </Label>
        <Popover open={skillsPopoverOpen} onOpenChange={setSkillsPopoverOpen}>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              role="combobox"
              className="w-full justify-between bg-surface-1 border-border"
            >
              <span className="truncate">
                {filters.skills.size === 0
                  ? 'Select skills...'
                  : `${filters.skills.size} skill${filters.skills.size !== 1 ? 's' : ''} selected`}
              </span>
              <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-[300px] p-0" align="start">
            <Command shouldFilter={false} className="!overflow-visible">
              <CommandInput
                placeholder="Search skills..."
                value={skillsSearch}
                onValueChange={setSkillsSearch}
                className="border-b"
              />
              <div 
                className="max-h-[300px] overflow-y-auto overflow-x-hidden"
                onWheel={(e) => e.stopPropagation()}
              >
                <CommandList className="max-h-none">
                  <CommandEmpty>No skills found.</CommandEmpty>
                  <CommandGroup>
                    {filteredSkills.map(skill => (
                      <CommandItem
                        key={skill}
                        value={skill}
                        onSelect={() => {
                          toggleSkill(skill);
                          setSkillsSearch('');
                        }}
                        className="cursor-pointer"
                      >
                        <Check
                          className={cn(
                            "mr-2 h-4 w-4",
                            filters.skills.has(skill) ? "opacity-100" : "opacity-0"
                          )}
                        />
                        {skill}
                      </CommandItem>
                    ))}
                  </CommandGroup>
                </CommandList>
              </div>
            </Command>
          </PopoverContent>
        </Popover>
        {filters.skills.size > 0 && (
          <div className="flex flex-wrap gap-2 mt-2">
            {Array.from(filters.skills).map(skill => (
              <Badge
                key={skill}
                variant="secondary"
                className="text-xs cursor-pointer hover:bg-secondary/80"
                onClick={() => toggleSkill(skill)}
              >
                {skill}
                <X className="ml-1 h-3 w-3" />
              </Badge>
            ))}
          </div>
        )}
      </div>

      {/* Email Found Filter */}
      <div className="space-y-3">
        <Label className="text-sm font-medium flex items-center gap-2">
          <Mail className="w-4 h-4" />
          Email Status
        </Label>
        <Select
          value={filters.emailFound}
          onValueChange={(value: 'all' | 'found' | 'not-found') =>
            updateFilters({ emailFound: value })
          }
        >
          <SelectTrigger className="w-full bg-surface-1 border-border">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="found">Email Found</SelectItem>
            <SelectItem value="not-found">Email Not Found</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Status Filter */}
      <div className="space-y-3">
        <Label className="text-sm font-medium flex items-center gap-2">
          <UserCheck className="w-4 h-4" />
          Status
        </Label>
        <div className="space-y-2">
          {statusOptions.map(option => (
            <div key={option.value} className="flex items-center space-x-2">
              <Checkbox
                id={`status-${option.value}`}
                checked={filters.status.has(option.value)}
                onCheckedChange={() => toggleStatus(option.value)}
              />
              <Label
                htmlFor={`status-${option.value}`}
                className="text-sm cursor-pointer flex-1"
              >
                {option.label}
              </Label>
            </div>
          ))}
        </div>
      </div>

      {/* Git Grade Filter */}
      <div className="space-y-3">
        <Label className="text-sm font-medium flex items-center gap-2">
          <Award className="w-4 h-4" />
          Git Grade
        </Label>
        <div className="flex flex-wrap gap-2">
          {gitGradeOptions.map(grade => (
            <Button
              key={grade}
              variant={filters.gitGrades.has(grade) ? 'default' : 'outline'}
              size="sm"
              onClick={() => toggleGitGrade(grade)}
              className={cn(
                "text-xs",
                filters.gitGrades.has(grade) && "bg-primary text-primary-foreground"
              )}
            >
              {grade}
            </Button>
          ))}
        </div>
      </div>

      {/* Interview Result Filter */}
      <div className="space-y-3">
        <Label className="text-sm font-medium flex items-center gap-2">
          <FileCheck className="w-4 h-4" />
          Interview Result
        </Label>
        <Select
          value={filters.interviewResult}
          onValueChange={(value: 'all' | 'pass' | 'fail' | 'strong_pass') =>
            updateFilters({ interviewResult: value })
          }
        >
          <SelectTrigger className="w-full bg-surface-1 border-border">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="pass">Pass</SelectItem>
            <SelectItem value="strong_pass">Strong Pass</SelectItem>
            <SelectItem value="fail">Fail</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* HRW Score Filter */}
      <div className="space-y-3">
        <Label className="text-sm font-medium flex items-center gap-2">
          <TrendingUp className="w-4 h-4" />
          HRW Score
        </Label>
        <div className="space-y-4 px-2">
          <div className="relative">
            <SliderPrimitive.Root
              value={[
                Math.min(...filters.hrwScoreRange),
                Math.max(...filters.hrwScoreRange)
              ]}
              onValueChange={(value) => {
                // Ensure range is always [min, max] - left handle is min, right handle is max
                const sorted = [...value].sort((a, b) => a - b) as [number, number];
                updateFilters({ hrwScoreRange: sorted });
              }}
              min={hrwScoreRange[0]}
              max={hrwScoreRange[1]}
              step={1}
              className="relative flex w-full touch-none select-none items-center"
            >
              <SliderPrimitive.Track className="relative h-2 w-full grow overflow-hidden rounded-full bg-secondary">
                {/* Selected range (between handles) - highlighted to show what's INCLUDED */}
                <SliderPrimitive.Range className="absolute h-full bg-primary" />
              </SliderPrimitive.Track>
              <SliderPrimitive.Thumb className="block h-5 w-5 rounded-full border-2 border-primary bg-background ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50" />
              <SliderPrimitive.Thumb className="block h-5 w-5 rounded-full border-2 border-primary bg-background ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50" />
            </SliderPrimitive.Root>
          </div>
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Min: {Math.round(Math.min(...filters.hrwScoreRange))}</span>
            <span>Max: {Math.round(Math.max(...filters.hrwScoreRange))}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export { defaultFilters };
