"use client";

import { useState, useCallback } from "react";
import { api } from "@/lib/axios";
import { useUIStore } from "@/store/useUIStore";
import toast from "react-hot-toast";

export function useUploadQueue() {
  const [isUploading, setIsUploading] = useState(false);
  const addActiveUpload = useUIStore((state) => state.addActiveUpload);

  const uploadFiles = useCallback(async (files: File[], virtualPath: string = "/") => {
    setIsUploading(true);
    
    const MAX_CONCURRENT = 2;
    const queue = [...files];
    const active = new Set<Promise<void>>();

    const processNext = async (): Promise<void> => {
      if (queue.length === 0) return;

      const file = queue.shift()!;
      const formData = new FormData();
      formData.append("file", file);
      formData.append("vpath", virtualPath);

      const task = (async () => {
        try {
          const response = await api.post("/files/upload", formData, {
            headers: { "Content-Type": "multipart/form-data" },
          });
          if (response.data.success) {
            addActiveUpload(response.data.data);
          }
        } catch (error: any) {
          toast.error(`Failed to initiate upload for ${file.name}`);
        }
      })();

      active.add(task);
      task.finally(() => active.delete(task));

      if (queue.length > 0) {
        await processNext();
      }
    };

    const initialTasks = [];
    for (let i = 0; i < Math.min(MAX_CONCURRENT, queue.length); i++) {
      initialTasks.push(processNext());
    }

    await Promise.all(initialTasks);
    setIsUploading(false);
    toast.success(`${files.length} upload jobs initiated.`);
  }, [addActiveUpload]);

  return { uploadFiles, isUploading };
}
