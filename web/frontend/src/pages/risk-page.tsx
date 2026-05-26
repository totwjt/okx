import { useQuery } from '@tanstack/react-query';
import { createColumnHelper } from '@tanstack/react-table';
import { useMemo } from 'react';
import { api, type RiskSummary } from '../api';
import { ErrorState, LoadingState } from '../components/query-state';
import { Metric } from '../components/metric';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { DataTable } from '../components/ui/data-table';
import { StatusBadge } from '../components/ui/status-badge';
import { statusText, statusTone } from '../lib/status';
import { formatNumber, formatPercent, stringifyValue } from '../lib/utils';

type RiskCheck = RiskSummary['checks'][number];
const checkColumn = createColumnHelper<RiskCheck>();

export function RiskPage() {
  const query = useQuery({ queryKey: ['risk-summary'], queryFn: api.riskSummary, refetchInterval: 10000 });
  const columns = useMemo(
    () => [
      checkColumn.accessor('label', { header: '检查项' }),
      checkColumn.accessor('observed', { header: '观测值', cell: (info) => formatNumber(info.getValue()) }),
      checkColumn.accessor('limit', { header: '限制', cell: (info) => formatNumber(info.getValue()) }),
      checkColumn.accessor('status', {
        header: '状态',
        cell: (info) => <StatusBadge tone={statusTone(info.getValue())}>{statusText(info.getValue())}</StatusBadge>,
      }),
    ],
    [],
  );

  if (query.isLoading) {
    return <LoadingState />;
  }
  if (query.error) {
    return <ErrorState error={query.error} />;
  }

  const data = query.data;
  const dailyLoss = data?.metrics.daily_loss as { loss_ratio?: number; loss_abs?: number; closed_trades?: number } | undefined;
  const consecutive = data?.metrics.consecutive_losses as { count?: number } | undefined;

  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader>
          <CardTitle>风控状态</CardTitle>
          <StatusBadge tone={data?.ok ? 'success' : 'error'}>{data?.ok ? '正常' : '异常'}</StatusBadge>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-4">
          <Metric label="策略" value={data?.strategy.strategy_name ?? data?.strategy.slug ?? '-'} />
          <Metric label="参数档案" value={data?.strategy.profile_name ?? '-'} />
          <Metric label="当日亏损" value={formatPercent(dailyLoss?.loss_ratio)} />
          <Metric label="连续亏损" value={consecutive?.count ?? 0} />
          <Metric label="最大回撤限制" value={formatPercent(Number(data?.rules.max_drawdown_pct ?? 0) / 100)} />
          <Metric label="日亏损金额" value={formatNumber(dailyLoss?.loss_abs)} />
          <Metric label="当日平仓" value={dailyLoss?.closed_trades ?? 0} />
          <Metric label="模式" value={data?.mode ?? '-'} />
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>规则检查</CardTitle></CardHeader>
        <DataTable data={data?.checks ?? []} columns={columns} />
      </Card>
      <Card>
        <CardHeader><CardTitle>错误与最近交易</CardTitle></CardHeader>
        <CardContent className="grid gap-3">
          <pre className="overflow-auto rounded-md border border-border bg-muted/50 p-3 text-xs text-muted-foreground">{stringifyValue(data?.errors)}</pre>
          {(data?.recent_closed_trades ?? []).slice(0, 5).map((trade, index) => (
            <div key={index} className="rounded-md border border-border bg-muted/50 p-3 text-xs text-muted-foreground">
              {stringifyValue(trade)}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
