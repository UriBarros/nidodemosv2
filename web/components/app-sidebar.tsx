"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LayoutDashboard, LogOut, ShoppingBag, Star, Wallet } from "lucide-react";
import { createClient } from "@/lib/supabase";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

const ITEMS = [
  { href: "/", label: "Visão geral", icon: LayoutDashboard },
  { href: "/pedidos", label: "Pedidos", icon: ShoppingBag },
  { href: "/financeiro", label: "Financeiro", icon: Wallet },
  { href: "/reviews", label: "Reviews", icon: Star },
];

export function AppSidebar({ userEmail }: { userEmail?: string | null }) {
  const pathname = usePathname();
  const router = useRouter();

  async function handleSignOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  }

  return (
    <aside className="flex h-screen w-64 flex-col bg-sidebar text-sidebar-foreground">
      {/* Logo */}
      <div className="flex h-20 items-center gap-3 border-b border-white/10 px-4">
        <Image
          src="/brand/logo-white.png"
          alt="Aceleradora GTR"
          width={48}
          height={48}
          className="h-12 w-12 object-contain"
          priority
        />
        <div className="flex flex-col leading-tight">
          <span className="text-lg font-bold tracking-tight">gtrifood</span>
          <span className="text-[0.7rem] uppercase tracking-wider text-white/70">
            Aceleradora GTR
          </span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-1 p-3">
        {ITEMS.map((item) => {
          const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground/85 hover:bg-white/10 hover:text-sidebar-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* User + Sair */}
      <div className="border-t border-white/10 p-4">
        {userEmail && (
          <div className="mb-3 px-1 text-xs text-sidebar-foreground/70 truncate" title={userEmail}>
            {userEmail}
          </div>
        )}
        <Button
          variant="outline"
          size="sm"
          onClick={handleSignOut}
          className="w-full border-white/30 bg-white/10 text-white hover:bg-white/20 hover:text-white"
        >
          <LogOut className="h-4 w-4" />
          Sair
        </Button>
        <Separator className="my-4 bg-white/10" />
        <div className="space-y-1 text-[0.7rem] text-sidebar-foreground/60">
          <Link href="/privacidade" className="block hover:text-sidebar-foreground/90">
            Privacidade
          </Link>
          <Link href="/termos" className="block hover:text-sidebar-foreground/90">
            Termos de uso
          </Link>
        </div>
      </div>
    </aside>
  );
}
