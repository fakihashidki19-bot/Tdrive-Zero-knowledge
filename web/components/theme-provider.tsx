"use client"

import * as React from "react"
import { ThemeProvider as NextThemesProvider } from "next-themes"
import { type ThemeProviderProps } from "next-themes/dist/types"
import { useUIStore } from "@/store/useUIStore"

export function ThemeProvider({ children, ...props }: ThemeProviderProps) {
  const { accentColor, density, themeMode } = useUIStore();

  React.useEffect(() => {
    const root = window.document.documentElement;
    
    root.classList.remove("accent-blue", "accent-green", "accent-purple");
    root.classList.add(`accent-${accentColor}`);

    root.classList.remove("density-comfortable", "density-compact");
    root.classList.add(`density-${density}`);
  }, [accentColor, density]);

  return (
    <NextThemesProvider 
      {...props} 
      forcedTheme={themeMode === "system" ? undefined : themeMode}
      attribute="class"
    >
      {children}
    </NextThemesProvider>
  )
}
