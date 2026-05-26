import { useQuery } from '@tanstack/react-query';
import { createColumnHelper } from '@tanstack/react-table';
import { useEffect, useMemo, useState } from 'react';
import { api, type StrategyProfile, type StrategySummary } from '../api';
import { ErrorState, LoadingState } from '../components/query-state';
import { Metric } from '../components/metric';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { DataTable } from '../components/ui/data-table';
import { StatusBadge } from '../components/ui/status-badge';
import { countKeys, formatDateTime } from '../lib/utils';
import { statusText, statusTone } from '../lib/status';

const profileColumn = createColumnHelper<StrategyProfile>();

export function StrategiesPage() {
  const [selectedSlug, setSelectedSlug] = useState('');
  const strategiesQuery = useQuery({ queryKey: ['strategies'], queryFn: api.strategies });
  const strategies = strategiesQuery.data ?? [];

  useEffect(() => {
    if (!selectedSlug && strategies.length > 0) {
      setSelectedSlug(strategies[0].slug);
    }
  }, [selectedSlug, strategies]);

  const detailQuery = useQuery({
    queryKey: ['strategy', selectedSlug],
    queryFn: () => api.strategy(selectedSlug),
    enabled: Boolean(selectedSlug),
  });
  const profilesQuery = useQuery({
    queryKey: ['strategy-profiles', selectedSlug],
    queryFn: () => api.profiles(selectedSlug),
    enabled: Boolean(selectedSlug),
  });

  const selectedSummary = strategies.find((strategy) => strategy.slug === selectedSlug);
  const profiles = profilesQuery.data ?? [];
  const visibleSpecKeys = useMemo(() => {
    const hidden = new Set(['entry_conditions', 'exit_conditions', 'derived_indicators']);
    return Object.keys(detailQuery.data?.spec ?? {}).filter((key) => !hidden.has(key)).sort();
  }, [detailQuery.data?.spec]);

  const columns = useMemo(
    () => [
      profileColumn.accessor('profile_name', { header: '参数档案' }),
      profileColumn.accessor('status', {
        header: '状态',
        cell: (info) => <StatusBadge tone={statusTone(info.getValue())}>{statusText(info.getValue())}</StatusBadge>,
      }),
      profileColumn.accessor('is_active', { header: '生效', cell: (info) => (info.getValue() ? '是' : '-') }),
      profileColumn.accessor('source', { header: '来源', cell: (info) => info.getValue() ?? '-' }),
      profileColumn.accessor('overrides', { header: '覆盖参数', cell: (info) => countKeys(info.getValue()) }),
      profileColumn.accessor('validation', { header: '验证信息', cell: (info) => countKeys(info.getValue()) }),
      profileColumn.accessor('updated_at', { header: '更新时间', cell: (info) => formatDateTime(info.getValue()) }),
    ],
    [],
  );

  if (strategiesQuery.isLoading) {
    return <LoadingState />;
  }
  if (strategiesQuery.error) {
    return <ErrorState error={strategiesQuery.error} />;
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[340px_minmax(0,1fr)]">
      <Card>
        <CardHeader>
          <CardTitle>策略注册表</CardTitle>
          <Button variant="ghost" onClick={() => void strategiesQuery.refetch()}>
            刷新
          </Button>
        </CardHeader>
        <CardContent className="grid gap-2">
          {strategies.map((strategy: StrategySummary) => (
            <button
              key={strategy.slug}
              type="button"
              onClick={() => setSelectedSlug(strategy.slug)}
              className={`rounded-md border p-3 text-left transition ${
                strategy.slug === selectedSlug
                  ? 'border-primary/40 bg-primary/10 text-primary'
                  : 'border-border bg-muted/40 hover:bg-muted'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="truncate text-sm font-bold">{strategy.name}</div>
                  <div className="truncate font-mono text-xs text-muted-foreground">{strategy.slug}</div>
                </div>
                <StatusBadge tone={statusTone(strategy.status)}>{statusText(strategy.status)}</StatusBadge>
              </div>
            </button>
          ))}
        </CardContent>
      </Card>

      <div className="grid gap-4">
        <Card>
          <CardHeader>
            <CardTitle>{selectedSummary?.name ?? '策略详情'}</CardTitle>
            {selectedSummary ? (
              <StatusBadge tone={statusTone(selectedSummary.status)}>{statusText(selectedSummary.status)}</StatusBadge>
            ) : null}
          </CardHeader>
          <CardContent>
            {detailQuery.isLoading ? (
              <LoadingState />
            ) : detailQuery.error ? (
              <ErrorState error={detailQuery.error} />
            ) : (
              <div className="grid gap-3 md:grid-cols-4">
                <Metric label="策略标识" value={detailQuery.data?.slug ?? '-'} />
                <Metric label="当前参数档案" value={detailQuery.data?.active_profile ?? '-'} />
                <Metric label="参数档案数" value={detailQuery.data?.profile_count ?? 0} />
                <Metric label="更新时间" value={formatDateTime(detailQuery.data?.updated_at)} />
                <Metric className="md:col-span-4" label="说明" value={detailQuery.data?.description ?? '-'} />
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>参数档案状态</CardTitle>
            <StatusBadge>{profiles.filter((profile) => profile.is_active).length} 个生效</StatusBadge>
          </CardHeader>
          <DataTable data={profiles} columns={columns} />
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>策略定义摘要</CardTitle>
            <StatusBadge>不展示生成代码</StatusBadge>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {visibleSpecKeys.map((key) => (
              <div key={key} className="rounded-md border border-border bg-muted px-3 py-2">
                <div className="text-xs text-muted-foreground">{key}</div>
                <div className="text-sm font-semibold">{typeof detailQuery.data?.spec[key]}</div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
