"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Ban,
  CheckCircle2,
  Loader2,
  PackageCheck,
  Truck,
} from "lucide-react";
import { toast } from "sonner";
import { apiGet, apiPost } from "@/lib/api";
import { formatCurrency, formatDateTime } from "@/lib/utils";
import type { Merchant, Order, OrderEvent, OrderStatus } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { OrderStatusBadge } from "@/components/order-status-badge";
import { ClientFilter } from "@/components/client-filter";

const STATUS_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "all", label: "Todos" },
  { value: "PLACED", label: "Recebido" },
  { value: "CONFIRMED", label: "Confirmado" },
  { value: "READY_FOR_PICKUP", label: "Pronto" },
  { value: "DISPATCHED", label: "A caminho" },
  { value: "CONCLUDED", label: "Concluído" },
  { value: "CANCELLED", label: "Cancelado" },
];

export default function PedidosPage() {
  const qc = useQueryClient();
  const [clientId, setClientId] = useState<string | null>(null);
  const [merchantId, setMerchantId] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const merchants = useQuery({
    queryKey: ["merchants"],
    queryFn: () => apiGet<Merchant[]>("/merchants"),
  });

  const orders = useQuery({
    queryKey: ["orders", clientId, merchantId, statusFilter],
    queryFn: () =>
      apiGet<Order[]>("/orders", {
        client_id: clientId ?? undefined,
        merchant_id: merchantId === "all" ? undefined : merchantId,
        status: statusFilter === "all" ? undefined : statusFilter,
        limit: 100,
      }),
  });

  const selected = useMemo(
    () => orders.data?.find((o) => o.id === selectedId) ?? null,
    [orders.data, selectedId],
  );

  const events = useQuery({
    queryKey: ["order-events", selectedId],
    queryFn: () => apiGet<OrderEvent[]>(`/orders/${selectedId}/events`),
    enabled: !!selectedId,
  });

  const action = useMutation({
    mutationFn: ({ id, kind, reason }: { id: string; kind: "confirm" | "dispatch" | "ready-to-pickup" | "cancel"; reason?: string }) => {
      const params = kind === "cancel" ? { reason: reason ?? "Cancelamento solicitado", code: "501" } : undefined;
      return apiPost<{ message: string }>(`/orders/${id}/${kind}`, undefined, params);
    },
    onSuccess: (data) => {
      toast.success(data.message);
      setTimeout(() => qc.invalidateQueries({ queryKey: ["orders"] }), 1500);
      setTimeout(() => qc.invalidateQueries({ queryKey: ["order-events"] }), 1500);
    },
    onError: (e: any) => toast.error(e?.message ?? "Falha"),
  });

  const totalDisplay = orders.data?.reduce((acc, o) => acc + Number(o.total_amount ?? 0), 0) ?? 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Pedidos</h1>
        <p className="text-sm text-muted-foreground">
          {orders.data?.length ?? 0} pedido(s) · Total {formatCurrency(totalDisplay)}
        </p>
      </div>

      {/* Filtros */}
      <Card>
        <CardContent className="flex flex-wrap items-end gap-4 p-4">
          <div className="min-w-[260px] space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Cliente</label>
            <ClientFilter value={clientId} onChange={setClientId} />
          </div>
          <div className="min-w-[200px] space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Merchant</label>
            <Select value={merchantId} onValueChange={setMerchantId}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                {merchants.data?.map((m) => (
                  <SelectItem key={m.id} value={m.id}>
                    {m.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="min-w-[160px] space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Status</label>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Tabela */}
      <Card>
        <CardContent className="p-0">
          {orders.isLoading ? (
            <div className="flex h-40 items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : orders.data?.length ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nº</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Total</TableHead>
                  <TableHead>Cliente</TableHead>
                  <TableHead>Criado</TableHead>
                  <TableHead>Atualizado</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {orders.data.map((o) => (
                  <TableRow
                    key={o.id}
                    onClick={() => setSelectedId(o.id)}
                    className={`cursor-pointer ${selectedId === o.id ? "bg-muted" : ""}`}
                  >
                    <TableCell className="font-medium">
                      <a
                        href={`/pedidos/${o.id}`}
                        onClick={(e) => e.stopPropagation()}
                        className="hover:underline"
                      >
                        #{o.display_id ?? "—"}
                      </a>
                    </TableCell>
                    <TableCell>
                      <OrderStatusBadge status={o.status as OrderStatus} />
                    </TableCell>
                    <TableCell className="text-muted-foreground">{o.order_type ?? "—"}</TableCell>
                    <TableCell className="font-medium">{formatCurrency(o.total_amount)}</TableCell>
                    <TableCell>{o.customer_name ?? "—"}</TableCell>
                    <TableCell className="text-muted-foreground">{formatDateTime(o.created_at_ifood)}</TableCell>
                    <TableCell className="text-muted-foreground">{formatDateTime(o.updated_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">
              Nenhum pedido com esses filtros.
            </div>
          )}
        </CardContent>
      </Card>

      {/* Detalhe do pedido selecionado */}
      {selected && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-4">
            <CardTitle>
              Pedido #{selected.display_id ?? selected.ifood_order_id.slice(0, 8)}
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                ({selected.status})
              </span>
            </CardTitle>
            <div className="flex flex-wrap items-center gap-2">
              {selected.status === "PLACED" && (
                <>
                  <Button
                    size="sm"
                    onClick={() => action.mutate({ id: selected.id, kind: "confirm" })}
                    disabled={action.isPending}
                  >
                    <CheckCircle2 className="h-4 w-4" /> Confirmar
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => action.mutate({ id: selected.id, kind: "ready-to-pickup" })}
                    disabled={action.isPending}
                  >
                    <PackageCheck className="h-4 w-4" /> Pronto
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => action.mutate({ id: selected.id, kind: "dispatch" })}
                    disabled={action.isPending}
                  >
                    <Truck className="h-4 w-4" /> Despachar
                  </Button>
                </>
              )}
              {(selected.status === "CONFIRMED" || selected.status === "READY_FOR_PICKUP") && (
                <Button
                  size="sm"
                  onClick={() => action.mutate({ id: selected.id, kind: "dispatch" })}
                  disabled={action.isPending}
                >
                  <Truck className="h-4 w-4" /> Despachar
                </Button>
              )}
              {!["CONCLUDED", "CANCELLED"].includes(selected.status) && (
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={() => {
                    const reason = prompt("Motivo do cancelamento:");
                    if (reason) action.mutate({ id: selected.id, kind: "cancel", reason });
                  }}
                  disabled={action.isPending}
                >
                  <Ban className="h-4 w-4" /> Cancelar
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            <h3 className="mb-2 text-sm font-semibold">Timeline</h3>
            {events.isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            ) : events.data?.length ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Recebido</TableHead>
                    <TableHead>Código</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Confirmado ao iFood</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {events.data.map((e) => (
                    <TableRow key={e.id}>
                      <TableCell>{formatDateTime(e.received_at)}</TableCell>
                      <TableCell className="font-mono">{e.code}</TableCell>
                      <TableCell>{e.full_code ?? "—"}</TableCell>
                      <TableCell>{formatDateTime(e.acknowledged_at)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <p className="text-sm text-muted-foreground">Nenhum evento registrado.</p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
