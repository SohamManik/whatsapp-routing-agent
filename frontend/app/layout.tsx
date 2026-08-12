"use client";

import '../app/globals.css';
import { Sidebar } from '@/components/Sidebar';
import { useState } from 'react';
import { Menu, X } from 'lucide-react';
import { Bot } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const pathname = usePathname();

  const links = [
    { href: '/', label: 'Dashboard' },
    { href: '/messages', label: 'Messages' },
    { href: '/monitor', label: 'Live Monitor' },
  ];

  return (
    <html lang="en" className="dark">
      <body className="bg-zinc-950 text-zinc-100 flex h-screen overflow-hidden">
        <Sidebar />
        
        {/* Mobile Header */}
        <div className="md:hidden fixed top-0 left-0 right-0 h-16 border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-md z-40 flex items-center justify-between px-4">
          <div className="flex items-center">
            <Bot className="w-5 h-5 text-violet-500 mr-2" />
            <span className="font-semibold text-zinc-100">Agentic Router</span>
          </div>
          <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="p-2 -mr-2 text-zinc-400">
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {/* Mobile Menu Overlay */}
        {mobileMenuOpen && (
          <div className="md:hidden fixed inset-0 top-16 bg-zinc-950 z-30 p-4 border-t border-zinc-800">
            <nav className="flex flex-col space-y-2">
              {links.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`p-3 rounded-md text-sm font-medium ${
                    pathname === link.href || (link.href !== '/' && pathname.startsWith(link.href))
                      ? 'bg-zinc-800 text-zinc-100'
                      : 'text-zinc-400'
                  }`}
                >
                  {link.label}
                </Link>
              ))}
            </nav>
          </div>
        )}

        <main className="flex-1 overflow-y-auto pt-16 md:pt-0 pb-safe relative">
          <div className="max-w-7xl mx-auto w-full h-full">
            {children}
          </div>
        </main>
      </body>
    </html>
  );
}
