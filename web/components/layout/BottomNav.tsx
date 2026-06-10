"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  Folder, 
  Clock, 
  Settings
} from "lucide-react";
import { cn } from "@/components/ui";

export function BottomNav() {
  const pathname = usePathname();

  const items = [
    { name: "Files", href: "/files", icon: Folder },
    { name: "Jobs", href: "/jobs", icon: Clock },
    { name: "Settings", href: "/settings", icon: Settings },
  ];

  return (
    <nav className="fixed bottom-0 left-0 right-0 h-[64px] bg-card/80 backdrop-blur-lg border-t z-50 md:hidden flex items-center justify-around px-4 pb-[env(safe-area-inset-bottom)]">
      {items.map((item) => {
        const isActive = pathname.startsWith(item.href);
        return (
          <Link
            key={item.name}
            href={item.href}
            className={cn(
              "flex flex-col items-center justify-center space-y-1 w-16 h-full transition-all active:scale-90",
              isActive ? "text-primary" : "text-neutral-500 dark:text-neutral-400"
            )}
          >
            <div className={cn(
              "p-1.5 rounded-full transition-colors",
              isActive && "bg-primary/10"
            )}>
              <item.icon size={22} strokeWidth={isActive ? 2.5 : 2} />
            </div>
            <span className={cn(
              "text-[10px] font-bold uppercase tracking-tighter transition-all",
              isActive ? "opacity-100" : "opacity-70"
            )}>
              {item.name}
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
