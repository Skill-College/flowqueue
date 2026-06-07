import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Database,
  GitFork,
  History,
  ListChecks,
  ShieldCheck,
  Webhook,
  Terminal,
  Sparkles,
} from "lucide-react";
import { LogoMark } from "@/components/Logo";
import { Button } from "@/components/ui/button";
import { Section, SectionHeading } from "@/components/marketing/Section";
import { Reveal } from "@/components/marketing/Reveal";
import { FeatureCard } from "@/components/marketing/FeatureCard";
import { FanOutDiagram } from "@/components/marketing/FanOutDiagram";
import { ParticleField } from "@/components/marketing/ParticleField";
import { CodeBlock } from "@/components/marketing/CodeBlock";

const features = [
  {
    icon: Database,
    title: "Durable by default",
    description:
      "Every message and delivery is persisted in PostgreSQL — no Redis, no data loss on restart. Your queue is as durable as your database.",
  },
  {
    icon: GitFork,
    title: "Fan-out to many consumers",
    description:
      "One message, many independent consumers. Each gets its own delivery with separate retries, status and audit trail.",
  },
  {
    icon: ListChecks,
    title: "Per-consumer lifecycle",
    description:
      "pending → processing → completed / failed / dead. Visibility timeouts reclaim stuck work; a DLQ catches what never succeeds.",
  },
  {
    icon: Webhook,
    title: "Webhooks with routing",
    description:
      "Push to HTTPS endpoints with HMAC signing and conditional routing rules — deliver only the messages each endpoint cares about.",
  },
  {
    icon: History,
    title: "Replay & backfill",
    description:
      "Re-deliver failed messages, a date range, or specific IDs — rate-limited and safe. Recover from a bad deploy in one click.",
  },
  {
    icon: ShieldCheck,
    title: "Tamper-evident audit log",
    description:
      "Every state transition is appended to an HMAC-chained log. Know exactly what happened to every message, when, and why.",
  },
];

const stats = [
  { value: "100%", label: "Postgres-backed durability" },
  { value: "3", label: "Consumer types — pull, SDK, webhook" },
  { value: "0", label: "Extra infra to run" },
  { value: "Free", label: "During public beta" },
];

const quickstart = `pip install flowqueue`;

const codeSample = `from flowqueue import FlowQueueClient, FlowQueueConsumer

client = FlowQueueClient("https://your-host", "fq_your_api_key")

# 1. create a durable queue + a pull consumer
queue = client.create_queue("orders", max_retries=5, dlq_enabled=True)
consumer = client.create_consumer(queue["id"], "billing", type="http")

# 2. publish (idempotent)
client.publish(queue["id"], {"order_id": 42}, idempotency_key="order-42")

# 3. consume — return to complete, raise to retry
FlowQueueConsumer(client, consumer["id"]).run(
    lambda d: charge(d.payload["order_id"])
)`;

export function Home() {
  return (
    <>
      {/* ---------------------------------------------------------------- */}
      {/* Hero                                                             */}
      {/* ---------------------------------------------------------------- */}
      <section className="relative overflow-hidden">
        {/* gradient blobs */}
        <div className="pointer-events-none absolute inset-0 -z-10">
          <div className="brand-glow absolute left-1/2 top-[-10%] h-[480px] w-[480px] -translate-x-1/2 animate-blob rounded-full" />
          <div className="absolute right-[10%] top-[20%] h-72 w-72 animate-blob rounded-full bg-[#2BD4F0]/10 blur-3xl [animation-delay:4s]" />
          <div className="absolute left-[8%] bottom-[5%] h-72 w-72 animate-blob rounded-full bg-[#58CC02]/10 blur-3xl [animation-delay:8s]" />
        </div>
        <ParticleField className="pointer-events-none absolute inset-0 -z-10 opacity-70" />
        <div className="pointer-events-none absolute inset-0 -z-10 bg-grid-faint bg-[size:44px_44px] opacity-[0.15] [mask-image:radial-gradient(ellipse_at_center,black,transparent_75%)]" />

        <div className="mx-auto max-w-6xl px-5 pb-20 pt-20 sm:pt-28">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            className="mb-8 flex justify-center"
          >
            <LogoMark size={72} />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="mx-auto mb-5 flex w-fit items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-4 py-1.5 text-sm font-medium text-primary"
          >
            <Sparkles size={14} />
            Now in public beta — free to use
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
            className="mx-auto max-w-4xl text-center font-display text-4xl font-bold leading-[1.1] tracking-tight sm:text-6xl"
          >
            Durable message queues with{" "}
            <span className="text-gradient">fan-out, replay</span> &amp; webhooks
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.25, ease: [0.16, 1, 0.3, 1] }}
            className="mx-auto mt-6 max-w-2xl text-center text-lg text-muted-foreground"
          >
            FlowQueue is a Postgres-backed message processing platform. Publish once,
            deliver to many consumers — pull over HTTP, run an SDK worker, or push to a
            webhook. Every delivery is tracked, retried and replayable.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.35 }}
            className="mt-9 flex flex-wrap items-center justify-center gap-3"
          >
            <Link to="/register">
              <Button size="lg" className="shadow-xl shadow-primary/30">
                Start free <ArrowRight size={16} />
              </Button>
            </Link>
            <Link to="/docs/api">
              <Button size="lg" variant="outline">
                <Terminal size={16} /> Read the docs
              </Button>
            </Link>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.5 }}
            className="mx-auto mt-16 max-w-3xl rounded-2xl border border-border bg-card/60 p-6 backdrop-blur-sm"
          >
            <FanOutDiagram />
          </motion.div>
        </div>
      </section>

      {/* ---------------------------------------------------------------- */}
      {/* Features                                                         */}
      {/* ---------------------------------------------------------------- */}
      <Section id="features">
        <SectionHeading
          eyebrow="Why FlowQueue"
          title="Everything you need to move messages reliably"
          subtitle="Built for teams who want queue semantics, fan-out and full observability without standing up a broker."
        />
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f, i) => (
            <FeatureCard key={f.title} {...f} delay={i * 0.06} />
          ))}
        </div>
      </Section>

      {/* ---------------------------------------------------------------- */}
      {/* Code / DX                                                        */}
      {/* ---------------------------------------------------------------- */}
      <Section className="py-12 sm:py-16">
        <div className="grid items-center gap-10 lg:grid-cols-2">
          <Reveal direction="right">
            <span className="mb-3 inline-block rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-primary">
              Developer first
            </span>
            <h2 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">
              From zero to consuming in <span className="text-gradient">5 lines</span>
            </h2>
            <p className="mt-4 text-muted-foreground">
              Use the official Python SDK, or talk to the plain HTTP API from any language.
              Scoped API keys, idempotent publishes, and a worker loop that handles retries
              for you.
            </p>
            <div className="mt-6 max-w-xs">
              <CodeBlock code={quickstart} lang="bash" />
            </div>
            <div className="mt-6 flex gap-3">
              <Link to="/docs/sdk">
                <Button variant="outline">
                  SDK reference <ArrowRight size={15} />
                </Button>
              </Link>
              <Link to="/docs/api">
                <Button variant="ghost">HTTP API</Button>
              </Link>
            </div>
          </Reveal>

          <Reveal direction="left" delay={0.1}>
            <CodeBlock code={codeSample} lang="python" />
          </Reveal>
        </div>
      </Section>

      {/* ---------------------------------------------------------------- */}
      {/* Stats band                                                       */}
      {/* ---------------------------------------------------------------- */}
      <Section className="py-12">
        <Reveal>
          <div className="grid gap-px overflow-hidden rounded-2xl border border-border bg-border sm:grid-cols-2 lg:grid-cols-4">
            {stats.map((s) => (
              <div key={s.label} className="bg-card p-8 text-center">
                <div className="font-display text-3xl font-bold text-gradient">{s.value}</div>
                <div className="mt-2 text-sm text-muted-foreground">{s.label}</div>
              </div>
            ))}
          </div>
        </Reveal>
      </Section>

      {/* ---------------------------------------------------------------- */}
      {/* Final CTA                                                        */}
      {/* ---------------------------------------------------------------- */}
      <Section className="py-20">
        <Reveal>
          <div className="relative overflow-hidden rounded-3xl border border-primary/30 bg-brand-gradient bg-[size:200%_200%] p-10 text-center text-white animate-gradient-pan sm:p-16">
            <div className="pointer-events-none absolute inset-0 bg-grid-faint bg-[size:40px_40px] opacity-20" />
            <h2 className="relative font-display text-3xl font-bold tracking-tight sm:text-4xl">
              Ship reliable messaging today
            </h2>
            <p className="relative mx-auto mt-4 max-w-xl text-white/90">
              Free during beta. No credit card. Create a queue and publish your first
              message in minutes.
            </p>
            <div className="relative mt-8 flex flex-wrap justify-center gap-3">
              <Link to="/register">
                <Button size="lg" variant="secondary" className="shadow-xl">
                  Create your account <ArrowRight size={16} />
                </Button>
              </Link>
              <Link to="/feedback">
                <Button
                  size="lg"
                  variant="outline"
                  className="border-white/40 bg-transparent text-white hover:bg-white/10"
                >
                  Share feedback
                </Button>
              </Link>
            </div>
          </div>
        </Reveal>
      </Section>
    </>
  );
}
