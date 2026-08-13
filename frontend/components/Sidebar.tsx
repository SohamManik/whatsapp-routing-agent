"use client";

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, MessageSquare, Activity, Bot } from 'lucide-react';

export function Sidebar() {
  const pathname = usePathname();

  const links = [
    { href: '/', label: 'Dashboard', icon: LayoutDashboard },
    { href: '/messages', label: 'Messages', icon: MessageSquare },
    { href: '/monitor', label: 'Live Monitor', icon: Activity },
  ];

  return (
    <aside className="w-64 bg-zinc-950 border-r border-zinc-800 flex flex-col h-screen shrink-0 hidden md:flex">
      <div className="h-16 flex items-center px-6 border-b border-zinc-800">
        <Bot className="w-6 h-6 text-violet-500 mr-3" />
        <span className="font-semibold text-zinc-100 tracking-tight">Agentic Router</span>
      </div>
      <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
        {links.map((link) => {
          const isActive = pathname === link.href || (link.href !== '/' && pathname.startsWith(link.href));
          const Icon = link.icon;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`flex items-center px-3 py-2.5 rounded-md transition-all duration-200 group relative ${
                isActive
                  ? 'bg-zinc-800/50 text-zinc-100'
                  : 'text-zinc-400 hover:bg-zinc-800/30 hover:text-zinc-200'
              }`}
            >
              {isActive && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-violet-500 rounded-r-full" />
              )}
              <Icon className={`w-5 h-5 mr-3 flex-shrink-0 ${isActive ? 'text-violet-500' : 'text-zinc-500 group-hover:text-zinc-400'}`} />
              <span className="font-medium text-sm">{link.label}</span>
            </Link>
          );
        })}
      </nav>

    </aside>
  );
}
