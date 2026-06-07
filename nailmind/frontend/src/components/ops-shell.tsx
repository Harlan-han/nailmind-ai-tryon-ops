'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  BarChart3,
  Bot,
  Calendar,
  ClipboardCheck,
  Flame,
  LayoutGrid,
  Lightbulb,
  Sparkles,
  Settings,
  Store,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';
import { clearAuthSession, getCurrentUser, isOperator, validateAuthSession, type AuthUser } from '@/lib/auth';

const primaryNav = [
  { href: '/admin/assistant', label: 'Chat', icon: Bot },
  { href: '/admin', label: '今日行动', icon: ClipboardCheck },
  { href: '/merchant/bookings', label: '预约跟进', icon: Calendar },
  { href: '/admin/suggestions', label: '建议中心', icon: Lightbulb },
  { href: '/admin/hot', label: '爆款候选', icon: Flame },
  { href: '/admin/cold', label: '冷门修复', icon: TrendingDown },
  { href: '/admin/trends', label: '趋势分析', icon: BarChart3 },
  { href: '/admin/insights', label: '智能洞察', icon: Sparkles },
  { href: '/admin/designs', label: '款式管理', icon: LayoutGrid },
];

const secondaryNav = [
  { href: '/merchant', label: '商家概览', icon: Store },
  { href: '/admin/report', label: '运营日报', icon: TrendingUp },
  { href: '/admin/seasonal', label: '节日专题', icon: Calendar },
  { href: '/admin/settings', label: '配置中心', icon: Settings },
];

export function OpsShell({
  title,
  subtitle,
  eyebrow = 'NailMind Ops',
  action,
  children,
}: {
  title: string;
  subtitle?: string;
  eyebrow?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [operator, setOperator] = useState<AuthUser | null>(null);
  const navGroups = [
    { title: '行动工作台', items: primaryNav },
    { title: '基础配置', items: secondaryNav },
  ];

  const allNavItems = [...primaryNav, ...secondaryNav];

  useEffect(() => {
    let active = true;

    void Promise.resolve().then(async () => {
      const currentUser = getCurrentUser();
      if (!isOperator(currentUser)) {
        router.replace('/admin/login');
        return;
      }
      if (active) {
        setOperator(currentUser);
      }
      const freshUser = await validateAuthSession();
      if (!isOperator(freshUser)) {
        router.replace('/admin/login');
        return;
      }
      if (active) {
        setOperator(freshUser);
      }
    });

    return () => {
      active = false;
    };
  }, [router]);

  const logout = () => {
    clearAuthSession();
    router.replace('/admin/login');
  };

  return (
    <div className="min-h-screen bg-[#f7f1e7] text-stone-950">
      <aside className="fixed inset-y-0 left-0 z-50 hidden w-72 border-r border-stone-200 bg-[#fffaf0]/95 px-4 py-5 shadow-sm backdrop-blur-xl xl:block">
        <Link href="/admin/assistant" className="block rounded-[1.75rem] bg-stone-950 p-5 text-amber-50">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-amber-100/55">NailMind</p>
          <h2 className="mt-2 text-2xl font-bold">Ops Center</h2>
          <p className="mt-2 text-xs leading-5 text-amber-100/70">从 Chat 开始，让 Agent 读数据、出建议、推日报、同步行动卡。</p>
        </Link>

        <nav className="mt-6 space-y-6">
          {navGroups.map((group) => (
            <div key={group.title}>
              <p className="mb-2 px-3 text-xs font-bold text-stone-400">{group.title}</p>
              <div className="space-y-1">
                {group.items.map((item) => {
                  const active = pathname === item.href;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={
                        active
                          ? 'flex items-center gap-3 rounded-2xl bg-stone-950 px-4 py-3 text-sm font-semibold text-amber-50 shadow-sm'
                          : 'flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium text-stone-600 transition hover:bg-white hover:text-stone-950'
                      }
                    >
                      <item.icon className="h-4 w-4" />
                      {item.label}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
      </aside>

      <aside className="fixed inset-y-0 left-0 z-50 w-16 border-r border-stone-200 bg-[#fffaf0]/95 px-2 py-4 shadow-sm backdrop-blur-xl xl:hidden">
        <Link
          href="/admin/assistant"
          className="mb-4 flex h-11 w-11 items-center justify-center rounded-2xl bg-stone-950 text-sm font-bold text-amber-50"
          title="NailMind Ops"
        >
          NM
        </Link>
        <nav className="space-y-2">
          {allNavItems.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                title={item.label}
                className={
                  active
                    ? 'flex h-11 w-11 items-center justify-center rounded-2xl bg-stone-950 text-amber-50 shadow-sm'
                    : 'flex h-11 w-11 items-center justify-center rounded-2xl text-stone-500 transition hover:bg-white hover:text-stone-950'
                }
              >
                <item.icon className="h-4 w-4" />
              </Link>
            );
          })}
        </nav>
      </aside>

      <div className="pl-16 xl:pl-72">
        <header className="sticky top-0 z-40 border-b border-stone-200 bg-[#f7f1e7]/90 backdrop-blur-xl">
          <div className="mx-auto max-w-7xl px-4 py-4 md:px-6 xl:px-8">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-xs font-medium uppercase tracking-[0.3em] text-stone-400">{eyebrow}</p>
                <h1 className="mt-1 text-2xl font-bold text-stone-950">{title}</h1>
                {subtitle && <p className="mt-1 text-sm text-stone-500">{subtitle}</p>}
              </div>
              <div className="flex items-center gap-3">
                {operator && (
                  <button
                    type="button"
                    onClick={logout}
                    className="rounded-full border border-stone-200 bg-white px-4 py-2 text-sm font-semibold text-stone-600 shadow-sm"
                  >
                    {operator.nickname || '运营账号'} · 退出
                  </button>
                )}
                {action}
              </div>
            </div>
          </div>
        </header>

        <main className="mx-auto max-w-7xl px-4 py-6 md:px-6 xl:px-8">{children}</main>
      </div>
    </div>
  );
}

export function OpsStatCard({
  label,
  value,
  helper,
  tone = 'bg-white',
}: {
  label: string;
  value: string | number;
  helper?: string;
  tone?: string;
}) {
  return (
    <div className={`rounded-3xl border border-stone-200 p-4 shadow-sm ${tone}`}>
      <p className="text-2xl font-bold text-stone-950">{value}</p>
      <p className="mt-1 text-sm text-stone-500">{label}</p>
      {helper && <p className="mt-3 text-xs text-stone-400">{helper}</p>}
    </div>
  );
}
