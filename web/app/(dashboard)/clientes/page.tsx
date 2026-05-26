"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Loader2, Plus, RefreshCw, Store } from "lucide-react";
import { toast } from "sonner";
import { apiGet } from "@/lib/api";
import type { Client } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const STATUS_LABEL: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  pending: { label: "Aguardando autorização", variant: "outline" },
  connected: { label: "Conectado", variant: "default" },
  disconnected: { label: "Desconectado", variant: "secondary" },
  error: { label: "Erro", variant: "destructive" },
};

export default function ClientesPage() {
  const [clients, setClients] = useState<Client[] | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const data = await apiGet<Client[]>("/clients");
      setClients(data);
    } catch (e: any) {
      toast.error(e?.message ?? "Falha ao carregar clientes");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Clientes</h1>
          <p className="text-muted-foreground">
            Lojistas iFood gerenciados pela Aceleradora.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Atualizar
          </Button>
          <Button asChild>
            <Link href="/clientes/novo">
              <Plus className="h-4 w-4" />
              Novo cliente
            </Link>
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Store className="h-5 w-5" />
            {clients?.length ?? 0} cliente(s)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {clients === null ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : clients.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground">
              Nenhum cliente cadastrado ainda.
              <div className="mt-4">
                <Button asChild>
                  <Link href="/clientes/novo">
                    <Plus className="h-4 w-4" />
                    Cadastrar primeiro cliente
                  </Link>
                </Button>
              </div>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nome</TableHead>
                  <TableHead>CNPJ</TableHead>
                  <TableHead>Telefone</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Conectado em</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {clients.map((c) => {
                  const s = STATUS_LABEL[c.status] ?? STATUS_LABEL.pending;
                  return (
                    <TableRow key={c.id} className="cursor-pointer">
                      <TableCell>
                        <Link
                          href={`/clientes/${c.id}`}
                          className="font-medium hover:underline"
                        >
                          {c.name}
                        </Link>
                        {c.legal_name && (
                          <div className="text-xs text-muted-foreground">
                            {c.legal_name}
                          </div>
                        )}
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {c.cnpj || "—"}
                      </TableCell>
                      <TableCell>{c.phone || "—"}</TableCell>
                      <TableCell>
                        <Badge variant={s.variant}>{s.label}</Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {c.connected_at
                          ? new Date(c.connected_at).toLocaleString("pt-BR")
                          : "—"}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
