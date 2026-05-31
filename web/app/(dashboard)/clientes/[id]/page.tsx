"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Loader2,
  MessageSquare,
  RefreshCw,
  ShoppingBag,
  Star,
  Store,
  Trash2,
  TrendingUp,
  Wallet,
  Zap,
} from "lucide-react";
import { toast } from "sonner";
import { apiDelete, apiGet, apiPost } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import type { Client, Merchant, UserCodeSession } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { StatCard } from "@/components/stat-card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DateRangeFilter,
  presetToDateRange,
  presetToRange,
  type DateRangePreset,
} from "@/components/date-range-filter";

const STATUS_LABEL: Record<
  string,
  { label: string; variant: "default" | "secondary" | "destructive" | "outline" }
> = {
  pending: { label: "Aguardando autorização", variant: "outline" },
  connected: { label: "Conectado", variant: "default" },
  disconnected: { label: "Desconectado", variant: "secondary" },
  error: { label: "Erro", variant: "destructive" },
};

type ReviewsSummary = {
  total: number;
  average_score: number;
  answered_count: number;
  answered_pct: number;
};

export default function ClienteDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const clientId = params.id;

  const [client, setClient] = useState<Client | null>(null);
  const [merchants, setMerchants] = useState<Merchant[]>([]);
  const [ordersTotal, setOrdersTotal] = useState<number | null>(null);
  const [ordersPlaced, setOrdersPlaced] = useState<number | null>(null);
  const [financial, setFinancial] = useState<Record<string, number>>({});
  const [reviews, setReviews] = useState<ReviewsSummary | null>(null);

  const [period, setPeriod] = useState<DateRangePreset>("30d");
  const [loading, setLoading] = useState(true);
  const [reconnecting, setReconnecting] = useState(false);
  const [deleting, setDeleting] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const r = presetToRange(period);
      const dr = presetToDateRange(period);
      const [c, m, ot, op, fs, rs] = await Promise.all([
        apiGet<Client>(`/clients/${clientId}`),
        apiGet<Merchant[]>("/merchants", { client_id: clientId }),
        apiGet<{ count: number }>("/orders/count", {
          client_id: clientId,
          begin: r.begin,
          end: r.end,
        }),
        // "Em aberto" sempre mostra o presente
        apiGet<{ count: number }>("/orders/count", {
          client_id: clientId,
          status: "PLACED",
        }),
        apiGet<Record<string, number>>("/financial/summary", {
          client_id: clientId,
          begin: dr.begin,
          end: dr.end,
        }),
        apiGet<ReviewsSummary>("/reviews/summary", {
          client_id: clientId,
          begin: r.begin,
          end: r.end,
        }),
      ]);
      setClient(c);
      setMerchants(m);
      setOrdersTotal(ot.count);
      setOrdersPlaced(op.count);
      setFinancial(fs);
      setReviews(rs);
    } catch (e: any) {
      toast.error(e?.message ?? "Falha ao carregar dados do cliente");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clientId, period]);

  async function reconnect() {
    if (
      !confirm(
        "Gerar novo código de autorização? O lojista terá que autorizar de novo.",
      )
    )
      return;
    setReconnecting(true);
    try {
      const sess = await apiPost<UserCodeSession>(
        `/clients/${clientId}/connect`,
        {},
      );
      toast.success(`Novo código: ${sess.user_code}`);
      router.push("/clientes/novo?reconnecting=" + clientId);
    } catch (e: any) {
      toast.error(e?.message ?? "Falha ao reconectar");
    } finally {
      setReconnecting(false);
    }
  }

  async function remove() {
    if (
      !confirm(
        "Remover cliente? Isso apaga TODOS os pedidos e dados dele permanentemente.",
      )
    )
      return;
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

  if (loading && !client) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }
  if (!client) return null;

  const s = STATUS_LABEL[client.status] ?? STATUS_LABEL.pending;
  const totalSales = financial.SALE ?? 0;
  const avgTicket =
    ordersTotal && ordersTotal > 0 ? totalSales / ordersTotal : 0;

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
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw
              className={`h-4 w-4 ${loading ? "animate-spin" : ""}`}
            />
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

      {/* ===== Período ===== */}
      <div className="flex justify-end">
        <DateRangeFilter value={period} onChange={setPeriod} />
      </div>

      {/* ===== KPIs ===== */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Pedidos"
          value={ordersTotal ?? "—"}
          icon={ShoppingBag}
          hint={
            ordersPlaced !== null && ordersPlaced > 0
              ? `${ordersPlaced} em aberto`
              : undefined
          }
        />
        <StatCard
          label="Vendas"
          value={formatCurrency(totalSales)}
          icon={Wallet}
          tone="success"
        />
        <StatCard
          label="Ticket médio"
          value={formatCurrency(avgTicket)}
          icon={TrendingUp}
        />
        <StatCard
          label="Reviews"
          value={reviews?.total ?? "—"}
          icon={Star}
          hint={
            reviews && reviews.total > 0
              ? `Média ${reviews.average_score} · ${reviews.answered_pct}% respondidas`
              : undefined
          }
        />
      </div>

      {/* ===== Merchants vinculados ===== */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Store className="h-5 w-5" />
            Restaurantes vinculados ({merchants.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {merchants.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              Nenhum merchant sincronizado ainda. Após o lojista autorizar a
              integração no iFood, os dados aparecem aqui automaticamente.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nome</TableHead>
                  <TableHead>ID iFood</TableHead>
                  <TableHead>CNPJ</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {merchants.map((m) => (
                  <TableRow key={m.id}>
                    <TableCell className="font-medium">{m.name}</TableCell>
                    <TableCell className="font-mono text-xs">
                      {m.ifood_merchant_id}
                    </TableCell>
                    <TableCell className="font-mono text-sm">
                      {m.cnpj || "—"}
                    </TableCell>
                    <TableCell>
                      <Badge variant={m.status === "active" ? "default" : "secondary"}>
                        {m.status === "active" ? "Ativo" : "Inativo"}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* ===== Dados de cadastro ===== */}
      <Card>
        <CardHeader>
          <CardTitle>Dados de cadastro</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-3 sm:grid-cols-2">
            <Field label="ID iFood" value={client.ifood_merchant_id} mono />
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

      {/* ===== Conexão iFood ===== */}
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
