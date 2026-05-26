import { AlertTriangle, Loader2 } from 'lucide-react';

export function LoadingState({ label = '加载中' }: { label?: string }) {
  return (
    <div className="flex min-h-32 items-center justify-center gap-2 text-sm text-muted-foreground">
      <Loader2 className="h-4 w-4 animate-spin" />
      <span>{label}</span>
    </div>
  );
}

export function ErrorState({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : '请求失败';
  return (
    <div className="flex items-start gap-2 rounded-md border border-rose-900 bg-rose-950/40 p-3 text-sm text-rose-100">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
      <span>{message}</span>
    </div>
  );
}

export function EmptyState({ label = '暂无数据' }: { label?: string }) {
  return <div className="flex min-h-24 items-center justify-center text-sm text-muted-foreground">{label}</div>;
}
