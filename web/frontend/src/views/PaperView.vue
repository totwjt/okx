<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { fetchPaperSummary, type PaperSummary } from '../api/paper';

const loading = ref(false);
const error = ref('');
const summary = ref<PaperSummary | null>(null);

async function loadPaper() {
  loading.value = true;
  error.value = '';
  try {
    summary.value = await fetchPaperSummary();
  } catch (err) {
    error.value = err instanceof Error ? err.message : '模拟盘摘要加载失败';
  } finally {
    loading.value = false;
  }
}

function money(value: unknown): string {
  return typeof value === 'number' ? value.toFixed(4) : '-';
}

function percent(value: unknown): string {
  return typeof value === 'number' ? `${value.toFixed(2)}%` : '-';
}

function pctRatio(value: unknown): string {
  return typeof value === 'number' ? `${(value * 100).toFixed(2)}%` : '-';
}

function tradeSide(trade: Record<string, unknown>): string {
  return trade.is_short ? '空' : '多';
}

onMounted(loadPaper);
</script>

<template>
  <section class="page-grid">
    <div class="panel panel-wide">
      <div class="panel-header">
        <span>模拟盘监控</span>
        <button class="icon-button" type="button" :disabled="loading" @click="loadPaper">
          刷新
        </button>
      </div>

      <div v-if="error" class="error-line">{{ error }}</div>

      <div v-if="summary" class="paper-status-grid">
        <div class="detail-cell">
          <span>模式</span>
          <strong>{{ summary.dry_run ? '模拟盘' : '非模拟盘' }}</strong>
        </div>
        <div class="detail-cell">
          <span>接口</span>
          <strong>{{ summary.api.ok ? '可访问' : '不可访问' }}</strong>
        </div>
        <div class="detail-cell">
          <span>执行基线</span>
          <strong>{{ summary.execution_baseline }} / WebSocket {{ summary.websocket_enabled ? '开启' : '关闭' }}</strong>
        </div>
        <div class="detail-cell">
          <span>当前持仓</span>
          <strong>{{ summary.open_trades.count }}</strong>
        </div>
        <div class="detail-cell">
          <span>总余额</span>
          <strong>{{ money(summary.balance.data?.total) }} {{ summary.balance.data?.stake ?? 'USDT' }}</strong>
        </div>
        <div class="detail-cell">
          <span>机器人资金</span>
          <strong>{{ money(summary.balance.data?.total_bot) }} {{ summary.balance.data?.stake ?? 'USDT' }}</strong>
        </div>
        <div class="detail-cell">
          <span>累计盈亏</span>
          <strong>{{ money(summary.profit.data?.profit_all_coin) }} {{ summary.balance.data?.stake ?? 'USDT' }}</strong>
        </div>
        <div class="detail-cell">
          <span>胜率</span>
          <strong>{{ pctRatio(summary.profit.data?.winrate) }}</strong>
        </div>
      </div>
      <div v-else class="placeholder-body">{{ loading ? '加载中' : '暂无数据' }}</div>
    </div>

    <div class="panel panel-wide">
      <div class="panel-header">
        <span>当前持仓</span>
        <span class="badge badge-muted">{{ summary?.open_trades.count ?? 0 }}</span>
      </div>
      <div v-if="summary && !summary.open_trades.ok" class="error-line">
        {{ summary.open_trades.error }}
      </div>
      <div class="table-wrap">
        <table class="dense-table paper-table">
          <thead>
            <tr>
              <th>编号</th>
              <th>交易对</th>
              <th>方向</th>
              <th>投入</th>
              <th>开仓价</th>
              <th>盈亏</th>
              <th>盈亏比例</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="trade in summary?.open_trades.items ?? []" :key="String(trade.trade_id)">
              <td class="numeric">#{{ trade.trade_id }}</td>
              <td>{{ trade.pair }}</td>
              <td>{{ tradeSide(trade) }}</td>
              <td class="numeric">{{ money(trade.stake_amount) }}</td>
              <td class="numeric">{{ money(trade.open_rate) }}</td>
              <td class="numeric">{{ money(trade.profit_abs) }}</td>
              <td class="numeric">{{ percent(trade.profit_pct) }}</td>
            </tr>
            <tr v-if="summary && summary.open_trades.items.length === 0">
              <td colspan="7">暂无持仓</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="panel panel-wide">
      <div class="panel-header">
        <span>最近交易</span>
        <span class="badge badge-muted">{{ summary?.recent_trades.items.length ?? 0 }}</span>
      </div>
      <div v-if="summary && !summary.recent_trades.ok" class="error-line">
        {{ summary.recent_trades.error }}
      </div>
      <div class="table-wrap">
        <table class="dense-table paper-table">
          <thead>
            <tr>
              <th>编号</th>
              <th>交易对</th>
              <th>方向</th>
              <th>状态</th>
              <th>投入</th>
              <th>盈亏</th>
              <th>原因</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="trade in summary?.recent_trades.items ?? []" :key="String(trade.trade_id)">
              <td class="numeric">#{{ trade.trade_id }}</td>
              <td>{{ trade.pair }}</td>
              <td>{{ tradeSide(trade) }}</td>
              <td>{{ trade.is_open ? '持仓中' : '已平仓' }}</td>
              <td class="numeric">{{ money(trade.stake_amount) }}</td>
              <td class="numeric">{{ money(trade.profit_abs) }}</td>
              <td>{{ trade.exit_reason ?? '-' }}</td>
            </tr>
            <tr v-if="summary && summary.recent_trades.items.length === 0">
              <td colspan="7">暂无最近交易</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>
