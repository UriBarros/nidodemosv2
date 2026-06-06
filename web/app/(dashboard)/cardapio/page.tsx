"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen, Edit, Image as ImageIcon, Loader2, Plus, RefreshCw, Save, Upload, X } from "lucide-react";
import { toast } from "sonner";
import { apiGet, apiPatch, apiPost, apiUpload } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import type {
  CatalogCategory,
  CatalogItem,
  CatalogSyncResult,
  Merchant,
  UploadImageOut,
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

  // Forms criar/editar
  const [showCategoryForm, setShowCategoryForm] = useState(false);
  const [categoryName, setCategoryName] = useState("");
  const [showItemForm, setShowItemForm] = useState(false);
  const [itemName, setItemName] = useState("");
  const [itemDesc, setItemDesc] = useState("");
  const [itemPrice, setItemPrice] = useState("");
  const [itemCategoryId, setItemCategoryId] = useState<string>("");
  const [editingItemId, setEditingItemId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");

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

  function resolveMerchantId(): string | null {
    return merchantId === "all" ? merchants.data?.[0]?.id ?? null : merchantId;
  }

  const createCategory = useMutation({
    mutationFn: () => {
      const m = resolveMerchantId();
      if (!m) throw new Error("Selecione um merchant");
      return apiPost(`/catalog/categories`, {
        merchant_id: m,
        name: categoryName.trim(),
      });
    },
    onSuccess: () => {
      toast.success("Categoria criada — sincroniza pra ver");
      setShowCategoryForm(false);
      setCategoryName("");
    },
    onError: (e: any) => toast.error(e?.message ?? "Falha"),
  });

  const createItem = useMutation({
    mutationFn: () => {
      const m = resolveMerchantId();
      if (!m || !itemCategoryId) throw new Error("Merchant e categoria obrigatórios");
      const price = parseFloat(itemPrice.replace(",", "."));
      if (isNaN(price)) throw new Error("Preço inválido");
      return apiPost(`/catalog/items`, {
        merchant_id: m,
        category_id: itemCategoryId,
        name: itemName.trim(),
        description: itemDesc.trim() || undefined,
        price,
      });
    },
    onSuccess: () => {
      toast.success("Item criado — sincroniza pra ver");
      setShowItemForm(false);
      setItemName("");
      setItemDesc("");
      setItemPrice("");
      setItemCategoryId("");
    },
    onError: (e: any) => toast.error(e?.message ?? "Falha"),
  });

  const updateItem = useMutation({
    mutationFn: (id: string) =>
      apiPatch<CatalogItem>(`/catalog/items/${id}`, {
        name: editName.trim() || undefined,
        description: editDesc.trim() || undefined,
      }),
    onSuccess: () => {
      toast.success("Item atualizado");
      setEditingItemId(null);
      setEditName("");
      setEditDesc("");
      qc.invalidateQueries({ queryKey: ["catalog-items"] });
    },
    onError: (e: any) => toast.error(e?.message ?? "Falha"),
  });

  const uploadImageForItem = useMutation({
    mutationFn: async ({ id, file }: { id: string; file: File }) => {
      const m = resolveMerchantId();
      if (!m) throw new Error("Selecione um merchant");
      const up = await apiUpload<UploadImageOut>("/catalog/upload-image", file, {
        merchant_id: m,
      });
      if (!up?.path) throw new Error("upload sem path");
      return apiPatch<CatalogItem>(`/catalog/items/${id}`, {
        image_path: up.path,
      });
    },
    onSuccess: () => {
      toast.success("Imagem atualizada");
      qc.invalidateQueries({ queryKey: ["catalog-items"] });
    },
    onError: (e: any) => toast.error(e?.message ?? "Falha upload"),
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
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => setShowCategoryForm(!showCategoryForm)}
            disabled={!merchants.data?.length}
          >
            <Plus className="h-4 w-4" />
            Categoria
          </Button>
          <Button
            variant="outline"
            onClick={() => setShowItemForm(!showItemForm)}
            disabled={!merchants.data?.length || !categories.data?.length}
          >
            <Plus className="h-4 w-4" />
            Item
          </Button>
          <Button
            onClick={() => sync.mutate()}
            disabled={sync.isPending || !merchants.data?.length}
            variant="outline"
          >
            <RefreshCw
              className={sync.isPending ? "h-4 w-4 animate-spin" : "h-4 w-4"}
            />
            Sincronizar
          </Button>
        </div>
      </div>

      {/* Form criar categoria */}
      {showCategoryForm && (
        <Card>
          <CardContent className="space-y-3 p-4">
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">
                Nome da categoria
              </label>
              <Input
                value={categoryName}
                onChange={(e) => setCategoryName(e.target.value)}
                placeholder="Ex: Teste Homologação"
                autoFocus
              />
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={() => createCategory.mutate()}
                disabled={createCategory.isPending || !categoryName.trim()}
              >
                {createCategory.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Save className="h-4 w-4" />
                )}
                Criar
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowCategoryForm(false)}
              >
                Cancelar
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Form criar item */}
      {showItemForm && (
        <Card>
          <CardContent className="space-y-3 p-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">
                  Categoria
                </label>
                <Select value={itemCategoryId} onValueChange={setItemCategoryId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Selecione" />
                  </SelectTrigger>
                  <SelectContent>
                    {categories.data?.map((c) => (
                      <SelectItem key={c.id} value={c.id}>
                        {c.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">
                  Preço (R$)
                </label>
                <Input
                  value={itemPrice}
                  onChange={(e) => setItemPrice(e.target.value)}
                  placeholder="0,00"
                />
              </div>
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">
                Nome do item
              </label>
              <Input
                value={itemName}
                onChange={(e) => setItemName(e.target.value)}
                placeholder="Ex: Produto Teste"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">
                Descrição
              </label>
              <Input
                value={itemDesc}
                onChange={(e) => setItemDesc(e.target.value)}
                placeholder="Descrição opcional"
              />
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={() => createItem.mutate()}
                disabled={
                  createItem.isPending ||
                  !itemName.trim() ||
                  !itemPrice ||
                  !itemCategoryId
                }
              >
                {createItem.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Save className="h-4 w-4" />
                )}
                Criar item
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowItemForm(false)}
              >
                Cancelar
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

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
                      {editingItemId === it.id ? (
                        <div className="space-y-2">
                          <Input
                            value={editName}
                            onChange={(e) => setEditName(e.target.value)}
                            placeholder="Nome"
                            className="h-8 text-sm"
                          />
                          <Input
                            value={editDesc}
                            onChange={(e) => setEditDesc(e.target.value)}
                            placeholder="Descrição"
                            className="h-8 text-xs"
                          />
                          <div className="flex gap-1">
                            <Button
                              size="sm"
                              onClick={() => updateItem.mutate(it.id)}
                              disabled={updateItem.isPending}
                            >
                              <Save className="h-3 w-3" />
                              Salvar
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => {
                                setEditingItemId(null);
                                setEditName("");
                                setEditDesc("");
                              }}
                            >
                              <X className="h-3 w-3" />
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <div className="flex items-start gap-2">
                          {it.image_path && (
                            <ImageIcon className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                          )}
                          <div className="flex-1">
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
                          </div>
                          <div className="flex flex-col gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 px-2"
                              onClick={() => {
                                setEditingItemId(it.id);
                                setEditName(it.name);
                                setEditDesc(it.description ?? "");
                              }}
                              title="Editar nome/descrição"
                            >
                              <Edit className="h-3 w-3" />
                            </Button>
                            <label
                              htmlFor={`upload-${it.id}`}
                              className="inline-flex h-7 cursor-pointer items-center justify-center rounded-md px-2 text-xs font-medium hover:bg-accent"
                              title="Trocar foto"
                            >
                              <Upload className="h-3 w-3" />
                              <input
                                id={`upload-${it.id}`}
                                type="file"
                                accept="image/*"
                                className="hidden"
                                onChange={(e) => {
                                  const f = e.target.files?.[0];
                                  if (f) uploadImageForItem.mutate({ id: it.id, file: f });
                                  e.target.value = "";
                                }}
                              />
                            </label>
                          </div>
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
