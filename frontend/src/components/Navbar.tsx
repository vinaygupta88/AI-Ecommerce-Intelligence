'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Activity, Package, Bell, LayoutDashboard, Sparkles } from 'lucide-react';

export default function Navbar() {
  const pathname = usePathname();

  const navItems = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Inventory & Catalog', href: '/products', icon: Package },
    { name: 'Alerts Hub', href: '/alerts', icon: Bell },
  ];

  return (
    <header className="border-b border-zinc-800/80 bg-zinc-950/70 backdrop-blur-xl sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        
        {/* Brand Logo */}
        <Link href="/dashboard" className="flex items-center space-x-3 group">
          <div className="p-2 bg-gradient-to-tr from-indigo-600 to-violet-500 rounded-xl text-white shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition">
            <Activity className="w-5 h-5" />
          </div>
          <div className="flex items-center space-x-2">
            <span className="font-extrabold text-white text-lg tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-zinc-200 to-zinc-400">
              DemandPulse
            </span>
            <span className="flex items-center space-x-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <Sparkles className="w-3 h-3" />
              <span>AI Engine</span>
            </span>
          </div>
        </Link>

        {/* Navigation Links */}
        <nav className="flex items-center space-x-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg text-sm font-medium transition ${
                  isActive
                    ? 'bg-zinc-800/90 text-white shadow-sm border border-zinc-700/60'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/60'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-indigo-400' : 'text-zinc-400'}`} />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}