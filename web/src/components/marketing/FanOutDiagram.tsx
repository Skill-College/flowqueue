import { useId } from "react";
import { motion } from "framer-motion";
import { Globe, Webhook, Boxes } from "lucide-react";

/**
 * Animated "fan-out" diagram: one producer publishes to a queue, which delivers
 * independently to three consumer types (HTTP pull, Webhook push, SDK worker).
 * Message dots travel the paths on a loop. Pure SVG + framer-motion.
 */
const consumers = [
  { y: 30, label: "HTTP pull", icon: Globe },
  { y: 100, label: "Webhook", icon: Webhook },
  { y: 170, label: "SDK worker", icon: Boxes },
];

export function FanOutDiagram() {
  const gid = useId().replace(/:/g, "");
  const srcX = 70;
  const qX = 195;
  const dstX = 320;

  return (
    <div className="relative w-full">
      <svg viewBox="0 0 420 200" className="w-full" role="img" aria-label="Message fan-out diagram">
        <defs>
          <linearGradient id={`fg-${gid}`} x1="0" y1="0" x2="420" y2="0" gradientUnits="userSpaceOnUse">
            <stop stopColor="#58CC02" />
            <stop offset="0.5" stopColor="#1CB0A8" />
            <stop offset="1" stopColor="#2BD4F0" />
          </linearGradient>
        </defs>

        {/* producer -> queue */}
        <path
          d={`M${srcX + 26} 100 H ${qX - 26}`}
          stroke={`url(#fg-${gid})`}
          strokeWidth={2}
          fill="none"
        />
        <motion.circle
          r={4}
          fill="#58CC02"
          cy={100}
          animate={{ cx: [srcX + 26, qX - 26] }}
          transition={{ duration: 1.1, repeat: Infinity, ease: "easeInOut", repeatDelay: 0.6 }}
        />

        {/* queue -> consumers */}
        {consumers.map((c, i) => (
          <g key={i}>
            <path
              d={`M${qX + 26} 100 C ${qX + 70} 100, ${dstX - 70} ${c.y}, ${dstX - 26} ${c.y}`}
              stroke={`url(#fg-${gid})`}
              strokeWidth={2}
              fill="none"
              opacity={0.7}
            />
            <motion.circle
              r={3.5}
              fill="#2BD4F0"
              cy={100}
              cx={qX + 26}
              animate={{
                cx: [qX + 26, dstX - 26],
                cy: [100, c.y],
              }}
              transition={{
                duration: 1.2,
                repeat: Infinity,
                ease: "easeInOut",
                delay: 0.9 + i * 0.18,
                repeatDelay: 0.5,
              }}
            />
          </g>
        ))}

        {/* producer node */}
        <g>
          <rect x={srcX - 26} y={84} width={52} height={32} rx={9} className="fill-card stroke-border" strokeWidth={1.5} />
          <text x={srcX} y={104} textAnchor="middle" className="fill-foreground" fontSize={11} fontWeight={600}>
            Producer
          </text>
        </g>

        {/* queue node */}
        <g>
          <rect x={qX - 26} y={82} width={52} height={36} rx={10} fill={`url(#fg-${gid})`} />
          <text x={qX} y={104} textAnchor="middle" fill="#fff" fontSize={11} fontWeight={700}>
            Queue
          </text>
        </g>
      </svg>

      {/* consumer chips overlaid on the right */}
      <div className="pointer-events-none absolute inset-y-0 right-0 flex w-[26%] flex-col justify-between py-1">
        {consumers.map((c) => (
          <div
            key={c.label}
            className="glass flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs font-medium shadow-sm"
          >
            <c.icon size={14} className="text-primary" />
            {c.label}
          </div>
        ))}
      </div>
    </div>
  );
}
