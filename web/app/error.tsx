"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[gtrifood] Client error:", error);
  }, [error]);

  const isMissingConfig = error.message?.includes("NEXT_PUBLIC_SUPABASE");

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 p-4 text-center">
      <AlertTriangle className="h-12 w-12 text-destructive" />
      <div className="space-y-2">
        <h1 className="text-2xl font-bold">Algo deu errado</h1>
        {isMissingConfig ? (
          <p className="max-w-md text-muted-foreground">
            Variáveis de ambiente do Supabase não foram configuradas no build.
            <br />
            Defina <code className="rounded bg-muted px-1 py-0.5 text-xs">NEXT_PUBLIC_SUPABASE_URL</code> e{" "}
            <code className="rounded bg-muted px-1 py-0.5 text-xs">NEXT_PUBLIC_SUPABASE_ANON_KEY</code> nos{" "}
            GitHub Secrets e faça um novo deploy.
          </p>
        ) : (
          <p className="max-w-md text-muted-foreground">
            {error.message || "Erro inesperado no cliente."}
          </p>
        )}
      </div>
      <Button onClick={reset} variant="outline">
        <RefreshCw className="mr-2 h-4 w-4" />
        Tentar novamente
      </Button>
    </div>
  );
}
