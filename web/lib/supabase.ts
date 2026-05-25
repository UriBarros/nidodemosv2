import { createBrowserClient } from "@supabase/ssr";

export function createClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!url || !key) {
    // Happens when GitHub Secrets were not set before the Docker build ran.
    // NEXT_PUBLIC_* vars are baked into the bundle at build time.
    throw new Error(
      "Supabase não configurado. Defina NEXT_PUBLIC_SUPABASE_URL e " +
        "NEXT_PUBLIC_SUPABASE_ANON_KEY nos GitHub Secrets e faça um novo build.",
    );
  }

  return createBrowserClient(url, key);
}
