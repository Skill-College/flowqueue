import { useId } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

/**
 * FlowQueue brand mark: a single source node fanning out to three consumer
 * nodes — the product's core idea (one message → many consumers). Paths draw
 * in and nodes pop on mount. Works on light and dark backgrounds.
 */
export function LogoMark({
  size = 36,
  animated = true,
  className,
}: {
  size?: number;
  animated?: boolean;
  className?: string;
}) {
  const gid = useId().replace(/:/g, "");
  const targets = [
    { x: 33, y: 9 },
    { x: 33, y: 20 },
    { x: 33, y: 31 },
  ];
  const path = (t: { x: number; y: number }) =>
    `M9 20 C 19 20, 21 ${t.y}, ${t.x} ${t.y}`;

  const draw = animated
    ? {
        initial: { pathLength: 0, opacity: 0 },
        animate: { pathLength: 1, opacity: 1 },
      }
    : {};
  const pop = animated
    ? { initial: { scale: 0, opacity: 0 }, animate: { scale: 1, opacity: 1 } }
    : {};

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 42 40"
      fill="none"
      className={cn("shrink-0", className)}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={`g-${gid}`} x1="0" y1="0" x2="42" y2="40" gradientUnits="userSpaceOnUse">
          <stop stopColor="#58CC02" />
          <stop offset="0.5" stopColor="#1CB0A8" />
          <stop offset="1" stopColor="#2BD4F0" />
        </linearGradient>
      </defs>

      {targets.map((t, i) => (
        <motion.path
          key={i}
          d={path(t)}
          stroke={`url(#g-${gid})`}
          strokeWidth={2.4}
          strokeLinecap="round"
          {...draw}
          transition={{ duration: 0.7, delay: 0.15 + i * 0.12, ease: "easeInOut" }}
        />
      ))}

      {/* source node */}
      <motion.circle
        cx={9}
        cy={20}
        r={5}
        fill={`url(#g-${gid})`}
        {...pop}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      />
      {/* consumer nodes */}
      {targets.map((t, i) => (
        <motion.circle
          key={i}
          cx={t.x}
          cy={t.y}
          r={3.6}
          fill="hsl(var(--background))"
          stroke={`url(#g-${gid})`}
          strokeWidth={2.4}
          {...pop}
          transition={{ duration: 0.4, delay: 0.5 + i * 0.12, ease: [0.16, 1, 0.3, 1] }}
        />
      ))}
    </svg>
  );
}

export function Logo({
  size = 36,
  animated = true,
  className,
  textClassName,
}: {
  size?: number;
  animated?: boolean;
  className?: string;
  textClassName?: string;
}) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <LogoMark size={size} animated={animated} />
      <span
        className={cn(
          "font-display text-xl font-bold tracking-tight",
          textClassName
        )}
      >
        Flow<span className="text-gradient">Queue</span>
      </span>
    </span>
  );
}
