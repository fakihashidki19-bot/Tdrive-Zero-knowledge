"use client";

import React from "react";
import Link from "next/link";
import { ChevronRight, Home, MoreHorizontal } from "lucide-react";
import { cn } from "@/components/ui";

export function Breadcrumbs({ path }: { path: string[] }) {
  const isCollapsed = path.length > 2;
  const visibleSegments = isCollapsed ? path.slice(-2) : path;

  return (
    <nav className="flex items-center space-x-1 text-sm text-neutral-500 font-medium overflow-hidden">
      <Link 
        href="/files" 
        className="p-1 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-md transition-colors flex items-center"
      >
        <Home size={18} strokeWidth={2} />
      </Link>
      
      {isCollapsed && (
        <>
          <ChevronRight size={14} className="text-neutral-300" />
          <button className="p-1 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-md">
            <MoreHorizontal size={14} />
          </button>
        </>
      )}

      {visibleSegments.map((segment, index) => {
        const actualIndex = isCollapsed ? (path.length - 2 + index) : index;
        const href = `/files/${path.slice(0, actualIndex + 1).join("/")}`;
        const isLast = actualIndex === path.length - 1;

        return (
          <React.Fragment key={href}>
            <ChevronRight size={14} className="text-neutral-300 shrink-0" />
            <Link 
              href={href} 
              className={cn(
                "px-1.5 py-1 rounded-md transition-colors truncate max-w-[120px] md:max-w-[200px]",
                isLast 
                  ? "text-neutral-900 dark:text-neutral-100 font-bold" 
                  : "hover:bg-neutral-100 dark:hover:bg-neutral-800"
              )}
            >
              {decodeURIComponent(segment)}
            </Link>
          </React.Fragment>
        );
      })}
    </nav>
  );
}
