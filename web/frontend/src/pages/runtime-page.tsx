import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createColumnHelper } from '@tanstack/react-table';
import { useCallback, useMemo, useState } from 'react';
import { RefreshCw, Wand2 } from 'lucide-react';
import { api, type RuntimeArtifact, type WebJob } from '../api';
import { useRealtimeStatus, useRealtimeTopic } from '../hooks/use-realtime';
import { artifactTypeText, statusTone } from '../lib/status';
import { fileName, formatDateTime, shortHash } from '../lib/utils';
import { ErrorState, LoadingState } from '../components/query-state';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { DataTable } from '../components/ui/data-table';
import { StatusBadge } from '../components/ui/status-badge';

const artifactColumn = createColumnHelper<RuntimeArtifact>();

export function RuntimePage() {
  const queryClient = useQueryClient();
  const realtimeStatus = useRealtimeStatus();
  const [selectedStrategy, setSelectedStrategy] = useState('');
  const strategiesQuery = useQuery({ queryKey: ['strategies'], queryFn: api.strategies });
  const artifactsQuery = useQuery({ queryKey: ['runtime-artifacts'], queryFn: () => api.runtimeArtifacts(50) });
  const systemQuery = useQuery({ queryKey: ['system-check'], queryFn: api.systemCheck });

  const materializeMutation = useMutation({
    mutationFn: () => api.materialize(selectedStrategy),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['jobs'] }),
  });

  const handleRuntime = useCallback(
    () => void queryClient.invalidateQueries({ queryKey: ['runtime-artifacts'] }),
    [queryClient],
  );
  const handleJobs = useCallback(
    (message: { payload: { items?: WebJob[] } }) => {
      const finished = message.payload.items?.some((job) =>
        ['success', 'failed'].includes(job.status) && job.job_type === 'materialize',
      );
      if (finished) {
        void queryClient.invalidateQueries({ queryKey: ['runtime-artifacts'] });
        void queryClient.invalidateQueries({ queryKey: ['system-check'] });
      }
    },
    [queryClient],
  );

  useRealtimeTopic('runtime.artifacts', handleRuntime);
  useRealtimeTopic('jobs', handleJobs);

  const strategies = strategiesQuery.data ?? [];
  const selected = selectedStrategy || strategies[0]?.slug || '';

  const columns = useMemo(
    () => [
      artifactColumn.accessor('strategy_slug', { header: '策略' }),
      artifactColumn.accessor('profile_name', { header: '参数档案' }),
      artifactColumn.accessor('artifact_type', { header: '类型', cell: (info) => artifactTypeText(info.getValue()) }),
      artifactColumn.accessor('artifact_path', {
        header: '文件',
        cell: (info) => <span title={info.getValue()}>{fileName(info.getValue())}</span>,
      }),
      artifactColumn.accessor('artifact_hash', {
        header: '哈希',
        cell: (info) => <span title={info.getValue()}>{shortHash(info.getValue())}</span>,
      }),
      artifactColumn.accessor('created_at', { header: '生成时间', cell: (info) => formatDateTime(info.getValue()) }),
    ],
    [],
  );

  if (strategiesQuery.error || artifactsQuery.error || systemQuery.error) {
    return <ErrorState error={strategiesQuery.error ?? artifactsQuery.error ?? systemQuery.error} />;
  }

  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader>
          <CardTitle>生成运行产物</CardTitle>
          <Button
            disabled={materializeMutation.isPending || !selected}
            onClick={() => materializeMutation.mutate()}
          >
            <Wand2 className="h-4 w-4" />
            {materializeMutation.isPending ? '生成中' : '生成'}
          </Button>
        </CardHeader>
        <CardContent className="grid gap-3 lg:grid-cols-[360px_minmax(0,1fr)]">
          <label className="grid gap-1 text-sm">
            <span className="text-xs font-semibold text-muted-foreground">策略</span>
            <select
              className="h-10 rounded-md border border-input bg-muted px-3"
              value={selected}
              onChange={(event) => setSelectedStrategy(event.target.value)}
            >
              {strategies.map((strategy) => (
                <option key={strategy.slug} value={strategy.slug}>
                  {strategy.slug} / {strategy.active_profile ?? '当前生效'}
                </option>
              ))}
            </select>
          </label>
          <div className="rounded-md border border-border bg-muted/50 p-3 text-sm text-muted-foreground">
            操作会写入运行策略目录；实时通道{' '}
            <StatusBadge tone={statusTone(realtimeStatus)}>{realtimeStatus}</StatusBadge>，完成后自动刷新。
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>运行产物</CardTitle>
          <Button variant="ghost" onClick={() => void artifactsQuery.refetch()}>
            <RefreshCw className="h-4 w-4" />
            刷新
          </Button>
        </CardHeader>
        {artifactsQuery.isLoading ? <LoadingState /> : <DataTable data={artifactsQuery.data ?? []} columns={columns} />}
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>系统检查</CardTitle>
          <StatusBadge tone={systemQuery.data?.ok ? 'success' : 'warning'}>
            {systemQuery.data?.operations_ready ? '可运行' : '需检查'}
          </StatusBadge>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2">
          {Object.entries(systemQuery.data?.checks ?? {}).map(([name, check]) => (
            <div key={name} className="rounded-md border border-border bg-muted/50 p-3">
              <div className="mb-2 flex items-center justify-between">
                <span className="font-semibold">{name}</span>
                <StatusBadge tone={check.ok ? 'success' : 'warning'}>{check.ok ? '正常' : '警告'}</StatusBadge>
              </div>
              <pre className="overflow-auto whitespace-pre-wrap text-xs text-muted-foreground">{JSON.stringify(check, null, 2)}</pre>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
