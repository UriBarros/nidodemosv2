"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Plus, Save } from "lucide-react";
import { toast } from "sonner";
import { apiGet, apiPatch, apiPost } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import type { CatalogItem, OptionGroup } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface Props {
  merchantId: string | null;
}

interface OptionDraft {
  name: string;
  price: string;
}

/**
 * Gestão de grupos de complementos (option groups) + options.
 *
 * Catalog v2.0 do iFood não tem POST /optionGroups standalone: grupo nasce
 * dentro de PUT /items com options aninhadas. UI:
 * - "Novo grupo" exige escolher item ancora; backend monta payload completo
 *   e faz PUT /items via /catalog/option-groups/add-to-item
 * - "Adicionar option": POST /optionGroups/{ogId}/options (existing group)
 * - "Pausar grupo": PATCH /optionGroups/{ogId}/status
 * - "Pausar/Ativar option": batch PATCH /options/status
 */
export function CatalogComplements({ merchantId }: Props) {
  const qc = useQueryClient();
  const [showGroupForm, setShowGroupForm] = useState(false);
  const [groupName, setGroupName] = useState("");
  const [groupMin, setGroupMin] = useState("0");
  const [groupMax, setGroupMax] = useState("1");
  const [groupItemId, setGroupItemId] = useState<string>("");
  const [groupOptions, setGroupOptions] = useState<OptionDraft[]>([
    { name: "", price: "" },
    { name: "", price: "" },
  ]);

  const [addingToGroup, setAddingToGroup] = useState<string | null>(null);
  const [optName, setOptName] = useState("");
  const [optPrice, setOptPrice] = useState("");

  const groups = useQuery({
    queryKey: ["option-groups", merchantId],
    queryFn: () =>
      apiGet<OptionGroup[]>("/catalog/option-groups", {
        merchant_id: merchantId ?? undefined,
      }),
    enabled: !!merchantId,
  });

  const items = useQuery({
    queryKey: ["catalog-items", merchantId],
    queryFn: () =>
      apiGet<CatalogItem[]>("/catalog/items", {
        merchant_id: merchantId ?? undefined,
      }),
    enabled: !!merchantId && showGroupForm,
  });

  const createGroup = useMutation({
    mutationFn: () => {
      if (!merchantId) throw new Error("Selecione merchant");
      if (!groupItemId) throw new Error("Selecione item ancora");
      const opts = groupOptions
        .filter((o) => o.name.trim() && o.price.trim())
        .map((o) => ({
          name: o.name.trim(),
          price: parseFloat(o.price.replace(",", ".")) || 0,
          status: "AVAILABLE",
        }));
      if (!opts.length) throw new Error("Adicione pelo menos 1 complemento");
      return apiPost("/catalog/option-groups/add-to-item", {
        merchant_id: merchantId,
        item_id: groupItemId,
        name: groupName.trim(),
        min: parseInt(groupMin) || 0,
        max: parseInt(groupMax) || 1,
        options: opts,
      });
    },
    onSuccess: () => {
      toast.success("Grupo + complementos criados");
      setShowGroupForm(false);
      setGroupName("");
      setGroupMin("0");
      setGroupMax("1");
      setGroupItemId("");
      setGroupOptions([
        { name: "", price: "" },
        { name: "", price: "" },
      ]);
      qc.invalidateQueries({ queryKey: ["option-groups", merchantId] });
    },
    onError: (e: any) => toast.error(e?.message ?? "Falha"),
  });

  const createOption = useMutation({
    mutationFn: ({ groupId }: { groupId: string }) => {
      if (!merchantId) throw new Error("Selecione merchant");
      const price = parseFloat(optPrice.replace(",", "."));
      if (isNaN(price)) throw new Error("Preço inválido");
      return apiPost("/catalog/options", {
        merchant_id: merchantId,
        option_group_id: groupId,
        name: optName.trim(),
        price,
      });
    },
    onSuccess: () => {
      toast.success("Complemento criado");
      setAddingToGroup(null);
      setOptName("");
      setOptPrice("");
      qc.invalidateQueries({ queryKey: ["option-groups", merchantId] });
    },
    onError: (e: any) => toast.error(e?.message ?? "Falha"),
  });

  const toggleOption = useMutation({
    mutationFn: ({ id, currentStatus }: { id: string; currentStatus: string }) => {
      if (!merchantId) throw new Error("Selecione merchant");
      const next = currentStatus === "AVAILABLE" ? "UNAVAILABLE" : "AVAILABLE";
      return apiPatch(`/catalog/options/${id}?merchant_id=${merchantId}`, {
        status: next,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["option-groups", merchantId] });
    },
    onError: (e: any) => toast.error(e?.message ?? "Falha"),
  });

  const toggleGroup = useMutation({
    mutationFn: ({ id, currentStatus }: { id: string; currentStatus: string }) => {
      if (!merchantId) throw new Error("Selecione merchant");
      const next = currentStatus === "AVAILABLE" ? "UNAVAILABLE" : "AVAILABLE";
      return apiPatch(
        `/catalog/option-groups/${id}/status?merchant_id=${merchantId}&status=${next}`,
        {},
      );
    },
    onSuccess: () => {
      toast.success("Status do grupo atualizado");
      qc.invalidateQueries({ queryKey: ["option-groups", merchantId] });
    },
    onError: (e: any) => toast.error(e?.message ?? "Falha"),
  });

  if (!merchantId) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Complementos</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Selecione um merchant pra ver os grupos de complementos.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base">
          Complementos ({groups.data?.length ?? 0} grupo[s])
        </CardTitle>
        <Button
          size="sm"
          variant="outline"
          onClick={() => setShowGroupForm(!showGroupForm)}
        >
          <Plus className="h-4 w-4" />
          Novo grupo
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {showGroupForm && (
          <div className="space-y-3 rounded-md border bg-muted/30 p-4">
            <div className="space-y-1">
              <Label htmlFor="gitem">Vincular a item *</Label>
              <select
                id="gitem"
                value={groupItemId}
                onChange={(e) => setGroupItemId(e.target.value)}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="">Selecione um item...</option>
                {items.data?.map((it) => (
                  <option key={it.id} value={it.id}>
                    {it.name}
                  </option>
                ))}
              </select>
              <p className="text-xs text-muted-foreground">
                iFood Catalog v2.0 exige item ancora pra criar grupo
              </p>
            </div>
            <div className="space-y-1">
              <Label htmlFor="gname">Nome do grupo *</Label>
              <Input
                id="gname"
                value={groupName}
                onChange={(e) => setGroupName(e.target.value)}
                placeholder="Ex: Bordas, Adicionais, Bebidas"
              />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <Label htmlFor="gmin">Mínimo escolhas</Label>
                <Input
                  id="gmin"
                  type="number"
                  min={0}
                  value={groupMin}
                  onChange={(e) => setGroupMin(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="gmax">Máximo escolhas</Label>
                <Input
                  id="gmax"
                  type="number"
                  min={1}
                  value={groupMax}
                  onChange={(e) => setGroupMax(e.target.value)}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Complementos iniciais *</Label>
              {groupOptions.map((opt, idx) => (
                <div key={idx} className="grid gap-2 sm:grid-cols-[1fr_8rem]">
                  <Input
                    value={opt.name}
                    onChange={(e) => {
                      const next = [...groupOptions];
                      next[idx] = { ...next[idx], name: e.target.value };
                      setGroupOptions(next);
                    }}
                    placeholder={`Nome complemento ${idx + 1}`}
                  />
                  <Input
                    value={opt.price}
                    onChange={(e) => {
                      const next = [...groupOptions];
                      next[idx] = { ...next[idx], price: e.target.value };
                      setGroupOptions(next);
                    }}
                    placeholder="Preço"
                  />
                </div>
              ))}
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() =>
                  setGroupOptions([
                    ...groupOptions,
                    { name: "", price: "" },
                  ])
                }
              >
                <Plus className="h-3 w-3" />
                Mais um
              </Button>
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={() => createGroup.mutate()}
                disabled={
                  createGroup.isPending ||
                  !groupName.trim() ||
                  !groupItemId
                }
              >
                {createGroup.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Save className="h-4 w-4" />
                )}
                Criar grupo
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setShowGroupForm(false)}
              >
                Cancelar
              </Button>
            </div>
          </div>
        )}

        {groups.isLoading ? (
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        ) : !groups.data?.length ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            Nenhum grupo cadastrado. Crie um pra começar.
          </p>
        ) : (
          groups.data.map((g, gi) => {
            const groupId = g.id ?? `g${gi}`;
            const opts: any[] = g.options ?? [];
            return (
              <div
                key={groupId}
                className="space-y-3 rounded-md border bg-card p-4"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">{g.name ?? "—"}</div>
                    <div className="text-xs text-muted-foreground">
                      Min {g.min ?? 0} · Max {g.max ?? 1} ·{" "}
                      <Badge
                        variant={
                          g.status === "AVAILABLE" ? "default" : "secondary"
                        }
                        className="ml-1"
                      >
                        {g.status === "AVAILABLE" ? "Ativo" : "Pausado"}
                      </Badge>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    {g.id && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() =>
                          toggleGroup.mutate({
                            id: g.id!,
                            currentStatus: g.status ?? "AVAILABLE",
                          })
                        }
                        disabled={toggleGroup.isPending}
                      >
                        {g.status === "AVAILABLE" ? "Pausar grupo" : "Ativar grupo"}
                      </Button>
                    )}
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() =>
                        setAddingToGroup(addingToGroup === groupId ? null : groupId)
                      }
                    >
                      <Plus className="h-3 w-3" />
                      Complemento
                    </Button>
                  </div>
                </div>

                {addingToGroup === groupId && (
                  <div className="space-y-2 rounded-md border bg-muted/30 p-3">
                    <div className="grid gap-2 sm:grid-cols-2">
                      <Input
                        value={optName}
                        onChange={(e) => setOptName(e.target.value)}
                        placeholder="Nome do complemento"
                        autoFocus
                      />
                      <Input
                        value={optPrice}
                        onChange={(e) => setOptPrice(e.target.value)}
                        placeholder="Preço"
                      />
                    </div>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        onClick={() => createOption.mutate({ groupId: g.id! })}
                        disabled={
                          createOption.isPending || !optName.trim() || !optPrice
                        }
                      >
                        Salvar
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setAddingToGroup(null)}
                      >
                        Cancelar
                      </Button>
                    </div>
                  </div>
                )}

                {opts.length > 0 && (
                  <table className="w-full text-sm">
                    <tbody>
                      {opts.map((o, oi) => (
                        <tr key={o.id ?? oi} className="border-t">
                          <td className="py-2">
                            <div className="font-medium">{o.name ?? "—"}</div>
                            {o.externalCode && (
                              <div className="font-mono text-[10px] text-muted-foreground">
                                {o.externalCode}
                              </div>
                            )}
                          </td>
                          <td className="py-2 text-right font-mono">
                            {o.price?.value !== undefined
                              ? formatCurrency(o.price.value)
                              : "—"}
                          </td>
                          <td className="py-2 px-2">
                            <Badge
                              variant={
                                o.status === "AVAILABLE" ? "default" : "secondary"
                              }
                            >
                              {o.status === "AVAILABLE"
                                ? "Disponível"
                                : "Indisponível"}
                            </Badge>
                          </td>
                          <td className="py-2 text-right">
                            {o.id && (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() =>
                                  toggleOption.mutate({
                                    id: o.id,
                                    currentStatus: o.status,
                                  })
                                }
                                disabled={toggleOption.isPending}
                              >
                                {o.status === "AVAILABLE" ? "Pausar" : "Ativar"}
                              </Button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            );
          })
        )}
      </CardContent>
    </Card>
  );
}
