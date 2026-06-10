"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Plus, Save, Upload } from "lucide-react";
import { toast } from "sonner";
import { apiGet, apiPatch, apiPost, apiUpload } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import type { OptionGroup, UploadImageOut } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface Props {
  /** ID local (UUID) do item ao qual os grupos pertencem. */
  itemId: string | null;
  /** ID do merchant (precisa pra mutations de status/preço de opção). */
  merchantId: string | null;
}

/**
 * Gestão de grupos de complementos (option groups) e suas opções,
 * vinculados a UM item específico (API v2.0 do iFood).
 *
 * Atende Cenário 2 (criar grupo + 2 complementos) e Cenário 3
 * (pausar complemento) do checklist iFood Catalog.
 */
export function CatalogComplements({ itemId, merchantId }: Props) {
  const qc = useQueryClient();
  const [showGroupForm, setShowGroupForm] = useState(false);
  const [groupName, setGroupName] = useState("");
  const [groupMin, setGroupMin] = useState("0");
  const [groupMax, setGroupMax] = useState("1");

  const [addingToGroup, setAddingToGroup] = useState<string | null>(null);
  const [optName, setOptName] = useState("");
  const [optPrice, setOptPrice] = useState("");

  const groups = useQuery({
    queryKey: ["option-groups", itemId],
    queryFn: () =>
      apiGet<OptionGroup[]>("/catalog/option-groups", {
        merchant_id: merchantId ?? undefined,
        item_id: itemId ?? undefined,
      }),
    enabled: !!itemId && !!merchantId,
  });

  const createGroup = useMutation({
    mutationFn: () => {
      if (!merchantId || !itemId) throw new Error("Selecione item primeiro");
      return apiPost(`/catalog/option-groups?item_id=${itemId}`, {
        merchant_id: merchantId,
        name: groupName.trim(),
        min_choices: parseInt(groupMin) || 0,
        max_choices: parseInt(groupMax) || 1,
      });
    },
    onSuccess: () => {
      toast.success("Grupo criado");
      setShowGroupForm(false);
      setGroupName("");
      setGroupMin("0");
      setGroupMax("1");
      qc.invalidateQueries({ queryKey: ["option-groups", itemId] });
    },
    onError: (e: any) => toast.error(e?.message ?? "Falha"),
  });

  const createOption = useMutation({
    mutationFn: ({ groupId }: { groupId: string }) => {
      if (!merchantId || !itemId) throw new Error("Selecione item");
      const price = parseFloat(optPrice.replace(",", "."));
      if (isNaN(price)) throw new Error("Preço inválido");
      return apiPost(`/catalog/options?item_id=${itemId}`, {
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
      qc.invalidateQueries({ queryKey: ["option-groups", itemId] });
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
      qc.invalidateQueries({ queryKey: ["option-groups", itemId] });
    },
    onError: (e: any) => toast.error(e?.message ?? "Falha"),
  });

  const uploadOptionImage = useMutation({
    mutationFn: async ({ id, file }: { id: string; file: File }) => {
      if (!merchantId) throw new Error("Selecione merchant");
      const up = await apiUpload<UploadImageOut>("/catalog/upload-image", file, {
        merchant_id: merchantId,
      });
      if (!up?.path) throw new Error("upload sem path");
      return apiPatch(`/catalog/options/${id}?merchant_id=${merchantId}`, {
        image_path: up.path,
      });
    },
    onSuccess: () => {
      toast.success("Foto enviada");
      qc.invalidateQueries({ queryKey: ["option-groups", itemId] });
    },
    onError: (e: any) => toast.error(e?.message ?? "Falha"),
  });

  if (!itemId) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Complementos</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Selecione um item pra ver os grupos de complementos. Na API v2.0
            do iFood, complementos pertencem a um item específico.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base">
          Complementos do item ({groups.data?.length ?? 0} grupo[s])
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
              <Label htmlFor="gname">Nome do grupo</Label>
              <Input
                id="gname"
                value={groupName}
                onChange={(e) => setGroupName(e.target.value)}
                placeholder="Ex: Bordas, Adicionais, Bebidas"
                autoFocus
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
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={() => createGroup.mutate()}
                disabled={createGroup.isPending || !groupName.trim()}
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
            Nenhum grupo cadastrado neste item.
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
                      Min {g.min ?? 0} · Max {g.max ?? 1} · Status {g.status ?? "—"}
                    </div>
                  </div>
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
                            <div className="inline-flex gap-1">
                              <label
                                htmlFor={`upopt-${o.id}`}
                                className="inline-flex h-8 cursor-pointer items-center justify-center rounded-md border px-2 text-xs hover:bg-accent"
                                title="Trocar foto"
                              >
                                <Upload className="h-3 w-3" />
                                <input
                                  id={`upopt-${o.id}`}
                                  type="file"
                                  accept="image/*"
                                  className="hidden"
                                  onChange={(e) => {
                                    const f = e.target.files?.[0];
                                    if (f && o.id)
                                      uploadOptionImage.mutate({ id: o.id, file: f });
                                    e.target.value = "";
                                  }}
                                />
                              </label>
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
                            </div>
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
