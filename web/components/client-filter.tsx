"use client";

import { useEffect, useState } from "react";
import { Loader2, Store, X } from "lucide-react";
import { apiGet } from "@/lib/api";
import type { Client } from "@/lib/types";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";

const ALL_VALUE = "__all__";

interface ClientFilterProps {
  value: string | null;
  onChange: (clientId: string | null) => void;
  className?: string;
}

/**
 * Dropdown reusável para filtrar dados por cliente.
 * value=null = "Todos os clientes". Caso contrário, UUID do client selecionado.
 */
export function ClientFilter({ value, onChange, className }: ClientFilterProps) {
  const [clients, setClients] = useState<Client[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancel = false;
    setLoading(true);
    apiGet<Client[]>("/clients")
      .then((data) => {
        if (!cancel) setClients(data);
      })
      .catch(() => {
        if (!cancel) setClients([]);
      })
      .finally(() => {
        if (!cancel) setLoading(false);
      });
    return () => {
      cancel = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Carregando clientes...
      </div>
    );
  }

  if (!clients || clients.length === 0) {
    return null; // Sem clientes ainda — não mostra filtro
  }

  return (
    <div className={`flex items-center gap-2 ${className ?? ""}`}>
      <Store className="h-4 w-4 text-muted-foreground" />
      <Select
        value={value ?? ALL_VALUE}
        onValueChange={(v) => onChange(v === ALL_VALUE ? null : v)}
      >
        <SelectTrigger className="h-9 w-[260px]">
          <SelectValue placeholder="Todos os clientes" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL_VALUE}>Todos os clientes</SelectItem>
          {clients.map((c) => (
            <SelectItem key={c.id} value={c.id}>
              {c.name}
              {c.ifood_merchant_id && (
                <span className="ml-2 font-mono text-xs text-muted-foreground">
                  {c.ifood_merchant_id.slice(0, 8)}…
                </span>
              )}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {value && (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onChange(null)}
          className="h-9 px-2"
          aria-label="Limpar filtro"
        >
          <X className="h-4 w-4" />
        </Button>
      )}
    </div>
  );
}
