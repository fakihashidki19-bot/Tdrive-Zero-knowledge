"use client";

import React from "react";
import { Search, Menu, User, Settings as SettingsIcon, Bell } from "lucide-react";
import { useUIStore } from "@/store/useUIStore";
import { useNotificationStore } from "@/store/useNotificationStore";
import { NotificationCenter } from "@/components/notifications/NotificationCenter";
import { cn } from "@/components/ui";

export function Header() {
  const { 
    toggleDesktopSidebar, 
    toggleMobileMenu, 
    searchQuery, 
    setSearchQuery 
  } = useUIStore();
  
  const { unreadCount } = useNotificationStore();
  const [isNotifOpen, setIsNotifOpen] = React.useState(false);

  return (
    <header className="h-[52px] min-h-[52px] border-b bg-card/80 backdrop-blur-md flex items-center px-3 md:px-4 z-40 shrink-0 sticky top-0">
      {/* 1. Brand & Toggle */}
      <div className="flex items-center w-[50px] md:w-[200px] shrink-0">
        <button 
          onClick={() => {
            if (window.innerWidth < 768) toggleMobileMenu();
            else toggleDesktopSidebar();
          }}
          className="p-1.5 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-full transition-colors active:scale-90"
        >
          <Menu size={18} className="text-neutral-600 dark:text-neutral-400" />
        </button>
        <div className="hidden md:flex items-center ml-3 space-x-2">
          <div className="w-7 h-7 bg-primary rounded-lg flex items-center justify-center text-primary-foreground font-black shadow-sm text-xs">T</div>
          <span className="font-black text-lg tracking-tighter text-neutral-800 dark:text-white">TDrive</span>
        </div>
      </div>

      {/* 2. Focused Search Bar */}
      <div className="flex-1 flex justify-center px-2 md:px-6">
        <div className="relative w-full max-w-[640px] group">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-neutral-500 group-focus-within:text-primary transition-colors">
            <Search size={16} />
          </div>
          <input
            type="text"
            placeholder="Search in TDrive"
            className="w-full h-9 bg-neutral-100 dark:bg-neutral-800 border-none focus:bg-card focus:shadow-md focus:ring-1 focus:ring-neutral-200 dark:focus:ring-neutral-700 rounded-lg pl-10 pr-4 text-xs md:text-sm outline-none transition-all placeholder:text-neutral-500 font-medium"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* 3. Global Actions */}
      <div className="flex items-center justify-end w-[50px] md:w-[200px] space-x-1.5 md:space-x-2 shrink-0">
        {/* Notification Bell */}
        <div className="relative">
          <button 
            onClick={() => setIsNotifOpen(true)}
            className="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-full transition-colors relative active:scale-90"
          >
            <Bell size={18} className="text-neutral-600 dark:text-neutral-400" />
            {unreadCount > 0 && (
              <span className="absolute top-1.5 right-1.5 w-3.5 h-3.5 bg-primary text-[7px] font-black text-primary-foreground rounded-full flex items-center justify-center border-2 border-card">
                {unreadCount > 9 ? "9+" : unreadCount}
              </span>
            )}
          </button>
          <NotificationCenter isOpen={isNotifOpen} onClose={() => setIsNotifOpen(false)} />
        </div>

        <button className="hidden md:flex p-2 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-full transition-colors active:scale-90">
          <SettingsIcon size={18} className="text-neutral-600 dark:text-neutral-400" />
        </button>
        
        <div className="w-8 h-8 bg-neutral-200 dark:bg-neutral-800 rounded-full flex items-center justify-center text-neutral-600 dark:text-neutral-300 border border-neutral-300/20 shadow-sm cursor-pointer hover:border-primary/40 transition-colors">
          <User size={16} />
        </div>
      </div>
    </header>
  );
}
