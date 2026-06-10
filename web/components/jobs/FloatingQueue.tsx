"use client";

import React from "react";
import { useJobs } from "@/hooks/api/useJobs";
import { useUIStore } from "@/store/useUIStore";
import { Progress } from "@/components/ui";
import { X, ChevronUp, ChevronDown, CheckCircle2, AlertCircle, Loader2, ArrowUpCircle } from "lucide-react";
import { cn } from "@/components/ui";

export function FloatingQueue() {
  const [isOpen, setIsOpen] = React.useState(true);
  const { data: jobs } = useJobs(true); 
  const { density } = useUIStore();
  const isCompact = density === "compact";
  const activeCount = jobs?.length || 0;

  if (activeCount === 0) return null;

  return (
    <div className={cn(
      "fixed bottom-20 md:bottom-6 right-4 w-[calc(100%-2rem)] md:w-72 bg-card border border-neutral-200 dark:border-neutral-800 rounded-xl shadow-2xl z-50 overflow-hidden animate-in slide-in-from-right-4 duration-300",
      isCompact ? "md:w-64" : "md:w-72"
    )}>
      <div 
        className={cn(
          "bg-neutral-900 text-white flex justify-between items-center cursor-pointer select-none active:bg-black transition-colors",
          isCompact ? "p-2.5" : "p-3"
        )}
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-center space-x-2">
          <ArrowUpCircle size={14} className={cn(isOpen && "animate-pulse text-primary")} />
          <span className="font-black text-[10px] uppercase tracking-[0.15em]">Tasks ({activeCount})</span>
        </div>
        {isOpen ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
      </div>
      
      {isOpen && (
        <div className={cn(
          "max-h-[50vh] md:max-h-80 overflow-y-auto bg-card/50 backdrop-blur-md scrollbar-none",
          isCompact ? "p-2 space-y-1.5" : "p-3 space-y-2"
        )}>
          {jobs?.map((job) => (
            <div key={job.job_id} className={cn(
              "border border-neutral-100 dark:border-neutral-800 bg-background shadow-sm space-y-2",
              isCompact ? "p-2 rounded-lg" : "p-3 rounded-xl"
            )}>
              <div className="flex justify-between items-center text-[9px] uppercase font-black tracking-tight">
                <span className="truncate max-w-[120px] text-neutral-500">
                  {job.type}ing...
                </span>
                <span className={cn(
                  "px-1 py-0.5 rounded text-[8px] font-black border",
                  job.status === "failed" ? "text-destructive border-destructive/20 bg-destructive/5" : "text-primary border-primary/20 bg-primary/5"
                )}>
                  {job.status}
                </span>
              </div>
              
              <Progress value={job.progress} className="h-1 rounded-full" />
              
              <div className="flex justify-between text-[8px] font-bold font-mono text-neutral-400">
                <span>{job.progress.toFixed(0)}%</span>
                <span>#{job.job_id.slice(0, 6)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
