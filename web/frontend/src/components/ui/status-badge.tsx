import type * as React from 'react';
import { cn } from '@/lib/utils';
import type { StatusTone } from '@/lib/status';

const toneClass: Record<StatusTone, string> = {
  default: 'border-input bg-muted text-foreground',
  success: 'border-emerald-300 bg-emerald-50 text-emerald-700 dark:border-emerald-700 dark:bg-emerald-950 dark:text-emerald-200',
  processing: 'border-sky-300 bg-sky-50 text-sky-700 dark:border-sky-700 dark:bg-sky-950 dark:text-sky-200',
  warning: 'border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-200',
  error: 'border-rose-300 bg-rose-50 text-rose-700 dark:border-rose-700 dark:bg-rose-950 dark:text-rose-200',
};

export function StatusBadge({
  tone = 'default',
  children,
  className,
}: {
  tone?: StatusTone;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        'inline-flex min-h-6 items-center rounded-md border px-2 text-xs font-semibold leading-none',
        toneClass[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
