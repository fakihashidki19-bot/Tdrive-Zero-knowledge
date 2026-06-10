"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/axios";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const response = await api.get("/bootstrap/status");
        const status = response.data.data;

        if (!status.is_initialized || !status.is_logged_in) {
          router.replace("/setup");
        } else {
          router.replace("/login");
        }
      } catch (error) {
        console.error("Failed to check system status", error);
        router.replace("/login");
      }
    };

    checkStatus();
  }, [router]);

  return (
    <div className="h-screen w-full flex items-center justify-center bg-background">
       <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin" />
    </div>
  );
}
