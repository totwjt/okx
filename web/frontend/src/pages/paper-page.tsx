import { useQuery } from '@tanstack/react-query';
import { api } from '../api';
import { ErrorState, LoadingState } from '../components/query-state';
import { Metric } from '../components/metric';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { StatusBadge } from '../components/ui/status-badge';
import { formatNumber, formatPercent, stringifyValue } from '../lib/utils';

export function PaperPage() {
  const query = useQuery({ queryKey: ['paper-summary'], queryFn: api.paperSummary, refetchInterval: 10000 });

  if (query.isLoading) {
    return <LoadingState />;
  }
  if (query.error) {
    return <ErrorState error={query.error} />;
  }

  const data = query.data;

  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader>
          <CardTitle>模拟盘概览</CardTitle>
          <StatusBadge tone={data?.ok ? 'success' : 'warning'}>{data?.mode ?? '-'}</StatusBadge>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-4">
          <Metric label="Dry Run" value={data?.dry_run ? '是' : '否'} />
          <Metric label="交易模式" value={`${data?.trading_mode ?? '-'} / ${data?.margin_mode ?? '-'}`} />
          <Metric label="Freqtrade API" value={data?.api.ok ? '正常' : data?.api.url ?? '-'} />
          <Metric label="交易对" value={data?.pair_whitelist?.join(', ') || '-'} />
        </CardContent>
      </Card>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>账户与收益</CardTitle></CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-2">
            <Metric label="总资产" value={formatNumber(Number(data?.balance.data?.total))} />
            <Metric label="Bot 资产" value={formatNumber(Number(data?.balance.data?.total_bot))} />
            <Metric label="总收益" value={formatNumber(data?.profit.data?.profit_all_coin)} />
            <Metric label="收益率" value={formatPercent(data?.profit.data?.profit_all_percent)} />
            <Metric label="已平仓" value={formatNumber(data?.profit.data?.closed_trade_count, 0)} />
            <Metric label="胜率" value={formatPercent(data?.profit.data?.winrate)} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>持仓与最近交易</CardTitle></CardHeader>
          <CardContent className="grid gap-3 text-sm">
            <div className="rounded-md border border-border bg-muted/50 p-3">
              <div className="text-xs text-muted-foreground">开放交易</div>
              <div className="mt-1 font-mono font-semibold">{data?.open_trades.count ?? 0}</div>
            </div>
            {(data?.recent_trades.items ?? []).slice(0, 5).map((trade, index) => (
              <div key={index} className="rounded-md border border-border bg-muted/50 p-3 text-xs text-muted-foreground">
                {stringifyValue(trade)}
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
