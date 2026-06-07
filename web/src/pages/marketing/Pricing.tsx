import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, Check, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Section, SectionHeading } from "@/components/marketing/Section";
import { Reveal } from "@/components/marketing/Reveal";

const betaFeatures = [
  "Unlimited queues & consumers",
  "Fan-out to HTTP, SDK & webhook consumers",
  "Retries, visibility timeouts & dead-letter queue",
  "Replay & backfill",
  "Conditional webhook routing + HMAC signing",
  "Tamper-evident audit log",
  "Scoped API keys",
  "Python SDK + full HTTP API",
];

const futureTiers = [
  {
    name: "Starter",
    price: "$—",
    blurb: "For small teams shipping to production.",
    points: ["Higher throughput limits", "Longer message retention", "Email support"],
  },
  {
    name: "Pro",
    price: "$—",
    blurb: "For high-volume, multi-team workloads.",
    points: ["Priority delivery & SLAs", "Advanced metrics & alerts", "SSO & audit export"],
  },
];

const faqs = [
  {
    q: "Is it really free?",
    a: "Yes — FlowQueue is free during the public beta. No credit card required.",
  },
  {
    q: "What happens to my data when paid plans launch?",
    a: "Your account and data carry over. Beta users will get advance notice and a generous transition window before any limits apply.",
  },
  {
    q: "Are there limits during beta?",
    a: "We apply fair-use limits to keep the service healthy. If you have a heavy workload, reach out via the feedback page.",
  },
];

export function Pricing() {
  return (
    <>
      <Section className="pt-16 sm:pt-24">
        <SectionHeading
          eyebrow="Pricing"
          title={
            <>
              Free while we&apos;re in <span className="text-gradient">beta</span>
            </>
          }
          subtitle="Use every feature, at no cost, while FlowQueue is in public beta. Paid tiers are coming — beta users get the best deal."
        />

        <div className="mx-auto grid max-w-5xl gap-6 lg:grid-cols-[1.1fr_1fr]">
          {/* Beta plan */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            className="relative overflow-hidden rounded-3xl border-2 border-primary/60 bg-card/70 p-8 backdrop-blur-sm"
          >
            <div className="pointer-events-none absolute right-0 top-0 h-40 w-40 brand-glow rounded-full" />
            <span className="inline-flex items-center gap-1.5 rounded-full bg-brand-gradient px-3 py-1 text-xs font-semibold text-white">
              <Sparkles size={13} /> Current plan
            </span>
            <h3 className="mt-5 font-display text-2xl font-bold">Beta</h3>
            <div className="mt-2 flex items-end gap-2">
              <span className="font-display text-5xl font-bold text-gradient">Free</span>
              <span className="mb-1.5 text-sm text-muted-foreground">while in beta</span>
            </div>
            <p className="mt-3 text-sm text-muted-foreground">
              Everything in FlowQueue, no credit card.
            </p>
            <ul className="mt-6 grid gap-3 sm:grid-cols-2">
              {betaFeatures.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm">
                  <Check size={16} className="mt-0.5 shrink-0 text-primary" />
                  <span>{f}</span>
                </li>
              ))}
            </ul>
            <Link to="/register" className="mt-8 block">
              <Button size="lg" className="w-full shadow-lg shadow-primary/25">
                Start free <ArrowRight size={16} />
              </Button>
            </Link>
          </motion.div>

          {/* Future tiers */}
          <div className="grid gap-6">
            {futureTiers.map((t, i) => (
              <Reveal key={t.name} delay={i * 0.1}>
                <div className="relative h-full rounded-3xl border border-dashed border-border bg-card/40 p-7">
                  <span className="absolute right-5 top-5 rounded-full border border-border bg-secondary px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                    Coming soon
                  </span>
                  <h3 className="font-display text-xl font-bold text-muted-foreground">{t.name}</h3>
                  <div className="mt-1 font-display text-3xl font-bold text-muted-foreground/70">
                    {t.price}
                  </div>
                  <p className="mt-2 text-sm text-muted-foreground">{t.blurb}</p>
                  <ul className="mt-4 space-y-2">
                    {t.points.map((p) => (
                      <li key={p} className="flex items-start gap-2 text-sm text-muted-foreground">
                        <Check size={15} className="mt-0.5 shrink-0 opacity-50" />
                        <span>{p}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </Section>

      <Section className="py-12">
        <SectionHeading eyebrow="FAQ" title="Questions, answered" />
        <div className="mx-auto max-w-2xl space-y-4">
          {faqs.map((f, i) => (
            <Reveal key={f.q} delay={i * 0.06}>
              <div className="rounded-2xl border border-border bg-card/60 p-6">
                <h3 className="font-semibold">{f.q}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{f.a}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </Section>
    </>
  );
}
