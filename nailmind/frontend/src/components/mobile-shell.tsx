'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Bookmark, Bot, Camera, Clock3, Images } from 'lucide-react';

const navItems = [
  { href: '/', label: '模板', icon: Images },
  { href: '/upload', label: '手照', icon: Camera },
  { href: '/assistant', label: '助手', icon: Bot },
  { href: '/records', label: '记录', icon: Clock3 },
  { href: '/candidates', label: '候选', icon: Bookmark },
];

export function MobileShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-[#f7f2eb] text-stone-950">
      <main className="mx-auto min-h-screen max-w-[430px] bg-[#fbf7ef] pb-28 shadow-2xl shadow-stone-200/80">
        {children}
        <nav className="fixed inset-x-0 bottom-0 z-40 mx-auto max-w-[430px] border-t border-stone-200 bg-[#fbf7ef]/90 px-6 py-3 backdrop-blur-2xl">
          <div className="grid grid-cols-5 text-xs font-medium text-stone-500">
            {navItems.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={active ? 'flex flex-col items-center gap-1 text-stone-950' : 'flex flex-col items-center gap-1'}
                >
                  <item.icon className="h-5 w-5" />
                  {item.label}
                </Link>
              );
            })}
          </div>
        </nav>
      </main>
    </div>
  );
}
