"use client";

import Link from "next/link";
import { useState } from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Ban,
  Calendar,
  CalendarClock,
  CheckCircle2,
  CreditCard,
  Loader2,
  MapPin,
  MessageSquare,
  PackageCheck,
  Receipt,
  ShoppingBag,
  Tag,
  Truck,
  User,
  Wallet,
} from "lucide-react";
import { toast } from "sonner";
import { apiGet, apiPost } from "@/lib/api";
import { formatCurrency, formatDateTime } from "@/lib/utils";
import type { OrderDetail, OrderEvent } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { OrderStatusBadge } from "@/components/order-status-badge";

export default function PedidoDetalhePage() {
  const qc = useQueryClient();
  const params = useParams<{ id: string }>();
  const orderId = params.id;

  const order = useQuery({
    queryKey: ["order", orderId],
    queryFn: () => apiGet<OrderDetail>(`/orders/${orderId}`),
  });

  const events = useQuery({
    queryKey: ["order-events", orderId],
    queryFn: () => apiGet<OrderEvent[]>(`/orders/${orderId}/events`),
  });

  const [cancelReason, setCancelReason] = useState("");
  const [showCancel, setShowCancel] = useState(false);

  const action = useMutation({
    mutationFn: ({
      kind,
      reason,
    }: {
      kind: "confirm" | "dispatch" | "ready-to-pickup" | "cancel";
      reason?: string;
    }) => {
      const params =
        kind === "cancel"
          ? { reason: reason ?? "Cancelamento solicitado", code: "501" }
          : undefined;
      return apiPost<{ message: string }>(
        `/orders/${orderId}/${kind}`,
        undefined,
        params,
      );
    },
    onSuccess: (data) => {
      toast.success(data.message);
      setTimeout(() => {
        qc.invalidateQueries({ queryKey: ["order", orderId] });
        qc.invalidateQueries({ queryKey: ["order-events", orderId] });
      }, 1500);
    },
    onError: (e: any) => toast.error(e?.message ?? "Falha"),
  });

  if (order.isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!order.data) return null;

  const r = order.data.raw_data ?? {};
  const status = order.data.status;
  const customer = r.customer ?? {};
  const delivery = r.delivery ?? {};
  const takeout = r.takeout ?? {};
  const items: any[] = r.items ?? [];
  const total = r.total ?? {};
  const benefits: any[] = r.benefits ?? [];
  const payments = r.payments ?? {};
  const methods: any[] = payments.methods ?? [];
  const isScheduled = r.orderTiming === "SCHEDULED";
  const scheduledDate = r.schedule?.deliveryDateTimeStart ?? r.scheduledDate;

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" asChild className="-ml-3">
        <Link href="/pedidos">
          <ArrowLeft className="h-4 w-4" />
          Voltar
        </Link>
      </Button>

      {/* Hero */}
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-bold tracking-tight">
            Pedido #{order.data.display_id ?? order.data.ifood_order_id.slice(0, 8)}
          </h1>
          <OrderStatusBadge status={status as any} />
          <Badge variant="outline" className="gap-1">
            {order.data.order_type === "TAKEOUT" ? (
              <ShoppingBag className="h-3 w-3" />
            ) : order.data.order_type === "INDOOR" ? (
              <Receipt className="h-3 w-3" />
            ) : (
              <Truck className="h-3 w-3" />
            )}
            {order.data.order_type ?? "—"}
          </Badge>
          {isScheduled && (
            <Badge variant="outline" className="gap-1 border-amber-400 text-amber-700">
              <CalendarClock className="h-3 w-3" />
              Agendado
            </Badge>
          )}
        </div>
        <p className="font-mono text-xs text-muted-foreground">
          {order.data.ifood_order_id}
        </p>
        {order.data.created_at_ifood && (
          <p className="text-sm text-muted-foreground">
            Recebido em {formatDateTime(order.data.created_at_ifood)}
          </p>
        )}
      </div>

      {/* Ações */}
      <div className="flex flex-wrap gap-2">
        {(status === "PLACED" || status === "CREATED") && (
          <Button
            onClick={() => action.mutate({ kind: "confirm" })}
            disabled={action.isPending}
          >
            <CheckCircle2 className="h-4 w-4" />
            Confirmar
          </Button>
        )}
        {status === "CONFIRMED" && (
          <Button
            onClick={() => action.mutate({ kind: "ready-to-pickup" })}
            disabled={action.isPending}
            variant="outline"
          >
            <PackageCheck className="h-4 w-4" />
            Pronto
          </Button>
        )}
        {(status === "CONFIRMED" || status === "READY_FOR_PICKUP") && (
          <Button
            onClick={() => action.mutate({ kind: "dispatch" })}
            disabled={action.isPending}
            variant="outline"
          >
            <Truck className="h-4 w-4" />
            Despachar
          </Button>
        )}
        {!["CONCLUDED", "CANCELLED"].includes(status) && (
          <Button
            variant="destructive"
            onClick={() => setShowCancel(!showCancel)}
            disabled={action.isPending}
          >
            <Ban className="h-4 w-4" />
            Cancelar
          </Button>
        )}
      </div>

      {showCancel && (
        <Card>
          <CardContent className="space-y-2 p-4">
            <label className="text-xs font-medium text-muted-foreground">
              Motivo do cancelamento
            </label>
            <input
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
              placeholder="Ex: Sem produto em estoque"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            />
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="destructive"
                onClick={() => {
                  action.mutate({ kind: "cancel", reason: cancelReason });
                  setShowCancel(false);
                  setCancelReason("");
                }}
                disabled={!cancelReason.trim()}
              >
                Confirmar cancelamento
              </Button>
              <Button size="sm" variant="outline" onClick={() => setShowCancel(false)}>
                Voltar
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Agendamento */}
      {isScheduled && scheduledDate && (
        <Card className="border-amber-300 bg-amber-50/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <CalendarClock className="h-5 w-5 text-amber-600" />
              Pedido Agendado
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              <Field
                label="Data/Hora prevista"
                value={formatDateTime(scheduledDate)}
              />
              {r.schedule?.deliveryDateTimeEnd && (
                <Field
                  label="Janela final"
                  value={formatDateTime(r.schedule.deliveryDateTimeEnd)}
                />
              )}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Cliente */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <User className="h-5 w-5" />
              Cliente
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Field label="Nome" value={customer.name ?? order.data.customer_name} />
            <Field label="Telefone" value={customer.phone?.number ?? customer.phone} />
            <Field
              label="CPF/CNPJ"
              value={customer.documentNumber ?? customer.taxPayerIdentificationNumber}
              mono
            />
            {customer.orderHistory?.totalOrders && (
              <Field
                label="Total pedidos cliente"
                value={String(customer.orderHistory.totalOrders)}
              />
            )}
          </CardContent>
        </Card>

        {/* Entrega / Retirada */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              {order.data.order_type === "TAKEOUT" ? (
                <ShoppingBag className="h-5 w-5" />
              ) : (
                <MapPin className="h-5 w-5" />
              )}
              {order.data.order_type === "TAKEOUT" ? "Retirada" : "Entrega"}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {order.data.order_type === "TAKEOUT" ? (
              <>
                <Field
                  label="Modo"
                  value={takeout.mode ?? "Cliente retira no balcão"}
                />
                <Field
                  label="Horário previsto"
                  value={takeout.takeoutDateTime ? formatDateTime(takeout.takeoutDateTime) : null}
                />
              </>
            ) : (
              <>
                <Field
                  label="Endereço"
                  value={
                    delivery.deliveryAddress
                      ? formatAddress(delivery.deliveryAddress)
                      : null
                  }
                />
                <Field
                  label="Complemento"
                  value={delivery.deliveryAddress?.complement}
                />
                <Field
                  label="Referência"
                  value={delivery.deliveryAddress?.reference}
                />
                <Field
                  label="Modo"
                  value={delivery.mode ?? "Entrega pelo estabelecimento"}
                />
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Itens */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Tag className="h-5 w-5" />
            Itens do pedido ({items.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {items.map((it, idx) => (
            <div key={idx} className="space-y-1 border-b pb-3 last:border-0 last:pb-0">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1">
                  <div className="font-medium">
                    {it.quantity}× {it.name}
                  </div>
                  {it.externalCode && (
                    <div className="font-mono text-[10px] text-muted-foreground">
                      {it.externalCode}
                    </div>
                  )}
                  {it.observations && (
                    <div className="mt-1 text-xs text-muted-foreground">
                      <MessageSquare className="mr-1 inline h-3 w-3" />
                      {it.observations}
                    </div>
                  )}
                  {it.options?.length > 0 && (
                    <ul className="ml-4 mt-1 list-disc text-xs text-muted-foreground">
                      {it.options.map((opt: any, oi: number) => (
                        <li key={oi}>
                          {opt.quantity ?? 1}× {opt.name}
                          {opt.price?.value > 0 && (
                            <span className="ml-1">
                              (+{formatCurrency(opt.price.value)})
                            </span>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                <div className="text-right text-sm">
                  <div className="font-mono">
                    {formatCurrency(it.totalPrice ?? it.price?.value ?? 0)}
                  </div>
                  {it.unitPrice && it.quantity > 1 && (
                    <div className="text-xs text-muted-foreground">
                      Unit. {formatCurrency(it.unitPrice)}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Pagamento */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <CreditCard className="h-5 w-5" />
              Pagamento
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {methods.map((m, i) => (
              <div key={i} className="space-y-1 border-b pb-2 last:border-0 last:pb-0">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">
                    {m.method ?? m.type ?? "—"}
                  </span>
                  <span className="font-mono text-sm">
                    {formatCurrency(m.value ?? 0)}
                  </span>
                </div>
                <div className="text-xs text-muted-foreground">
                  {m.prepaid ? "Pago no app" : "Pagamento na entrega/retirada"}
                </div>
                {/* Troco */}
                {m.method === "CASH" && m.cash?.changeFor && (
                  <div className="rounded-md bg-amber-50 p-2 text-xs">
                    <Wallet className="mr-1 inline h-3 w-3 text-amber-700" />
                    <strong>Troco para:</strong>{" "}
                    {formatCurrency(m.cash.changeFor)} ·{" "}
                    <strong>Troco:</strong>{" "}
                    {formatCurrency(
                      (m.cash.changeFor ?? 0) - (m.value ?? 0),
                    )}
                  </div>
                )}
                {/* Cartão info */}
                {m.card && (
                  <div className="text-xs text-muted-foreground">
                    {m.card.brand ?? m.card.type ?? ""}{" "}
                    {m.card.cardNumber ? `•••• ${m.card.cardNumber.slice(-4)}` : ""}
                  </div>
                )}
              </div>
            ))}
            <Separator />
            <div className="space-y-1 text-sm">
              <SummaryRow label="Subtotal" value={total.subTotal} />
              <SummaryRow label="Taxa entrega" value={total.deliveryFee} />
              <SummaryRow label="Benefícios" value={-(total.benefits ?? 0)} />
              <SummaryRow label="Total" value={total.orderAmount} bold />
            </div>
          </CardContent>
        </Card>

        {/* Voucher / Benefícios */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Tag className="h-5 w-5" />
              Voucher / Cupons ({benefits.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {benefits.length === 0 ? (
              <p className="text-sm text-muted-foreground">Sem voucher aplicado.</p>
            ) : (
              benefits.map((b, i) => (
                <div key={i} className="space-y-1 border-b pb-2 last:border-0 last:pb-0">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">
                      {b.description ?? b.target ?? "Desconto"}
                    </span>
                    <span className="font-mono text-sm text-emerald-700">
                      −{formatCurrency(b.value ?? 0)}
                    </span>
                  </div>
                  {b.target && (
                    <div className="text-xs text-muted-foreground">
                      Aplicado em: {b.target}
                    </div>
                  )}
                  {b.sponsorshipValues && (
                    <div className="text-xs text-muted-foreground">
                      Patrocinado: {JSON.stringify(b.sponsorshipValues)}
                    </div>
                  )}
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      {/* Observação */}
      {r.extraInfo && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <MessageSquare className="h-5 w-5" />
              Observação do cliente
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm">{r.extraInfo}</p>
          </CardContent>
        </Card>
      )}

      {/* Timeline eventos */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Calendar className="h-5 w-5" />
            Histórico de eventos
          </CardTitle>
        </CardHeader>
        <CardContent>
          {events.isLoading ? (
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          ) : !events.data?.length ? (
            <p className="text-sm text-muted-foreground">Sem eventos registrados.</p>
          ) : (
            <ul className="space-y-2">
              {events.data.map((e) => (
                <li
                  key={e.id}
                  className="flex items-center gap-3 border-b pb-2 text-sm last:border-0 last:pb-0"
                >
                  <Badge variant="outline" className="font-mono">
                    {e.code}
                  </Badge>
                  <span className="flex-1 text-xs text-muted-foreground">
                    {e.full_code}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {formatDateTime(e.received_at)}
                  </span>
                </li>
              ))}
            </ul>
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
      <dd className={`mt-0.5 text-sm ${mono ? "font-mono" : ""}`}>
        {value || "—"}
      </dd>
    </div>
  );
}

function SummaryRow({
  label,
  value,
  bold,
}: {
  label: string;
  value: number | null | undefined;
  bold?: boolean;
}) {
  if (value === null || value === undefined) return null;
  return (
    <div className={`flex justify-between ${bold ? "font-semibold" : ""}`}>
      <span>{label}</span>
      <span className="font-mono">{formatCurrency(value)}</span>
    </div>
  );
}

function formatAddress(a: any): string {
  if (!a) return "—";
  const parts = [
    a.streetName,
    a.streetNumber,
    a.neighborhood,
    a.city,
    a.state,
    a.postalCode,
  ].filter(Boolean);
  return parts.join(", ");
}
