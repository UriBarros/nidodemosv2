"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, ShoppingBag, Store, Wallet, Zap } from "lucide-react";
import { toast } from "sonner";
import { apiGet, apiPost } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import type { Count, Merchant } from "@/lib/types";
import { StatCard } from "@/components/stat-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function DashboardHome() {
  const qc = useQueryClient();

  const merchants = useQuery({
    queryKey: ["merchants"],
    queryFn: () => apiGet<Merchant[]>("/merchants"),
  });
  const ordersTotal = useQuery({
    queryKey: ["orders-count"],
    queryFn: () => apiGet<Count>("/orders/count"),
  });
  const ordersPlaced = useQuery({
    queryKey: ["orders-count", "PLACED"],
    queryFn: () => apiGet<Count>("/orders/count", { status: "PLACED" }),
  });
  const financialSummary = useQuery({
    queryKey: ["financial-summary"],
    queryFn: () => apiGet<Record<string, number>>("/financial/summary"),
  });

  const syncMerchants = useMutation({
    mutationFn: () => apiPost<{ message: string }>("/merchants/sync"),
    onSuccess: (data) => {
      toast.success(data.message);
      qc.invalidateQueries({ queryKey: ["merchants"] });
    },
    onError: (e: any) => toast.error(e?.message ?? "Falha ao sincronizar"),
  });

  const totalSales = financialSummary.data?.SALE ?? 0;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Visão geral</h1>
          <p className="text-sm text-muted-foreground">
            Resumo dos seus dados iFood em tempo real.
          </p>
        </div>
        <Button
          onClick={() => syncMerchants.mutate()}
          disabled={syncMerchants.isPending}
          variant="outline"
        >
          <RefreshCw className={syncMerchants.isPending ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
          Sincronizar merchants
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Merchants" value={merchants.data?.length ?? "—"} icon={Store} />
        <StatCard label="Pedidos" value={ordersTotal.data?.count ?? "—"} icon={ShoppingBag} />
        <StatCard
          label="Em aberto"
          value={ordersPlaced.data?.count ?? "—"}
          icon={Zap}
          tone="warning"
          hint="Status PLACED"
        />
        <StatCard
          label="Vendas (total)"
          value={formatCurrency(totalSales)}
          icon={Wallet}
          tone="success"
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Como funciona</CardTitle>
          <CardDescription>
            Pedidos são sincronizados automaticamente pelo nosso worker. Você confirma,
            despacha e cancela direto do painel Pedidos.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm sm:grid-cols-3">
          <div className="rounded-lg border bg-muted/30 p-3">
            <div className="mb-1 font-semibold">1. Receba</div>
            <div className="text-muted-foreground">
              Cada pedido entra em PLACED automaticamente.
            </div>
          </div>
          <div className="rounded-lg border bg-muted/30 p-3">
            <div className="mb-1 font-semibold">2. Gerencie</div>
            <div className="text-muted-foreground">
              Confirme → Pronto → Despache em poucos cliques.
            </div>
          </div>
          <div className="rounded-lg border bg-muted/30 p-3">
            <div className="mb-1 font-semibold">3. Analise</div>
            <div className="text-muted-foreground">
              Financeiro e reviews aparecem nas abas dedicadas.
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
