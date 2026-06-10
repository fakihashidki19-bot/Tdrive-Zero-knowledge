"use client";

import React from "react";
import { useNotificationStore, Notification } from "@/store/useNotificationStore";
import { 
  Bell, 
  X, 
  CheckCircle2, 
  AlertCircle, 
  Info, 
  AlertTriangle,
  Trash,
  Check
} from "lucide-react";
import { Button, cn } from "@/components/ui";
import { formatDistanceToNow } from "date-fns";

export function NotificationCenter({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const { notifications, unreadCount, markAsRead, markAllAsRead, clearAll } = useNotificationStore();

  const getIcon = (type: string) => {
    switch (type) {
      case "success": return <CheckCircle2 className="text-green-500" size={18} />;
      case "error": return <AlertCircle className="text-destructive" size={18} />;
      case "warning": return <AlertTriangle className="text-yellow-500" size={18} />;
      default: return <Info className="text-blue-500" size={18} />;
    }
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-[100] bg-neutral-950/20 backdrop-blur-[1px] md:bg-transparent md:backdrop-blur-0" onClick={onClose} />
      
      {/* Drawer */}
      <div className="fixed inset-y-0 right-0 z-[110] w-full max-w-[320px] bg-background shadow-2xl border-l border-neutral-200 dark:border-neutral-800 animate-in slide-in-from-right duration-300 flex flex-col">
        <div className="p-4 border-b flex items-center justify-between bg-neutral-50/50 dark:bg-neutral-900/50">
          <div>
            <h2 className="text-lg font-black tracking-tight">Notifications</h2>
            <p className="text-[9px] font-bold text-neutral-400 uppercase tracking-widest mt-0.5">
              {unreadCount} unread
            </p>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-neutral-200 dark:hover:bg-neutral-800 rounded-full transition-colors">
            <X size={18} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {notifications.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-neutral-400 opacity-30 space-y-3">
               <Bell size={48} strokeWidth={1} />
               <p className="font-bold uppercase tracking-widest text-[10px]">All caught up</p>
            </div>
          ) : (
            notifications.map((notif) => (
              <div 
                key={notif.id}
                onClick={() => !notif.read && markAsRead(notif.id)}
                className={cn(
                  "p-3 rounded-xl border transition-all cursor-pointer group relative overflow-hidden",
                  notif.read 
                    ? "bg-card border-neutral-100 dark:border-neutral-800 grayscale-[0.5]" 
                    : "bg-primary/[0.03] border-primary/20 shadow-sm"
                )}
              >
                {!notif.read && <div className="absolute top-0 left-0 w-0.5 h-full bg-primary" />}
                
                <div className="flex items-start space-x-3">
                  <div className="p-1.5 bg-background rounded-lg shadow-sm shrink-0">
                     {getIcon(notif.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-bold text-xs leading-tight mb-0.5 truncate">{notif.title}</p>
                    <p className="text-[11px] text-neutral-500 font-medium leading-tight line-clamp-2">{notif.message}</p>
                    <p className="text-[9px] text-neutral-400 mt-1.5 font-bold uppercase tracking-tighter">
                      {formatDistanceToNow(notif.timestamp, { addSuffix: true })}
                    </p>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {notifications.length > 0 && (
          <div className="p-3 border-t grid grid-cols-2 gap-2 bg-neutral-50/50 dark:bg-neutral-900/50">
            <Button variant="outline" className="rounded-lg h-9 text-[10px] font-bold" onClick={markAllAsRead}>
               <Check size={14} className="mr-1.5" />
               Read All
            </Button>
            <Button variant="ghost" className="rounded-lg h-9 text-[10px] font-bold text-neutral-500" onClick={clearAll}>
               <Trash size={14} className="mr-1.5" />
               Clear
            </Button>
          </div>
        )}
      </div>
    </>
  );
}
