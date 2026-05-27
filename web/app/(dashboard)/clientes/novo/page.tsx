"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Copy,
  ExternalLink,
  Loader2,
  Store,
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

// UUID v4 leve (não-estrito): 8-4-4-4-12 chars hex
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export default function NovoClientePage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("form");

  const [form, setForm] = useState<ClientIn>({ name: "", ifood_merchant_id: "" });
  const [showOptionals, setShowOptionals] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const [session, setSession] = useState<UserCodeSession | null>(null);
  const [clientId, setClientId] = useState<string | null>(null);
  const [pollStatus, setPollStatus] = useState<UserCodePoll | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.ifood_merchant_id?.trim()) {
      toast.error("ID do merchant iFood é obrigatório");
      return;
    }
    if (!UUID_RE.test(form.ifood_merchant_id.trim())) {
      toast.error("ID do merchant iFood deve ser um UUID válido");
      return;
    }
    if (!form.name?.trim()) {
      // Auto-preenche apelido com prefixo do UUID se vazio
      form.name = `Cliente ${form.ifood_merchant_id.slice(0, 8)}`;
    }

    setSubmitting(true);
    try {
      const sess = await apiPost<UserCodeSession>("/clients", {
        ...form,
        ifood_merchant_id: form.ifood_merchant_id.trim(),
        name: form.name.trim(),
      });
      setSession(sess);
      setClientId(sess.client_id);
      setStep("connect");
    } catch (e: any) {
      toast.error(e?.message ?? "Falha ao criar cliente");
    } finally {
      setSubmitting(false);
    }
  }

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
          toast.success(res.message ?? "Cliente conectado!");
        } else if (res.status === "expired" || res.status === "error") {
          setStep("error");
          setErrorMsg(res.message ?? "Erro desconhecido");
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        }
      } catch (e) {
        console.warn("poll falhou:", e);
      }
    }

    poll();
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
            <CardTitle className="flex items-center gap-2">
              <Store className="h-5 w-5" />
              Adicionar restaurante
            </CardTitle>
            <CardDescription>
              Cola o <strong>ID do merchant iFood</strong> do cliente. Depois o lojista
              confirma a integração no Portal iFood dele.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="ifood_merchant_id">
                  ID do iFood <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="ifood_merchant_id"
                  required
                  placeholder="e51f621f-7674-47c1-8a3e-986663c563ae"
                  value={form.ifood_merchant_id ?? ""}
                  onChange={(e) =>
                    setForm({ ...form, ifood_merchant_id: e.target.value })
                  }
                  className="font-mono"
                  autoFocus
                />
                <p className="text-xs text-muted-foreground">
                  UUID do merchant no Portal iFood Gestor (formato:{" "}
                  <code className="font-mono">8-4-4-4-12</code>).
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="name">Apelido</Label>
                <Input
                  id="name"
                  placeholder="Pizzaria do Zé"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                />
                <p className="text-xs text-muted-foreground">
                  Nome interno pra organizar. Se deixar vazio, gera automático.
                </p>
              </div>

              <button
                type="button"
                onClick={() => setShowOptionals(!showOptionals)}
                className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
              >
                {showOptionals ? (
                  <ChevronUp className="h-4 w-4" />
                ) : (
                  <ChevronDown className="h-4 w-4" />
                )}
                Dados adicionais (opcional)
              </button>

              {showOptionals && (
                <div className="space-y-4 rounded-md border border-border/50 bg-muted/20 p-4">
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
                      <Label htmlFor="phone">Telefone</Label>
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
                </div>
              )}

              <Button type="submit" disabled={submitting} className="w-full">
                {submitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  "Adicionar restaurante e gerar código"
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {step === "connect" && session && (
        <Card>
          <CardHeader>
            <CardTitle>Confirmar no Portal iFood</CardTitle>
            <CardDescription>
              O lojista precisa abrir o link abaixo e autorizar a integração. Vamos
              detectar automaticamente.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="rounded-lg border-2 border-dashed border-primary/30 bg-primary/5 p-6 text-center">
              <Label className="text-xs uppercase text-muted-foreground">
                Código de autorização
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
                Manda link via WhatsApp. Lojista abre, faz login iFood, confirma na aba
                Integrações. Pronto.
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
              Expira em: {new Date(session.expires_at).toLocaleString("pt-BR")}
            </div>
          </CardContent>
        </Card>
      )}

      {step === "done" && (
        <Card>
          <CardHeader className="text-center">
            <CheckCircle2 className="mx-auto h-16 w-16 text-green-600" />
            <CardTitle className="mt-4">Restaurante conectado!</CardTitle>
            <CardDescription>
              {pollStatus?.message ?? "Integração ativa. Sincronizando dados."}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex justify-center gap-2">
            <Button asChild>
              <Link href="/clientes">Ver lista</Link>
            </Button>
            {clientId && (
              <Button variant="outline" asChild>
                <Link href={`/clientes/${clientId}`}>Detalhes</Link>
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
