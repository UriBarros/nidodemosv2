"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  CheckCircle2,
  Copy,
  ExternalLink,
  Loader2,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";
import { apiGet, apiPost } from "@/lib/api";
import type { ClientIn, UserCodePoll, UserCodeSession } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type Step = "form" | "connect" | "done" | "error";

export default function NovoClientePage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("form");

  // Form
  const [form, setForm] = useState<ClientIn>({ name: "" });
  const [submitting, setSubmitting] = useState(false);

  // Sessão userCode
  const [session, setSession] = useState<UserCodeSession | null>(null);
  const [clientId, setClientId] = useState<string | null>(null);
  const [pollStatus, setPollStatus] = useState<UserCodePoll | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // ---- Step 1: cria cliente + dispara userCode ----
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim()) {
      toast.error("Nome é obrigatório");
      return;
    }
    setSubmitting(true);
    try {
      const sess = await apiPost<UserCodeSession>("/clients", form);
      setSession(sess);
      setClientId(sess.client_id);
      setStep("connect");
    } catch (e: any) {
      toast.error(e?.message ?? "Falha ao criar cliente");
    } finally {
      setSubmitting(false);
    }
  }

  // ---- Step 2: polling a cada 5s ----
  useEffect(() => {
    if (step !== "connect" || !clientId) return;

    let canceled = false;
    async function poll() {
      try {
        const res = await apiGet<UserCodePoll>(`/clients/${clientId}/poll`);
        if (canceled) return;
        setPollStatus(res);
        if (res.status === "authorized") {
          setStep("done");
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          toast.success("Cliente conectado!");
        } else if (res.status === "expired" || res.status === "error") {
          setStep("error");
          setErrorMsg(res.message ?? "Erro desconhecido");
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        }
      } catch (e: any) {
        // Erro intermitente — continua tentando
        console.warn("poll falhou:", e);
      }
    }

    poll(); // primeira chamada imediata
    pollIntervalRef.current = setInterval(poll, 5000);

    return () => {
      canceled = true;
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [step, clientId]);

  function copyUserCode() {
    if (!session) return;
    navigator.clipboard.writeText(session.user_code);
    toast.success("Código copiado");
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Button variant="ghost" size="sm" asChild className="-ml-3">
        <Link href="/clientes">
          <ArrowLeft className="h-4 w-4" />
          Voltar
        </Link>
      </Button>

      {step === "form" && (
        <Card>
          <CardHeader>
            <CardTitle>Novo cliente</CardTitle>
            <CardDescription>
              Cadastra os dados do lojista. Depois geramos um código que ele
              precisa autorizar no Portal iFood dele.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Nome do estabelecimento *</Label>
                <Input
                  id="name"
                  required
                  placeholder="Pizzaria do Zé"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="cnpj">CNPJ</Label>
                  <Input
                    id="cnpj"
                    placeholder="00.000.000/0001-00"
                    value={form.cnpj ?? ""}
                    onChange={(e) => setForm({ ...form, cnpj: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="phone">Telefone / WhatsApp</Label>
                  <Input
                    id="phone"
                    placeholder="(11) 99999-9999"
                    value={form.phone ?? ""}
                    onChange={(e) => setForm({ ...form, phone: e.target.value })}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="legal_name">Razão social</Label>
                <Input
                  id="legal_name"
                  placeholder="Pizzaria do Zé LTDA"
                  value={form.legal_name ?? ""}
                  onChange={(e) => setForm({ ...form, legal_name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">E-mail</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="contato@pizzaria.com"
                  value={form.email ?? ""}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="notes">Observações internas</Label>
                <Input
                  id="notes"
                  placeholder="Plano, comissão, etc"
                  value={form.notes ?? ""}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                />
              </div>
              <Button type="submit" disabled={submitting} className="w-full">
                {submitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  "Cadastrar e gerar código"
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {step === "connect" && session && (
        <Card>
          <CardHeader>
            <CardTitle>Conectar com iFood</CardTitle>
            <CardDescription>
              Envia o código abaixo pro lojista. Ele precisa colar no Portal
              iFood dele e autorizar. Vamos detectar automaticamente.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="rounded-lg border-2 border-dashed border-primary/30 bg-primary/5 p-6 text-center">
              <Label className="text-xs uppercase text-muted-foreground">
                Código do lojista
              </Label>
              <div className="my-3 font-mono text-4xl font-bold tracking-widest text-primary">
                {session.user_code}
              </div>
              <Button variant="outline" size="sm" onClick={copyUserCode}>
                <Copy className="h-4 w-4" />
                Copiar código
              </Button>
            </div>

            <div className="space-y-2">
              <Label className="text-xs uppercase text-muted-foreground">
                Link para o lojista
              </Label>
              <div className="flex gap-2">
                <Input
                  readOnly
                  value={session.verification_url_complete ?? session.verification_url}
                  className="font-mono text-xs"
                />
                <Button variant="outline" asChild>
                  <a
                    href={session.verification_url_complete ?? session.verification_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <ExternalLink className="h-4 w-4" />
                  </a>
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Manda esse link via WhatsApp. Lojista abre, faz login iFood,
                autoriza. Pronto.
              </p>
            </div>

            <div className="flex items-center gap-3 rounded-md bg-muted/40 p-3 text-sm">
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
              <div>
                <div className="font-medium">Aguardando autorização do lojista…</div>
                <div className="text-xs text-muted-foreground">
                  {pollStatus?.message ?? "Verificando a cada 5s."}
                  {pollStatus && ` (poll #${session.poll_count + 1})`}
                </div>
              </div>
            </div>

            <div className="text-xs text-muted-foreground">
              Expira em:{" "}
              {new Date(session.expires_at).toLocaleString("pt-BR")}
            </div>
          </CardContent>
        </Card>
      )}

      {step === "done" && (
        <Card>
          <CardHeader className="text-center">
            <CheckCircle2 className="mx-auto h-16 w-16 text-green-600" />
            <CardTitle className="mt-4">Cliente conectado!</CardTitle>
            <CardDescription>
              O lojista autorizou. Já estamos sincronizando merchants e pedidos.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex justify-center gap-2">
            <Button asChild>
              <Link href="/clientes">Ver lista de clientes</Link>
            </Button>
            {clientId && (
              <Button variant="outline" asChild>
                <Link href={`/clientes/${clientId}`}>Detalhes deste cliente</Link>
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {step === "error" && (
        <Card>
          <CardHeader className="text-center">
            <XCircle className="mx-auto h-16 w-16 text-destructive" />
            <CardTitle className="mt-4">Algo deu errado</CardTitle>
            <CardDescription>{errorMsg ?? "Erro desconhecido"}</CardDescription>
          </CardHeader>
          <CardContent className="flex justify-center gap-2">
            <Button onClick={() => router.refresh()}>Tentar de novo</Button>
            <Button variant="outline" asChild>
              <Link href="/clientes">Voltar pra lista</Link>
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
