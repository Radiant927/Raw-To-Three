"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Cpu, House, Play, Info, Menu, X } from "lucide-react";

const LINKS = [
  { href: "/", label: "首页", icon: House },
  { href: "/pipeline", label: "原理", icon: Cpu },
  { href: "/demo", label: "体验", icon: Play },
  { href: "/about", label: "关于", icon: Info },
];

export default function Navbar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 glass-card border-b border-white/5 rounded-none">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <Link
            href="/"
            className="flex items-center gap-2 text-[#00d4aa] font-bold text-xl tracking-wider"
            style={{ fontFamily: "var(--font-orbitron), sans-serif" }}
          >
            <Cpu className="h-6 w-6" />
            RT Pipeline
          </Link>

          <div className="hidden md:flex items-center gap-1">
            {LINKS.map(({ href, label, icon: Icon }) => {
              const active = isActive(href);
              return (
                <Link
                  key={href}
                  href={href}
                  className={`relative flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    active
                      ? "text-[#00d4aa]"
                      : "text-[#94a3b8] hover:text-[#e2e8f0]"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                  {active && (
                    <span className="absolute bottom-0 left-1/2 -translate-x-1/2 h-0.5 w-6 rounded-full bg-[#00d4aa] shadow-[0_0_10px_rgba(0,212,170,0.6)]" />
                  )}
                </Link>
              );
            })}
          </div>

          <button
            className="md:hidden p-2 rounded-lg text-[#94a3b8] hover:text-[#e2e8f0] hover:bg-white/5 transition-colors"
            aria-label="Toggle menu"
            onClick={() => setOpen((v) => !v)}
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {open && (
        <div className="md:hidden border-t border-white/5 px-4 py-2">
          {LINKS.map(({ href, label, icon: Icon }) => {
            const active = isActive(href);
            return (
              <Link
                key={href}
                href={href}
                onClick={() => setOpen(false)}
                className={`flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  active
                    ? "text-[#00d4aa] bg-[#00d4aa]/10"
                    : "text-[#94a3b8] hover:text-[#e2e8f0] hover:bg-white/5"
                }`}
              >
                <Icon className="h-4 w-4" />
                {label}
              </Link>
            );
          })}
        </div>
      )}
    </nav>
  );
}
