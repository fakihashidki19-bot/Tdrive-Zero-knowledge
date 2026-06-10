"use client";

import React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { api } from "@/lib/axios";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { 
  Lock, 
  ShieldCheck, 
  KeyRound, 
  Loader2, 
  Globe, 
  ArrowRight,
  ChevronRight
} from "lucide-react";
import { 
  Button, 
  Input, 
  Form, 
  FormControl, 
  FormField, 
  FormItem, 
  FormLabel, 
  FormMessage 
} from "@/components/ui";

const loginSchema = z.object({
  password: z.string().min(1, "Master Password is required"),
});

export default function LoginPage() {
  const router = useRouter();
  const form = useForm<z.infer<typeof loginSchema>>({
    resolver: zodResolver(loginSchema),
    defaultValues: { password: "" },
  });

  const onSubmit = async (values: z.infer<typeof loginSchema>) => {
    try {
      const response = await api.post("/auth/login", values);
      const { access_token, csrf_token } = response.data.data;

      localStorage.setItem("tdrive_session_token", access_token);
      localStorage.setItem("tdrive_csrf_token", csrf_token);

      toast.success("Identity Verified");
      router.push("/files");
    } catch (error: any) {
      toast.error(error.response?.data?.error?.message || "Verification Failed");
    }
  };

  return (
    <div className="min-h-screen w-full flex flex-col md:flex-row bg-background">
      {/* 1. Left Branding Panel (Desktop Only) */}
      <div className="hidden lg:flex flex-col justify-between w-[40%] bg-neutral-900 p-12 text-white relative overflow-hidden">
        <div className="absolute inset-0 opacity-20 pointer-events-none">
          <div className="absolute top-[-10%] right-[-10%] w-[600px] h-[600px] bg-primary rounded-full blur-[120px]" />
          <div className="absolute bottom-[-10%] left-[-10%] w-[400px] h-[400px] bg-blue-500 rounded-full blur-[100px]" />
        </div>

        <div className="relative z-10 flex items-center space-x-3">
          <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center font-bold text-xl">T</div>
          <span className="text-2xl font-bold tracking-tight">TDrive</span>
        </div>

        <div className="relative z-10 space-y-6">
          <h1 className="text-5xl font-bold leading-tight tracking-tighter">
            Your Personal<br />
            <span className="text-primary">Cloud Fortress.</span>
          </h1>
          <p className="text-neutral-400 text-lg max-w-md leading-relaxed">
            Zero-knowledge encrypted storage powered by Telegram's resilient backend. 
            Privacy isn't a feature, it's our core architecture.
          </p>
          
          <div className="flex items-center space-x-8 pt-4">
            <div className="space-y-1">
              <p className="text-2xl font-bold">AES-256</p>
              <p className="text-xs uppercase font-bold text-neutral-500 tracking-widest">Encryption</p>
            </div>
            <div className="w-px h-10 bg-neutral-800" />
            <div className="space-y-1">
              <p className="text-2xl font-bold">UNLIMITED</p>
              <p className="text-xs uppercase font-bold text-neutral-500 tracking-widest">Storage</p>
            </div>
          </div>
        </div>

        <div className="relative z-10 flex items-center space-x-2 text-xs text-neutral-500 font-bold uppercase tracking-widest">
          <ShieldCheck size={14} className="text-primary" />
          <span>Local decryption only</span>
        </div>
      </div>

      {/* 2. Login Form Area */}
      <div className="flex-1 flex flex-col items-center justify-center p-6 md:p-12 lg:p-24 relative">
        {/* Mobile Logo */}
        <div className="lg:hidden mb-12 flex flex-col items-center space-y-4">
          <div className="w-16 h-16 bg-primary rounded-2xl flex items-center justify-center font-bold text-3xl text-white shadow-xl shadow-primary/20">T</div>
          <h2 className="text-2xl font-bold tracking-tight">TDrive Cloud</h2>
        </div>

        <div className="w-full max-w-sm space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
          <div className="space-y-2 text-center md:text-left">
            <h3 className="text-3xl font-bold tracking-tight">Unlock Drive</h3>
            <p className="text-neutral-500 dark:text-neutral-400 text-sm">
              Enter your Master Password to decrypt your session.
            </p>
          </div>

          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem className="space-y-3">
                    <FormLabel className="text-xs font-bold uppercase tracking-widest text-neutral-400">Master Password</FormLabel>
                    <FormControl>
                      <div className="relative group">
                        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-neutral-400 group-focus-within:text-primary transition-colors">
                          <Lock size={18} />
                        </div>
                        <input
                          type="password"
                          placeholder="••••••••••••"
                          className="w-full h-14 bg-neutral-50 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-2xl pl-12 pr-4 outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all font-mono"
                          {...field}
                        />
                      </div>
                    </FormControl>
                    <FormMessage className="text-xs font-medium" />
                  </FormItem>
                )}
              />

              <Button 
                type="submit" 
                className="w-full h-14 rounded-2xl text-base font-bold shadow-lg shadow-primary/20 group overflow-hidden"
                disabled={form.formState.isSubmitting}
              >
                {form.formState.isSubmitting ? (
                  <Loader2 className="animate-spin" size={20} />
                ) : (
                  <span className="flex items-center justify-center">
                    Access Files
                    <ChevronRight size={18} className="ml-2 group-hover:translate-x-1 transition-transform" />
                  </span>
                )}
              </Button>
            </form>
          </Form>

          <div className="pt-8 grid grid-cols-1 gap-4">
            <div className="p-4 bg-neutral-50 dark:bg-neutral-900 rounded-2xl border border-neutral-100 dark:border-neutral-800 flex items-center space-x-4">
              <div className="p-2 bg-white dark:bg-neutral-800 rounded-lg shadow-sm text-neutral-400">
                <Globe size={18} />
              </div>
              <p className="text-xs text-neutral-500 leading-relaxed font-medium">
                Your data is stored on Telegram servers but only <strong>you</strong> hold the keys.
              </p>
            </div>
          </div>
        </div>

        {/* Footer Link */}
        <footer className="mt-12 md:absolute md:bottom-8 text-center text-xs text-neutral-400 font-medium">
          TDrive Personal Agent v1.3.3 • Built for Privacy • Built with DLA
        </footer>
      </div>
    </div>
  );
}
