import { useQuery, useQueryClient } from '@tanstack/react-query';
import { createColumnHelper } from '@tanstack/react-table';
import { useCallback, useMemo } from 'react';
import { RefreshCw } from 'lucide-react';
import { api, type WebJob } from '../api';
import { useRealtimeStatus, useRealtimeTopic } from '../hooks/use-realtime';
import { statusText, statusTone } from '../lib/status';
import { formatDateTime, stringifyValue } from '../lib/utils';
import { ErrorState, LoadingState } from '../components/query-state';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle } from '../components/ui/card';
import { DataTable } from '../components/ui/data-table';
import { StatusBadge } from '../components/ui/status-badge';

const jobColumn = createColumnHelper<WebJob>();

export function JobsPage() {
  const queryClient = useQueryClient();
  const jobsQuery = useQuery({ queryKey: ['jobs'], queryFn: () => api.jobs(100) });
  const realtimeStatus = useRealtimeStatus();

  const handleJobs = useCallback(
    () => void queryClient.invalidateQueries({ queryKey: ['jobs'] }),
    [queryClient],
  );
  useRealtimeTopic('jobs', handleJobs);

  const columns = useMemo(
    () => [
      jobColumn.accessor('id', { header: 'ID' }),
      jobColumn.accessor('job_type', { header: '类型' }),
      jobColumn.accessor('status', {
        header: '状态',
        cell: (info) => <StatusBadge tone={statusTone(info.getValue())}>{statusText(info.getValue())}</StatusBadge>,
      }),
      jobColumn.accessor('payload', {
        header: '参数',
        cell: (info) => <span title={stringifyValue(info.getValue())}>{stringifyValue(info.getValue())}</span>,
      }),
      jobColumn.accessor('error_summary', { header: '错误', cell: (info) => info.getValue() ?? '-' }),
      jobColumn.accessor('updated_at', { header: '更新时间', cell: (info) => formatDateTime(info.getValue()) }),
    ],
    [],
  );

  if (jobsQuery.error) {
    return <ErrorState error={jobsQuery.error} />;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>任务队列</CardTitle>
        <div className="flex items-center gap-2">
          <StatusBadge tone={statusTone(realtimeStatus)}>WS {realtimeStatus}</StatusBadge>
          <Button variant="ghost" onClick={() => void jobsQuery.refetch()}>
            <RefreshCw className="h-4 w-4" />
            刷新
          </Button>
        </div>
      </CardHeader>
      {jobsQuery.isLoading ? <LoadingState /> : <DataTable data={jobsQuery.data ?? []} columns={columns} />}
    </Card>
  );
}
