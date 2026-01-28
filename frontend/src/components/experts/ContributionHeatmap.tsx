/// <reference types="vite/client" />
import { useEffect, useState, useMemo } from 'react'

interface ContributionHeatmapProps {
  username: string
}

interface ContributionDay {
  date: string
  contributionCount: number
  color: string
}

interface ContributionWeek {
  contributionDays: ContributionDay[]
}

interface ContributionData {
  weeks: ContributionWeek[]
  totalContributions: number
}

// GitHub Personal Access Token from environment
// Note: Vite only exposes env vars prefixed with VITE_ to the frontend
const GITHUB_TOKEN = import.meta.env.VITE_GITHUB_TOKEN || ''

function ContributionHeatmap({ username }: ContributionHeatmapProps) {
  const [selectedYear, setSelectedYear] = useState<number>(new Date().getFullYear())
  const [contributionData, setContributionData] = useState<ContributionData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const availableYears = [2024, 2025, 2026]

  // GraphQL query to fetch contribution data
  const getContributionQuery = (username: string, year: number) => {
    const from = `${year}-01-01T00:00:00Z`
    const to = `${year}-12-31T23:59:59Z`
    
    return `
      query($userName: String!, $from: DateTime!, $to: DateTime!) {
        user(login: $userName) {
          contributionsCollection(from: $from, to: $to) {
            contributionCalendar {
              totalContributions
              weeks {
                contributionDays {
                  date
                  contributionCount
                  color
                }
              }
            }
          }
        }
      }
    `
  }

  const fetchContributions = async (year: number) => {
    if (!GITHUB_TOKEN || GITHUB_TOKEN === '') {
      setError('GitHub token not configured')
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const fromDate = `${year}-01-01T00:00:00Z`
      const toDate = `${year}-12-31T23:59:59Z`

      const query = getContributionQuery(username, year)
      const variables = {
        userName: username,
        from: fromDate,
        to: toDate
      }

      const response = await fetch('https://api.github.com/graphql', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${GITHUB_TOKEN}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query,
          variables
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()

      if (result.errors) {
        throw new Error(result.errors[0].message)
      }

      const calendar = result.data?.user?.contributionsCollection?.contributionCalendar
      if (!calendar) {
        throw new Error('No contribution data found')
      }

      let weeks = calendar.weeks || []
      const expectedWeeks = 53
      const finalWeeks: ContributionWeek[] = []
      
      // Determine the actual start date from GitHub's first week
      let actualStartDate: Date | null = null
      if (weeks.length > 0 && weeks[0]?.contributionDays?.length > 0) {
        const firstDayDate = new Date(weeks[0].contributionDays[0].date)
        const dayOfWeek = firstDayDate.getDay()
        const mondayOffset = dayOfWeek === 0 ? -6 : 1 - dayOfWeek
        actualStartDate = new Date(firstDayDate)
        actualStartDate.setDate(firstDayDate.getDate() + mondayOffset)
      }
      
      // Fallback to calculated start date
      if (!actualStartDate) {
        const jan1 = new Date(year, 0, 1)
        const dayOfWeek = jan1.getDay()
        const mondayOffset = dayOfWeek === 0 ? -6 : 1 - dayOfWeek
        actualStartDate = new Date(jan1)
        actualStartDate.setDate(jan1.getDate() + mondayOffset)
      }
      
      // Create exactly 53 weeks with 7 days each
      for (let i = 0; i < expectedWeeks; i++) {
        const weekDays: ContributionDay[] = []
        const weekStartDate = new Date(actualStartDate)
        weekStartDate.setDate(actualStartDate.getDate() + (i * 7))
        
        const githubDaysMap = new Map<string, ContributionDay>()
        if (i < weeks.length && weeks[i]?.contributionDays) {
          weeks[i].contributionDays.forEach((day: ContributionDay) => {
            githubDaysMap.set(day.date, day)
          })
        }
        
        for (let d = 0; d < 7; d++) {
          const dayDate = new Date(weekStartDate)
          dayDate.setDate(weekStartDate.getDate() + d)
          const dateStr = dayDate.toISOString().split('T')[0]
          
          const githubDay = githubDaysMap.get(dateStr)
          
          if (githubDay) {
            weekDays.push(githubDay)
          } else {
            weekDays.push({
              date: dateStr,
              contributionCount: 0,
              color: '#ebedf0'
            })
          }
        }
        
        finalWeeks.push({ contributionDays: weekDays })
      }
      
      setContributionData({
        weeks: finalWeeks,
        totalContributions: calendar.totalContributions
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch contributions')
      console.error('Error fetching contributions:', err)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (username) {
      fetchContributions(selectedYear)
    }
  }, [username, selectedYear])

  // Get contribution level for custom colors
  const getContributionLevel = (count: number, maxCount: number) => {
    if (count === 0) return 0
    const ratio = count / maxCount
    if (ratio < 0.25) return 1
    if (ratio < 0.5) return 2
    if (ratio < 0.75) return 3
    return 4
  }

  // Calculate max contributions for color scaling
  const maxContributions = useMemo(() => {
    if (!contributionData) return 1
    
    let max = 0
    contributionData.weeks.forEach(week => {
      week.contributionDays.forEach(day => {
        if (day.contributionCount > max) {
          max = day.contributionCount
        }
      })
    })
    return Math.max(max, 1)
  }, [contributionData])

  // Generate month labels - find the last week of each month (like GitHub does)
  // Labels appear near the end of each month, not at the beginning
  const monthLabels = useMemo(() => {
    const labels: Array<{ weekIndex: number; month: string }> = []
    if (!contributionData) return labels
  
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    const seen = new Set<number>()
  
    // Find the last week that contains each month (position labels at end of month)
    for (let monthIdx = 0; monthIdx < 12; monthIdx++) {
      if (seen.has(monthIdx)) continue
      
      // Find the last day of this month
      const lastDayOfMonth = new Date(selectedYear, monthIdx + 1, 0) // Day 0 of next month = last day of current month
      const lastDayStr = lastDayOfMonth.toISOString().split('T')[0]
      
      // Search backwards through weeks to find the last week containing this month
      let foundWeekIndex = -1
      for (let weekIndex = contributionData.weeks.length - 1; weekIndex >= 0; weekIndex--) {
        const week = contributionData.weeks[weekIndex]
        const days = week.contributionDays || []
        
        // Check if this week contains any day from this month
        const hasMonthDay = days.some(d => {
          const dt = new Date(d.date)
          return dt.getFullYear() === selectedYear && dt.getMonth() === monthIdx
        })
        
        if (hasMonthDay) {
          foundWeekIndex = weekIndex
          break // Found the last week for this month
        }
      }
      
      if (foundWeekIndex !== -1) {
        labels.push({ weekIndex: foundWeekIndex, month: months[monthIdx] })
        seen.add(monthIdx)
      }
    }
  
    // Sort by week index to ensure correct order
    labels.sort((a, b) => a.weekIndex - b.weekIndex)
    return labels
  }, [contributionData, selectedYear])

  const getHeatmapColor = (level: number) => {
    const colors = [
      'bg-surface-2',      // level 0 - no contributions
      'bg-primary/20',     // level 1 - low
      'bg-primary/40',     // level 2 - medium-low
      'bg-primary/60',      // level 3 - medium-high
      'bg-primary/80',      // level 4 - high
    ]
    return colors[level] || colors[0]
  }

  if (error && (!GITHUB_TOKEN || GITHUB_TOKEN === '')) {
    return (
      <div className="card-terminal p-6">
        <div className="text-center py-8">
          <p className="text-sm text-muted-foreground mb-2">⚠️ GitHub Token Required</p>
          <p className="text-xs text-muted-foreground">Configure VITE_GITHUB_TOKEN in .env file to view heatmap</p>
        </div>
      </div>
    )
  }

  return (
    <div className="card-terminal p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-mono uppercase text-muted-foreground">Contribution Activity</h3>
        <div className="flex items-center gap-3">
          <select 
            className="px-3 py-1.5 text-xs bg-surface-2 border border-border rounded font-mono text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
            value={selectedYear}
            onChange={(e) => setSelectedYear(Number(e.target.value))}
            disabled={isLoading}
          >
            {availableYears.map(year => (
              <option key={year} value={year}>
                {year}
              </option>
            ))}
          </select>
          {contributionData && (
            <span className="text-xs text-muted-foreground font-mono">
              {contributionData.totalContributions} contributions
            </span>
          )}
        </div>
      </div>
      
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="text-sm text-muted-foreground">Loading contributions...</div>
        </div>
      )}

      {error && GITHUB_TOKEN && (
        <div className="text-center py-8">
          <p className="text-sm text-destructive">⚠️ Error: {error}</p>
        </div>
      )}

      {!isLoading && !error && contributionData && (
        <div className="overflow-x-auto">
          {/* Calculate total width: day labels (20px) + 53 weeks (12px each + 2px gaps) */}
          {/* 53 weeks: 53 * 12px = 636px, 52 gaps: 52 * 2px = 104px, total = 740px */}
          <div className="inline-block" style={{ width: '760px' }}>
            {/* Month labels - positioned at the end of each month (like GitHub) */}
            <div className="relative mb-2" style={{ paddingLeft: '20px', height: '16px', width: '740px' }}>
              {monthLabels.map((label, idx) => {
                // Calculate position: each week column is 14px wide (12px square + 2px gap)
                // Position labels at the end of the month (last week of that month)
                const weekWidth = 14  // 12px square + 2px gap
                // Position at the week that contains the end of the month
                const position = label.weekIndex * weekWidth
                return (
                  <span
                    key={`month-${idx}`}
                    className="absolute text-xs text-muted-foreground font-mono whitespace-nowrap"
                    style={{ 
                      left: `${position}px`
                    }}
                  >
                    {label.month}
                  </span>
                )
              })}
            </div>
            
            {/* Heatmap grid */}
            <div className="flex gap-[2px]">
              {/* Day labels */}
              <div className="flex flex-col gap-[2px] mr-2 flex-shrink-0">
                {['Mon', '', 'Wed', '', 'Fri', '', 'Sun'].map((day, idx) => (
                  <div key={idx} className="w-3 h-3 flex items-center">
                    {day && (
                      <span className="text-xs text-muted-foreground font-mono text-right w-full">
                        {day}
                      </span>
                    )}
                  </div>
                ))}
              </div>
              
              {/* Weeks - ensure all 53 weeks are visible, including Nov/Dec */}
              <div className="flex gap-[2px] flex-shrink-0">
                {contributionData.weeks.map((week, weekIndex) => (
                  <div key={weekIndex} className="flex flex-col gap-[2px]">
                    {week.contributionDays.map((day, dayIndex) => {
                      const level = getContributionLevel(day.contributionCount, maxContributions)
                      const date = new Date(day.date).toLocaleDateString()
                      return (
                        <div
                          key={dayIndex}
                          className={`w-3 h-3 rounded-sm ${getHeatmapColor(level)} cursor-pointer hover:ring-2 hover:ring-primary/50 transition-all`}
                          title={`${date}: ${day.contributionCount} contributions`}
                        />
                      )
                    })}
                  </div>
                ))}
              </div>
            </div>
            
            {/* Legend */}
            <div className="flex items-center gap-2 mt-4 justify-end">
              <span className="text-xs text-muted-foreground font-mono">Less</span>
              <div className="flex gap-[2px]">
                {[0, 1, 2, 3, 4].map((level) => (
                  <div
                    key={level}
                    className={`w-3 h-3 rounded-sm ${getHeatmapColor(level)}`}
                  />
                ))}
              </div>
              <span className="text-xs text-muted-foreground font-mono">More</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ContributionHeatmap
