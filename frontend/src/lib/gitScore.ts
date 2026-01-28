// Utility function to convert numeric git score to letter grade
// Adjusted ranges for better distribution across candidates
// Since git score is average of 6 metrics, these ranges provide better differentiation
export function getGitGrade(score: number): string {
  if (score >= 90) return 'A+';  // Exceptional (top 5-10%)
    if (score >= 80) return 'A';   // Excellent (top 10-20%)
    if (score >= 70) return 'B+';  // Very Good (top 20-30%)
    if (score >= 60) return 'B';   // Good (30-40%)
    if (score >= 50) return 'C+';  // Above Average (40-50%)
    if (score >= 40) return 'C';   // Average (50-60%)
    if (score >= 30) return 'D+';  // Below Average (60-70%)
    if (score >= 20) return 'D';  // Poor (70-80%)
    return 'F';                    // Inadequate (< 20)
  }
// Get color class based on grade
export function getGradeColor(grade: string): string {
  if (grade.startsWith('A')) return 'text-terminal-green';
  if (grade.startsWith('B')) return 'text-terminal-cyan';
  if (grade.startsWith('C')) return 'text-terminal-amber';
  if (grade.startsWith('D')) return 'text-terminal-amber';
  return 'text-terminal-red';
}

// Get background color class based on grade
export function getGradeBgColor(grade: string): string {
  if (grade.startsWith('A')) return 'bg-terminal-green/20';
  if (grade.startsWith('B')) return 'bg-terminal-cyan/20';
  if (grade.startsWith('C')) return 'bg-terminal-amber/20';
  if (grade.startsWith('D')) return 'bg-terminal-amber/20';
  return 'bg-terminal-red/20';
}
