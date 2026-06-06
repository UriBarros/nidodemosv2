"use client";

import Link from "next/link";
import { useState } from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  CalendarClock,
  CircleStop,
  Clock,
  Loader2,
  Plus,
  Save,
  Store,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { apiDelete, apiGet, apiPost, apiPut } from "@/lib/api";
import type {
  DayOfWeek,
  Interruption,
  Merchant,
  OpeningHours,
  Shift,
} from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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

const DAYS: { value: DayOfWeek; label: string }[] = [
  { value: "MONDAY", label: "Segunda" },
  { value: "TUESDAY", label: "Terça" },
  { value: "WEDNESDAY", label: "Quarta" },
  { value: "THURSDAY", label: "Quinta" },
  { value: "FRIDAY", label: "Sexta" },
  { value: "SATURDAY", label: "Sábado" },
  { value: "SUNDAY", label: "Domingo" },
];

type Tab = "geral" | "pausas" | "horario";

export default function MerchantDetailPage() {
  const qc = useQueryClient();
  const params = useParams<{ id: string }>();
  const merchantId = params.id;
  const [tab, setTab] = useState<Tab>("geral");

  const merchant = useQuery({
    queryKey: ["merchant", merchantId],
    queryFn: () => apiGet<Merchant>(`/merchants/${merchantId}`),
  });

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
          <h1 className="flex items-center gap-2 text-3xl font-bold tracking-tight">
            <Store className="h-7 w-7" />
            {merchant.data?.name ?? "Carregando..."}
          </h1>
          {merchant.data?.corporate_name && (
            <p className="text-muted-foreground">{merchant.data.corporate_name}</p>
          )}
          {merchant.data?.ifood_merchant_id && (
            <p className="mt-1 font-mono text-xs text-muted-foreground">
              {merchant.data.ifood_merchant_id}
            </p>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        <TabBtn current={tab} value="geral" onClick={() => setTab("geral")} icon={<Store className="h-4 w-4" />}>
          Geral
        </TabBtn>
        <TabBtn current={tab} value="pausas" onClick={() => setTab("pausas")} icon={<CircleStop className="h-4 w-4" />}>
          Pausas
        </TabBtn>
        <TabBtn current={tab} value="horario" onClick={() => setTab("horario")} icon={<Clock className="h-4 w-4" />}>
          Horário
        </TabBtn>
      </div>

      {tab === "geral" && <GeralTab merchantId={merchantId} />}
      {tab === "pausas" && <PausasTab merchantId={merchantId} qc={qc} />}
      {tab === "horario" && <HorarioTab merchantId={merchantId} qc={qc} />}
    </div>
  );
}

function TabBtn({
  current,
  value,
  onClick,
  icon,
  children,
}: {
  current: Tab;
  value: Tab;
  onClick: () => void;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  const active = current === value;
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
        active
          ? "border-primary text-primary"
          : "border-transparent text-muted-foreground hover:text-foreground"
      }`}
    >
      {icon}
      {children}
    </button>
  );
}

// =============================================================================
// Tab Geral — status + disponibilidade
// =============================================================================
function GeralTab({ merchantId }: { merchantId: string }) {
  const status = useQuery({
    queryKey: ["merchant-status", merchantId],
    queryFn: () => apiGet<any[]>(`/merchants/${merchantId}/status`),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Disponibilidade / Status</CardTitle>
      </CardHeader>
      <CardContent>
        {status.isLoading ? (
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        ) : !status.data?.length ? (
          <p className="text-sm text-muted-foreground">
            Sem informações de status. Merchant pode não estar autorizado.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Operação</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Mensagem</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {status.data.map((s, i) => (
                <TableRow key={i}>
                  <TableCell className="font-mono text-xs">
                    {s.operation ?? "—"}
                  </TableCell>
                  <TableCell>
                    <Badge variant={s.state === "OK" ? "default" : "secondary"}>
                      {s.state ?? "—"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {s.message?.title ?? s.message ?? "—"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

// =============================================================================
// Tab Pausas
// =============================================================================
function PausasTab({
  merchantId,
  qc,
}: {
  merchantId: string;
  qc: ReturnType<typeof useQueryClient>;
}) {
  const [showForm, setShowForm] = useState(false);
  const [desc, setDesc] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");

  const list = useQuery({
    queryKey: ["interruptions", merchantId],
    queryFn: () =>
      apiGet<Interruption[]>(`/merchants/${merchantId}/interruptions`),
  });

  const create = useMutation({
    mutationFn: () =>
      apiPost(`/merchants/${merchantId}/interruptions`, {
        description: desc,
        start: new Date(start).toISOString(),
        end: new Date(end).toISOString(),
      }),
    onSuccess: () => {
      toast.success("Pausa criada — verifica no Portal iFood");
      setShowForm(false);
      setDesc("");
      setStart("");
      setEnd("");
      qc.invalidateQueries({ queryKey: ["interruptions", merchantId] });
    },
    onError: (e: any) => toast.error(e?.message ?? "Falha"),
  });

  const remove = useMutation({
    mutationFn: (id: string) =>
      apiDelete(`/merchants/${merchantId}/interruptions/${id}`),
    onSuccess: () => {
      toast.success("Pausa removida");
      qc.invalidateQueries({ queryKey: ["interruptions", merchantId] });
    },
    onError: (e: any) => toast.error(e?.message ?? "Falha ao remover"),
  });

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base">Pausas ativas/agendadas</CardTitle>
        <Button size="sm" onClick={() => setShowForm(!showForm)}>
          <Plus className="h-4 w-4" />
          Nova pausa
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {showForm && (
          <div className="space-y-3 rounded-md border bg-muted/30 p-4">
            <div className="space-y-1">
              <Label htmlFor="desc">Descrição</Label>
              <Input
                id="desc"
                value={desc}
                onChange={(e) => setDesc(e.target.value)}
                placeholder="Ex: Almoço, manutenção, evento privado"
              />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <Label htmlFor="start">Início</Label>
                <Input
                  id="start"
                  type="datetime-local"
                  value={start}
                  onChange={(e) => setStart(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="end">Fim</Label>
                <Input
                  id="end"
                  type="datetime-local"
                  value={end}
                  onChange={(e) => setEnd(e.target.value)}
                />
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={() => create.mutate()}
                disabled={create.isPending || !desc || !start || !end}
              >
                {create.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Save className="h-4 w-4" />
                )}
                Salvar pausa
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowForm(false)}
              >
                Cancelar
              </Button>
            </div>
          </div>
        )}

        {list.isLoading ? (
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        ) : !list.data?.length ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            Nenhuma pausa cadastrada.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Descrição</TableHead>
                <TableHead>Início</TableHead>
                <TableHead>Fim</TableHead>
                <TableHead className="w-[80px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.data.map((i) => (
                <TableRow key={i.id ?? Math.random()}>
                  <TableCell>{i.description ?? "—"}</TableCell>
                  <TableCell className="text-sm">
                    {i.start
                      ? new Date(i.start).toLocaleString("pt-BR")
                      : "—"}
                  </TableCell>
                  <TableCell className="text-sm">
                    {i.end ? new Date(i.end).toLocaleString("pt-BR") : "—"}
                  </TableCell>
                  <TableCell>
                    {i.id && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => remove.mutate(i.id!)}
                        disabled={remove.isPending}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

// =============================================================================
// Tab Horário
// =============================================================================
function HorarioTab({
  merchantId,
  qc,
}: {
  merchantId: string;
  qc: ReturnType<typeof useQueryClient>;
}) {
  const current = useQuery({
    queryKey: ["opening-hours", merchantId],
    queryFn: () => apiGet<OpeningHours>(`/merchants/${merchantId}/opening-hours`),
  });

  const [shifts, setShifts] = useState<Shift[]>([]);

  // Sincroniza state com query quando carrega
  function loadFromQuery() {
    setShifts(current.data?.shifts ?? []);
  }

  // Auto-load primeira vez
  if (!shifts.length && current.data?.shifts?.length) {
    setTimeout(() => loadFromQuery(), 0);
  }

  function addShift() {
    setShifts([
      ...shifts,
      { dayOfWeek: "MONDAY", start: "10:00:00", duration: 480 },
    ]);
  }

  function updateShift(idx: number, patch: Partial<Shift>) {
    setShifts(shifts.map((s, i) => (i === idx ? { ...s, ...patch } : s)));
  }

  function removeShift(idx: number) {
    setShifts(shifts.filter((_, i) => i !== idx));
  }

  const save = useMutation({
    mutationFn: () => apiPut(`/merchants/${merchantId}/opening-hours`, { shifts }),
    onSuccess: () => {
      toast.success("Horário atualizado — verifica no Portal iFood");
      qc.invalidateQueries({ queryKey: ["opening-hours", merchantId] });
    },
    onError: (e: any) => toast.error(e?.message ?? "Falha"),
  });

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base">Horário de funcionamento</CardTitle>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={addShift}>
            <Plus className="h-4 w-4" />
            Adicionar turno
          </Button>
          <Button
            size="sm"
            onClick={() => save.mutate()}
            disabled={save.isPending || !shifts.length}
          >
            {save.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <CalendarClock className="h-4 w-4" />
            )}
            Salvar
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {current.isLoading ? (
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        ) : !shifts.length ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            Nenhum turno cadastrado. Clica em "Adicionar turno" pra começar.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Dia</TableHead>
                <TableHead>Início (HH:MM:SS)</TableHead>
                <TableHead>Duração (min)</TableHead>
                <TableHead className="w-[80px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {shifts.map((s, idx) => (
                <TableRow key={idx}>
                  <TableCell>
                    <Select
                      value={s.dayOfWeek}
                      onValueChange={(v) =>
                        updateShift(idx, { dayOfWeek: v as DayOfWeek })
                      }
                    >
                      <SelectTrigger className="w-[140px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {DAYS.map((d) => (
                          <SelectItem key={d.value} value={d.value}>
                            {d.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </TableCell>
                  <TableCell>
                    <Input
                      value={s.start}
                      onChange={(e) =>
                        updateShift(idx, { start: e.target.value })
                      }
                      className="w-[120px] font-mono"
                    />
                  </TableCell>
                  <TableCell>
                    <Input
                      type="number"
                      min={1}
                      max={1440}
                      value={s.duration}
                      onChange={(e) =>
                        updateShift(idx, { duration: parseInt(e.target.value) || 0 })
                      }
                      className="w-[100px]"
                    />
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeShift(idx)}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
