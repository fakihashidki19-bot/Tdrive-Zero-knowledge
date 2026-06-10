"use client";

import React from "react";
import { Plus, Upload, Loader2, FileUp } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/axios";
import toast from "react-hot-toast";
import { useUIStore } from "@/store/useUIStore";
import { cn } from "@/components/ui";

export function UploadButton({ currentPath }: { currentPath: string }) {
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();
  const { addActiveUpload } = useUIStore();

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("vpath", currentPath);
      
      console.log("UPLOADING_TO_PATH", currentPath);
      
      const response = await api.post("/files/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return response.data.data;
    },
    onSuccess: (jobId) => {
      toast.success("Upload started");
      addActiveUpload(jobId);
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["files", currentPath] });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error?.message || "Upload failed");
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      Array.from(files).forEach(file => {
        uploadMutation.mutate(file);
      });
      e.target.value = "";
    }
  };

  return (
    <div className="relative">
      <input
        type="file"
        multiple
        ref={fileInputRef}
        onChange={handleFileChange}
        className="hidden"
      />
      
      <button
        onClick={() => fileInputRef.current?.click()}
        disabled={uploadMutation.isPending}
        className={cn(
          "flex items-center space-x-3 px-5 h-12 md:h-14 bg-card hover:bg-neutral-50 dark:hover:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-2xl shadow-sm hover:shadow-md transition-all active:scale-95 group",
          uploadMutation.isPending && "opacity-50 cursor-not-allowed"
        )}
      >
        <div className="p-1.5 bg-primary/10 text-primary rounded-lg group-hover:scale-110 transition-transform">
          {uploadMutation.isPending ? (
            <Loader2 size={20} className="animate-spin" />
          ) : (
            <Plus size={24} strokeWidth={2.5} />
          )}
        </div>
        <span className="hidden md:block font-bold text-sm text-neutral-700 dark:text-neutral-300">
          New Upload
        </span>
        <span className="md:hidden font-bold text-sm text-primary">
          Upload
        </span>
      </button>
    </div>
  );
}
