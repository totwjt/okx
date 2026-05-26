import { cn } from '../lib/utils';

export function Metric({
  label,
  value,
  className,
}: {
  label: string;
  value: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn('rounded-md border border-border bg-muted/50 p-3', className)}>
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 truncate font-mono text-sm font-semibold text-foreground">{value}</div>
    </div>
  );
}
