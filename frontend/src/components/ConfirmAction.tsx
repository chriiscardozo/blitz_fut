import { useState } from "react";
import {
  Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle,
} from "@mui/material";

type Props = {
  label: string;
  title: string;
  description: string;
  confirmLabel?: string;
  color?: "primary" | "error";
  disabled?: boolean;
  onConfirm: () => Promise<void> | void;
};

export function ConfirmAction({
  label, title, description, confirmLabel = "Confirm", color = "primary",
  disabled = false, onConfirm,
}: Props) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  async function confirm() {
    setBusy(true);
    try { await onConfirm(); setOpen(false); } finally { setBusy(false); }
  }
  return (
    <>
      <Button color={color} disabled={disabled} onClick={() => setOpen(true)}>{label}</Button>
      <Dialog open={open} onClose={() => !busy && setOpen(false)}>
        <DialogTitle>{title}</DialogTitle>
        <DialogContent><DialogContentText>{description}</DialogContentText></DialogContent>
        <DialogActions>
          <Button disabled={busy} onClick={() => setOpen(false)}>Cancel</Button>
          <Button color={color} variant="contained" disabled={busy} onClick={() => void confirm()}>
            {busy ? "Working…" : confirmLabel}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
