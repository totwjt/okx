import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import {
  AlertCircle,
  ArrowDown,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  ClipboardList,
  Edit3,
  FileText,
  History,
  ListChecks,
  Play,
  Plus,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
} from 'lucide-react';
import { api, type LifecycleStep, type StrategyProfile } from '../api';
import { ErrorState, LoadingState } from '../components/query-state';
import { Metric } from '../components/metric';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Sheet, SheetBody, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from '../components/ui/sheet';
import { StatusBadge } from '../components/ui/status-badge';
import type { AppShellOutletContext } from '../components/app-shell';
import { statusText, statusTone } from '../lib/status';
import { cn, formatDateTime, stringifyValue } from '../lib/utils';

function StepDetailList({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) {
    return null;
  }
  return (
    <div className="grid gap-1 rounded-md border border-border bg-background p-2">
      <div className="text-xs font-semibold text-muted-foreground">{title}</div>
      <div className="grid gap-1 text-sm">
        {items.map((item) => (
          <div key={item} className="leading-6 text-foreground">
            {item}
          </div>
        ))}
      </div>
    </div>
  );
}

interface StepAction {
  label: string;
  icon: React.ReactNode;
  disabled?: boolean;
  onClick?: () => void;
  to?: string;
}

interface StepOperationResult {
  status: 'success' | 'error';
  title: string;
  detail: string;
  nextStep?: string;
}

type LifecycleSheet = 'create-strategy' | 'create-profile' | 'edit-thesis' | 'edit-definition' | 'edit-profile' | null;

function operationDetail(value: unknown): string {
  if (!value || typeof value !== 'object') {
    return stringifyValue(value);
  }
  const result = value as Record<string, unknown>;
  const jobs = Array.isArray(result.jobs) ? result.jobs as Array<Record<string, unknown>> : [];
  if (jobs.length > 0) {
    return jobs.map((job) => {
      const deduped = job.deduped ? '，命中 dedupe' : '';
      const reason = job.dedupe_reason ? `：${job.dedupe_reason}` : '';
      const error = job.error_summary ? `，错误：${job.error_summary}` : '';
      return `job #${job.id} / ${job.job_type} / ${job.status}${deduped}${reason}${error}`;
    }).join('；');
  }
  if (result.promoted !== undefined) {
    return result.promoted ? `已晋级到 ${stringifyValue(result.to_status)}` : `未晋级：${stringifyValue(result.failed_checks ?? result.evidence)}`;
  }
  if (result.deduped) {
    return `命中 dedupe：${stringifyValue(result.dedupe_reason)}`;
  }
  if (result.id) {
    return `记录 #${result.id} / ${stringifyValue(result.status)}`;
  }
  if (result.scaffold_explanation || result.profile_explanation) {
    const explanation = (result.scaffold_explanation ?? result.profile_explanation) as Record<string, unknown>;
    const lines = [
      stringifyValue(explanation.warning_zh),
      explanation.factors ? `因子：${stringifyValue(explanation.factors)}` : '',
      explanation.entry_conditions ? `入场：${stringifyValue(explanation.entry_conditions)}` : '',
      explanation.exit_conditions ? `出场：${stringifyValue(explanation.exit_conditions)}` : '',
      explanation.timeranges ? `区间：${stringifyValue(explanation.timeranges)}` : '',
      explanation.risk_model ? `风控：${stringifyValue(explanation.risk_model)}` : '',
      explanation.trade_controls ? `交易参数：${stringifyValue(explanation.trade_controls)}` : '',
      explanation.overrides ? `overrides：${stringifyValue(explanation.overrides)}` : '',
    ].filter(Boolean);
    return lines.join('\n');
  }
  return stringifyValue(value);
}

const PROFILE_EDIT_FIELDS = [
  { key: 'max_open_trades', label: 'max_open_trades', type: 'number' },
  { key: 'stoploss', label: 'stoploss', type: 'number' },
  { key: 'trailing_stop_positive', label: 'trailing_stop_positive', type: 'number' },
  { key: 'trailing_stop_positive_offset', label: 'trailing_stop_positive_offset', type: 'number' },
  { key: 'ma_period', label: 'MA period', type: 'number' },
  { key: 'rsi_period', label: 'RSI period', type: 'number' },
  { key: 'rsi_oversold', label: 'RSI oversold', type: 'number' },
  { key: 'rsi_overbought', label: 'RSI overbought', type: 'number' },
  { key: 'volume_ratio', label: 'volume ratio', type: 'number' },
] as const;

const PROTECTED_PROFILE_STATUSES = new Set(['validated', 'paper_active', 'live_candidate', 'live_active', 'archived']);

function readProfileEditDraft(overrides: Record<string, unknown>): Record<string, string> {
  const factors = (overrides.factors ?? {}) as Record<string, Record<string, unknown>>;
  const riskModel = (overrides.risk_model ?? {}) as Record<string, unknown>;
  return {
    max_open_trades: stringifyValue(riskModel.max_open_trades),
    stoploss: stringifyValue(overrides.stoploss),
    trailing_stop_positive: stringifyValue(overrides.trailing_stop_positive),
    trailing_stop_positive_offset: stringifyValue(overrides.trailing_stop_positive_offset),
    minimal_roi: JSON.stringify(overrides.minimal_roi ?? {}, null, 2),
    ma_period: stringifyValue(factors.ma?.period),
    rsi_period: stringifyValue(factors.rsi?.period),
    rsi_oversold: stringifyValue(factors.rsi_oversold?.value),
    rsi_overbought: stringifyValue(factors.rsi_overbought?.value),
    volume_ratio: stringifyValue(factors.volume?.ratio_threshold),
  };
}

function parseOptionalNumber(label: string, value: string): number | undefined {
  const trimmed = value.trim();
  if (!trimmed || trimmed === '-') {
    return undefined;
  }
  const parsed = Number(trimmed);
  if (!Number.isFinite(parsed)) {
    throw new Error(`${label} 必须是数字`);
  }
  return parsed;
}

function buildProfileOverrides(draft: Record<string, string>): Record<string, unknown> {
  const minimalRoiText = draft.minimal_roi?.trim() || '{}';
  let minimalRoi: unknown;
  try {
    minimalRoi = JSON.parse(minimalRoiText);
  } catch (error) {
    throw new Error(`minimal_roi 必须是 JSON：${error instanceof Error ? error.message : stringifyValue(error)}`);
  }
  if (!minimalRoi || typeof minimalRoi !== 'object' || Array.isArray(minimalRoi)) {
    throw new Error('minimal_roi 必须是 JSON 对象');
  }

  const factors: Record<string, Record<string, number>> = {};
  const maPeriod = parseOptionalNumber('MA period', draft.ma_period ?? '');
  const rsiPeriod = parseOptionalNumber('RSI period', draft.rsi_period ?? '');
  const rsiOversold = parseOptionalNumber('RSI oversold', draft.rsi_oversold ?? '');
  const rsiOverbought = parseOptionalNumber('RSI overbought', draft.rsi_overbought ?? '');
  const volumeRatio = parseOptionalNumber('volume ratio', draft.volume_ratio ?? '');
  if (maPeriod !== undefined) factors.ma = { period: maPeriod };
  if (rsiPeriod !== undefined) factors.rsi = { period: rsiPeriod };
  if (rsiOversold !== undefined) factors.rsi_oversold = { value: rsiOversold };
  if (rsiOverbought !== undefined) factors.rsi_overbought = { value: rsiOverbought };
  if (volumeRatio !== undefined) factors.volume = { ratio_threshold: volumeRatio };

  const maxOpenTrades = parseOptionalNumber('max_open_trades', draft.max_open_trades ?? '');
  const overrides: Record<string, unknown> = {
    factors,
    minimal_roi: minimalRoi,
  };
  if (maxOpenTrades !== undefined) {
    overrides.risk_model = { max_open_trades: maxOpenTrades };
  }
  for (const field of ['stoploss', 'trailing_stop_positive', 'trailing_stop_positive_offset'] as const) {
    const parsed = parseOptionalNumber(field, draft[field] ?? '');
    if (parsed !== undefined) {
      overrides[field] = parsed;
    }
  }
  return overrides;
}

function StepOperationResultView({ result }: { result?: StepOperationResult }) {
  if (!result) {
    return null;
  }
  const toneClass = result.status === 'error'
    ? 'border-rose-300 bg-rose-50 text-rose-800 dark:border-rose-900 dark:bg-rose-950/30 dark:text-rose-100'
    : 'border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-100';
  return (
    <div className={`grid gap-1 rounded-md border p-3 text-sm ${toneClass}`}>
      <div className="flex items-center gap-2 font-semibold">
        {result.status === 'error' ? <AlertCircle className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
        {result.title}
      </div>
      <div className="whitespace-pre-wrap break-words leading-6">{result.detail}</div>
      {result.nextStep ? <div className="text-xs opacity-80">下一步：{result.nextStep}</div> : null}
    </div>
  );
}

function StepCard({
  step,
  index,
  defaultOpen,
  actions,
  operationResult,
  toolbar,
}: {
  step: LifecycleStep;
  index: number;
  defaultOpen: boolean;
  actions: StepAction[];
  operationResult?: StepOperationResult;
  toolbar?: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const hasProblems = step.blocked_reasons.length > 0;
  const evidenceItems = step.evidence.map((item) => `${item.label_zh}: ${stringifyValue(item.value)}`);
  const gateItems = step.gate_checks.map((item) => `${item.label_zh}: ${stringifyValue(item.value)} / ${statusText(item.status)}`);
  const substepItems = step.substeps.map((item) => `${item.title_zh} / ${statusText(item.status)}`);
  const completed = step.status === 'completed';
  const blocked = step.status === 'blocked';
  const current = step.status === 'pending';

  return (
    <div
      className={cn(
        'overflow-hidden rounded-lg border border-border bg-card text-card-foreground shadow-md shadow-slate-200/70 transition dark:shadow-none',
        blocked && 'ring-1 ring-rose-300 dark:ring-rose-900',
        current && 'ring-1 ring-sky-300 dark:ring-sky-900',
      )}
    >
      <button
        type="button"
        className="flex w-full items-center justify-between gap-3 bg-card px-4 py-3 text-left transition hover:bg-muted/60"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <div className="flex min-w-0 items-center gap-3">
          <div
            className={cn(
              'flex h-9 w-9 shrink-0 items-center justify-center rounded-full border font-bold',
              completed && 'border-emerald-300 bg-emerald-100 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-200',
              blocked && 'border-rose-300 bg-rose-100 text-rose-700 dark:border-rose-800 dark:bg-rose-950 dark:text-rose-200',
              current && 'border-sky-300 bg-sky-100 text-sky-700 dark:border-sky-800 dark:bg-sky-950 dark:text-sky-200',
              !completed && !blocked && !current && 'border-border bg-muted',
            )}
          >
            {completed ? <CheckCircle2 className="h-4 w-4" /> : <span className="text-sm">{index + 1}</span>}
          </div>
          <div className="min-w-0">
            <div className="truncate font-semibold">{step.title_zh}</div>
            <div className="mt-0.5 line-clamp-1 text-xs text-muted-foreground">{step.description_zh}</div>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {step.required ? <span className="text-xs text-muted-foreground">必需</span> : null}
          <StatusBadge tone={statusTone(step.status)}>{statusText(step.status)}</StatusBadge>
          {open ? <ChevronDown className="h-4 w-4 text-muted-foreground" /> : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
        </div>
      </button>

      {open ? (
        <div className="grid gap-3 border-t border-border px-4 py-3">
          {toolbar ? <div className="sticky top-0 z-10 -mx-4 -mt-3 border-b border-border bg-card/95 px-4 py-3 backdrop-blur">{toolbar}</div> : null}

          <p className="text-sm leading-6 text-muted-foreground">{step.description_zh}</p>

          {hasProblems ? (
            <div className="rounded-md border border-rose-300 bg-rose-50 p-3 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950/30 dark:text-rose-100">
              {step.blocked_reasons.join('；')}
            </div>
          ) : null}

          <StepOperationResultView result={operationResult} />

          <div className="grid gap-3 md:grid-cols-2">
            <StepDetailList title="输入" items={step.inputs} />
            <StepDetailList title="输出" items={step.outputs} />
            <StepDetailList title="证据" items={evidenceItems} />
            <StepDetailList title="检查" items={gateItems} />
            <StepDetailList title="子步骤" items={substepItems} />
            <StepDetailList title="下一步" items={step.next_actions} />
          </div>

          {actions.length > 0 ? (
            <div className="flex flex-wrap gap-2 border-t border-border pt-3">
              {actions.map((action) => (
                action.to ? (
                  <Button key={action.label} asChild variant="ghost" size="sm">
                    <Link to={action.to}>
                      {action.icon}
                      {action.label}
                    </Link>
                  </Button>
                ) : (
                  <Button key={action.label} variant="ghost" size="sm" disabled={action.disabled} onClick={action.onClick}>
                    {action.icon}
                    {action.label}
                  </Button>
                )
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function LifecycleSteps({
  steps,
  currentStepKey,
  actionsForStep,
  operationResults,
  toolbarForStep,
}: {
  steps: LifecycleStep[];
  currentStepKey: string;
  actionsForStep: (step: LifecycleStep) => StepAction[];
  operationResults: Record<string, StepOperationResult>;
  toolbarForStep?: (step: LifecycleStep) => React.ReactNode;
}) {
  return (
    <div className="grid gap-3">
      {steps.map((step, index) => (
        <div key={step.key} id={`step-${step.key}`} className="scroll-mt-32 grid gap-2">
          <StepCard
            step={step}
            index={index}
            defaultOpen={step.key === currentStepKey || step.status === 'blocked'}
            actions={actionsForStep(step)}
            operationResult={operationResults[step.key]}
            toolbar={toolbarForStep?.(step)}
          />
          {index < steps.length - 1 ? (
            <div className="flex justify-center text-muted-foreground/70" aria-hidden="true">
              <ArrowDown className="h-5 w-5" />
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}

function StepFloatingNav({ steps, currentStepKey }: { steps: LifecycleStep[]; currentStepKey: string }) {
  return (
    <nav className="fixed right-5 top-45 z-30 hidden w-44 rounded-lg border border-border bg-card/95 p-2 shadow-lg backdrop-blur 2xl:block" aria-label="流程目录">
      <div className="mb-2 px-2 text-xs font-semibold text-muted-foreground">流程目录</div>
      <div className="grid gap-1">
        {steps.map((step, index) => {
          const active = step.key === currentStepKey;
          const completed = step.status === 'completed';
          return (
            <button
              key={step.key}
              type="button"
              className={cn(
                'grid min-w-0 grid-cols-[20px_minmax(0,1fr)_16px] items-center gap-2 rounded-md border px-2 py-2 text-left text-xs leading-tight transition hover:bg-muted',
                active && 'border-sky-300 bg-sky-50 text-sky-900 dark:border-sky-900 dark:bg-sky-950/30 dark:text-sky-100',
                completed && !active && 'border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/25 dark:text-emerald-100',
                !completed && !active && 'border-transparent text-muted-foreground',
              )}
              onClick={() => document.getElementById(`step-${step.key}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
            >
              <span className={cn('flex h-5 w-5 items-center justify-center rounded-full border bg-background font-semibold', completed && 'border-emerald-300 bg-emerald-100 text-emerald-700')}>
                {completed ? <CheckCircle2 className="h-3.5 w-3.5" /> : index + 1}
              </span>
              <span className="min-w-0 break-words">{step.title_zh}</span>
              <span
                className={`h-2.5 w-2.5 justify-self-end rounded-full ${
                  step.status === 'completed'
                    ? 'bg-emerald-500'
                    : step.status === 'blocked'
                      ? 'bg-rose-500'
                      : step.status === 'locked'
                        ? 'bg-muted-foreground/40'
                        : 'bg-amber-500'
                }`}
              />
            </button>
          );
        })}
      </div>
    </nav>
  );
}

export function LifecyclePage() {
  const { setHeaderContent } = useOutletContext<AppShellOutletContext>();
  const queryClient = useQueryClient();
  const [strategySlug, setStrategySlug] = useState('');
  const [profileName, setProfileName] = useState('');
  const [thesisDraft, setThesisDraft] = useState<Record<string, string>>({});
  const [strategyDraft, setStrategyDraft] = useState({
    slug: '',
    name: '',
    description: '',
    one_liner: '',
    return_source: '',
  });
  const [profileDraftName, setProfileDraftName] = useState('');
  const [operationResults, setOperationResults] = useState<Record<string, StepOperationResult>>({});
  const [profileEditDraft, setProfileEditDraft] = useState<Record<string, string>>({});
  const [activeSheet, setActiveSheet] = useState<LifecycleSheet>(null);

  const strategiesQuery = useQuery({ queryKey: ['lifecycle-strategies'], queryFn: api.lifecycleStrategies });
  const strategyQuery = useQuery({
    queryKey: ['lifecycle-strategy', strategySlug],
    queryFn: () => api.lifecycleStrategy(strategySlug),
    enabled: Boolean(strategySlug),
  });
  const profileQuery = useQuery({
    queryKey: ['lifecycle-profile', strategySlug, profileName],
    queryFn: () => api.lifecycleProfile(strategySlug, profileName),
    enabled: Boolean(strategySlug && profileName),
  });
  const profiles = strategyQuery.data?.profiles ?? [];
  const detail = profileQuery.data;

  useEffect(() => {
    const first = strategiesQuery.data?.[0];
    if (!strategySlug && first) {
      setStrategySlug(first.slug);
    }
  }, [strategiesQuery.data, strategySlug]);

  useEffect(() => {
    const defaultName = strategyQuery.data?.default_profile_name;
    const active = strategyQuery.data?.profiles.find((profile) => profile.is_active);
    const first = defaultName ?? active?.profile_name ?? strategyQuery.data?.profiles[0]?.profile_name;
    if (first && !profileName) {
      setProfileName(first);
    }
  }, [profileName, strategyQuery.data]);

  useEffect(() => {
    if (detail?.thesis.values) {
      setThesisDraft(detail.thesis.values);
    }
  }, [detail?.profile.profile_name, detail?.strategy.slug, detail?.thesis.values]);

  useEffect(() => {
    if (detail?.profile.overrides) {
      setProfileEditDraft(readProfileEditDraft(detail.profile.overrides));
    }
  }, [detail?.profile.profile_name, detail?.strategy.slug, detail?.profile.overrides]);

  const refreshProfile = () =>
    void queryClient.invalidateQueries({ queryKey: ['lifecycle-profile', strategySlug, profileName] });
  const refreshStrategies = () => {
    void queryClient.invalidateQueries({ queryKey: ['lifecycle-strategies'] });
    void queryClient.invalidateQueries({ queryKey: ['lifecycle-strategy', strategySlug] });
  };
  const setStepSuccess = (stepKey: string, title: string, data: unknown, nextStep?: string) =>
    setOperationResults((value) => ({
      ...value,
      [stepKey]: { status: 'success', title, detail: operationDetail(data), nextStep },
    }));
  const setStepError = (stepKey: string, title: string, error: unknown) =>
    setOperationResults((value) => ({
      ...value,
      [stepKey]: {
        status: 'error',
        title,
        detail: error instanceof Error ? error.message : stringifyValue(error),
      },
    }));

  const createStrategyMutation = useMutation({
    mutationFn: () =>
      api.createStrategy({
        slug: strategyDraft.slug,
        name: strategyDraft.name,
        description: strategyDraft.description,
        profile_name: 'draft',
        thesis: {
          one_liner: strategyDraft.one_liner,
          return_source: strategyDraft.return_source,
          suitable_market: '',
          unsuitable_market: '',
          invalidation: '',
          observed_metrics: '',
          review_conclusion: '',
          next_action: '补齐 spec 与参数边界',
        },
      }),
    onSuccess: (data) => {
      setStrategySlug(strategyDraft.slug);
      setProfileName('draft');
      setOperationResults({
        hypothesis: {
          status: 'success',
          title: '策略草稿已创建',
          detail: operationDetail(data),
          nextStep: '策略定义',
        },
      });
      setStrategyDraft({ slug: '', name: '', description: '', one_liner: '', return_source: '' });
      setActiveSheet(null);
      refreshStrategies();
    },
    onError: (error) => setStepError('hypothesis', '策略草稿创建失败', error),
  });

  const createProfileMutation = useMutation({
    mutationFn: () =>
      api.createProfile(strategySlug, {
        profile_name: profileDraftName,
        source_profile: profileName,
        overrides: {},
        thesis: detail?.thesis.values ?? {},
      }),
    onSuccess: (data) => {
      setProfileName(profileDraftName);
      setStepSuccess('profile', '参数档案草稿已创建', data, '参数档案');
      setProfileDraftName('');
      setActiveSheet(null);
      refreshStrategies();
    },
    onError: (error) => setStepError('profile', '参数档案草稿创建失败', error),
  });

  const evidenceMutation = useMutation({
    mutationFn: () => api.evidenceCheck(strategySlug, profileName),
    onSuccess: (data) => {
      setStepSuccess('validation', '证据检查完成', data, '晋级验证');
      refreshProfile();
    },
    onError: (error) => setStepError('validation', '证据检查失败', error),
  });
  const promoteMutation = useMutation({
    mutationFn: (toStatus: string) => api.promoteLifecycle(strategySlug, profileName, toStatus, `web lifecycle promotion to ${toStatus}`),
    onSuccess: (data, toStatus) => {
      const stepKey = toStatus === 'validated' ? 'validation' : toStatus === 'paper_active' ? 'paper' : toStatus;
      setStepSuccess(stepKey, '人工晋级完成', data, toStatus === 'validated' ? 'test' : undefined);
      refreshProfile();
    },
    onError: (error, toStatus) => {
      const stepKey = toStatus === 'validated' ? 'validation' : toStatus === 'paper_active' ? 'paper' : toStatus;
      setStepError(stepKey, '人工晋级失败', error);
    },
  });
  const paperMutation = useMutation({
    mutationFn: () => api.createPaperRun(strategySlug, profileName),
    onSuccess: (data) => {
      setStepSuccess('paper', '模拟盘记录已创建', data, '人工晋级 paper_active');
      refreshProfile();
    },
    onError: (error) => setStepError('paper', '模拟盘记录创建失败', error),
  });
  const advanceMutation = useMutation({
    mutationFn: () => api.advanceLifecycle(strategySlug, profileName, 3),
    onSuccess: (data) => {
      const stepKey = typeof data.step_key === 'string' ? data.step_key : detail?.summary.current_step_key ?? 'runtime_artifact';
      setStepSuccess(stepKey, '步骤任务已提交', data, '等待任务完成后刷新当前步骤');
      refreshProfile();
      void queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
    onError: (error) => setStepError(detail?.summary.current_step_key ?? 'runtime_artifact', '步骤任务提交失败', error),
  });
  const thesisMutation = useMutation({
    mutationFn: () => api.updateThesis(strategySlug, profileName, thesisDraft),
    onSuccess: (data) => {
      setStepSuccess('hypothesis', 'Thesis 已保存', data, '策略定义');
      setActiveSheet(null);
      refreshProfile();
    },
    onError: (error) => setStepError('hypothesis', 'Thesis 保存失败', error),
  });
  const scaffoldDefinitionMutation = useMutation({
    mutationFn: () => api.scaffoldDefinition(strategySlug, profileName),
    onSuccess: (data) => {
      setStepSuccess('definition', '基础定义已生成', data, '参数档案');
      refreshStrategies();
      refreshProfile();
    },
    onError: (error) => setStepError('definition', '基础定义生成失败', error),
  });
  const scaffoldProfileMutation = useMutation({
    mutationFn: () => api.scaffoldProfileDefaults(strategySlug, profileName),
    onSuccess: (data) => {
      setStepSuccess('profile', '默认参数已生成', data, '生成运行产物');
      refreshStrategies();
      refreshProfile();
    },
    onError: (error) => setStepError('profile', '默认参数生成失败', error),
  });
  const profileOverridesMutation = useMutation({
    mutationFn: () =>
      api.updateProfileOverrides(strategySlug, profileName, {
        overrides: buildProfileOverrides(profileEditDraft),
      }),
    onSuccess: (data) => {
      setStepSuccess('profile', '参数档案已保存', data, '生成运行产物');
      setActiveSheet(null);
      refreshStrategies();
      refreshProfile();
    },
    onError: (error) => setStepError('profile', '参数档案保存失败', error),
  });

  const actionsForStep = (step: LifecycleStep): StepAction[] => {
    const isCurrent = step.key === detail?.summary.current_step_key;
    const canAdvance = isCurrent && !advanceMutation.isPending && step.status !== 'completed';
    const actions: StepAction[] = [];
    if (step.key === 'hypothesis') {
      actions.push({
        label: '查看/编辑 Thesis',
        icon: <FileText className="h-4 w-4" />,
        disabled: !detail,
        onClick: () => setActiveSheet('edit-thesis'),
      });
    }
    if (step.key === 'definition') {
      actions.push({
        label: '查看定义字段',
        icon: <ClipboardList className="h-4 w-4" />,
        disabled: !detail,
        onClick: () => setActiveSheet('edit-definition'),
      });
      actions.push({
        label: '生成基础定义',
        icon: <Sparkles className="h-4 w-4" />,
        disabled: scaffoldDefinitionMutation.isPending,
        onClick: () => scaffoldDefinitionMutation.mutate(),
      });
    }
    if (step.key === 'profile') {
      actions.push({
        label: '新增档案',
        icon: <Plus className="h-4 w-4" />,
        disabled: !strategySlug || !profileName,
        onClick: () => setActiveSheet('create-profile'),
      });
      actions.push({
        label: '查看/编辑档案',
        icon: <SlidersHorizontal className="h-4 w-4" />,
        disabled: !detail,
        onClick: () => setActiveSheet('edit-profile'),
      });
      actions.push({
        label: '生成默认参数',
        icon: <Sparkles className="h-4 w-4" />,
        disabled: scaffoldProfileMutation.isPending,
        onClick: () => scaffoldProfileMutation.mutate(),
      });
    }
    if (['runtime_artifact', 'train', 'validation', 'test'].includes(step.key)) {
      actions.push({
        label: step.key === 'runtime_artifact' ? '生成产物' : 'AI 推进',
        icon: <Sparkles className="h-4 w-4" />,
        disabled: !canAdvance,
        onClick: () => advanceMutation.mutate(),
      });
    }
    if (step.key === 'validation') {
      actions.push({
        label: '证据检查',
        icon: <ShieldCheck className="h-4 w-4" />,
        disabled: evidenceMutation.isPending,
        onClick: () => evidenceMutation.mutate(),
      });
      actions.push({
        label: '晋级验证',
        icon: <CheckCircle2 className="h-4 w-4" />,
        disabled: promoteMutation.isPending,
        onClick: () => promoteMutation.mutate('validated'),
      });
    }
    if (step.key === 'paper') {
      actions.push({
        label: '创建模拟',
        icon: <Play className="h-4 w-4" />,
        disabled: paperMutation.isPending || step.status === 'locked',
        onClick: () => paperMutation.mutate(),
      });
      actions.push({
        label: '晋级 paper_active',
        icon: <CheckCircle2 className="h-4 w-4" />,
        disabled: promoteMutation.isPending || step.status === 'locked',
        onClick: () => promoteMutation.mutate('paper_active'),
      });
    }
    if (step.key === 'live_candidate') {
      actions.push({
        label: '晋级 live_candidate',
        icon: <ShieldCheck className="h-4 w-4" />,
        disabled: promoteMutation.isPending || step.status === 'locked',
        onClick: () => promoteMutation.mutate('live_candidate'),
      });
    }
    if (step.key === 'live_active') {
      actions.push({
        label: '晋级 live_active',
        icon: <ShieldCheck className="h-4 w-4" />,
        disabled: promoteMutation.isPending || step.status === 'locked',
        onClick: () => promoteMutation.mutate('live_active'),
      });
    }
    if (['train', 'validation', 'test'].includes(step.key)) {
      actions.push({ label: '查看回测', icon: <History className="h-4 w-4" />, to: '/backtests' });
    }
    if (step.key === 'runtime_artifact') {
      actions.push({ label: '查看产物', icon: <History className="h-4 w-4" />, to: '/runtime' });
    }
    if (step.key === 'paper') {
      actions.push({ label: '查看模拟', icon: <History className="h-4 w-4" />, to: '/paper' });
    }
    actions.push({ label: '任务历史', icon: <History className="h-4 w-4" />, to: '/jobs' });
    return actions;
  };

  const toolbarForStep = (step: LifecycleStep) => {
    if (step.key === 'profile') {
      return (
        <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <label className="grid min-w-0 flex-1 gap-1 text-sm">
            <span className="text-xs font-semibold text-muted-foreground">参数档案</span>
            <select
              className="h-10 rounded-md border border-input bg-muted px-3"
              value={profileName}
              onChange={(event) => setProfileName(event.target.value)}
            >
              {profiles.map((profile: StrategyProfile) => <option key={profile.profile_name} value={profile.profile_name}>{profile.profile_name}</option>)}
            </select>
          </label>
          <div className="flex flex-wrap gap-2">
            <Button variant="ghost" size="sm" disabled={!strategySlug || !profileName} onClick={() => setActiveSheet('create-profile')}>
              <Plus className="h-4 w-4" />
              新增档案
            </Button>
            <Button size="sm" disabled={!detail} onClick={() => setActiveSheet('edit-profile')}>
              <SlidersHorizontal className="h-4 w-4" />
              查看/编辑
            </Button>
          </div>
        </div>
      );
    }
    if (['train', 'validation', 'test'].includes(step.key)) {
      return (
        <div className="flex flex-wrap items-center gap-2">
          <div className="mr-auto text-sm font-semibold">流程测试</div>
          <Button variant="ghost" size="sm" disabled={!strategySlug || !profileName || advanceMutation.isPending} onClick={() => advanceMutation.mutate()}>
            <Sparkles className="h-4 w-4" />
            AI 推进
          </Button>
          <Button asChild variant="ghost" size="sm">
            <Link to="/backtests">
              <History className="h-4 w-4" />
              查看回测
            </Link>
          </Button>
          <Button asChild variant="ghost" size="sm">
            <Link to="/jobs">
              <History className="h-4 w-4" />
              任务历史
            </Link>
          </Button>
        </div>
      );
    }
    return null;
  };

  const lifecycleHeaderContent = useMemo(
    () => (
      <div className="grid gap-3 rounded-md border border-border bg-background/70 p-3">
        <div className="flex min-w-0 items-center gap-2">
          <select
            className="h-9 min-w-0 max-w-[560px] flex-1 rounded-md border border-input bg-muted px-3 text-sm"
            aria-label="策略"
            value={strategySlug}
            onChange={(event) => { setStrategySlug(event.target.value); setProfileName(''); }}
          >
            {strategiesQuery.data?.map((strategy) => <option key={strategy.slug} value={strategy.slug}>{strategy.name}（{strategy.slug}）</option>)}
          </select>
          <Button size="sm" onClick={() => setActiveSheet('create-strategy')}>
            <Plus className="h-4 w-4" />
            新增策略
          </Button>
        </div>
        <div className="grid gap-3 md:grid-cols-4">
          <Metric label="当前档案" value={profileName || '-'} />
          <Metric label="当前阶段" value={detail?.summary.current_step_title_zh ?? '-'} />
          <Metric label="完成进度" value={detail ? `${detail.summary.completed_steps}/${detail.summary.total_steps}` : '-'} />
          <Metric label="运行一致性" value={detail?.alignment.summary_zh ?? '-'} />
        </div>
      </div>
    ),
    [detail, profileName, strategiesQuery.data, strategySlug],
  );

  useEffect(() => {
    setHeaderContent(lifecycleHeaderContent);
    return () => setHeaderContent(null);
  }, [setHeaderContent, lifecycleHeaderContent]);

  if (strategiesQuery.isLoading) {
    return <LoadingState />;
  }
  if (strategiesQuery.error || strategyQuery.error || profileQuery.error) {
    return <ErrorState error={strategiesQuery.error ?? strategyQuery.error ?? profileQuery.error} />;
  }

  return (
    <div className="grid gap-4 2xl:pr-52">
      {!detail ? <LoadingState /> : (
        <>
          <StepFloatingNav steps={detail.steps} currentStepKey={detail.summary.current_step_key} />

          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
            <Card className="border-2 border-border shadow-sm">
              <CardHeader className="min-h-14 bg-muted/40">
                <CardTitle className="text-base">{detail.strategy.name} / {detail.profile.profile_name}</CardTitle>
                <StatusBadge tone={statusTone(detail.summary.current_status)}>{detail.summary.current_status_zh}</StatusBadge>
              </CardHeader>
              <CardContent>
                <LifecycleSteps
                  steps={detail.steps}
                  currentStepKey={detail.summary.current_step_key}
                  actionsForStep={actionsForStep}
                  operationResults={operationResults}
                  toolbarForStep={toolbarForStep}
                />
              </CardContent>
            </Card>

            <div className="grid content-start gap-4">
              <Card>
                <CardHeader><CardTitle>最近晋级事件</CardTitle></CardHeader>
                <CardContent className="grid gap-2 text-sm">
                  {detail.promotion_events.slice(0, 5).map((event) => (
                    <div key={event.id} className="rounded-md border border-border bg-muted/50 p-2">
                      <div className="font-semibold">{event.from_status ?? '-'} → {event.to_status}</div>
                      <div className="text-xs text-muted-foreground">{formatDateTime(event.created_at)} / {event.reason ?? '-'}</div>
                    </div>
                  ))}
                  {detail.paper_run ? (
                    <div className="rounded-md border border-border bg-muted/50 p-2">
                      <div className="font-semibold">当前模拟：{detail.paper_run.run_name}</div>
                      <div className="text-xs text-muted-foreground">{stringifyValue(detail.paper_run.status)}</div>
                    </div>
                  ) : null}
                </CardContent>
              </Card>
            </div>
          </div>
        </>
      )}

      <Sheet open={activeSheet !== null} onOpenChange={(open) => { if (!open) setActiveSheet(null); }}>
        <SheetContent>
          {activeSheet === 'create-strategy' ? (
            <>
              <SheetHeader>
                <SheetTitle>新增策略 Draft</SheetTitle>
                <SheetDescription>创建成功后会自动切换到新策略，并默认选中 draft 参数档案。</SheetDescription>
              </SheetHeader>
              <SheetBody className="grid gap-3">
                <input className="h-10 rounded-md border border-input bg-muted px-3 text-sm" placeholder="strategy_slug，例如 grid_ls_v2" value={strategyDraft.slug} onChange={(event) => setStrategyDraft((value) => ({ ...value, slug: event.target.value }))} />
                <input className="h-10 rounded-md border border-input bg-muted px-3 text-sm" placeholder="中文策略名，例如 SOL 网格多空 V2" value={strategyDraft.name} onChange={(event) => setStrategyDraft((value) => ({ ...value, name: event.target.value }))} />
                <textarea className="min-h-24 resize-y rounded-md border border-input bg-muted px-3 py-2 text-sm leading-6 text-foreground" placeholder="策略说明" value={strategyDraft.description} onChange={(event) => setStrategyDraft((value) => ({ ...value, description: event.target.value }))} />
                <input className="h-10 rounded-md border border-input bg-muted px-3 text-sm" placeholder="一句话假设" value={strategyDraft.one_liner} onChange={(event) => setStrategyDraft((value) => ({ ...value, one_liner: event.target.value }))} />
                <input className="h-10 rounded-md border border-input bg-muted px-3 text-sm" placeholder="收益来源假设" value={strategyDraft.return_source} onChange={(event) => setStrategyDraft((value) => ({ ...value, return_source: event.target.value }))} />
              </SheetBody>
              <SheetFooter>
                <Button variant="ghost" onClick={() => setActiveSheet(null)}>取消</Button>
                <Button disabled={createStrategyMutation.isPending || !strategyDraft.slug || !strategyDraft.name || !strategyDraft.description} onClick={() => createStrategyMutation.mutate()}>
                  <Plus className="h-4 w-4" />
                  创建策略草稿
                </Button>
              </SheetFooter>
            </>
          ) : null}

          {activeSheet === 'create-profile' ? (
            <>
              <SheetHeader>
                <SheetTitle>新增参数档案</SheetTitle>
                <SheetDescription>基于当前档案复制 thesis，创建候选草稿后会自动选中新档案。</SheetDescription>
              </SheetHeader>
              <SheetBody className="grid gap-3">
                <Metric label="来源策略" value={strategySlug || '-'} />
                <Metric label="来源档案" value={profileName || '-'} />
                <input className="h-10 rounded-md border border-input bg-muted px-3 text-sm" placeholder="profile_name，例如 candidate_grid_20260525" value={profileDraftName} onChange={(event) => setProfileDraftName(event.target.value)} />
                <div className="rounded-md border border-border bg-muted/50 p-3 text-sm leading-6 text-muted-foreground">
                  复杂参数建议由 AI 推进或 optimization 任务生成；这里优先创建可追踪的档案草稿。
                </div>
              </SheetBody>
              <SheetFooter>
                <Button variant="ghost" onClick={() => setActiveSheet(null)}>取消</Button>
                <Button disabled={!strategySlug || !profileName || !profileDraftName || createProfileMutation.isPending} onClick={() => createProfileMutation.mutate()}>
                  <Plus className="h-4 w-4" />
                  创建档案草稿
                </Button>
              </SheetFooter>
            </>
          ) : null}

          {activeSheet === 'edit-thesis' && detail ? (
            <>
              <SheetHeader>
                <SheetTitle>策略 Thesis</SheetTitle>
                <SheetDescription>{detail.strategy.name} / {detail.profile.profile_name}</SheetDescription>
              </SheetHeader>
              <SheetBody className="grid gap-3 text-sm">
                {Object.entries(detail.thesis_required_fields).map(([key, label]) => (
                  <label key={key} className="grid gap-1">
                    <span className="text-xs font-semibold text-muted-foreground">{label}（选填）</span>
                    <textarea
                      className="min-h-24 resize-y rounded-md border border-input bg-muted px-3 py-2 text-sm leading-6 text-foreground"
                      value={thesisDraft[key] ?? ''}
                      onChange={(event) => setThesisDraft((value) => ({ ...value, [key]: event.target.value }))}
                    />
                  </label>
                ))}
                {detail.thesis.missing_fields.length > 0 ? (
                  <div className="rounded-md border border-amber-300 bg-amber-50 p-2 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-100">
                    建议补充：{detail.thesis.missing_fields.join('、')}
                  </div>
                ) : null}
              </SheetBody>
              <SheetFooter>
                <Button variant="ghost" onClick={() => setActiveSheet(null)}>取消</Button>
                <Button disabled={thesisMutation.isPending} onClick={() => thesisMutation.mutate()}>
                  <Edit3 className="h-4 w-4" />
                  保存 Thesis
                </Button>
              </SheetFooter>
            </>
          ) : null}

          {activeSheet === 'edit-definition' && detail ? (
            <>
              <SheetHeader>
                <SheetTitle>策略定义字段</SheetTitle>
                <SheetDescription>{detail.strategy.slug} 的当前 spec 与定义生成入口。</SheetDescription>
              </SheetHeader>
              <SheetBody className="grid gap-3 text-sm">
                <div className="grid gap-2 rounded-md border border-border bg-muted/50 p-3">
                  <div className="flex items-center gap-2 font-semibold">
                    <ListChecks className="h-4 w-4" />
                    当前策略定义
                  </div>
                  <pre className="max-h-[55vh] overflow-auto whitespace-pre-wrap break-words rounded-md bg-background p-3 font-mono text-xs leading-5">
                    {JSON.stringify(detail.strategy.spec ?? {}, null, 2)}
                  </pre>
                </div>
              </SheetBody>
              <SheetFooter>
                <Button variant="ghost" onClick={() => setActiveSheet(null)}>关闭</Button>
                <Button disabled={scaffoldDefinitionMutation.isPending} onClick={() => scaffoldDefinitionMutation.mutate()}>
                  <Sparkles className="h-4 w-4" />
                  生成基础定义
                </Button>
              </SheetFooter>
            </>
          ) : null}

          {activeSheet === 'edit-profile' && detail ? (
            <>
              <SheetHeader>
                <SheetTitle>参数档案</SheetTitle>
                <SheetDescription>{detail.strategy.name} / {detail.profile.profile_name}</SheetDescription>
              </SheetHeader>
              <SheetBody className="grid gap-3 text-sm">
                {PROTECTED_PROFILE_STATUSES.has(detail.profile.status) ? (
                  <div className="rounded-md border border-amber-300 bg-amber-50 p-2 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-100">
                    当前档案状态为 {detail.profile.status}，请新建草稿后再编辑参数。
                  </div>
                ) : null}
                <div className="grid gap-3 sm:grid-cols-2">
                  {PROFILE_EDIT_FIELDS.map((field) => (
                    <label key={field.key} className="grid gap-1">
                      <span className="text-xs font-semibold text-muted-foreground">{field.label}</span>
                      <input
                        className="h-10 rounded-md border border-input bg-muted px-3 text-sm"
                        disabled={PROTECTED_PROFILE_STATUSES.has(detail.profile.status)}
                        inputMode="decimal"
                        value={profileEditDraft[field.key] ?? ''}
                        onChange={(event) => setProfileEditDraft((value) => ({ ...value, [field.key]: event.target.value }))}
                      />
                    </label>
                  ))}
                </div>
                <label className="grid gap-1">
                  <span className="text-xs font-semibold text-muted-foreground">minimal_roi JSON</span>
                  <textarea
                    className="min-h-32 resize-y rounded-md border border-input bg-muted px-3 py-2 font-mono text-xs leading-5 text-foreground"
                    disabled={PROTECTED_PROFILE_STATUSES.has(detail.profile.status)}
                    value={profileEditDraft.minimal_roi ?? '{}'}
                    onChange={(event) => setProfileEditDraft((value) => ({ ...value, minimal_roi: event.target.value }))}
                  />
                </label>
              </SheetBody>
              <SheetFooter>
                <Button variant="ghost" onClick={() => setActiveSheet(null)}>取消</Button>
                <Button
                  disabled={
                    profileOverridesMutation.isPending
                    || PROTECTED_PROFILE_STATUSES.has(detail.profile.status)
                  }
                  onClick={() => profileOverridesMutation.mutate()}
                >
                  <Edit3 className="h-4 w-4" />
                  保存参数
                </Button>
              </SheetFooter>
            </>
          ) : null}
        </SheetContent>
      </Sheet>
    </div>
  );
}
