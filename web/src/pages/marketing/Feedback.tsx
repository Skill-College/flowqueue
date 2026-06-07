import { useState } from "react";
import { motion } from "framer-motion";
import { CheckCircle2, MessageSquareHeart, Send } from "lucide-react";
import { toast } from "sonner";
import api, { apiErrorMessage } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Section } from "@/components/marketing/Section";
import { Reveal } from "@/components/marketing/Reveal";

type Category = "bug" | "feature" | "general";

const categories: { value: Category; label: string }[] = [
  { value: "general", label: "General feedback" },
  { value: "feature", label: "Feature request" },
  { value: "bug", label: "Bug report" },
];

export function Feedback() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [category, setCategory] = useState<Category>("general");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim() || !message.trim()) {
      toast.error("Email and message are required");
      return;
    }
    setSubmitting(true);
    try {
      await api.post("/feedback", {
        name: name.trim() || null,
        email: email.trim(),
        category,
        message: message.trim(),
      });
      setDone(true);
      toast.success("Thanks! Your feedback was sent.");
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Section className="min-h-[70vh] max-w-2xl pt-16 sm:pt-24">
      <Reveal className="text-center">
        <div className="mx-auto mb-5 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-gradient text-white shadow-lg shadow-primary/25">
          <MessageSquareHeart size={26} />
        </div>
        <h1 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">
          We&apos;d love your <span className="text-gradient">feedback</span>
        </h1>
        <p className="mx-auto mt-4 max-w-lg text-muted-foreground">
          Found a bug, want a feature, or just have thoughts? FlowQueue is in beta and shaped
          by what you tell us.
        </p>
      </Reveal>

      <Reveal delay={0.1} className="mt-10">
        {done ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="rounded-2xl border border-primary/40 bg-card/70 p-10 text-center backdrop-blur-sm"
          >
            <CheckCircle2 size={44} className="mx-auto text-primary" />
            <h2 className="mt-4 font-display text-xl font-bold">Feedback received</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Thank you — we read every submission.
            </p>
            <Button
              variant="outline"
              className="mt-6"
              onClick={() => {
                setDone(false);
                setName("");
                setEmail("");
                setCategory("general");
                setMessage("");
              }}
            >
              Send another
            </Button>
          </motion.div>
        ) : (
          <form
            onSubmit={submit}
            className="space-y-5 rounded-2xl border border-border bg-card/60 p-6 backdrop-blur-sm sm:p-8"
          >
            <div className="grid gap-5 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="name">Name (optional)</Label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Ada Lovelace"
                  maxLength={120}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="category">Category</Label>
              <Select
                id="category"
                value={category}
                onChange={(e) => setCategory(e.target.value as Category)}
              >
                {categories.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="message">Message</Label>
              <Textarea
                id="message"
                required
                rows={6}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Tell us what's on your mind…"
                maxLength={4000}
                className="font-sans"
              />
              <p className="text-right text-xs text-muted-foreground">{message.length}/4000</p>
            </div>

            <Button type="submit" size="lg" className="w-full" disabled={submitting}>
              {submitting ? "Sending…" : (
                <>
                  Send feedback <Send size={16} />
                </>
              )}
            </Button>
          </form>
        )}
      </Reveal>
    </Section>
  );
}
