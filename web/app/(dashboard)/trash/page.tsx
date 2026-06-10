"use client";

import React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/axios";
import { FileItem as FileType, StructuredResponse } from "@/types";
import { FileItem } from "@/components/explorer/FileItem";
import { useNotificationStore } from "@/store/useNotificationStore";
import { 
  Trash2, 
  Loader2, 
  Search, 
  RotateCcw, 
  Trash,
  Info,
  AlertTriangle
} from "lucide-react";
import { Button, cn } from "@/components/ui";
import toast from "react-hot-toast";

export default function TrashPage() {
  const queryClient = useQueryClient();
  const { confirm, addNotification } = useNotificationStore();

  const { data: trashedFiles, isLoading, error } = useQuery({
    queryKey: ["trash"],
    queryFn: async () => {
      const response = await api.get<StructuredResponse<FileType[]>>("/trash");
      return response.data.data || [];
    },
  });

  const emptyTrashMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post("/trash/cleanup");
      return response.data;
    },
    onSuccess: (data) => {
      toast.success(`Trash emptied: ${data.data} items removed`);
      addNotification({
        type: "success",
        title: "Trash Purged",
        message: `Successfully deleted ${data.data} items permanently.`
      });
      queryClient.invalidateQueries({ queryKey: ["trash"] });
      queryClient.invalidateQueries({ queryKey: ["system-status"] });
    },
    onError: () => toast.error("Failed to empty trash"),
  });

  const handleEmptyTrash = async () => {
    const isConfirmed = await confirm({
      title: "Empty Trash Bin?",
      message: "This will permanently delete ALL items in the trash from Telegram. This action is irreversible.",
      confirmLabel: "Empty Trash Now"
    });
    
    if (isConfirmed) {
      emptyTrashMutation.mutate();
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500 max-w-6xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-card border border-neutral-200 dark:border-neutral-800 p-6 md:p-8 rounded-[2rem] shadow-sm">
        <div className="flex items-center space-x-5">
          <div className="p-4 bg-destructive/10 text-destructive rounded-2xl">
            <Trash2 size={28} />
          </div>
          <div>
            <h1 className="text-3xl font-black tracking-tight">Trash Bin</h1>
            <p className="text-xs text-neutral-400 font-bold uppercase tracking-widest mt-1">Items will be auto-deleted after 30 days</p>
          </div>
        </div>
        
        {trashedFiles && trashedFiles.length > 0 && (
          <Button 
            variant="destructive" 
            className="rounded-xl h-11 font-bold shadow-lg shadow-destructive/10"
            onClick={handleEmptyTrash}
            disabled={emptyTrashMutation.isPending}
          >
            {emptyTrashMutation.isPending ? <Loader2 className="animate-spin" size={18} /> : "Empty Trash Now"}
          </Button>
        )}
      </div>

      {/* Warning Box */}
      <div className="p-4 bg-amber-500/5 border border-amber-500/20 rounded-2xl flex items-center space-x-4 text-left">
         <AlertTriangle className="text-amber-500 shrink-0" size={20} />
         <p className="text-sm font-medium text-amber-700 dark:text-amber-400">
            Deleting files from trash is permanent. They cannot be recovered from Telegram once deleted.
         </p>
      </div>

      {/* Content Area */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-32 text-neutral-400">
          <Loader2 className="animate-spin mb-4" size={40} strokeWidth={1.5} />
          <p className="text-sm font-medium animate-pulse">Scanning trash...</p>
        </div>
      ) : trashedFiles?.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-32 bg-neutral-50/50 dark:bg-neutral-900/20 border-2 border-dashed border-neutral-200 dark:border-neutral-800 rounded-3xl text-neutral-400">
          <Trash size={64} strokeWidth={1} className="mb-4 opacity-20" />
          <p className="text-lg font-medium">Trash is empty</p>
          <p className="text-sm">Nice work keeping things tidy.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-2">
          {trashedFiles?.map((file) => (
            <FileItem 
              key={file.file_id} 
              file={file} 
              viewMode="list" 
              isTrashView={true} 
              currentPath="/trash"
            />
          ))}
        </div>
      )}
    </div>
  );
}
