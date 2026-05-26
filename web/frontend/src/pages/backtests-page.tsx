import { useMutation, useQuery } from '@tanstack/react-query';
import { createColumnHelper } from '@tanstack/react-table';
import { useEffect, useMemo, useState } from 'react';
import { Play } from 'lucide-react';
import { api, type StrategyProfile, type WebJob } from '../api';
import { ErrorState, LoadingState } from '../components/query-state';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { DataTable } from '../components/ui/data-table';
import { StatusBadge } from '../components/ui/status-badge';
import { statusText, statusTone } from '../lib/status';
import { formatDateTime, stringifyValue } from '../lib/utils';

const jobColumn = createColumnHelper<WebJob>();

export function BacktestsPage() {
  const [strategySlug, setStrategySlug] = useState('');
  const [profileName, setProfileName] = useState('');
  const [phase, setPhase] = useState<'train' | 'validation' | 'test' | 'custom'>('validation');
  const [timerange, setTimerange] = useState('');
  const strategiesQuery = useQuery({ queryKey: ['strategies'], queryFn: api.strategies });
  const profilesQuery = useQuery({
    queryKey: ['strategy-profiles', strategySlug],
    queryFn: () => api.profiles(strategySlug),
    enabled: Boolean(strategySlug),
  });
  const backtestsQuery = useQuery({ queryKey: ['backtest-results'], queryFn: () => api.backtestResults(50) });
  const validationQuery = useQuery({ queryKey: ['validation-results'], queryFn: () => api.validationResults(50) });

  useEffect(() => {
    const first = strategiesQuery.data?.[0];
    if (!strategySlug && first) {
      setStrategySlug(first.slug);
      setProfileName(first.active_profile ?? '');
    }
  }, [strategiesQuery.data, strategySlug]);

  useEffect(() => {
    const profiles = profilesQuery.data ?? [];
    const active = profiles.find((profile) => profile.is_active) ?? profiles[0];
    const currentProfileExists = profiles.some((profile) => profile.profile_name === profileName);
    if (active && (!profileName || !currentProfileExists)) {
      setProfileName(active.profile_name);
    }
  }, [profileName, profilesQuery.data]);

  const runBacktest = useMutation({
    mutationFn: () =>
      api.runBacktest({
        strategy_slug: strategySlug,
        profile_name: profileName || null,
        phase,
        timerange: timerange || null,
      }),
    onSuccess: () => void backtestsQuery.refetch(),
  });

  const runValidation = useMutation({
    mutationFn: () =>
      api.runValidation({
        strategy_slug: strategySlug,
        profile_name: profileName || null,
        timerange: timerange || null,
        min_trades: 30,
        min_profit: 0,
        min_profit_factor: 1.05,
        max_drawdown: 0.25,
        min_winrate: 0.35,
        min_avg_profit: 0,
        min_trades_per_day: 0.05,
      }),
    onSuccess: () => void validationQuery.refetch(),
  });

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
      jobColumn.accessor('result', {
        header: '结果',
        cell: (info) => <span title={stringifyValue(info.getValue())}>{stringifyValue(info.getValue())}</span>,
      }),
      jobColumn.accessor('updated_at', { header: '更新时间', cell: (info) => formatDateTime(info.getValue()) }),
    ],
    [],
  );

  const profiles = profilesQuery.data ?? [];

  if (strategiesQuery.isLoading) {
    return <LoadingState />;
  }
  if (strategiesQuery.error || profilesQuery.error || backtestsQuery.error || validationQuery.error) {
    return <ErrorState error={strategiesQuery.error ?? profilesQuery.error ?? backtestsQuery.error ?? validationQuery.error} />;
  }

  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader>
          <CardTitle>回测与验证</CardTitle>
          <div className="flex gap-2">
            <Button disabled={!strategySlug || runBacktest.isPending} onClick={() => runBacktest.mutate()}>
              <Play className="h-4 w-4" />
              回测
            </Button>
            <Button variant="ghost" disabled={!strategySlug || runValidation.isPending} onClick={() => runValidation.mutate()}>
              验证
            </Button>
          </div>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-4">
          <label className="grid gap-1 text-sm">
            <span className="text-xs font-semibold text-muted-foreground">策略</span>
            <select className="h-10 rounded-md border border-input bg-muted px-3" value={strategySlug} onChange={(event) => { setStrategySlug(event.target.value); setProfileName(''); }}>
              {strategiesQuery.data?.map((strategy) => <option key={strategy.slug} value={strategy.slug}>{strategy.name}（{strategy.slug}）</option>)}
            </select>
          </label>
          <label className="grid gap-1 text-sm">
            <span className="text-xs font-semibold text-muted-foreground">参数档案</span>
            <select className="h-10 rounded-md border border-input bg-muted px-3" value={profileName} onChange={(event) => setProfileName(event.target.value)}>
              {profiles.map((profile: StrategyProfile) => <option key={profile.profile_name} value={profile.profile_name}>{profile.profile_name}</option>)}
            </select>
          </label>
          <label className="grid gap-1 text-sm">
            <span className="text-xs font-semibold text-muted-foreground">阶段</span>
            <select className="h-10 rounded-md border border-input bg-muted px-3" value={phase} onChange={(event) => setPhase(event.target.value as typeof phase)}>
              <option value="train">train</option>
              <option value="validation">validation</option>
              <option value="test">test</option>
              <option value="custom">custom</option>
            </select>
          </label>
          <label className="grid gap-1 text-sm">
            <span className="text-xs font-semibold text-muted-foreground">Timerange</span>
            <input className="h-10 rounded-md border border-input bg-muted px-3" value={timerange} onChange={(event) => setTimerange(event.target.value)} placeholder="20240101-20240501" />
          </label>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>任务限制</CardTitle>
          <StatusBadge>默认开启</StatusBadge>
        </CardHeader>
        <CardContent className="text-sm leading-6 text-muted-foreground">
          同一策略、参数档案、阶段、Timerange 默认只允许 1 个 pending/running/success 回测或验证任务。train 可以由工作台 AI 推进生成多个候选档案，每个候选单独验证，避免同一份参数重复消耗任务。
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>回测任务</CardTitle></CardHeader>
        <DataTable data={backtestsQuery.data ?? []} columns={columns} />
      </Card>
      <Card>
        <CardHeader><CardTitle>验证任务</CardTitle></CardHeader>
        <DataTable data={validationQuery.data ?? []} columns={columns} />
      </Card>
    </div>
  );
}
