"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { UserButton, useUser, useAuth } from "@clerk/nextjs";
import {
  LayoutDashboard, FileText, Briefcase, Brain,
  BarChart3, Settings, Zap, Bell, Mail, Search, MessageSquare, Calendar, X, Menu
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useResumeBadge } from "@/hooks/useResumeBadge";
import { api } from "@/lib/api";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, exact: true },
  { href: "/resume", label: "Resume Vault", icon: FileText, badge: true },
  { href: "/applications", label: "Applications", icon: Briefcase },
  { href: "/jobs", label: "Job Matches", icon: Search, pro: true },
  { href: "/outreach", label: "Outreach", icon: Mail, pro: true },
  { href: "/intelligence", label: "AI Intelligence", icon: Brain },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/settings", label: "Settings", icon: Settings },
];

// Bottom nav shows most important 5 items on mobile
const bottomNavItems = [
  { href: "/dashboard", label: "Home", icon: LayoutDashboard, exact: true },
  { href: "/resume", label: "Resume", icon: FileText, badge: true },
  { href: "/applications", label: "Apps", icon: Briefcase },
  { href: "/jobs", label: "Jobs", icon: Search },
  { href: "/intelligence", label: "AI", icon: Brain },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user } = useUser();
  const { getToken } = useAuth();
  const showResumeBadge = useResumeBadge();
  const [plan, setPlan] = useState<string>("free");
  const [notifOpen, setNotifOpen] = useState(false);
  const [followUps, setFollowUps] = useState<any[]>([]);
  const [notifLoaded, setNotifLoaded] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);

  // Silently wake up Render server on mount to avoid cold-start delay
  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_API_URL?.replace("/v1", "") || "http://localhost:8000";
    fetch(`${base}/health`, { method: "GET" }).catch(() => {});
  }, []);

  useEffect(() => {
    const fetchPlan = async () => {
      const token = await getToken();
      if (!token) return;
      const resp = await api.getMe(token);
      if (resp.data?.plan) setPlan(resp.data.plan);
    };
    fetchPlan();
  }, [getToken]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setNotifOpen(false);
      }
    };
    if (notifOpen) document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [notifOpen]);

  // Close mobile nav on route change
  useEffect(() => { setMobileNavOpen(false); }, [pathname]);

  const openNotifications = async () => {
    setNotifOpen(v => !v);
    if (notifLoaded) return;
    const token = await getToken();
    if (!token) return;
    const resp = await api.getDashboard(token);
    if (resp.data?.follow_ups) setFollowUps(resp.data.follow_ups);
    setNotifLoaded(true);
  };

  const planLabel = plan === "pro" ? "Pro Plan" : plan === "team" ? "Team Plan" : "Free Plan";

  const SidebarContent = () => (
    <>
      <div className="flex items-center gap-2 px-6 py-5 border-b border-gray-800">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center">
          <Zap className="w-4 h-4 text-white" />
        </div>
        <span className="text-lg font-bold text-white tracking-tight">CareerOS</span>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = item.exact ? pathname === item.href : pathname.startsWith(item.href);
          const hasBadge = item.badge && showResumeBadge;
          return (
            <Link key={item.href} href={item.href}
              className={cn("flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
                isActive ? "bg-violet-600/20 text-violet-300 border border-violet-500/30"
                         : "text-gray-400 hover:text-gray-100 hover:bg-gray-800/60")}>
              <div className="relative">
                <item.icon className="w-4 h-4 shrink-0" />
                {hasBadge && <span className="absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full" />}
              </div>
              {item.label}
              <div className="ml-auto flex items-center gap-1">
                {hasBadge && <span className="text-xs bg-red-500/20 text-red-300 px-1.5 py-0.5 rounded-full">Fix</span>}
                {item.pro && <span className="text-xs bg-violet-500/20 text-violet-300 px-1.5 py-0.5 rounded-full">Pro</span>}
              </div>
            </Link>
          );
        })}
      </nav>

      <div className="px-3 pb-2">
        <Link href="/feedback/product"
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-500 hover:text-gray-300 hover:bg-gray-800/60 transition-all">
          <MessageSquare className="w-4 h-4 shrink-0" />
          Give Feedback
        </Link>
      </div>

      <div className="px-4 py-4 border-t border-gray-800">
        <div className="flex items-center gap-3">
          <UserButton afterSignOutUrl="/" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-200 truncate">{user?.firstName} {user?.lastName}</p>
            <p className="text-xs text-gray-500">{planLabel}</p>
          </div>
        </div>
      </div>
    </>
  );

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100">

      {/* Desktop sidebar */}
      <aside className="hidden md:flex w-64 flex-col border-r border-gray-800 bg-gray-950 shrink-0">
        <SidebarContent />
      </aside>

      {/* Mobile drawer overlay */}
      {mobileNavOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setMobileNavOpen(false)} />
          <aside className="absolute left-0 top-0 h-full w-64 flex flex-col bg-gray-950 border-r border-gray-800 z-50">
            <button
              onClick={() => setMobileNavOpen(false)}
              className="absolute top-4 right-4 text-gray-400 hover:text-gray-100">
              <X className="w-5 h-5" />
            </button>
            <SidebarContent />
          </aside>
        </div>
      )}

      <main className="flex-1 overflow-auto flex flex-col min-w-0">
        <header className="sticky top-0 z-10 flex items-center justify-between px-4 md:px-6 py-4 border-b border-gray-800 bg-gray-950/80 backdrop-blur">
          {/* Hamburger on mobile */}
          <button
            onClick={() => setMobileNavOpen(true)}
            className="md:hidden p-2 rounded-lg text-gray-400 hover:text-gray-100 hover:bg-gray-800">
            <Menu className="w-5 h-5" />
          </button>
          <div className="hidden md:block" />

          <div className="flex items-center gap-3">
            {/* Notification bell */}
            <div className="relative" ref={notifRef}>
              <button
                onClick={openNotifications}
                className={cn(
                  "relative p-2 rounded-lg transition-colors",
                  notifOpen ? "text-gray-100 bg-gray-800" : "text-gray-400 hover:text-gray-100 hover:bg-gray-800"
                )}
              >
                <Bell className="w-4 h-4" />
                {followUps.length > 0 && (
                  <span className="absolute top-1 right-1 w-2 h-2 bg-amber-400 rounded-full" />
                )}
              </button>

              {notifOpen && (
                <div className="absolute right-0 top-10 w-72 bg-gray-900 border border-gray-700 rounded-xl shadow-xl z-50 overflow-hidden">
                  <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
                    <p className="text-sm font-semibold text-gray-200">Follow-ups</p>
                    <button onClick={() => setNotifOpen(false)} className="text-gray-500 hover:text-gray-300">
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <div className="max-h-72 overflow-y-auto">
                    {!notifLoaded ? (
                      <p className="text-xs text-gray-500 text-center py-6">Loading...</p>
                    ) : followUps.length === 0 ? (
                      <div className="px-4 py-6 text-center">
                        <p className="text-sm text-gray-400">No pending follow-ups</p>
                        <p className="text-xs text-gray-600 mt-1">You're all caught up!</p>
                      </div>
                    ) : (
                      followUps.map((fu: any) => {
                        const isOutreach = !fu.application_id;
                        const title = isOutreach
                          ? (fu.message_draft || "").split('\n')[0] || "Outreach follow-up"
                          : fu.applications?.company_name || "Follow-up";
                        const subtitle = isOutreach
                          ? "Send follow-up email"
                          : fu.applications?.role_title || "";
                        return (
                          <div key={fu.id} className="px-4 py-3 border-b border-gray-800/50 last:border-0 hover:bg-gray-800/40 transition-colors">
                            <div className="flex items-start justify-between gap-2">
                              <div className="min-w-0">
                                <p className="text-sm text-gray-200 font-medium truncate">{title}</p>
                                <p className="text-xs text-gray-400 truncate">{subtitle}</p>
                                <p className="flex items-center gap-1 text-xs text-amber-400 mt-1">
                                  <Calendar className="w-3 h-3" />
                                  Due {fu.due_date}
                                </p>
                              </div>
                              {isOutreach && (
                                <span className="shrink-0 text-xs px-1.5 py-0.5 bg-violet-500/20 text-violet-300 rounded border border-violet-500/30">
                                  Outreach
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                  <div className="px-4 py-2.5 border-t border-gray-800">
                    <Link href="/applications" onClick={() => setNotifOpen(false)}
                      className="text-xs text-violet-400 hover:text-violet-300">
                      View all applications →
                    </Link>
                  </div>
                </div>
              )}
            </div>

            {plan !== "pro" && plan !== "team" && (
              <Link href="/pricing"
                className="px-3 py-1.5 text-xs font-semibold bg-gradient-to-r from-violet-600 to-blue-600 text-white rounded-lg hover:opacity-90 transition-opacity">
                Upgrade
              </Link>
            )}
          </div>
        </header>

        {/* Page content — extra bottom padding on mobile for bottom nav */}
        <div className="flex-1 overflow-auto p-4 md:p-6 pb-20 md:pb-6">
          {children}
        </div>
      </main>

      {/* Mobile bottom nav */}
      <nav className="fixed bottom-0 left-0 right-0 z-30 md:hidden bg-gray-950 border-t border-gray-800 flex">
        {bottomNavItems.map((item) => {
          const isActive = item.exact ? pathname === item.href : pathname.startsWith(item.href);
          const hasBadge = item.badge && showResumeBadge;
          return (
            <Link key={item.href} href={item.href}
              className={cn("flex-1 flex flex-col items-center justify-center py-2 gap-0.5 text-xs transition-colors",
                isActive ? "text-violet-400" : "text-gray-500 hover:text-gray-300")}>
              <div className="relative">
                <item.icon className="w-5 h-5" />
                {hasBadge && <span className="absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full" />}
              </div>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
