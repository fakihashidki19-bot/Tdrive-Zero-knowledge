"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/axios";
import { FileItem, StructuredResponse } from "@/types";

export function useFiles(path: string = "/") {
  return useQuery({
    queryKey: ["files", path],
    queryFn: async () => {
      const response = await api.get<StructuredResponse<FileItem[]>>("/files", {
        params: { path },
      });
      return response.data.data || [];
    },
    staleTime: 10000,
  });
}
