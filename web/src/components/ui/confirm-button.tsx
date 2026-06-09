import { type ReactNode, useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type ButtonVariant = "default" | "outline" | "ghost" | "destructive";
type ButtonSize = "default" | "sm" | "icon";

interface ConfirmButtonProps {
  /** Fired only after the user confirms. */
  onConfirm: () => void;
  /** Dialog heading. */
  title: string;
  /** Dialog body text. */
  description?: string;
  /** Label on the confirm button (default "Confirm"). */
  confirmLabel?: string;
  /** If set, the user must type this exact string to enable confirm. */
  confirmText?: string;
  /** Hint shown above the type-to-confirm input. */
  confirmTextLabel?: string;
  /** Style the confirm button as destructive. */
  destructive?: boolean;
  /** Disable the trigger. */
  disabled?: boolean;
  // Trigger button appearance (mirrors <Button/>):
  variant?: ButtonVariant;
  size?: ButtonSize;
  className?: string;
  /** Trigger content (icon + label). */
  children: ReactNode;
}

/**
 * A Button that opens a confirmation Dialog before firing `onConfirm`.
 * Pass `confirmText` to require the user to type an exact string (e.g. the
 * resource name) before the confirm button enables — used for high-risk,
 * irreversible actions like revoking an API key.
 */
export function ConfirmButton({
  onConfirm,
  title,
  description,
  confirmLabel = "Confirm",
  confirmText,
  confirmTextLabel,
  destructive = false,
  disabled = false,
  variant = "outline",
  size,
  className,
  children,
}: ConfirmButtonProps) {
  const [open, setOpen] = useState(false);
  const [typed, setTyped] = useState("");

  const close = () => {
    setOpen(false);
    setTyped("");
  };

  const matches = !confirmText || typed === confirmText;

  return (
    <>
      <Button
        variant={variant}
        size={size}
        className={className}
        disabled={disabled}
        onClick={() => setOpen(true)}
      >
        {children}
      </Button>

      <Dialog open={open} onClose={close} title={title} description={description}>
        <div className="space-y-4">
          {confirmText && (
            <div className="space-y-1.5">
              <Label>
                {confirmTextLabel ?? "Type to confirm:"}{" "}
                <span className="font-mono text-foreground">{confirmText}</span>
              </Label>
              <Input
                value={typed}
                onChange={(e) => setTyped(e.target.value)}
                placeholder={confirmText}
                autoFocus
              />
            </div>
          )}
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={close}>
              Cancel
            </Button>
            <Button
              variant={destructive ? "destructive" : "default"}
              disabled={!matches}
              onClick={() => {
                onConfirm();
                close();
              }}
            >
              {confirmLabel}
            </Button>
          </div>
        </div>
      </Dialog>
    </>
  );
}
