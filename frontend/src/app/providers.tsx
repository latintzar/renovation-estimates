"use client";

/**
 * Client-side Providers
 * =====================
 *
 * Wraps the app in all required React contexts.
 * This file is "use client" so the server-component layout can import it.
 */

import { AppStringsProvider } from "@/hooks/AppStringsContext";

export function Providers({ children }: { children: React.ReactNode }) {
  return <AppStringsProvider>{children}</AppStringsProvider>;
}
