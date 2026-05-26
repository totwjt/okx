import {
  BarChart3,
  ChevronRight,
  Database,
  FlaskConical,
  LayoutDashboard,
  LineChart,
  Moon,
  Network,
  PlayCircle,
  Settings,
  ShieldAlert,
  Sun,
  Workflow,
} from 'lucide-react';
import { useEffect, useMemo, useState, type Dispatch, type ReactNode, type SetStateAction } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { cn } from '../lib/utils';

const navItems = [
  { path: '/strategies', label: '策略', section: '策略注册表', title: '策略管理', icon: Database },
  { path: '/lifecycle', label: '工作台', section: '策略全流程', title: '工作台', icon: Workflow },
  { path: '/backtests', label: '回测', section: '验证闸门', title: '回测验证', icon: BarChart3 },
  { path: '/runtime', label: '运行', section: '运行产物', title: '运行系统', icon: Network },
  { path: '/jobs', label: '任务', section: '任务队列', title: '任务系统', icon: PlayCircle },
  { path: '/paper', label: '模拟', section: '模拟运行', title: '模拟盘', icon: LineChart },
  { path: '/risk', label: '风控', section: '风险控制', title: '风控看板', icon: ShieldAlert },
  { path: '/factors', label: '因子', section: '数据健康', title: '因子数据', icon: FlaskConical },
  { path: '/settings', label: '设置', section: '配置中心', title: '系统配置', icon: Settings },
];

const navGroups = [
  { label: '研究流程', items: navItems.slice(0, 4) },
  { label: '运行监控', items: navItems.slice(4, 8) },
  { label: '系统', items: navItems.slice(8) },
];

export interface AppShellOutletContext {
  setHeaderContent: Dispatch<SetStateAction<ReactNode>>;
}

function SidebarNav() {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex h-16 shrink-0 items-center gap-3 border-b border-border px-4">
        <div className="flex h-9 w-9 items-center justify-center rounded-md border border-primary/30 bg-primary/10 text-primary">
          <LayoutDashboard className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <div className="truncate text-sm font-bold leading-tight">AI-OuYi</div>
          <div className="truncate text-xs text-muted-foreground">量化管理控制台</div>
        </div>
      </div>

      <nav className="min-h-0 flex-1 overflow-y-auto px-3 py-4" aria-label="主导航">
        <div className="grid gap-5">
          {navGroups.map((group) => (
            <div key={group.label} className="grid gap-1.5">
              <div className="px-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                {group.label}
              </div>
              <div className="grid gap-1">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      className={({ isActive }) =>
                        cn(
                          'group flex h-9 items-center gap-2.5 rounded-md px-2.5 text-sm text-muted-foreground transition hover:bg-muted hover:text-foreground',
                          isActive && 'bg-primary/10 text-primary ring-1 ring-primary/15',
                        )
                      }
                    >
                      <Icon className="h-4 w-4 shrink-0" />
                      <span className="min-w-0 flex-1 truncate">{item.label}</span>
                      <ChevronRight className="h-3.5 w-3.5 opacity-0 transition group-hover:opacity-60" />
                    </NavLink>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </nav>

      <div className="shrink-0 border-t border-border px-4 py-3">
        <div className="rounded-md border border-border bg-muted/50 px-3 py-2">
          <div className="text-xs font-semibold text-foreground">默认策略</div>
          <div className="mt-0.5 truncate font-mono text-xs text-muted-foreground">GridLsV1Strategy</div>
        </div>
      </div>
    </div>
  );
}

export function AppShell() {
  const location = useLocation();
  const current = navItems.find((item) => location.pathname.startsWith(item.path)) ?? navItems[0];
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [headerContent, setHeaderContent] = useState<ReactNode>(null);

  const routeTrail = useMemo(() => [current.section, current.title], [current.section, current.title]);
  const outletContext = useMemo<AppShellOutletContext>(() => ({ setHeaderContent }), []);

  useEffect(() => {
    const savedTheme = localStorage.getItem('ai-ouyi-theme');
    setTheme(savedTheme === 'dark' ? 'dark' : 'light');
  }, []);

  useEffect(() => {
    setHeaderContent(null);
  }, [location.pathname]);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
    document.documentElement.style.colorScheme = theme;
    localStorage.setItem('ai-ouyi-theme', theme);
  }, [theme]);

  return (
    <div className="grid h-dvh min-h-screen min-w-[1180px] grid-cols-[248px_minmax(0,1fr)] bg-background text-foreground">
      <aside className="flex min-h-0 border-r border-border bg-card text-card-foreground">
        <SidebarNav />
      </aside>

      <div className="grid min-h-0 min-w-0 grid-rows-[auto_minmax(0,1fr)]">
        <header className="grid min-w-0 gap-3 border-b border-border bg-card/95 px-6 py-3 text-card-foreground backdrop-blur">
          <div className="flex min-w-0 items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <div className="min-w-0">
                <div className="flex min-w-0 items-center gap-1 text-xs text-muted-foreground">
                  {routeTrail.map((item, index) => (
                    <span key={item} className="flex min-w-0 items-center gap-1">
                      {index > 0 ? <ChevronRight className="h-3 w-3 shrink-0" /> : null}
                      <span className="truncate">{item}</span>
                    </span>
                  ))}
                </div>
                {/* <h1 className="mt-0.5 truncate text-lg font-bold leading-tight sm:text-xl">{current.title}</h1> */}
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <div className="flex items-center gap-2 rounded-md border border-emerald-300 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200">
                <span className="h-2 w-2 rounded-full bg-emerald-500" />
                <span>FastAPI 后端</span>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label={theme === 'dark' ? '切换到浅色模式' : '切换到深色模式'}
                onClick={() => setTheme((value) => (value === 'dark' ? 'light' : 'dark'))}
              >
                {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              </Button>
            </div>
          </div>
          {headerContent ? <div className="min-w-0">{headerContent}</div> : null}
        </header>
        <main className="min-h-0 min-w-0 overflow-auto bg-background">
          <div className="grid w-full min-w-0 max-w-[1680px] gap-4 px-6 py-5 [&>*]:min-w-0">
            <Outlet context={outletContext} />
          </div>
        </main>
      </div>
    </div>
  );
}
