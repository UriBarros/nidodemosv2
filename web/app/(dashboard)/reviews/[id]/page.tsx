"use client";

import Link from "next/link";
import { useState } from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  Loader2,
  MessageSquare,
  Send,
  Star,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { apiGet, apiPost } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";
import type { Review } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

export default function ReviewDetalhePage() {
  const qc = useQueryClient();
  const params = useParams<{ id: string }>();
  const reviewId = params.id;
  const [replyDraft, setReplyDraft] = useState("");
  const [showReply, setShowReply] = useState(false);

  const review = useQuery({
    queryKey: ["review", reviewId],
    queryFn: () => apiGet<Review>(`/reviews/${reviewId}`),
    retry: false,
  });

  const reply = useMutation({
    mutationFn: () =>
      apiPost<Review>(`/reviews/${reviewId}/reply`, { text: replyDraft.trim() }),
    onSuccess: () => {
      toast.success("Resposta enviada ao iFood");
      setReplyDraft("");
      setShowReply(false);
      qc.invalidateQueries({ queryKey: ["review", reviewId] });
    },
    onError: (e: any) => toast.error(e?.message ?? "Falha"),
  });

  if (review.isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Erro 404 explícito (cenário C2 — ID inexistente)
  if (review.isError) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" size="sm" asChild className="-ml-3">
          <Link href="/reviews">
            <ArrowLeft className="h-4 w-4" />
            Voltar
          </Link>
        </Button>
        <Card>
          <CardHeader className="text-center">
            <AlertTriangle className="mx-auto h-12 w-12 text-destructive" />
            <CardTitle className="mt-4">Avaliação não encontrada</CardTitle>
          </CardHeader>
          <CardContent className="text-center">
            <p className="text-sm text-muted-foreground">
              ID:{" "}
              <code className="rounded bg-muted px-1 py-0.5 font-mono">
                {reviewId}
              </code>
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              {(review.error as any)?.message ??
                "Esse ID não corresponde a nenhuma avaliação no sistema."}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!review.data) return null;

  const r = review.data;

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" asChild className="-ml-3">
        <Link href="/reviews">
          <ArrowLeft className="h-4 w-4" />
          Voltar
        </Link>
      </Button>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Star
                key={i}
                className={`h-5 w-5 ${
                  i < (r.score ?? 0)
                    ? "fill-amber-400 text-amber-400"
                    : "text-muted-foreground/30"
                }`}
              />
            ))}
            <span className="ml-2 text-base">{r.score ?? "—"} / 5</span>
            {r.answered && (
              <Badge variant="default" className="ml-auto">
                ✓ Respondida
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <dl className="grid gap-3 sm:grid-cols-2">
            <Field label="Cliente" value={r.customer_name ?? "Anônimo"} />
            <Field
              label="Data"
              value={r.created_at_ifood ? formatDateTime(r.created_at_ifood) : null}
            />
            <Field
              label="ID iFood (review)"
              value={r.ifood_review_id}
              mono
            />
            <Field
              label="ID pedido"
              value={r.ifood_order_id ?? null}
              mono
            />
          </dl>

          {r.comment && (
            <>
              <Separator />
              <div>
                <div className="mb-1 text-xs uppercase text-muted-foreground">
                  Comentário do cliente
                </div>
                <p className="rounded-md bg-muted/30 p-3 text-sm">{r.comment}</p>
              </div>
            </>
          )}

          {r.answered && r.answer_text && (
            <>
              <Separator />
              <div>
                <div className="mb-1 text-xs uppercase text-muted-foreground">
                  Nossa resposta
                </div>
                <p className="rounded-md bg-emerald-50 p-3 text-sm">
                  {r.answer_text}
                </p>
              </div>
            </>
          )}

          {!r.answered && (
            <>
              <Separator />
              {showReply ? (
                <div className="space-y-2">
                  <textarea
                    value={replyDraft}
                    onChange={(e) => setReplyDraft(e.target.value)}
                    maxLength={1000}
                    rows={4}
                    placeholder="Digite a resposta ao cliente..."
                    className="w-full rounded-md border border-input bg-background p-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                    autoFocus
                  />
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs text-muted-foreground">
                      {replyDraft.length}/1000
                    </span>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setShowReply(false);
                          setReplyDraft("");
                        }}
                      >
                        <X className="h-4 w-4" />
                        Cancelar
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => reply.mutate()}
                        disabled={reply.isPending || !replyDraft.trim()}
                      >
                        {reply.isPending ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Send className="h-4 w-4" />
                        )}
                        Enviar
                      </Button>
                    </div>
                  </div>
                </div>
              ) : (
                <Button onClick={() => setShowReply(true)}>
                  <MessageSquare className="h-4 w-4" />
                  Responder avaliação
                </Button>
              )}
            </>
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
