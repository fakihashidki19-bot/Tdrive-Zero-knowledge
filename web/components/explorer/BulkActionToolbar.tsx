"use client";

import React from "react";
import { 
  Download, 
  Star, 
  StarOff, 
  FolderOpen, 
  Trash, 
  X,
  Check
} from "lucide-react";
import { cn } from "@/components/ui";

interface BulkActionToolbarProps {
  selectedCount: number;
  onClear: () => void;
  onDownload: () => void;
  onStar?: () => void;
  onUnstar?: () => void;
  onMove?: () => void;
  onTrash: () => void;
}

export function BulkActionToolbar({
  selectedCount,
  onClear,
  onDownload,
  onStar,
  onUnstar,
  onMove,
  onTrash,
}: BulkActionToolbarProps) {
  if (selectedCount === 0) return null;

  return (
    <div 
      className={cn(
        "fixed left-1/2 -translate-x-1/2 z-[100] flex items-center justify-between",
        "bg-neutral-950/95 dark:bg-neutral-900/95 text-white border border-white/10 shadow-2xl rounded-full p-2 transition-all duration-300",
        "bottom-20 md:bottom-6 w-[92%] sm:w-auto max-w-lg md:max-w-2xl px-3"
      )}
      role="toolbar"
      aria-label="Bulk actions"
    >
      {/* Left section: count & clear */}
      <div className="flex items-center gap-2 border-r border-white/10 pr-3 py-0.5 shrink-0">
        <button 
          onClick={onClear}
          className="p-1 hover:bg-white/10 rounded-full text-neutral-400 hover:text-white transition-colors"
          aria-label="Clear selection"
        >
          <X size={14} />
        </button>
        <span className="bg-primary/20 text-primary text-[11px] font-black px-2 py-0.5 rounded-full min-w-[18px] text-center">
          {selectedCount}
        </span>
        <span className="text-[10px] font-black uppercase tracking-wider text-neutral-400 hidden xs:inline">
          Selected
        </span>
      </div>

      {/* Right section: buttons */}
      <div className="flex items-center gap-1 overflow-x-auto scrollbar-none pl-2">
        <button 
          onClick={onDownload}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-bold text-neutral-300 hover:text-white hover:bg-white/10 active:scale-95 transition-all shrink-0"
          title="Download ZIP"
        >
          <Download size={14} />
          <span className="hidden sm:inline">ZIP</span>
        </button>

        {onStar && (
          <button 
            onClick={onStar}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-bold text-neutral-300 hover:text-white hover:bg-white/10 active:scale-95 transition-all shrink-0"
            title="Star items"
          >
            <Star size={14} />
            <span className="hidden sm:inline">Star</span>
          </button>
        )}

        {onUnstar && (
          <button 
            onClick={onUnstar}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-bold text-neutral-300 hover:text-white hover:bg-white/10 active:scale-95 transition-all shrink-0"
            title="Unstar items"
          >
            <StarOff size={14} />
            <span className="hidden sm:inline">Unstar</span>
          </button>
        )}

        {onMove && (
          <button 
            onClick={onMove}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-bold text-neutral-300 hover:text-white hover:bg-white/10 active:scale-95 transition-all shrink-0"
            title="Move items"
          >
            <FolderOpen size={14} />
            <span className="hidden sm:inline">Move</span>
          </button>
        )}

        <button 
          onClick={onTrash}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-bold text-red-400 hover:text-red-300 hover:bg-red-500/10 active:scale-95 transition-all shrink-0"
          title="Move to Trash"
        >
          <Trash size={14} />
          <span className="hidden sm:inline">Trash</span>
        </button>
      </div>
    </div>
  );
}
