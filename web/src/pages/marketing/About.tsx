import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Section, SectionHeading } from "@/components/marketing/Section";
import { Reveal } from "@/components/marketing/Reveal";
import { FanOutDiagram } from "@/components/marketing/FanOutDiagram";

const problems = [
  "Running Redis or a broker just to get a durable queue",
  "Losing visibility once a message leaves your service",
  "No clean way to replay a bad batch after an incident",
  "Fanning the same event out to several services reliably",
];

const principles = [
  {
    title: "Durability over cleverness",
    body: "If your database survives, your queue survives. State lives in Postgres, in transactions, with no separate moving parts to lose.",
  },
  {
    title: "Observability is not optional",
    body: "Every delivery has a status and an append-only, tamper-evident history. You should never wonder what happened to a message.",
  },
  {
    title: "Meet developers where they are",
    body: "A typed Python SDK and a plain HTTP API. Pull, push, or run a worker — whatever fits your stack.",
  },
];

export function About() {
  return (
    <>
      <Section className="pt-16 sm:pt-24">
        <SectionHeading
          eyebrow="About"
          title={
            <>
              Queues that are <span className="text-gradient">durable, observable</span> and
              simple to run
            </>
          }
          subtitle="FlowQueue started from a simple frustration: getting reliable, fan-out message delivery shouldn't require a broker, a cache, and a week of plumbing."
        />

        <Reveal className="mx-auto mt-4 max-w-3xl rounded-2xl border border-border bg-card/60 p-6 backdrop-blur-sm">
          <FanOutDiagram />
        </Reveal>
      </Section>

      <Section className="py-12">
        <div className="grid gap-10 lg:grid-cols-2">
          <Reveal direction="right">
            <h2 className="font-display text-2xl font-bold sm:text-3xl">The problem</h2>
            <p className="mt-4 text-muted-foreground">
              Most teams reach for a broker the moment they need retries or fan-out — and
              inherit the operational weight that comes with it. The common pain:
            </p>
            <ul className="mt-6 space-y-3">
              {problems.map((p) => (
                <li key={p} className="flex items-start gap-3 text-sm">
                  <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-primary" />
                  <span>{p}</span>
                </li>
              ))}
            </ul>
          </Reveal>

          <Reveal direction="left" delay={0.1}>
            <h2 className="font-display text-2xl font-bold sm:text-3xl">How FlowQueue works</h2>
            <p className="mt-4 text-muted-foreground">
              Publish a message to a queue. FlowQueue creates an independent{" "}
              <strong className="text-foreground">delivery</strong> for each consumer
              subscribed to that queue. Pull consumers fetch and acknowledge; webhook
              consumers are pushed to with HMAC signing and optional routing rules. Failed
              deliveries retry under a visibility timeout, then land in a dead-letter queue —
              and you can replay any of it.
            </p>
            <div className="mt-6 grid grid-cols-3 gap-3 text-center">
              {["Publish", "Fan-out", "Deliver"].map((step, i) => (
                <div key={step} className="rounded-xl border border-border bg-card/60 p-4">
                  <div className="font-display text-2xl font-bold text-gradient">{i + 1}</div>
                  <div className="mt-1 text-sm font-medium">{step}</div>
                </div>
              ))}
            </div>
          </Reveal>
        </div>
      </Section>

      <Section className="py-12">
        <SectionHeading eyebrow="Principles" title="What we optimise for" />
        <div className="grid gap-5 md:grid-cols-3">
          {principles.map((p, i) => (
            <Reveal key={p.title} delay={i * 0.08}>
              <div className="h-full rounded-2xl border border-border bg-card/60 p-6 backdrop-blur-sm">
                <h3 className="font-display text-lg font-semibold">{p.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{p.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </Section>

      <Section className="py-16">
        <Reveal className="rounded-3xl border border-border bg-card/60 p-10 text-center backdrop-blur-sm">
          <h2 className="font-display text-2xl font-bold sm:text-3xl">
            We&apos;re in beta — and listening
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-muted-foreground">
            FlowQueue is free while in public beta. Tell us what you need next.
          </p>
          <div className="mt-7 flex flex-wrap justify-center gap-3">
            <Link to="/register">
              <Button size="lg">
                Start free <ArrowRight size={16} />
              </Button>
            </Link>
            <Link to="/feedback">
              <Button size="lg" variant="outline">
                Share feedback
              </Button>
            </Link>
          </div>
        </Reveal>
      </Section>
    </>
  );
}
