"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/axios";
import { Button, Input, cn } from "@/components/ui";
import { 
  ShieldCheck, 
  Send, 
  Database, 
  Lock, 
  CheckCircle2, 
  ChevronRight, 
  Loader2,
  AlertCircle,
  Key
} from "lucide-react";
import toast from "react-hot-toast";

type Step = "init" | "login" | "success";

export default function SetupPage() {
  const router = useRouter();
  const [step, setStep] = React.useState<Step>("init");
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // --- Step 1: Init State ---
  const [initForm, setInitForm] = React.useState({
    api_id: "",
    api_hash: "",
    channel_id: "",
    master_password: "",
    confirm_password: ""
  });

  // --- Step 2: Login State ---
  const [loginForm, setLoginForm] = React.useState({
    phone: "",
    code: "",
    phone_code_hash: "",
    password_2fa: ""
  });
  const [isCodeSent, setIsCodeSent] = React.useState(false);
  const [needs2FA, setNeeds2FA] = React.useState(false);

  // Initial check
  React.useEffect(() => {
    const checkStatus = async () => {
      try {
        const resp = await api.get("/bootstrap/status");
        const status = resp.data.data;
        if (status.is_initialized) {
          if (status.is_logged_in) setStep("success");
          else setStep("login");
        }
      } catch (e) {}
    };
    checkStatus();
  }, []);

  const handleInit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (initForm.master_password !== initForm.confirm_password) {
      toast.error("Passwords do not match");
      return;
    }
    
    setLoading(true);
    setError(null);
    try {
      await api.post("/bootstrap/init", {
        api_id: parseInt(initForm.api_id),
        api_hash: initForm.api_hash,
        channel_id: parseInt(initForm.channel_id),
        master_password: initForm.master_password
      });
      toast.success("System initialized!");
      setStep("login");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Initialization failed");
    } finally {
      setLoading(false);
    }
  };

  const handleSendCode = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.post("/bootstrap/send-code", { phone: loginForm.phone });
      setLoginForm({ ...loginForm, phone_code_hash: resp.data.data });
      setIsCodeSent(true);
      toast.success("Verification code sent to Telegram");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to send code");
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const resp = await api.post("/bootstrap/verify-code", {
        phone: loginForm.phone,
        code: loginForm.code,
        phone_code_hash: loginForm.phone_code_hash,
        password: loginForm.password_2fa || null
      });

      if (resp.data.error?.code === "2FA_REQUIRED") {
        setNeeds2FA(true);
        toast.error("Two-factor authentication required");
      } else {
        toast.success("Login successful!");
        setStep("success");
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || "Verification failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full bg-neutral-950 flex items-center justify-center p-4">
      <div className="w-full max-w-xl">
        {/* Progress Tracker */}
        <div className="flex items-center justify-between mb-12 px-6">
          <div className={cn("flex flex-col items-center space-y-2", step === "init" ? "text-primary" : "text-neutral-600")}>
            <div className={cn("w-10 h-10 rounded-full flex items-center justify-center border-2", step === "init" ? "border-primary bg-primary/10" : "border-neutral-800")}>
               <Database size={20} />
            </div>
            <span className="text-[10px] font-black uppercase tracking-widest">Configure</span>
          </div>
          <div className="h-px flex-1 bg-neutral-900 mx-4" />
          <div className={cn("flex flex-col items-center space-y-2", step === "login" ? "text-primary" : "text-neutral-600")}>
            <div className={cn("w-10 h-10 rounded-full flex items-center justify-center border-2", step === "login" ? "border-primary bg-primary/10" : "border-neutral-800")}>
               <Send size={20} />
            </div>
            <span className="text-[10px] font-black uppercase tracking-widest">Connect</span>
          </div>
          <div className="h-px flex-1 bg-neutral-900 mx-4" />
          <div className={cn("flex flex-col items-center space-y-2", step === "success" ? "text-primary" : "text-neutral-600")}>
            <div className={cn("w-10 h-10 rounded-full flex items-center justify-center border-2", step === "success" ? "border-primary bg-primary/10" : "border-neutral-800")}>
               <CheckCircle2 size={20} />
            </div>
            <span className="text-[10px] font-black uppercase tracking-widest">Ready</span>
          </div>
        </div>

        {/* Content Card */}
        <div className="bg-neutral-900/50 border border-neutral-800 rounded-[2.5rem] p-8 md:p-12 shadow-2xl backdrop-blur-xl">
          {error && (
            <div className="mb-8 p-4 bg-destructive/10 border border-destructive/20 rounded-2xl flex items-center space-x-3 text-destructive animate-in slide-in-from-top-2">
               <AlertCircle size={20} />
               <p className="text-sm font-bold">{error}</p>
            </div>
          )}

          {step === "init" && (
            <form onSubmit={handleInit} className="space-y-6 animate-in fade-in duration-500">
              <div className="space-y-2 text-center mb-8">
                <h1 className="text-3xl font-black tracking-tight text-white">Welcome to TDrive</h1>
                <p className="text-neutral-500 font-medium">Let's set up your personal cloud node.</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-[10px] font-black uppercase text-neutral-500 ml-4">API ID</label>
                  <Input 
                    required 
                    placeholder="123456" 
                    className="h-14 rounded-2xl bg-black/40 border-neutral-800"
                    value={initForm.api_id}
                    onChange={(e) => setInitForm({...initForm, api_id: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-black uppercase text-neutral-500 ml-4">API Hash</label>
                  <Input 
                    required 
                    placeholder="abc123..." 
                    className="h-14 rounded-2xl bg-black/40 border-neutral-800"
                    value={initForm.api_hash}
                    onChange={(e) => setInitForm({...initForm, api_hash: e.target.value})}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-[10px] font-black uppercase text-neutral-500 ml-4">Storage Channel ID</label>
                <Input 
                  required 
                  placeholder="-100123456789" 
                  className="h-14 rounded-2xl bg-black/40 border-neutral-800"
                  value={initForm.channel_id}
                  onChange={(e) => setInitForm({...initForm, channel_id: e.target.value})}
                />
              </div>

              <div className="h-px bg-neutral-800 my-4" />

              <div className="space-y-2">
                <label className="text-[10px] font-black uppercase text-primary ml-4">Master Password (Encryption)</label>
                <Input 
                  required 
                  type="password" 
                  placeholder="Set your secure master password" 
                  className="h-14 rounded-2xl bg-black/40 border-primary/20 focus:border-primary"
                  value={initForm.master_password}
                  onChange={(e) => setInitForm({...initForm, master_password: e.target.value})}
                />
              </div>
              <div className="space-y-2">
                <label className="text-[10px] font-black uppercase text-neutral-500 ml-4">Confirm Password</label>
                <Input 
                  required 
                  type="password" 
                  placeholder="Repeat your password" 
                  className="h-14 rounded-2xl bg-black/40 border-neutral-800"
                  value={initForm.confirm_password}
                  onChange={(e) => setInitForm({...initForm, confirm_password: e.target.value})}
                />
              </div>

              <Button 
                disabled={loading}
                className="w-full h-16 rounded-[1.5rem] font-black text-lg shadow-xl shadow-primary/20"
              >
                {loading ? <Loader2 className="animate-spin" /> : "Save Configuration"}
              </Button>
            </form>
          )}

          {step === "login" && (
            <div className="space-y-8 animate-in slide-in-from-right-10 duration-500">
               <div className="space-y-2 text-center">
                <h1 className="text-3xl font-black tracking-tight text-white">Connect Telegram</h1>
                <p className="text-neutral-500 font-medium">Authorize TDrive to access your cloud channel.</p>
              </div>

              {!isCodeSent ? (
                <div className="space-y-6">
                  <div className="space-y-2">
                    <label className="text-[10px] font-black uppercase text-neutral-500 ml-4">Phone Number</label>
                    <Input 
                      placeholder="+62..." 
                      className="h-16 rounded-2xl bg-black/40 border-neutral-800 text-xl font-bold px-6"
                      value={loginForm.phone}
                      onChange={(e) => setLoginForm({...loginForm, phone: e.target.value})}
                    />
                  </div>
                  <Button 
                    onClick={handleSendCode}
                    disabled={loading}
                    className="w-full h-16 rounded-[1.5rem] font-black text-lg shadow-xl shadow-primary/20"
                  >
                    {loading ? <Loader2 className="animate-spin" /> : "Send Verification Code"}
                  </Button>
                </div>
              ) : (
                <form onSubmit={handleVerifyCode} className="space-y-6">
                   <div className="space-y-2">
                    <label className="text-[10px] font-black uppercase text-neutral-500 ml-4">Verification Code</label>
                    <Input 
                      required
                      placeholder="Enter 5-digit code" 
                      className="h-16 rounded-2xl bg-black/40 border-primary/20 text-2xl font-black tracking-[0.5em] text-center"
                      value={loginForm.code}
                      onChange={(e) => setLoginForm({...loginForm, code: e.target.value})}
                    />
                  </div>

                  {needs2FA && (
                    <div className="space-y-2 animate-in zoom-in-95">
                      <label className="text-[10px] font-black uppercase text-amber-500 ml-4">2-Factor Password</label>
                      <Input 
                        required
                        type="password"
                        placeholder="Enter your 2FA password" 
                        className="h-14 rounded-2xl bg-black/40 border-amber-500/20"
                        value={loginForm.password_2fa}
                        onChange={(e) => setLoginForm({...loginForm, password_2fa: e.target.value})}
                      />
                    </div>
                  )}

                  <Button 
                    disabled={loading}
                    className="w-full h-16 rounded-[1.5rem] font-black text-lg shadow-xl shadow-primary/20"
                  >
                    {loading ? <Loader2 className="animate-spin" /> : "Complete Connection"}
                  </Button>
                  <Button variant="ghost" onClick={() => setIsCodeSent(false)} className="w-full h-12 text-neutral-500 font-bold">
                    Use different phone number
                  </Button>
                </form>
              )}
            </div>
          )}

          {step === "success" && (
             <div className="text-center space-y-8 animate-in zoom-in-95 duration-500">
                <div className="w-24 h-24 bg-green-500/10 text-green-500 rounded-[2.5rem] flex items-center justify-center mx-auto shadow-2xl shadow-green-500/20">
                   <ShieldCheck size={48} />
                </div>
                <div className="space-y-2">
                   <h1 className="text-3xl font-black tracking-tight text-white">TDrive is Ready!</h1>
                   <p className="text-neutral-500 font-medium leading-relaxed">
                      Your hybrid agent is fully initialized and connected to Telegram.
                   </p>
                </div>
                <div className="grid grid-cols-2 gap-4">
                   <div className="p-4 bg-neutral-950/50 rounded-2xl border border-neutral-800">
                      <p className="text-[9px] font-black uppercase text-neutral-600 mb-1">Status</p>
                      <p className="text-xs font-bold text-green-500">Connected</p>
                   </div>
                   <div className="p-4 bg-neutral-950/50 rounded-2xl border border-neutral-800">
                      <p className="text-[9px] font-black uppercase text-neutral-600 mb-1">Encryption</p>
                      <p className="text-xs font-bold text-primary">AES-256-GCM</p>
                   </div>
                </div>
                <Button 
                  onClick={() => router.push("/login")}
                  className="w-full h-16 rounded-[1.5rem] font-black text-lg shadow-xl shadow-primary/20 group"
                >
                  <span>Launch Dashboard</span>
                  <ChevronRight className="ml-2 group-hover:translate-x-1 transition-transform" />
                </Button>
             </div>
          )}
        </div>

        {/* Footer */}
        <p className="mt-8 text-center text-[10px] font-black uppercase tracking-[0.3em] text-neutral-700">
           TDrive Unified Agent • Built for Privacy
        </p>
      </div>
    </div>
  );
}
