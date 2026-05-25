<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { fetchFactorsHealth, type FactorDataset, type FactorsHealth } from '../api/factors';
import StatusTag from '../components/StatusTag.vue';

const loading = ref(false);
const error = ref('');
const health = ref<FactorsHealth | null>(null);

const worstGaps = computed(() => {
  const allRows = [...(health.value?.coverage.ohlcv ?? []), ...(health.value?.coverage.funding ?? [])];
  return allRows
    .filter((row) => (row.gap_count ?? 0) > 0 || !row.ok)
    .sort((a, b) => (b.missing_intervals ?? 0) - (a.missing_intervals ?? 0))
    .slice(0, 8);
});

async function loadFactors() {
  loading.value = true;
  error.value = '';
  try {
    health.value = await fetchFactorsHealth();
  } catch (err) {
    error.value = err instanceof Error ? err.message : '因子数据健康检查失败';
  } finally {
    loading.value = false;
  }
}

function numberText(value: unknown): string {
  return typeof value === 'number' ? value.toLocaleString() : '-';
}

function dateText(value: unknown): string {
  if (typeof value !== 'string' || !value) {
    return '-';
  }
  return value.replace('T', ' ').replace('+00:00', 'Z');
}

function intervalText(seconds: unknown): string {
  if (typeof seconds !== 'number' || seconds <= 0) {
    return '-';
  }
  if (seconds % 3600 === 0) {
    return `${seconds / 3600}h`;
  }
  if (seconds % 60 === 0) {
    return `${seconds / 60}m`;
  }
  return `${seconds}s`;
}

function statusTone(row: FactorDataset): 'default' | 'success' | 'warning' | 'error' {
  if (!row.ok) {
    return 'error';
  }
  if ((row.gap_count ?? 0) > 0) {
    return 'warning';
  }
  if ((row.rows ?? 0) === 0) {
    return 'default';
  }
  return 'success';
}

function statusText(row: FactorDataset): string {
  if (!row.ok) {
    return '异常';
  }
  if ((row.gap_count ?? 0) > 0) {
    return '有缺口';
  }
  if ((row.rows ?? 0) === 0) {
    return '空数据';
  }
  return '正常';
}

function firstGap(row: FactorDataset): string {
  const sample = row.samples?.[0];
  if (!sample) {
    return '-';
  }
  return `${dateText(sample.from)} -> ${dateText(sample.to)} (${numberText(sample.missing_intervals)})`;
}

onMounted(loadFactors);
</script>

<template>
  <section class="page-grid">
    <div class="panel panel-wide">
      <div class="panel-header">
        <span>因子数据健康</span>
        <button class="icon-button" type="button" :disabled="loading" @click="loadFactors">
          刷新
        </button>
      </div>

      <div v-if="error" class="error-line">{{ error }}</div>
      <div v-if="health?.error" class="error-line">{{ health.error }}</div>

      <div v-if="health" class="factor-status-grid">
        <div class="detail-cell">
          <span>数据集</span>
          <strong>{{ numberText(health.summary.dataset_count) }}</strong>
        </div>
        <div class="detail-cell">
          <span>OHLCV</span>
          <strong>{{ numberText(health.summary.ohlcv_count) }}</strong>
        </div>
        <div class="detail-cell">
          <span>资金费率</span>
          <strong>{{ numberText(health.summary.funding_count) }}</strong>
        </div>
        <div class="detail-cell">
          <span>存在缺口</span>
          <strong>{{ numberText(health.summary.gap_dataset_count) }}</strong>
        </div>
        <div class="detail-cell">
          <span>扫描状态</span>
          <strong>{{ health.ok ? '正常' : '异常' }}</strong>
        </div>
        <div class="detail-cell">
          <span>读取路径</span>
          <strong>Freqtrade 容器</strong>
        </div>
      </div>
      <div v-else class="placeholder-body">{{ loading ? '加载中' : '暂无数据' }}</div>
    </div>

    <div class="panel panel-wide">
      <div class="panel-header">
        <span>资金费率覆盖</span>
        <StatusTag>{{ health?.coverage.funding.length ?? 0 }}</StatusTag>
      </div>
      <div class="table-wrap">
        <table class="dense-table factor-table">
          <thead>
            <tr>
              <th>交易对</th>
              <th>来源</th>
              <th>间隔</th>
              <th>行数</th>
              <th>开始</th>
              <th>结束</th>
              <th>缺口</th>
              <th>缺失</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in health?.coverage.funding ?? []" :key="row.file">
              <td>{{ row.pair }}</td>
              <td>{{ row.source }}</td>
              <td class="numeric">{{ intervalText(row.expected_interval_seconds) }}</td>
              <td class="numeric">{{ numberText(row.rows) }}</td>
              <td>{{ dateText(row.start) }}</td>
              <td>{{ dateText(row.end) }}</td>
              <td class="numeric">{{ numberText(row.gap_count) }}</td>
              <td class="numeric">{{ numberText(row.missing_intervals) }}</td>
              <td><StatusTag :tone="statusTone(row)">{{ statusText(row) }}</StatusTag></td>
            </tr>
            <tr v-if="health && health.coverage.funding.length === 0">
              <td colspan="9">暂无资金费率数据集</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="panel panel-wide">
      <div class="panel-header">
        <span>OHLCV 覆盖</span>
        <StatusTag>{{ health?.coverage.ohlcv.length ?? 0 }}</StatusTag>
      </div>
      <div class="table-wrap">
        <table class="dense-table factor-table">
          <thead>
            <tr>
              <th>交易对</th>
              <th>类型</th>
              <th>周期</th>
              <th>行数</th>
              <th>开始</th>
              <th>结束</th>
              <th>缺口</th>
              <th>缺失</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in health?.coverage.ohlcv ?? []" :key="row.file">
              <td>{{ row.pair }}</td>
              <td>{{ row.kind }}</td>
              <td class="numeric">{{ row.timeframe }}</td>
              <td class="numeric">{{ numberText(row.rows) }}</td>
              <td>{{ dateText(row.start) }}</td>
              <td>{{ dateText(row.end) }}</td>
              <td class="numeric">{{ numberText(row.gap_count) }}</td>
              <td class="numeric">{{ numberText(row.missing_intervals) }}</td>
              <td><StatusTag :tone="statusTone(row)">{{ statusText(row) }}</StatusTag></td>
            </tr>
            <tr v-if="health && health.coverage.ohlcv.length === 0">
              <td colspan="9">暂无 OHLCV 数据集</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="panel panel-wide">
      <div class="panel-header">
        <span>缺口样本</span>
        <StatusTag>{{ worstGaps.length }}</StatusTag>
      </div>
      <div class="table-wrap">
        <table class="dense-table gap-table">
          <thead>
            <tr>
              <th>数据集</th>
              <th>类型</th>
              <th>缺口</th>
              <th>缺失</th>
              <th>最大缺口</th>
              <th>首个样本</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in worstGaps" :key="`gap-${row.file}`">
              <td>{{ row.filename }}</td>
              <td>{{ row.kind }}</td>
              <td class="numeric">{{ numberText(row.gap_count) }}</td>
              <td class="numeric">{{ numberText(row.missing_intervals) }}</td>
              <td class="numeric">{{ intervalText(row.max_gap_seconds) }}</td>
              <td class="path-cell">{{ row.error ?? firstGap(row) }}</td>
            </tr>
            <tr v-if="health && worstGaps.length === 0">
              <td colspan="6">未发现缺口</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>
