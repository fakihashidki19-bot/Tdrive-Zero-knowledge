"use client";

import React from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { BottomNav } from "@/components/layout/BottomNav";
import { Header } from "@/components/layout/Header";
import { DialogProvider } from "@/components/notifications/DialogProvider";
import { IntegrityBanner } from "@/components/notifications/IntegrityBanner";
import { FloatingQueue } from "@/components/jobs/FloatingQueue";
import { cn } from "@/components/ui";
import { useUIStore } from "@/store/useUIStore";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { 
    isDesktopSidebarOpen, 
    isMobileMenuOpen, 
    setMobileMenuOpen 
  } = useUIStore();

  return (
    <div className="flex h-screen w-full bg-background overflow-hidden relative font-sans text-neutral-900 dark:text-neutral-100">
      {/* 1. Global Notification & Dialog Layer */}
      <DialogProvider />
      <FloatingQueue />

      {/* 2. MOBILE DRAWER OVERLAY */}
      {isMobileMenuOpen && (
        <div 
          className="fixed inset-0 bg-neutral-900/40 backdrop-blur-[2px] z-[60] md:hidden animate-in fade-in duration-200"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* 3. MOBILE DRAWER */}
      <div className={cn(
        "fixed inset-y-0 left-0 z-[70] w-[260px] bg-card shadow-2xl transform transition-transform duration-300 ease-in-out md:hidden",
        isMobileMenuOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        <Sidebar isMobile={true} />
      </div>

      <div className="flex flex-col flex-1 min-w-0 h-full overflow-hidden">
        {/* 4. HEADER (64px fixed) */}
        <IntegrityBanner />
        <Header />

        <div className="flex flex-1 overflow-hidden">
          {/* 5. DESKTOP SIDEBAR */}
          <div className={cn(
            "hidden md:flex h-full transition-all duration-300 overflow-hidden",
            isDesktopSidebarOpen ? "w-[220px]" : "w-0"
          )}>
            <Sidebar isMobile={false} />
          </div>

          {/* 6. MAIN CONTENT */}
          <main className="flex-1 flex flex-col min-w-0 bg-background relative overflow-hidden">
            <div className="flex-1 overflow-y-auto overflow-x-hidden scroll-smooth pb-20 md:pb-6">
              <div className="w-full max-w-[1600px] mx-auto p-3 md:p-4 lg:p-6">
                {children}
              </div>
            </div>
            
            {/* 7. MOBILE BOTTOM NAV */}
            <BottomNav />
          </main>
        </div>
      </div>
    </div>
  );
}
