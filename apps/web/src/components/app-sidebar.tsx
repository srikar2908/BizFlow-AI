"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { LogoutButton } from "@/src/components/logout-button";

const navItems = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/dashboard/documents", label: "Documents" },
  { href: "/dashboard/chat", label: "Chat" },
  { href: "/dashboard/workflows", label: "Workflows" },
  { href: "/dashboard/settings", label: "Settings" },
];

function isActive(pathname: string, href: string) {
  if (href === "/dashboard") {
    return pathname === href;
  }

  return pathname.startsWith(href);
}

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside className="border-b border-slate-200 bg-white px-5 py-5 md:min-h-screen md:w-64 md:border-r md:border-b-0">
      <div className="flex items-center justify-between md:block">
        <Link className="text-lg font-semibold tracking-tight text-slate-950" href="/">
          BizFlow AI
        </Link>
        <span className="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 md:mt-3 md:inline-block">
          Shell
        </span>
      </div>
      <nav className="mt-5 flex gap-2 overflow-x-auto md:flex-col md:overflow-visible">
        {navItems.map((item) => {
          const active = isActive(pathname, item.href);

          return (
            <Link
              className={`whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium transition ${
                active
                  ? "bg-slate-950 text-white"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"
              }`}
              href={item.href}
              key={item.href}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
      <LogoutButton />
    </aside>
  );
}
