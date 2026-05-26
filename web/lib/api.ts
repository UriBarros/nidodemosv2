"use client";

import { createClient } from "@/lib/supabase";

const PUBLIC_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "/api";

export class ApiError extends Error {
  constructor(public status: number, message: string, public body?: unknown) {
    super(message);
  }
}

async function authHeaders(): Promise<HeadersInit> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session?.access_token
    ? { Authorization: `Bearer ${session.access_token}` }
    : {};
}

export async function apiGet<T>(
  path: string,
  params?: Record<string, string | number | boolean | undefined | null>,
): Promise<T> {
  const url = new URL(`${PUBLIC_BASE}${path}`, window.location.origin);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null) url.searchParams.set(k, String(v));
    }
  }
  const res = await fetch(url.toString(), {
    headers: { ...(await authHeaders()) },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    let msg = `GET ${path} → ${res.status}`;
    try {
      const j = JSON.parse(body);
      if (j?.detail) msg = String(j.detail);
    } catch {
      // body não é JSON
    }
    throw new ApiError(res.status, msg, body);
  }
  return (await res.json()) as T;
}

export async function apiDelete(path: string): Promise<void> {
  const url = new URL(`${PUBLIC_BASE}${path}`, window.location.origin);
  const res = await fetch(url.toString(), {
    method: "DELETE",
    headers: { ...(await authHeaders()) },
  });
  if (!res.ok && res.status !== 204) {
    const body = await res.text().catch(() => "");
    throw new ApiError(res.status, `DELETE ${path} → ${res.status}`, body);
  }
}

export async function apiPost<T>(
  path: string,
  body?: unknown,
  params?: Record<string, string | number | undefined>,
): Promise<T> {
  const url = new URL(`${PUBLIC_BASE}${path}`, window.location.origin);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined) url.searchParams.set(k, String(v));
    }
  }
  const res = await fetch(url.toString(), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(await authHeaders()),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    // Tenta extrair "detail" do JSON do FastAPI (HTTPException padrão)
    let msg = `POST ${path} → ${res.status}`;
    try {
      const j = JSON.parse(text);
      if (j?.detail) msg = String(j.detail);
    } catch {
      // body não é JSON, mantém msg genérica
    }
    throw new ApiError(res.status, msg, text);
  }
  const text = await res.text();
  return (text ? JSON.parse(text) : null) as T;
}
