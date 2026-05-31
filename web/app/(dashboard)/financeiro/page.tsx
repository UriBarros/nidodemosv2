"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, TrendingUp, Wallet, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import { apiGet, apiPost } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import type { FinancialEvent, Merchant } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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
import { StatCard } from "@/components/stat-card";
import { ClientFilter } from "@/components/client-filter";

export default function FinanceiroPage() {
  const qc = useQueryClient();
  const [clientId, setClientId] = useState<string | null>(null);
  const [merchantId, setMerchantId] = useState<string>("all");

  const merchants = useQuery({
    queryKey: ["merchants"],
    queryFn: () => apiGet<Merchant[]>("/merchants"),
  });

  const summary = useQuery({
    queryKey: ["financial-summary", clientId, merchantId],
    queryFn: () =>
      apiGet<Record<string, number>>("/financial/summary", {
        client_id: clientId ?? undefined,
        merchant_id: merchantId === "all" ? undefined : merchantId,
      }),
  });

  const list = useQuery({
    queryKey: ["financial-list", clientId, merchantId],
    queryFn: () =>
      apiGet<FinancialEvent[]>("/financial", {
        client_id: clientId ?? undefined,
        merchant_id: merchantId === "all" ? undefined : merchantId,
        limit: 200,
      }),
  });

  const sync = useMutation({
    mutationFn: () =>
      apiPost<{ message: string }>("/financial/sync", undefined, {
        merchant_id: merchantId === "all" ? merchants.data?.[0]?.id : merchantId,
        days_back: 30,
      }),
    onSuccess: (d) => {
      toast.success(d.message);
      qc.invalidateQueries({ queryKey: ["financial-summary"] });
      qc.invalidateQueries({ queryKey: ["financial-list"] });
    },
    onError: (e: any) => toast.error(e?.message ?? "Falha"),
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Financeiro</h1>
          <p className="text-sm text-muted-foreground">
            Vendas, antecipações e ocorrências.
          </p>
        </div>
        <Button onClick={() => sync.mutate()} disabled={sync.isPending} variant="outline">
          <RefreshCw className={sync.isPending ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
          Sincronizar
        </Button>
      </div>

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
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard label="Vendas" value={formatCurrency(summary.data?.SALE ?? 0)} icon={Wallet} tone="success" />
        <StatCard label="Antecipações" value={formatCurrency(summary.data?.ANTICIPATION ?? 0)} icon={TrendingUp} />
        <StatCard label="Ocorrências" value={formatCurrency(summary.data?.OCCURRENCE ?? 0)} icon={AlertCircle} tone="warning" />
      </div>

      <Card>
        <CardContent className="p-0">
          {list.data?.length ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Data competência</TableHead>
                  <TableHead>Valor</TableHead>
                  <TableHead>Descrição</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {list.data.map((e) => (
                  <TableRow key={e.id}>
                    <TableCell className="font-medium">{e.event_type}</TableCell>
                    <TableCell>{e.competence_date ?? "—"}</TableCell>
                    <TableCell>{formatCurrency(e.amount)}</TableCell>
                    <TableCell className="text-muted-foreground">{e.description ?? "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">
              Nenhum evento financeiro. Use "Sincronizar".
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
