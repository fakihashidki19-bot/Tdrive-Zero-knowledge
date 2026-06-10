"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api } from "@/lib/axios";
import { Job, StructuredResponse } from "@/types";

export function useJobs(activeOnly: boolean = false) {
  const [pollInterval, setPollInterval] = useState<number | false>(2000);

  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === "hidden") {
        setPollInterval(30000); 
      } else {
        setPollInterval(2000); 
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, []);

  return useQuery({
    queryKey: ["jobs", activeOnly],
    queryFn: async () => {
      const response = await api.get<StructuredResponse<Job[]>>("/jobs", {
        params: activeOnly ? { status: "running" } : {},
      });
      const jobs = response.data.data || [];
      
      const hasActive = jobs.some(j => j.status === "running" || j.status === "pending");
      if (!hasActive && document.visibilityState === "visible") {
        setPollInterval(10000);
      } else if (hasActive && document.visibilityState === "visible") {
        setPollInterval(2000);
      }

      return jobs;
    },
    refetchInterval: pollInterval,
  });
}
