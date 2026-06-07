import { type ReactNode, useEffect } from "react";
import { useLocation } from "react-router-dom";
import { MarketingNav } from "./MarketingNav";
import { Footer } from "./Footer";
import { useLenis } from "@/lib/useLenis";

export function MarketingLayout({ children }: { children: ReactNode }) {
  useLenis();
  const { pathname } = useLocation();

  // Reset scroll to the top on every marketing route change.
  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [pathname]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <MarketingNav />
      <main className="pt-16">{children}</main>
      <Footer />
    </div>
  );
}
