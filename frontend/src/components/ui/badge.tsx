import type { ReactNode } from 'react'
import { cn } from '../../lib/utils'

export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'teal' | 'amber' }) {
  return <span className={cn('badge', `badge-${tone}`)}>{children}</span>
}
