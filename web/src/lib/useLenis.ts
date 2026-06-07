import { useEffect } from "react";
import Lenis from "lenis";

/**
 * Mount smooth-scrolling for the marketing pages. Disabled automatically when
 * the visitor prefers reduced motion. Cleans up on unmount so the app routes
 * (sidebar dashboard) keep native scrolling.
 */
export function useLenis() {
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const lenis = new Lenis({
      duration: 1.1,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      smoothWheel: true,
    });

    let raf = 0;
    const loop = (time: number) => {
      lenis.raf(time);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);

    return () => {
      cancelAnimationFrame(raf);
      lenis.destroy();
    };
  }, []);
}
