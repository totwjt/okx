<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { fetchStrategies, type StrategySummary } from '../api/strategies';
import { fetchBacktestJobs, runBacktest, type BacktestResult } from '../api/backtests';
import {
  fetchValidationJobs,
  promoteProfile,
  runValidation,
  type ValidationResult,
} from '../api/validation';
import type { WebJob } from '../api/jobs';

const loading = ref(false);
const running = ref(false);
const error = ref('');
const validationError = ref('');
const strategies = ref<StrategySummary[]>([]);
const jobs = ref<WebJob[]>([]);
const validationJobs = ref<WebJob[]>([]);
const selectedStrategy = ref('');
const phase = ref<'train' | 'validation' | 'test' | 'custom'>('validation');
const timerange = ref('');
const validationTimerange = ref('20251001-20251003');
const minTrades = ref(1);
const minProfit = ref(0);
const minProfitFactor = ref(1);
const maxDrawdown = ref(0.3);

const selectedStrategyRow = computed(() =>
  strategies.value.find((strategy) => strategy.slug === selectedStrategy.value),
);

async function loadBacktestData() {
  loading.value = true;
  error.value = '';
  try {
    const [strategyRows, jobRows, validationRows] = await Promise.all([
      fetchStrategies(),
      fetchBacktestJobs(50),
      fetchValidationJobs(50),
    ]);
    strategies.value = strategyRows;
    jobs.value = jobRows;
    validationJobs.value = validationRows;
    if (!selectedStrategy.value && strategyRows.length > 0) {
      selectedStrategy.value = strategyRows[0].slug;
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '回测数据加载失败';
  } finally {
    loading.value = false;
  }
}

async function submitBacktest() {
  if (!selectedStrategy.value) return;
  const confirmed = window.confirm(`为 ${selectedStrategy.value} 发起回测任务？`);
  if (!confirmed) return;
  running.value = true;
  error.value = '';
  try {
    await runBacktest({
      strategy_slug: selectedStrategy.value,
      profile_name: selectedStrategyRow.value?.active_profile ?? null,
      phase: phase.value,
      timerange: timerange.value || null,
    });
    jobs.value = await fetchBacktestJobs(50);
    window.setTimeout(() => {
      void loadBacktestData();
    }, 3000);
  } catch (err) {
    error.value = err instanceof Error ? err.message : '回测任务发起失败';
    jobs.value = await fetchBacktestJobs(50).catch(() => jobs.value);
  } finally {
    running.value = false;
  }
}

async function submitValidation() {
  if (!selectedStrategy.value) return;
  const confirmed = window.confirm(`为 ${selectedStrategy.value} 运行验证闸门？`);
  if (!confirmed) return;
  running.value = true;
  validationError.value = '';
  try {
    await runValidation({
      strategy_slug: selectedStrategy.value,
      profile_name: selectedStrategyRow.value?.active_profile ?? null,
      timerange: validationTimerange.value || null,
      min_trades: minTrades.value,
      min_profit: minProfit.value,
      min_profit_factor: minProfitFactor.value,
      max_drawdown: maxDrawdown.value,
      min_winrate: 0,
      min_avg_profit: 0,
      min_trades_per_day: 0,
    });
    validationJobs.value = await fetchValidationJobs(50);
    window.setTimeout(() => {
      void loadBacktestData();
    }, 3000);
  } catch (err) {
    validationError.value = err instanceof Error ? err.message : '验证任务发起失败';
    validationJobs.value = await fetchValidationJobs(50).catch(() => validationJobs.value);
  } finally {
    running.value = false;
  }
}

function resultOf(job: WebJob): BacktestResult | null {
  return job.result as unknown as BacktestResult | null;
}

function validationOf(job: WebJob): ValidationResult | null {
  return job.result as unknown as ValidationResult | null;
}

function metric(job: WebJob, key: keyof BacktestResult['metrics']): string {
  const value = resultOf(job)?.metrics?.[key];
  if (typeof value === 'number') {
    if (key === 'total_trades' || key === 'wins' || key === 'losses' || key === 'draws') {
      return String(value);
    }
    return value.toFixed(4);
  }
  return '-';
}

function statusClass(status: WebJob['status']): string {
  if (status === 'success') return 'badge-ok';
  if (status === 'failed') return 'badge-danger';
  if (status === 'running') return 'badge-info';
  return 'badge-muted';
}

function statusText(status: WebJob['status']): string {
  const labels: Record<WebJob['status'], string> = {
    pending: '等待中',
    running: '运行中',
    success: '成功',
    failed: '失败',
  };
  return labels[status] ?? status;
}

function phaseText(value: unknown): string {
  const labels: Record<string, string> = {
    train: '训练段',
    validation: '验证段',
    test: '测试段',
    custom: '自定义',
  };
  return typeof value === 'string' ? labels[value] ?? value : '-';
}

function formatDate(value: string | null): string {
  if (!value) return '-';
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

function fileName(value: string | undefined): string {
  if (!value) return '-';
  return value.split('/').pop() ?? value;
}

function validationMessageText(value: string | undefined | null): string {
  if (!value) return '-';
  return value
    .replaceAll('total_trades', '交易数')
    .replaceAll('min_trades', '最少交易数')
    .replaceAll('profit_total', '总收益')
    .replaceAll('min_profit', '最低收益')
    .replaceAll('profit_factor', '利润因子')
    .replaceAll('min_profit_factor', '最低利润因子')
    .replaceAll('max_drawdown_account', '账户最大回撤')
    .replaceAll('max_drawdown', '最大回撤')
    .replaceAll('winrate', '胜率')
    .replaceAll('min_winrate', '最低胜率')
    .replaceAll('avg_profit', '平均收益')
    .replaceAll('min_avg_profit', '最低平均收益')
    .replaceAll('trades_per_day', '日均交易数')
    .replaceAll('min_trades_per_day', '最低日均交易数');
}

async function promoteFromValidation(job: WebJob) {
  const result = validationOf(job);
  if (!result?.passed) return;
  const confirmed = window.confirm(`将 ${result.strategy_slug}/${result.profile_name} 晋级为“已验证”？`);
  if (!confirmed) return;
  validationError.value = '';
  try {
    await promoteProfile(result.strategy_slug, result.profile_name, 'validated');
    await loadBacktestData();
  } catch (err) {
    validationError.value = err instanceof Error ? err.message : '参数档案晋级失败';
  }
}

onMounted(loadBacktestData);
</script>

<template>
  <section class="page-grid">
    <div class="panel panel-wide">
      <div class="panel-header">
        <span>回测任务</span>
        <button class="icon-button" type="button" :disabled="loading" @click="loadBacktestData">
          刷新
        </button>
      </div>

      <div class="backtest-form">
        <label class="field-label">
          <span>策略</span>
          <select v-model="selectedStrategy" class="select-input">
            <option v-for="strategy in strategies" :key="strategy.slug" :value="strategy.slug">
              {{ strategy.slug }} / {{ strategy.active_profile ?? '当前生效' }}
            </option>
          </select>
        </label>

        <label class="field-label field-label-compact">
          <span>阶段</span>
          <select v-model="phase" class="select-input">
            <option value="train">训练段</option>
            <option value="validation">验证段</option>
            <option value="test">测试段</option>
            <option value="custom">自定义</option>
          </select>
        </label>

        <label class="field-label">
          <span>时间范围</span>
          <input
            v-model="timerange"
            class="text-input"
            type="text"
            placeholder="留空使用阶段默认范围"
          />
        </label>

        <button
          class="icon-button primary-button"
          type="button"
          :disabled="running || !selectedStrategy"
          @click="submitBacktest"
        >
          发起
        </button>
      </div>
      <div v-if="error" class="error-line">{{ error }}</div>
    </div>

    <div class="panel panel-wide">
      <div class="panel-header">
        <span>验证闸门</span>
        <span class="badge badge-muted">{{ validationJobs.length }}</span>
      </div>

      <div class="backtest-form">
        <label class="field-label">
          <span>时间范围</span>
          <input v-model="validationTimerange" class="text-input" type="text" />
        </label>
        <label class="field-label field-label-compact">
          <span>最少交易数</span>
          <input v-model.number="minTrades" class="text-input" type="number" min="0" />
        </label>
        <label class="field-label field-label-compact">
          <span>最低收益</span>
          <input v-model.number="minProfit" class="text-input" type="number" step="0.001" />
        </label>
        <label class="field-label field-label-compact">
          <span>利润因子</span>
          <input v-model.number="minProfitFactor" class="text-input" type="number" step="0.1" />
        </label>
        <label class="field-label field-label-compact">
          <span>最大回撤</span>
          <input v-model.number="maxDrawdown" class="text-input" type="number" step="0.01" />
        </label>
        <button
          class="icon-button primary-button"
          type="button"
          :disabled="running || !selectedStrategy"
          @click="submitValidation"
        >
          验证
        </button>
      </div>
      <div v-if="validationError" class="error-line">{{ validationError }}</div>

      <div class="table-wrap">
        <table class="dense-table validation-table">
          <thead>
            <tr>
              <th>编号</th>
              <th>闸门</th>
              <th>策略</th>
              <th>参数档案</th>
              <th>时间范围</th>
              <th>交易数</th>
              <th>收益</th>
              <th>回撤</th>
              <th>利润因子</th>
              <th>失败检查</th>
              <th>晋级</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="job in validationJobs" :key="job.id">
              <td class="numeric">#{{ job.id }}</td>
              <td>
                <span
                  :class="[
                    'badge',
                    job.status !== 'success'
                      ? statusClass(job.status)
                      : validationOf(job)?.passed
                        ? 'badge-ok'
                        : 'badge-danger',
                  ]"
                >
                  {{ job.status !== 'success' ? statusText(job.status) : validationOf(job)?.passed ? '通过' : '未通过' }}
                </span>
              </td>
              <td>{{ validationOf(job)?.strategy_slug ?? job.payload.strategy_slug }}</td>
              <td>{{ validationOf(job)?.profile_name ?? job.payload.profile_name ?? '-' }}</td>
              <td>{{ validationOf(job)?.timerange ?? job.payload.timerange ?? '-' }}</td>
              <td class="numeric">{{ validationOf(job)?.metrics.total_trades ?? '-' }}</td>
              <td class="numeric">{{ validationOf(job)?.metrics.profit_total?.toFixed(4) ?? '-' }}</td>
              <td class="numeric">{{ validationOf(job)?.metrics.max_drawdown_account?.toFixed(4) ?? '-' }}</td>
              <td class="numeric">{{ validationOf(job)?.metrics.profit_factor?.toFixed(4) ?? '-' }}</td>
              <td class="path-cell" :title="validationOf(job)?.failed_checks?.join('; ') ?? job.error_summary ?? ''">
                {{ validationMessageText(validationOf(job)?.failed_checks?.join('; ') || job.error_summary) }}
              </td>
              <td>
                <button
                  class="icon-button"
                  type="button"
                  :disabled="!validationOf(job)?.passed"
                  @click="promoteFromValidation(job)"
                >
                  晋级已验证
                </button>
              </td>
            </tr>
            <tr v-if="!loading && validationJobs.length === 0">
              <td colspan="11">暂无验证记录</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="panel panel-wide">
      <div class="panel-header">
        <span>回测结果</span>
        <span class="badge badge-muted">{{ jobs.length }}</span>
      </div>

      <div class="table-wrap">
        <table class="dense-table backtest-table">
          <thead>
            <tr>
              <th>编号</th>
              <th>状态</th>
              <th>策略</th>
              <th>阶段</th>
              <th>时间范围</th>
              <th>交易数</th>
              <th>收益</th>
              <th>回撤</th>
              <th>胜率</th>
              <th>利润因子</th>
              <th>产物</th>
              <th>完成时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="job in jobs" :key="job.id">
              <td class="numeric">#{{ job.id }}</td>
              <td><span :class="['badge', statusClass(job.status)]">{{ statusText(job.status) }}</span></td>
              <td>{{ resultOf(job)?.strategy_slug ?? job.payload.strategy_slug }}</td>
              <td>{{ phaseText(resultOf(job)?.phase ?? job.payload.phase) }}</td>
              <td>{{ resultOf(job)?.timerange ?? job.payload.timerange ?? '-' }}</td>
              <td class="numeric">{{ metric(job, 'total_trades') }}</td>
              <td class="numeric">{{ metric(job, 'profit_total') }}</td>
              <td class="numeric">{{ metric(job, 'max_drawdown_account') }}</td>
              <td class="numeric">{{ metric(job, 'winrate') }}</td>
              <td class="numeric">{{ metric(job, 'profit_factor') }}</td>
              <td class="path-cell" :title="resultOf(job)?.backtest_zip ?? job.error_summary ?? ''">
                {{ job.status === 'failed' ? job.error_summary : fileName(resultOf(job)?.backtest_zip) }}
              </td>
              <td>{{ formatDate(job.finished_at) }}</td>
            </tr>
            <tr v-if="!loading && jobs.length === 0">
              <td colspan="12">暂无回测记录</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>
