import { useQuery } from '@tanstack/react-query';
import { createColumnHelper } from '@tanstack/react-table';
import { useMemo } from 'react';
import { api, type FactorDataset } from '../api';
import { ErrorState, LoadingState } from '../components/query-state';
import { Metric } from '../components/metric';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { DataTable } from '../components/ui/data-table';
import { StatusBadge } from '../components/ui/status-badge';
import { formatDateTime, formatNumber } from '../lib/utils';

const factorColumn = createColumnHelper<FactorDataset>();

export function FactorsPage() {
  const query = useQuery({ queryKey: ['factors-health'], queryFn: api.factorsHealth });
  const columns = useMemo(
    () => [
      factorColumn.accessor('filename', { header: '文件' }),
      factorColumn.accessor('kind', { header: '类型' }),
      factorColumn.accessor('pair', { header: '交易对', cell: (info) => info.getValue() ?? '-' }),
      factorColumn.accessor('timeframe', { header: '周期', cell: (info) => info.getValue() ?? '-' }),
      factorColumn.accessor('rows', { header: '行数', cell: (info) => formatNumber(info.getValue(), 0) }),
      factorColumn.accessor('gap_count', { header: '缺口', cell: (info) => formatNumber(info.getValue(), 0) }),
      factorColumn.accessor('start', { header: '开始', cell: (info) => formatDateTime(info.getValue()) }),
      factorColumn.accessor('end', { header: '结束', cell: (info) => formatDateTime(info.getValue()) }),
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
  const rows = [...(data?.coverage.ohlcv ?? []), ...(data?.coverage.funding ?? [])];

  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader>
          <CardTitle>因子数据健康</CardTitle>
          <StatusBadge tone={data?.ok ? 'success' : 'warning'}>{data?.ok ? '正常' : '需检查'}</StatusBadge>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-5">
          <Metric label="数据集" value={data?.summary.dataset_count ?? 0} />
          <Metric label="OHLCV" value={data?.summary.ohlcv_count ?? 0} />
          <Metric label="Funding" value={data?.summary.funding_count ?? 0} />
          <Metric label="有缺口" value={data?.summary.gap_dataset_count ?? 0} />
          <Metric label="错误" value={data?.summary.error_count ?? 0} />
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>覆盖明细</CardTitle></CardHeader>
        <DataTable data={rows} columns={columns} />
      </Card>
    </div>
  );
}
