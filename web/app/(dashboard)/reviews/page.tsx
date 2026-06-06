"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, MessageSquare, RefreshCw, Send, Star, X } from "lucide-react";
import { toast } from "sonner";
import { apiGet, apiPost } from "@/lib/api";
import type { Merchant, Review } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { StatCard } from "@/components/stat-card";
import { ClientFilter } from "@/components/client-filter";

type Summary = {
  total: number;
  average_score: number;
  answered_count: number;
  answered_pct: number;
};

export default function ReviewsPage() {
  const qc = useQueryClient();
  const [clientId, setClientId] = useState<string | null>(null);
  const [merchantId, setMerchantId] = useState<string>("all");
  const [replyFor, setReplyFor] = useState<string | null>(null);
  const [replyDraft, setReplyDraft] = useState<string>("");

  const merchants = useQuery({
    queryKey: ["merchants"],
    queryFn: () => apiGet<Merchant[]>("/merchants"),
  });

  const summary = useQuery({
    queryKey: ["reviews-summary", clientId, merchantId],
    queryFn: () =>
      apiGet<Summary>("/reviews/summary", {
        client_id: clientId ?? undefined,
        merchant_id: merchantId === "all" ? undefined : merchantId,
      }),
  });

  const list = useQuery({
    queryKey: ["reviews-list", clientId, merchantId],
    queryFn: () =>
      apiGet<Review[]>("/reviews", {
        client_id: clientId ?? undefined,
        merchant_id: merchantId === "all" ? undefined : merchantId,
        limit: 50,
      }),
  });

  const sync = useMutation({
    mutationFn: () =>
      apiPost<{ message: string }>("/reviews/sync", undefined, {
        merchant_id: merchantId === "all" ? merchants.data?.[0]?.id : merchantId,
      }),
    onSuccess: (d) => {
      toast.success(d.message);
      qc.invalidateQueries({ queryKey: ["reviews-summary"] });
      qc.invalidateQueries({ queryKey: ["reviews-list"] });
    },
    onError: (e: any) => toast.error(e?.message ?? "Falha"),
  });

  const reply = useMutation({
    mutationFn: ({ id, text }: { id: string; text: string }) =>
      apiPost<Review>(`/reviews/${id}/reply`, { text }),
    onSuccess: () => {
      setReplyFor(null);
      setReplyDraft("");
      qc.invalidateQueries({ queryKey: ["reviews-list"] });
      qc.invalidateQueries({ queryKey: ["reviews-summary"] });
      toast.success("Resposta enviada ao iFood");
    },
    onError: (e: any) => toast.error(e?.message ?? "Falha ao responder"),
  });

  function startReply(reviewId: string) {
    setReplyFor(reviewId);
    setReplyDraft("");
  }

  function cancelReply() {
    setReplyFor(null);
    setReplyDraft("");
  }

  function sendReply(reviewId: string) {
    const text = replyDraft.trim();
    if (!text) {
      toast.error("Digite uma resposta");
      return;
    }
    if (text.length > 1000) {
      toast.error("Resposta excede 1000 caracteres");
      return;
    }
    reply.mutate({ id: reviewId, text });
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Reviews</h1>
          <p className="text-sm text-muted-foreground">Avaliações dos seus clientes iFood.</p>
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
        <StatCard label="Total" value={summary.data?.total ?? 0} icon={MessageSquare} />
        <StatCard
          label="Média"
          value={`${summary.data?.average_score ?? 0} ★`}
          icon={Star}
          tone="warning"
        />
        <StatCard
          label="Respondidas"
          value={`${summary.data?.answered_pct ?? 0}%`}
          icon={MessageSquare}
          tone="success"
          hint={`${summary.data?.answered_count ?? 0} de ${summary.data?.total ?? 0}`}
        />
      </div>

      {list.data?.length ? (
        <div className="grid gap-3">
          {list.data.map((r) => (
            <Card key={r.id}>
              <CardContent className="space-y-2 p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <Star
                        key={i}
                        className={`h-4 w-4 ${i < (r.score ?? 0) ? "fill-amber-400 text-amber-400" : "text-muted-foreground/30"}`}
                      />
                    ))}
                    <span className="ml-2 text-sm font-medium">{r.customer_name ?? "Anônimo"}</span>
                    {r.ifood_order_id && (
                      <span className="ml-2 font-mono text-[10px] text-muted-foreground">
                        #{r.ifood_order_id.slice(0, 8)}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {r.created_at_ifood && (
                      <span className="text-xs text-muted-foreground">
                        {new Date(r.created_at_ifood).toLocaleDateString("pt-BR")}
                      </span>
                    )}
                    {r.answered && (
                      <span className="text-xs font-medium text-emerald-700">✓ Respondida</span>
                    )}
                  </div>
                </div>
                {r.comment && <p className="text-sm">{r.comment}</p>}
                {r.answer_text && (
                  <div className="rounded-md bg-muted/50 p-2 text-sm">
                    <strong>Resposta:</strong> {r.answer_text}
                  </div>
                )}

                {/* Bloco de responder */}
                {!r.answered && (
                  <div className="pt-1">
                    {replyFor === r.id ? (
                      <div className="space-y-2">
                        <textarea
                          value={replyDraft}
                          onChange={(e) => setReplyDraft(e.target.value)}
                          maxLength={1000}
                          rows={3}
                          autoFocus
                          placeholder="Digite a resposta ao cliente..."
                          className="w-full rounded-md border border-input bg-background p-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                          onKeyDown={(e) => {
                            if (e.key === "Escape") cancelReply();
                            if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                              sendReply(r.id);
                            }
                          }}
                        />
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs text-muted-foreground">
                            {replyDraft.length}/1000 · Ctrl+Enter envia
                          </span>
                          <div className="flex gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={cancelReply}
                              disabled={reply.isPending}
                            >
                              <X className="h-4 w-4" />
                              Cancelar
                            </Button>
                            <Button
                              size="sm"
                              onClick={() => sendReply(r.id)}
                              disabled={reply.isPending}
                            >
                              {reply.isPending ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <Send className="h-4 w-4" />
                              )}
                              Enviar resposta
                            </Button>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => startReply(r.id)}
                      >
                        <MessageSquare className="h-4 w-4" />
                        Responder
                      </Button>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="flex h-40 items-center justify-center text-sm text-muted-foreground">
            Nenhuma review. Use "Sincronizar".
          </CardContent>
        </Card>
      )}
    </div>
  );
}
