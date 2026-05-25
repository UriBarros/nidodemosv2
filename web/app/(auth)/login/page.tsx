"use client";

import { useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Loader2, LogIn, UserPlus } from "lucide-react";
import { toast } from "sonner";
import { createClient } from "@/lib/supabase";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    const supabase = createClient();
    try {
      if (mode === "signin") {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        toast.success("Bem-vindo!");
        router.replace("/");
        router.refresh();
      } else {
        const { data, error } = await supabase.auth.signUp({ email, password });
        if (error) throw error;
        if (data.session) {
          toast.success("Conta criada!");
          router.replace("/");
          router.refresh();
        } else {
          toast.info("Verifique seu e-mail pra confirmar a conta.");
          setMode("signin");
        }
      }
    } catch (e: any) {
      toast.error(e?.message ?? "Falha na autenticação");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-primary/5 via-background to-background p-4">
      <Card className="w-full max-w-md shadow-lg">
        <CardHeader className="space-y-3 text-center">
          <Image
            src="/brand/logo.png"
            alt="Aceleradora GTR"
            width={160}
            height={160}
            className="mx-auto h-24 w-auto object-contain"
            priority
          />
          <CardTitle className="text-2xl">gtrifood</CardTitle>
          <CardDescription>
            {mode === "signin" ? "Entre na sua conta" : "Crie sua conta gratuita"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">E-mail</Label>
              <Input
                id="email"
                type="email"
                placeholder="voce@exemplo.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Senha</Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
                autoComplete={mode === "signin" ? "current-password" : "new-password"}
              />
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : mode === "signin" ? (
                <LogIn className="h-4 w-4" />
              ) : (
                <UserPlus className="h-4 w-4" />
              )}
              {mode === "signin" ? "Entrar" : "Criar conta"}
            </Button>
          </form>
          <div className="mt-6 text-center text-sm text-muted-foreground">
            {mode === "signin" ? (
              <>
                Não tem conta?{" "}
                <button
                  className="font-medium text-primary hover:underline"
                  onClick={() => setMode("signup")}
                  type="button"
                >
                  Criar agora
                </button>
              </>
            ) : (
              <>
                Já tem conta?{" "}
                <button
                  className="font-medium text-primary hover:underline"
                  onClick={() => setMode("signin")}
                  type="button"
                >
                  Entrar
                </button>
              </>
            )}
          </div>
          <p className="mt-6 text-center text-xs text-muted-foreground">
            Ao continuar você aceita os{" "}
            <Link href="/termos" className="underline hover:text-foreground">
              Termos de Uso
            </Link>{" "}
            e a{" "}
            <Link href="/privacidade" className="underline hover:text-foreground">
              Política de Privacidade
            </Link>
            .
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
