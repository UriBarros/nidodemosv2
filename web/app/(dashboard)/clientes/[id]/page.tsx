"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Loader2, RefreshCw, Trash2, Zap } from "lucide-react";
import { toast } from "sonner";
import { apiDelete, apiGet, apiPost } from "@/lib/api";
import type { Client, UserCodeSession } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

const STATUS_LABEL: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  pending: { label: "Aguardando autorização", variant: "outline" },
  connected: { label: "Conectado", variant: "default" },
  disconnected: { label: "Desconectado", variant: "secondary" },
  error: { label: "Erro", variant: "destructive" },
};

export default function ClienteDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const clientId = params.id;

  const [client, setClient] = useState<Client | null>(null);
  const [loading, setLoading] = useState(true);
  const [reconnecting, setReconnecting] = useState(false);
  const [deleting, setDeleting] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const data = await apiGet<Client>(`/clients/${clientId}`);
      setClient(data);
    } catch (e: any) {
      toast.error(e?.message ?? "Falha ao carregar cliente");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [clientId]);

  async function reconnect() {
    if (!confirm("Gerar novo código de autorização? O lojista terá que autorizar de novo.")) {
      return;
    }
    setReconnecting(true);
    try {
      const sess = await apiPost<UserCodeSession>(`/clients/${clientId}/connect`, {});
      toast.success(`Novo código: ${sess.user_code}`);
      // Redirect pro fluxo de connect — usa novo (poderíamos ter URL própria)
      router.push("/clientes/novo?reconnecting=" + clientId);
    } catch (e: any) {
      toast.error(e?.message ?? "Falha ao reconectar");
    } finally {
      setReconnecting(false);
    }
  }

  async function remove() {
    if (!confirm("Remover cliente? Isso apaga TODOS os pedidos e dados dele permanentemente.")) {
      return;
    }
    setDeleting(true);
    try {
      await apiDelete(`/clients/${clientId}`);
      toast.success("Cliente removido");
      router.push("/clientes");
    } catch (e: any) {
      toast.error(e?.message ?? "Falha ao remover");
      setDeleting(false);
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }
  if (!client) return null;

  const s = STATUS_LABEL[client.status] ?? STATUS_LABEL.pending;

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" asChild className="-ml-3">
        <Link href="/clientes">
          <ArrowLeft className="h-4 w-4" />
          Voltar
        </Link>
      </Button>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{client.name}</h1>
          {client.legal_name && (
            <p className="text-muted-foreground">{client.legal_name}</p>
          )}
          <div className="mt-2">
            <Badge variant={s.variant}>{s.label}</Badge>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load}>
            <RefreshCw className="h-4 w-4" />
            Atualizar
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={reconnect}
            disabled={reconnecting}
          >
            <Zap className="h-4 w-4" />
            Reconectar
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={remove}
            disabled={deleting}
          >
            <Trash2 className="h-4 w-4" />
            Remover
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Dados de cadastro</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-3 sm:grid-cols-2">
            <Field label="CNPJ" value={client.cnpj} mono />
            <Field label="Telefone" value={client.phone} />
            <Field label="E-mail" value={client.email} />
            <Field label="Razão social" value={client.legal_name} />
          </dl>
          {client.notes && (
            <>
              <Separator className="my-4" />
              <Field label="Observações" value={client.notes} />
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Conexão iFood</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-3 sm:grid-cols-2">
            <Field
              label="Conectado em"
              value={
                client.connected_at
                  ? new Date(client.connected_at).toLocaleString("pt-BR")
                  : null
              }
            />
            <Field
              label="Desconectado em"
              value={
                client.disconnected_at
                  ? new Date(client.disconnected_at).toLocaleString("pt-BR")
                  : null
              }
            />
            <Field
              label="Cadastrado em"
              value={new Date(client.created_at).toLocaleString("pt-BR")}
            />
            <Field
              label="Última atualização"
              value={new Date(client.updated_at).toLocaleString("pt-BR")}
            />
          </dl>
          {client.last_error && (
            <>
              <Separator className="my-4" />
              <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
                <span className="font-medium">Último erro:</span>{" "}
                {client.last_error}
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Field({
  label,
  value,
  mono,
}: {
  label: string;
  value: string | null | undefined;
  mono?: boolean;
}) {
  return (
    <div>
      <dt className="text-xs uppercase text-muted-foreground">{label}</dt>
      <dd className={`mt-1 ${mono ? "font-mono text-sm" : ""}`}>
        {value || "—"}
      </dd>
    </div>
  );
}
