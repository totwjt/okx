<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import {
  fetchLifecycleProfile,
  fetchLifecycleStrategies,
  fetchLifecycleStrategy,
  createPaperRun,
  demoteLifecycleProfile,
  promoteLifecycleProfile,
  reviewPaperRun,
  runEvidenceCheck,
  updateProfileThesis,
  type EvidenceGateResult,
  type LifecycleProfileDetail,
} from '../api/lifecycle';
import type { StrategyProfile, StrategySummary } from '../api/strategies';
import {
  fetchOptimizationAssistant,
  saveDraftProfile,
  startAutoTuneJob,
  type OptimizationAssistant,
} from '../api/optimization';
import StatusTag from '../components/StatusTag.vue';
import { confirmAction } from '../services/confirm';

const loading = ref(false);
const detailLoading = ref(false);
const error = ref('');
const strategies = ref<StrategySummary[]>([]);
const profiles = ref<StrategyProfile[]>([]);
const selectedSlug = ref('');
const selectedProfile = ref('');
const lifecycle = ref<LifecycleProfileDetail | null>(null);
const evidenceChecking = ref(false);
const evidenceTarget = ref<'validated' | 'paper_active' | 'live_candidate' | 'live_active'>('validated');
const evidenceResult = ref<EvidenceGateResult | null>(null);
const promotionRunning = ref(false);
const promotionTarget = ref<'validated' | 'paper_active' | 'live_candidate' | 'live_active'>('paper_active');
const demotionTarget = ref<'validated' | 'archived'>('validated');
const promotionReason = ref('');
const promotionMessage = ref('');
const paperRunLoading = ref(false);
const paperReviewConclusion = ref('');
const optimization = ref<OptimizationAssistant | null>(null);
const optimizationLoading = ref(false);
const draftProfileName = ref('');
const draftOverridesText = ref('{}');
const optimizationMessage = ref('');
const autoTuneRunning = ref(false);
const autoTuneCount = ref(3);
const thesisDraft = ref<Record<string, string>>({});
const thesisSaving = ref(false);
const thesisMessage = ref('');

const selectedStrategy = computed(() =>
  strategies.value.find((strategy) => strategy.slug === selectedSlug.value),
);

const currentDefinition = computed(() => {
  if (!lifecycle.value) {
    return null;
  }
  return lifecycle.value.status_definitions[lifecycle.value.summary.current_status] ?? null;
});

const statusDefinitions = computed(() => {
  if (!lifecycle.value) {
    return [];
  }
  const order = [
    'draft',
    'generated',
    'backtested',
    'validated',
    'paper_active',
    'live_candidate',
    'live_active',
    'archived',
  ];
  return order.map((key) => ({ key, ...lifecycle.value!.status_definitions[key] })).filter((row) => row.title_zh);
});

function statusTone(status: string): 'default' | 'success' | 'processing' | 'warning' | 'error' {
  const normalized = status.toLowerCase();
  if (['completed', 'validated', 'paper_active'].includes(normalized)) {
    return 'success';
  }
  if (['pending', 'generated', 'backtested', 'live_candidate'].includes(normalized)) {
    return 'processing';
  }
  if (['blocked', 'live_active'].includes(normalized)) {
    return 'error';
  }
  if (['locked', 'archived'].includes(normalized)) {
    return 'default';
  }
  return 'warning';
}

function statusText(status: string): string {
  const labels: Record<string, string> = {
    draft: '草稿',
    generated: '已生成',
    backtested: '已回测',
    validated: '已验证',
    paper_active: '模拟盘生效',
    live_candidate: '实盘候选',
    live_active: '实盘生效',
    archived: '已归档',
    completed: '已完成',
    pending: '待执行',
    blocked: '阻塞',
    locked: '锁定',
  };
  return labels[status.toLowerCase()] ?? status;
}

function formatValue(value: string | number | boolean | null): string {
  if (value === null || value === undefined || value === '') {
    return '-';
  }
  return String(value);
}

function paperRunStatusText(status: string): string {
  const labels: Record<string, string> = {
    collecting_samples: 'COLLECT_MORE_SAMPLES',
    ready_for_review: 'READY_FOR_REVIEW',
    review_failed: '复盘未通过',
    review_passed: '复盘通过',
    stopped: '已停止',
  };
  return labels[status] ?? status;
}

async function loadProfile(strategySlug: string, profileName: string) {
  if (!strategySlug || !profileName) {
    lifecycle.value = null;
    return;
  }
  detailLoading.value = true;
  error.value = '';
  try {
    lifecycle.value = await fetchLifecycleProfile(strategySlug, profileName);
    thesisDraft.value = { ...(lifecycle.value.thesis.values ?? {}) };
    evidenceResult.value = null;
    void loadOptimization(strategySlug, profileName);
  } catch (err) {
    error.value = err instanceof Error ? err.message : '生命周期详情加载失败';
  } finally {
    detailLoading.value = false;
  }
}

async function loadOptimization(strategySlug: string, profileName: string) {
  optimizationLoading.value = true;
  optimizationMessage.value = '';
  try {
    optimization.value = await fetchOptimizationAssistant(strategySlug, profileName);
    draftProfileName.value = `${profileName}_draft`;
  } catch (err) {
    optimizationMessage.value = err instanceof Error ? err.message : '调优助手加载失败';
  } finally {
    optimizationLoading.value = false;
  }
}

async function submitEvidenceCheck() {
  if (!selectedSlug.value || !selectedProfile.value) return;
  evidenceChecking.value = true;
  error.value = '';
  try {
    evidenceResult.value = await runEvidenceCheck(
      selectedSlug.value,
      selectedProfile.value,
      evidenceTarget.value,
    );
  } catch (err) {
    error.value = err instanceof Error ? err.message : '证据闸门检查失败';
  } finally {
    evidenceChecking.value = false;
  }
}

async function submitPromotion() {
  if (!selectedSlug.value || !selectedProfile.value || !promotionReason.value.trim()) return;
  const confirmed = await confirmAction({
    title: '晋级参数档案',
    content: `将 ${selectedSlug.value}/${selectedProfile.value} 晋级为 ${statusText(promotionTarget.value)}。后端会先执行 evidence gate。`,
    okText: '晋级',
  });
  if (!confirmed) return;
  promotionRunning.value = true;
  promotionMessage.value = '';
  error.value = '';
  try {
    const result = await promoteLifecycleProfile(
      selectedSlug.value,
      selectedProfile.value,
      promotionTarget.value,
      promotionReason.value.trim(),
    );
    if (!result.promoted) {
      evidenceResult.value = result.evidence ?? evidenceResult.value;
      promotionMessage.value = `晋级被拦截：${result.failed_checks?.length ?? 0} 项证据未通过。`;
      return;
    }
    promotionMessage.value = '晋级成功，已写入 promotion event。';
    await selectStrategy(selectedSlug.value);
  } catch (err) {
    error.value = err instanceof Error ? err.message : '晋级失败';
  } finally {
    promotionRunning.value = false;
  }
}

async function submitDemotion() {
  if (!selectedSlug.value || !selectedProfile.value || !promotionReason.value.trim()) return;
  const confirmed = await confirmAction({
    title: '降级参数档案',
    content: `将 ${selectedSlug.value}/${selectedProfile.value} 降级为 ${statusText(demotionTarget.value)}。`,
    okText: '降级',
  });
  if (!confirmed) return;
  promotionRunning.value = true;
  promotionMessage.value = '';
  error.value = '';
  try {
    await demoteLifecycleProfile(
      selectedSlug.value,
      selectedProfile.value,
      demotionTarget.value,
      promotionReason.value.trim(),
    );
    promotionMessage.value = '降级成功，已写入 promotion event。';
    await selectStrategy(selectedSlug.value);
  } catch (err) {
    error.value = err instanceof Error ? err.message : '降级失败';
  } finally {
    promotionRunning.value = false;
  }
}

async function startPaperRun() {
  if (!selectedSlug.value || !selectedProfile.value) return;
  const confirmed = await confirmAction({
    title: '创建 Paper Run',
    content: `为 ${selectedSlug.value}/${selectedProfile.value} 创建模拟盘运行台账。`,
    okText: '创建',
  });
  if (!confirmed) return;
  paperRunLoading.value = true;
  error.value = '';
  try {
    await createPaperRun(selectedSlug.value, selectedProfile.value);
    await loadProfile(selectedSlug.value, selectedProfile.value);
  } catch (err) {
    error.value = err instanceof Error ? err.message : '创建 Paper Run 失败';
  } finally {
    paperRunLoading.value = false;
  }
}

async function submitPaperReview(passed: boolean) {
  if (!lifecycle.value?.paper_run || !paperReviewConclusion.value.trim()) return;
  paperRunLoading.value = true;
  error.value = '';
  try {
    await reviewPaperRun(lifecycle.value.paper_run.id, passed, paperReviewConclusion.value.trim());
    await loadProfile(selectedSlug.value, selectedProfile.value);
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Paper Run 复盘失败';
  } finally {
    paperRunLoading.value = false;
  }
}

async function submitDraftProfile() {
  if (!selectedSlug.value || !selectedProfile.value || !draftProfileName.value.trim()) return;
  optimizationMessage.value = '';
  try {
    const overrides = JSON.parse(draftOverridesText.value || '{}') as Record<string, unknown>;
    await saveDraftProfile(
      selectedSlug.value,
      draftProfileName.value.trim(),
      selectedProfile.value,
      overrides,
    );
    optimizationMessage.value = '候选 draft profile 已保存。';
    await selectStrategy(selectedSlug.value);
  } catch (err) {
    optimizationMessage.value = err instanceof Error ? err.message : '保存 draft profile 失败';
  }
}

async function submitAutoTune() {
  if (!selectedSlug.value || !selectedProfile.value) return;
  const confirmed = await confirmAction({
    title: '启动自动调优',
    content: `将基于 ${selectedProfile.value} 生成 ${autoTuneCount.value} 个 draft 候选，并为每个候选创建 train 回测任务。`,
    okText: '启动',
  });
  if (!confirmed) return;
  autoTuneRunning.value = true;
  optimizationMessage.value = '';
  try {
    const job = await startAutoTuneJob(selectedSlug.value, selectedProfile.value, autoTuneCount.value);
    optimizationMessage.value = `自动调优任务已创建：#${job.id}。候选不会自动晋级。`;
  } catch (err) {
    optimizationMessage.value = err instanceof Error ? err.message : '自动调优任务创建失败';
  } finally {
    autoTuneRunning.value = false;
  }
}

async function submitThesis() {
  if (!selectedSlug.value || !selectedProfile.value) return;
  thesisSaving.value = true;
  thesisMessage.value = '';
  try {
    await updateProfileThesis(selectedSlug.value, selectedProfile.value, thesisDraft.value);
    thesisMessage.value = '策略假设与复盘记录已保存。';
    await loadProfile(selectedSlug.value, selectedProfile.value);
  } catch (err) {
    thesisMessage.value = err instanceof Error ? err.message : 'thesis 保存失败';
  } finally {
    thesisSaving.value = false;
  }
}

async function selectStrategy(slug: string) {
  selectedSlug.value = slug;
  detailLoading.value = true;
  error.value = '';
  lifecycle.value = null;
  try {
    const detail = await fetchLifecycleStrategy(slug);
    profiles.value = detail.profiles;
    selectedProfile.value = detail.default_profile_name ?? detail.profiles[0]?.profile_name ?? '';
    if (selectedProfile.value) {
      await loadProfile(slug, selectedProfile.value);
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '策略生命周期加载失败';
  } finally {
    detailLoading.value = false;
  }
}

async function loadStrategies() {
  loading.value = true;
  error.value = '';
  try {
    strategies.value = await fetchLifecycleStrategies();
    if (strategies.value.length > 0) {
      await selectStrategy(strategies.value[0].slug);
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '策略列表加载失败';
  } finally {
    loading.value = false;
  }
}

watch(selectedProfile, async (profileName, previous) => {
  if (profileName && profileName !== previous) {
    await loadProfile(selectedSlug.value, profileName);
  }
});

onMounted(loadStrategies);
</script>

<template>
  <section class="lifecycle-layout">
    <div class="panel lifecycle-side">
      <div class="panel-header">
        <span>策略 / Profile</span>
        <button class="icon-button" type="button" :disabled="loading" @click="loadStrategies">
          刷新
        </button>
      </div>

      <div v-if="error" class="error-line">{{ error }}</div>

      <div class="lifecycle-picker">
        <label class="field-label">
          <span>Strategy</span>
          <select v-model="selectedSlug" class="select-input" @change="selectStrategy(selectedSlug)">
            <option v-for="strategy in strategies" :key="strategy.slug" :value="strategy.slug">
              {{ strategy.name }} / {{ strategy.slug }}
            </option>
          </select>
        </label>

        <label class="field-label">
          <span>Profile</span>
          <select v-model="selectedProfile" class="select-input">
            <option v-for="profile in profiles" :key="profile.profile_name" :value="profile.profile_name">
              {{ profile.profile_name }} / {{ statusText(profile.status) }}
            </option>
          </select>
        </label>
      </div>

      <div class="lifecycle-status-list">
        <div v-for="definition in statusDefinitions" :key="definition.key" class="status-definition">
          <div class="status-definition-title">
            <StatusTag :tone="statusTone(definition.key)">{{ definition.title_zh }}</StatusTag>
            <span>{{ definition.key }}</span>
          </div>
          <p>{{ definition.description_zh }}</p>
          <small>{{ definition.related_content_zh }}</small>
        </div>
      </div>
    </div>

    <div class="lifecycle-main">
      <div class="panel">
        <div class="panel-header">
          <span>{{ selectedStrategy?.name ?? '生命周期概览' }}</span>
          <StatusTag v-if="lifecycle" :tone="statusTone(lifecycle.summary.current_status)">
            {{ lifecycle.summary.current_status_zh }}
          </StatusTag>
        </div>

        <div v-if="detailLoading" class="placeholder-body">加载中</div>
        <div v-else-if="lifecycle" class="lifecycle-summary">
          <div class="detail-cell">
            <span>策略</span>
            <strong>{{ lifecycle.strategy.slug }}</strong>
          </div>
          <div class="detail-cell">
            <span>Profile</span>
            <strong>{{ lifecycle.profile.profile_name }}</strong>
          </div>
          <div class="detail-cell">
            <span>当前 step</span>
            <strong>{{ lifecycle.summary.current_step_title_zh }}</strong>
          </div>
          <div class="detail-cell">
            <span>完成度</span>
            <strong>{{ lifecycle.summary.completed_steps }} / {{ lifecycle.summary.total_steps }}</strong>
          </div>
          <div class="detail-cell detail-cell-wide">
            <span>当前状态解释</span>
            <strong>{{ currentDefinition?.description_zh ?? '-' }}</strong>
          </div>
        </div>
      </div>

      <div v-if="lifecycle" class="lifecycle-alert-grid">
        <div class="panel">
          <div class="panel-header">
            <span>Runtime Alignment</span>
            <StatusTag :tone="lifecycle.alignment.ok ? 'success' : 'error'">
              {{ lifecycle.alignment.summary_zh }}
            </StatusTag>
          </div>
          <div class="alignment-check-list">
            <div v-for="check in lifecycle.alignment.checks" :key="check.key" class="alignment-check-row">
              <div>
                <strong>{{ check.title_zh }}</strong>
                <p>{{ check.details_zh }}</p>
              </div>
              <StatusTag :tone="check.passed ? 'success' : check.status === 'unknown' ? 'warning' : 'error'">
                {{ check.passed ? '对齐' : check.status === 'unknown' ? '未知' : '漂移' }}
              </StatusTag>
            </div>
          </div>
        </div>

        <div class="panel">
          <div class="panel-header">
            <span>阻塞原因</span>
            <StatusTag :tone="lifecycle.summary.blocked_reasons.length ? 'error' : 'success'">
              {{ lifecycle.summary.blocked_reasons.length }}
            </StatusTag>
          </div>
          <div class="lifecycle-list-body">
            <p v-if="!lifecycle.summary.blocked_reasons.length" class="muted-line">当前没有阻塞项。</p>
            <p v-for="reason in lifecycle.summary.blocked_reasons" :key="reason" class="blocked-line">
              {{ reason }}
            </p>
          </div>
        </div>

        <div class="panel lifecycle-alert-wide">
          <div class="panel-header">
            <span>下一步动作</span>
            <StatusTag>{{ lifecycle.summary.next_actions.length }}</StatusTag>
          </div>
          <div class="lifecycle-list-body">
            <p v-if="!lifecycle.summary.next_actions.length" class="muted-line">暂无待执行动作。</p>
            <p v-for="action in lifecycle.summary.next_actions" :key="action" class="next-line">
              {{ action }}
            </p>
          </div>
        </div>
      </div>

      <div v-if="lifecycle" class="panel">
        <div class="panel-header">
          <span>Evidence Gate</span>
          <StatusTag v-if="evidenceResult" :tone="evidenceResult.passed ? 'success' : 'error'">
            {{ evidenceResult.summary_zh }}
          </StatusTag>
        </div>
        <div class="evidence-gate-toolbar">
          <label class="field-label field-label-compact">
            <span>目标状态</span>
            <select v-model="evidenceTarget" class="select-input">
              <option value="validated">已验证</option>
              <option value="paper_active">模拟盘生效</option>
              <option value="live_candidate">实盘候选</option>
              <option value="live_active">实盘生效</option>
            </select>
          </label>
          <button
            class="icon-button primary-button"
            type="button"
            :disabled="evidenceChecking"
            @click="submitEvidenceCheck"
          >
            检查证据
          </button>
        </div>
        <div v-if="evidenceResult" class="evidence-check-list">
          <div v-for="check in evidenceResult.checks" :key="check.key" class="evidence-check-row">
            <div>
              <strong>{{ check.title_zh }}</strong>
              <p>{{ check.details_zh }}</p>
            </div>
            <StatusTag :tone="check.passed ? 'success' : check.status === 'warning' ? 'warning' : 'error'">
              {{ check.passed ? '通过' : check.status === 'warning' ? '提示' : '失败' }}
            </StatusTag>
          </div>
        </div>
      </div>

      <div v-if="lifecycle" class="panel">
        <div class="panel-header">
          <span>Promotion Workflow</span>
          <StatusTag>{{ lifecycle.promotion_events.length }} 条事件</StatusTag>
        </div>
        <div class="promotion-form">
          <label class="field-label field-label-compact">
            <span>晋级目标</span>
            <select v-model="promotionTarget" class="select-input">
              <option value="validated">已验证</option>
              <option value="paper_active">模拟盘生效</option>
              <option value="live_candidate">实盘候选</option>
              <option value="live_active">实盘生效</option>
            </select>
          </label>
          <label class="field-label field-label-compact">
            <span>降级目标</span>
            <select v-model="demotionTarget" class="select-input">
              <option value="validated">已验证</option>
              <option value="archived">已归档</option>
            </select>
          </label>
          <label class="field-label promotion-reason-field">
            <span>Reason / Review Note</span>
            <input v-model="promotionReason" class="text-input" type="text" placeholder="必须填写晋级或降级原因" />
          </label>
          <button
            class="icon-button primary-button"
            type="button"
            :disabled="promotionRunning || !promotionReason.trim()"
            @click="submitPromotion"
          >
            晋级
          </button>
          <button
            class="icon-button"
            type="button"
            :disabled="promotionRunning || !promotionReason.trim()"
            @click="submitDemotion"
          >
            降级
          </button>
        </div>
        <div v-if="promotionMessage" class="promotion-message">{{ promotionMessage }}</div>
        <div class="promotion-event-list">
          <div v-for="event in lifecycle.promotion_events" :key="event.id" class="promotion-event-row">
            <span>#{{ event.id }} {{ statusText(event.from_status ?? '-') }} -> {{ statusText(event.to_status) }}</span>
            <strong>{{ event.reason ?? '-' }}</strong>
          </div>
          <div v-if="!lifecycle.promotion_events.length" class="placeholder-body">暂无 promotion event</div>
        </div>
      </div>

      <div v-if="lifecycle" class="panel">
        <div class="panel-header">
          <span>Paper Run Ledger</span>
          <StatusTag v-if="lifecycle.paper_run" :tone="lifecycle.paper_run.status === 'ready_for_review' ? 'processing' : lifecycle.paper_run.status === 'review_passed' ? 'success' : 'warning'">
            {{ paperRunStatusText(lifecycle.paper_run.status) }}
          </StatusTag>
        </div>
        <div v-if="!lifecycle.paper_run" class="paper-run-empty">
          <span>当前 strategy/profile 还没有 paper run 台账。</span>
          <button class="icon-button primary-button" type="button" :disabled="paperRunLoading" @click="startPaperRun">
            创建台账
          </button>
        </div>
        <div v-else class="paper-run-grid">
          <div class="detail-cell">
            <span>Run</span>
            <strong>#{{ lifecycle.paper_run.id }} {{ lifecycle.paper_run.run_name }}</strong>
          </div>
          <div class="detail-cell">
            <span>自然成交</span>
            <strong>{{ lifecycle.paper_run.natural_closed_trades }}</strong>
          </div>
          <div class="detail-cell">
            <span>Force 交易</span>
            <strong>{{ lifecycle.paper_run.force_trades }}</strong>
          </div>
          <div class="detail-cell">
            <span>PNL</span>
            <strong>{{ lifecycle.paper_run.pnl ?? '-' }}</strong>
          </div>
          <div class="detail-cell">
            <span>当前余额</span>
            <strong>{{ lifecycle.paper_run.current_balance ?? '-' }}</strong>
          </div>
          <div class="detail-cell">
            <span>最大回撤</span>
            <strong>{{ lifecycle.paper_run.max_drawdown ?? '-' }}</strong>
          </div>
          <div class="detail-cell">
            <span>dry_run</span>
            <strong>{{ lifecycle.paper_run.dry_run ? '是' : '否' }}</strong>
          </div>
          <div class="detail-cell">
            <span>artifact hash</span>
            <strong>{{ lifecycle.paper_run.artifact_hash?.slice(0, 12) ?? '-' }}</strong>
          </div>
        </div>
        <div v-if="lifecycle.paper_run" class="paper-review-form">
          <label class="field-label promotion-reason-field">
            <span>Review Conclusion</span>
            <input v-model="paperReviewConclusion" class="text-input" type="text" placeholder="填写模拟盘复盘结论" />
          </label>
          <button class="icon-button primary-button" type="button" :disabled="paperRunLoading || !paperReviewConclusion.trim()" @click="submitPaperReview(true)">
            复盘通过
          </button>
          <button class="icon-button" type="button" :disabled="paperRunLoading || !paperReviewConclusion.trim()" @click="submitPaperReview(false)">
            复盘不通过
          </button>
        </div>
      </div>

      <div v-if="lifecycle" class="panel">
        <div class="panel-header">
          <span>Optimization Assistant</span>
          <StatusTag>{{ optimization?.candidates.length ?? 0 }} 个候选</StatusTag>
        </div>
        <div v-if="optimizationLoading" class="placeholder-body">加载中</div>
        <div v-else class="optimization-body">
          <div class="optimization-notes">
            <p v-for="line in optimization?.scoring_zh ?? []" :key="line">{{ line }}</p>
          </div>
          <div class="parameter-list">
            <div v-for="param in optimization?.parameters ?? []" :key="param.path" class="parameter-chip">
              <span>{{ param.title_zh }}</span>
              <strong>{{ param.current }} [{{ param.min }}, {{ param.max }}]</strong>
            </div>
          </div>
          <div class="candidate-list">
            <div v-for="candidate in optimization?.candidates.slice(0, 8) ?? []" :key="candidate.profile_name" class="candidate-row">
              <div>
                <strong>{{ candidate.profile_name }}</strong>
                <p>{{ candidate.reasons_zh.join(' ') }}</p>
                <small v-if="candidate.warnings_zh.length">{{ candidate.warnings_zh.join('；') }}</small>
              </div>
              <StatusTag :tone="candidate.warnings_zh.length ? 'warning' : 'success'">
                {{ candidate.score.toFixed(2) }}
              </StatusTag>
            </div>
          </div>
          <div class="draft-profile-form">
            <label class="field-label field-label-compact">
              <span>自动候选数</span>
              <input v-model.number="autoTuneCount" class="text-input" type="number" min="3" max="12" />
            </label>
            <button class="icon-button primary-button" type="button" :disabled="autoTuneRunning" @click="submitAutoTune">
              自动调优
            </button>
            <label class="field-label field-label-compact">
              <span>Draft Profile</span>
              <input v-model="draftProfileName" class="text-input" type="text" />
            </label>
            <label class="field-label draft-overrides-field">
              <span>Overrides JSON</span>
              <textarea v-model="draftOverridesText" class="text-area-input" rows="3"></textarea>
            </label>
            <button class="icon-button primary-button" type="button" @click="submitDraftProfile">
              保存 Draft
            </button>
          </div>
          <div v-if="optimizationMessage" class="promotion-message">{{ optimizationMessage }}</div>
        </div>
      </div>

      <div v-if="lifecycle" class="panel">
        <div class="panel-header">
          <span>Strategy Thesis</span>
          <StatusTag :tone="lifecycle.thesis.complete ? 'success' : 'error'">
            {{ lifecycle.thesis.complete ? '完整' : `缺失 ${lifecycle.thesis.missing_fields.length}` }}
          </StatusTag>
        </div>
        <div class="thesis-grid">
          <label v-for="(label, key) in lifecycle.thesis_required_fields" :key="key" class="field-label thesis-field">
            <span>{{ label }}</span>
            <textarea v-model="thesisDraft[key]" class="text-area-input" rows="2"></textarea>
          </label>
        </div>
        <div class="thesis-actions">
          <button class="icon-button primary-button" type="button" :disabled="thesisSaving" @click="submitThesis">
            保存 Thesis
          </button>
          <span v-if="thesisMessage">{{ thesisMessage }}</span>
        </div>
      </div>

      <div v-if="lifecycle" class="lifecycle-steps">
        <article v-for="step in lifecycle.steps" :key="step.key" class="panel lifecycle-step">
          <div class="panel-header">
            <span>{{ step.title_zh }}</span>
            <StatusTag :tone="statusTone(step.status)">{{ statusText(step.status) }}</StatusTag>
          </div>

          <div class="lifecycle-step-body">
            <p class="step-description">{{ step.description_zh }}</p>

            <div class="step-meta-grid">
              <div>
                <h3>输入</h3>
                <p v-for="item in step.inputs" :key="item">{{ item }}</p>
              </div>
              <div>
                <h3>输出</h3>
                <p v-for="item in step.outputs" :key="item">{{ item }}</p>
              </div>
            </div>

            <div class="evidence-grid">
              <div v-for="item in step.evidence" :key="`${step.key}-${item.label_zh}-${item.source}`" class="evidence-item">
                <span>{{ item.label_zh }}</span>
                <strong>{{ formatValue(item.value) }}</strong>
                <small>{{ item.source }}</small>
              </div>
            </div>

            <div v-if="step.gate_checks.length" class="gate-list">
              <div v-for="check in step.gate_checks" :key="`${step.key}-${check.label_zh}`" class="gate-item">
                <span>{{ check.label_zh }}</span>
                <strong>{{ formatValue(check.value) }}</strong>
              </div>
            </div>

            <div v-if="step.blocked_reasons.length || step.next_actions.length" class="step-note-grid">
              <div v-if="step.blocked_reasons.length">
                <h3>阻塞</h3>
                <p v-for="reason in step.blocked_reasons" :key="reason" class="blocked-line">{{ reason }}</p>
              </div>
              <div v-if="step.next_actions.length">
                <h3>下一步</h3>
                <p v-for="action in step.next_actions" :key="action" class="next-line">{{ action }}</p>
              </div>
            </div>

            <div v-if="step.substeps.length" class="substep-list">
              <div v-for="substep in step.substeps" :key="substep.key" class="substep-row">
                <span>{{ substep.title_zh }}</span>
                <StatusTag :tone="statusTone(substep.status)">{{ statusText(substep.status) }}</StatusTag>
              </div>
            </div>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>
