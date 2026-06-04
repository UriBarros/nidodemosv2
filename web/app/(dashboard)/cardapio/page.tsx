"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen, Loader2, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { apiGet, apiPatch, apiPost } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import type {
  CatalogCategory,
  CatalogItem,
  CatalogSyncResult,
  Merchant,
} from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
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
import { ClientFilter } from "@/components/client-filter";

export default function CardapioPage() {
  const qc = useQueryClient();
  const [clientId, setClientId] = useState<string | null>(null);
  const [merchantId, setMerchantId] = useState<string>("all");
  const [categoryId, setCategoryId] = useState<string>("all");
  const [editingPriceFor, setEditingPriceFor] = useState<string | null>(null);
  const [priceDraft, setPriceDraft] = useState<string>("");

  const merchants = useQuery({
    queryKey: ["merchants", clientId],
    queryFn: () =>
      apiGet<Merchant[]>("/merchants", { client_id: clientId ?? undefined }),
  });

  const categories = useQuery({
    queryKey: ["catalog-categories", clientId, merchantId],
    queryFn: () =>
      apiGet<CatalogCategory[]>("/catalog/categories", {
        client_id: clientId ?? undefined,
        merchant_id: merchantId === "all" ? undefined : merchantId,
      }),
  });

  const items = useQuery({
    queryKey: ["catalog-items", clientId, merchantId, categoryId],
    queryFn: () =>
      apiGet<CatalogItem[]>("/catalog/items", {
        client_id: clientId ?? undefined,
        merchant_id: merchantId === "all" ? undefined : merchantId,
        category_id: categoryId === "all" ? undefined : categoryId,
      }),
  });

  const sync = useMutation({
    mutationFn: () => {
      const m = merchantId === "all" ? merchants.data?.[0]?.id : merchantId;
      if (!m) throw new Error("Selecione um merchant para sincronizar");
      return apiPost<CatalogSyncResult>("/catalog/sync", undefined, {
        merchant_id: m,
      });
    },
    onSuccess: (data) => {
      toast.success(
        `Cardápio sincronizado: ${data.categories} categoria(s), ${data.items} item(ns)`,
      );
      qc.invalidateQueries({ queryKey: ["catalog-categories"] });
      qc.invalidateQueries({ queryKey: ["catalog-items"] });
    },
    onError: (e: any) => toast.error(e?.message ?? "Falha ao sincronizar"),
  });

  const toggleStatus = useMutation({
    mutationFn: ({ id, current }: { id: string; current: string }) => {
      const next = current === "AVAILABLE" ? "UNAVAILABLE" : "AVAILABLE";
      return apiPatch<CatalogItem>(`/catalog/items/${id}/status`, {
        status: next,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["catalog-items"] });
    },
    onError: (e: any) => toast.error(e?.message ?? "Falha ao alterar status"),
  });

  const updatePrice = useMutation({
    mutationFn: ({ id, price }: { id: string; price: number }) =>
      apiPatch<CatalogItem>(`/catalog/items/${id}/price`, { price }),
    onSuccess: () => {
      setEditingPriceFor(null);
      setPriceDraft("");
      qc.invalidateQueries({ queryKey: ["catalog-items"] });
      toast.success("Preço atualizado");
    },
    onError: (e: any) => toast.error(e?.message ?? "Falha ao atualizar preço"),
  });

  function startEditPrice(item: CatalogItem) {
    setEditingPriceFor(item.id);
    setPriceDraft(item.price ?? "0");
  }

  function savePrice(item: CatalogItem) {
    const n = parseFloat(priceDraft.replace(",", "."));
    if (isNaN(n) || n < 0) {
      toast.error("Preço inválido");
      return;
    }
    updatePrice.mutate({ id: item.id, price: n });
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Cardápio</h1>
          <p className="text-sm text-muted-foreground">
            {items.data?.length ?? 0} item(ns) ·{" "}
            {categories.data?.length ?? 0} categoria(s)
          </p>
        </div>
        <Button
          onClick={() => sync.mutate()}
          disabled={sync.isPending || !merchants.data?.length}
          variant="outline"
        >
          <RefreshCw
            className={sync.isPending ? "h-4 w-4 animate-spin" : "h-4 w-4"}
          />
          Sincronizar com iFood
        </Button>
      </div>

      {/* Filtros */}
      <Card>
        <CardContent className="flex flex-wrap items-end gap-4 p-4">
          <div className="min-w-[260px] space-y-1">
            <label className="text-xs font-medium text-muted-foreground">
              Cliente
            </label>
            <ClientFilter value={clientId} onChange={setClientId} />
          </div>
          <div className="min-w-[200px] space-y-1">
            <label className="text-xs font-medium text-muted-foreground">
              Merchant
            </label>
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
          <div className="min-w-[200px] space-y-1">
            <label className="text-xs font-medium text-muted-foreground">
              Categoria
            </label>
            <Select value={categoryId} onValueChange={setCategoryId}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas</SelectItem>
                {categories.data?.map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    {c.name}
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
          {items.isLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : !items.data || items.data.length === 0 ? (
            <div className="py-12 text-center text-sm text-muted-foreground">
              <BookOpen className="mx-auto mb-2 h-10 w-10 opacity-40" />
              Nenhum item sincronizado ainda. Clica em{" "}
              <span className="font-medium">Sincronizar com iFood</span> pra
              puxar.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Item</TableHead>
                  <TableHead className="w-[180px]">Preço</TableHead>
                  <TableHead className="w-[160px]">Status</TableHead>
                  <TableHead className="w-[100px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.data.map((it) => (
                  <TableRow key={it.id}>
                    <TableCell>
                      <div className="font-medium">{it.name}</div>
                      {it.description && (
                        <div className="line-clamp-2 text-xs text-muted-foreground">
                          {it.description}
                        </div>
                      )}
                      {it.external_code && (
                        <div className="mt-0.5 font-mono text-[10px] text-muted-foreground">
                          {it.external_code}
                        </div>
                      )}
                    </TableCell>
                    <TableCell>
                      {editingPriceFor === it.id ? (
                        <div className="flex gap-1">
                          <Input
                            value={priceDraft}
                            onChange={(e) => setPriceDraft(e.target.value)}
                            className="h-8 w-24"
                            autoFocus
                            onKeyDown={(e) => {
                              if (e.key === "Enter") savePrice(it);
                              if (e.key === "Escape") {
                                setEditingPriceFor(null);
                                setPriceDraft("");
                              }
                            }}
                          />
                          <Button
                            size="sm"
                            onClick={() => savePrice(it)}
                            disabled={updatePrice.isPending}
                          >
                            OK
                          </Button>
                        </div>
                      ) : (
                        <button
                          onClick={() => startEditPrice(it)}
                          className="font-mono hover:underline"
                        >
                          {it.price ? formatCurrency(Number(it.price)) : "—"}
                        </button>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          it.status === "AVAILABLE" ? "default" : "secondary"
                        }
                      >
                        {it.status === "AVAILABLE"
                          ? "Disponível"
                          : "Indisponível"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          toggleStatus.mutate({ id: it.id, current: it.status })
                        }
                        disabled={toggleStatus.isPending}
                      >
                        {it.status === "AVAILABLE" ? "Pausar" : "Ativar"}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
