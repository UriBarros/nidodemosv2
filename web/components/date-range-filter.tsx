"use client";

import { Calendar } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export type DateRangePreset = "today" | "7d" | "30d" | "90d" | "all";

interface DateRangeFilterProps {
  value: DateRangePreset;
  onChange: (preset: DateRangePreset) => void;
  className?: string;
}

const PRESETS: { value: DateRangePreset; label: string }[] = [
  { value: "today", label: "Hoje" },
  { value: "7d", label: "Últimos 7 dias" },
  { value: "30d", label: "Últimos 30 dias" },
  { value: "90d", label: "Últimos 90 dias" },
  { value: "all", label: "Tudo" },
];

export function DateRangeFilter({
  value,
  onChange,
  className,
}: DateRangeFilterProps) {
  return (
    <div className={`flex items-center gap-2 ${className ?? ""}`}>
      <Calendar className="h-4 w-4 text-muted-foreground" />
      <Select value={value} onValueChange={(v) => onChange(v as DateRangePreset)}>
        <SelectTrigger className="h-9 w-[180px]">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {PRESETS.map((p) => (
            <SelectItem key={p.value} value={p.value}>
              {p.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

/**
 * Converte preset em { begin, end } ISO strings (ou undefined se 'all').
 * - today: meia-noite local de hoje
 * - 7d / 30d / 90d: N dias atrás
 * - all: sem filtro
 */
export function presetToRange(preset: DateRangePreset): {
  begin?: string;
  end?: string;
} {
  if (preset === "all") return {};

  const now = new Date();
  const end = now.toISOString();

  if (preset === "today") {
    const begin = new Date(now);
    begin.setHours(0, 0, 0, 0);
    return { begin: begin.toISOString(), end };
  }

  const daysMap: Record<Exclude<DateRangePreset, "all" | "today">, number> = {
    "7d": 7,
    "30d": 30,
    "90d": 90,
  };
  const days = daysMap[preset as "7d" | "30d" | "90d"];
  const begin = new Date(now);
  begin.setDate(begin.getDate() - days);
  return { begin: begin.toISOString(), end };
}

/**
 * Converte preset em { begin, end } como YYYY-MM-DD (pra endpoints
 * que usam tipo `date` em vez de datetime — ex: /financial/summary).
 */
export function presetToDateRange(preset: DateRangePreset): {
  begin?: string;
  end?: string;
} {
  const r = presetToRange(preset);
  return {
    begin: r.begin?.slice(0, 10),
    end: r.end?.slice(0, 10),
  };
}
