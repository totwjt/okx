<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { fetchRiskSummary, type RiskSummary } from '../api/risk';

const loading = ref(false);
const error = ref('');
const summary = ref<RiskSummary | null>(null);

const ruleRows = computed(() => [
  ['最大回撤', pctFromNumber(summary.value?.rules.max_drawdown_pct)],
  ['单日亏损', pctFromNumber(summary.value?.rules.max_daily_loss_pct)],
  ['连续亏损', text(summary.value?.rules.max_consecutive_losses)],
  ['冷却期', `${text(summary.value?.rules.cooldown_candles_after_loss_streak)} 根K线`],
  ['最大持仓数', text(summary.value?.rules.max_open_trades)],
  ['要求保护配置', summary.value?.rules.protections_in_config_required ? '是' : '否'],
]);

async function loadRisk() {
  loading.value = true;
  error.value = '';
  try {
    summary.value = await fetchRiskSummary();
  } catch (err) {
    error.value = err instanceof Error ? err.message : '风控摘要加载失败';
  } finally {
    loading.value = false;
  }
}

function text(value: unknown): string {
  return value === undefined || value === null || value === '' ? '-' : String(value);
}

function money(value: unknown): string {
  return typeof value === 'number' ? value.toFixed(4) : '-';
}

function pctRatio(value: unknown): string {
  return typeof value === 'number' ? `${(value * 100).toFixed(2)}%` : '-';
}

function pctFromNumber(value: unknown): string {
  return typeof value === 'number' ? `${value.toFixed(2)}%` : '-';
}

function checkValue(check: { key: string; observed: number }): string {
  if (check.key === 'consecutive_losses' || check.key === 'cooldown') {
    return String(check.observed);
  }
  return pctRatio(check.observed);
}

function checkLimit(check: { key: string; limit?: number }): string {
  if (check.limit === undefined || check.limit === null) {
    return '-';
  }
  if (check.key === 'consecutive_losses' || check.key === 'cooldown') {
    return String(check.limit);
  }
  return pctRatio(check.limit);
}

function badgeClass(status: string): string {
  if (status === 'ok' || status === 'standby') {
    return 'badge-ok';
  }
  if (status === 'active') {
    return 'badge-info';
  }
  if (status === 'breach') {
    return 'badge-danger';
  }
  return 'badge-muted';
}

function statusText(status: string): string {
  const labels: Record<string, string> = {
    ok: '正常',
    standby: '待命',
    active: '生效',
    breach: '触发',
  };
  return labels[status] ?? status;
}

function checkLabelText(key: string, fallback: string): string {
  const labels: Record<string, string> = {
    max_drawdown: '最大回撤',
    daily_loss: '单日亏损',
    consecutive_losses: '连续亏损',
    cooldown: '冷却期',
  };
  return labels[key] ?? fallback;
}

function sideText(value: unknown): string {
  if (value === 'long') return '多';
  if (value === 'short') return '空';
  return text(value);
}

function side(trade: Record<string, unknown>): string {
  return trade.is_short ? '空' : '多';
}

onMounted(loadRisk);
</script>

<template>
  <section class="page-grid">
    <div class="panel panel-wide">
      <div class="panel-header">
        <span>风控概览</span>
        <button class="icon-button" type="button" :disabled="loading" @click="loadRisk">
          刷新
        </button>
      </div>

      <div v-if="error" class="error-line">{{ error }}</div>
      <div v-if="summary?.source.rule_error" class="error-line">{{ summary.source.rule_error }}</div>

      <div v-if="summary" class="risk-status-grid">
        <div class="detail-cell">
          <span>模式</span>
          <strong>{{ summary.mode }}</strong>
        </div>
        <div class="detail-cell">
          <span>策略</span>
          <strong>{{ summary.strategy.slug }} / {{ summary.strategy.profile_name }}</strong>
        </div>
        <div class="detail-cell">
          <span>最大回撤</span>
          <strong>{{ pctRatio(summary.metrics.max_drawdown_ratio) }} / {{ money(summary.metrics.max_drawdown_abs) }}</strong>
        </div>
        <div class="detail-cell">
          <span>当前回撤</span>
          <strong>{{ pctRatio(summary.metrics.current_drawdown_ratio) }} / {{ money(summary.metrics.current_drawdown_abs) }}</strong>
        </div>
        <div class="detail-cell">
          <span>单日亏损</span>
          <strong>{{ pctRatio(summary.metrics.daily_loss.loss_ratio) }} / {{ money(summary.metrics.daily_loss.loss_abs) }}</strong>
        </div>
        <div class="detail-cell">
          <span>连续亏损</span>
          <strong>{{ summary.metrics.consecutive_losses.count }}</strong>
        </div>
        <div class="detail-cell">
          <span>冷却期</span>
          <strong>{{ summary.metrics.cooldown.active_locks }} 个生效 / {{ summary.metrics.cooldown.configured_candles }} 根K线</strong>
        </div>
        <div class="detail-cell">
          <span>接口数据源</span>
          <strong>
            盈亏 {{ summary.source.freqtrade_profit_ok ? '正常' : '失败' }} /
            交易 {{ summary.source.freqtrade_trades_ok ? '正常' : '失败' }} /
            锁定 {{ summary.source.freqtrade_locks_ok ? '正常' : '失败' }}
          </strong>
        </div>
      </div>
      <div v-else class="placeholder-body">{{ loading ? '加载中' : '暂无数据' }}</div>
    </div>

    <div class="panel panel-wide">
      <div class="panel-header">
        <span>风控检查</span>
        <span class="badge badge-muted">只读</span>
      </div>
      <div class="table-wrap">
        <table class="dense-table risk-check-table">
          <thead>
            <tr>
              <th>检查项</th>
              <th>当前值</th>
              <th>阈值</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="check in summary?.checks ?? []" :key="check.key">
              <td>{{ checkLabelText(check.key, check.label) }}</td>
              <td class="numeric">{{ checkValue(check) }}</td>
              <td class="numeric">{{ checkLimit(check) }}</td>
              <td><span class="badge" :class="badgeClass(check.status)">{{ statusText(check.status) }}</span></td>
            </tr>
            <tr v-if="summary && summary.checks.length === 0">
              <td colspan="4">暂无检查项</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="risk-split">
      <div class="panel">
        <div class="panel-header">
          <span>规则</span>
          <span class="badge badge-muted">{{ summary?.strategy.profile_status ?? '-' }}</span>
        </div>
        <div class="placeholder-body">
          <div v-for="row in ruleRows" :key="row[0]" class="metric-row">
            <span>{{ row[0] }}</span>
            <strong>{{ row[1] }}</strong>
          </div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <span>冷却锁定</span>
          <span class="badge badge-muted">{{ summary?.metrics.cooldown.active_locks ?? 0 }}</span>
        </div>
        <div class="table-wrap">
          <table class="dense-table lock-table">
            <thead>
              <tr>
                <th>编号</th>
                <th>交易对</th>
                <th>方向</th>
                <th>截止</th>
                <th>原因</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="lock in summary?.metrics.cooldown.locks ?? []" :key="String(lock.id ?? lock.lock_id)">
                <td class="numeric">#{{ lock.id ?? lock.lock_id }}</td>
                <td>{{ lock.pair ?? '-' }}</td>
                <td>{{ sideText(lock.side) }}</td>
                <td>{{ lock.lock_end_time ?? lock.lock_end_timestamp ?? '-' }}</td>
                <td>{{ lock.reason ?? '-' }}</td>
              </tr>
              <tr v-if="summary && summary.metrics.cooldown.locks.length === 0">
                <td colspan="5">暂无生效锁定</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div class="panel panel-wide">
      <div class="panel-header">
        <span>最近已平仓交易</span>
        <span class="badge badge-muted">{{ summary?.recent_closed_trades.length ?? 0 }}</span>
      </div>
      <div class="table-wrap">
        <table class="dense-table risk-trade-table">
          <thead>
            <tr>
              <th>编号</th>
              <th>交易对</th>
              <th>方向</th>
              <th>平仓时间</th>
              <th>盈亏</th>
              <th>盈亏比例</th>
              <th>原因</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="trade in summary?.recent_closed_trades ?? []" :key="String(trade.trade_id)">
              <td class="numeric">#{{ trade.trade_id }}</td>
              <td>{{ trade.pair }}</td>
              <td>{{ side(trade) }}</td>
              <td>{{ trade.close_date }}</td>
              <td class="numeric">{{ money(trade.profit_abs) }}</td>
              <td class="numeric">{{ text(trade.profit_pct) }}%</td>
              <td>{{ trade.exit_reason ?? '-' }}</td>
            </tr>
            <tr v-if="summary && summary.recent_closed_trades.length === 0">
              <td colspan="7">暂无已平仓交易</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>
