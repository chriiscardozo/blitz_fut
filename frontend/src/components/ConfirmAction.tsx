import { useState } from "react";
import {
  Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, TextField,
} from "@mui/material";

type Props = {
  label: string;
  title: string;
  description: string;
  confirmLabel?: string;
  color?: "primary" | "error";
  disabled?: boolean;
  confirmationText?: string;
  onConfirm: (confirmation: string) => Promise<void> | void;
};

export function ConfirmAction({
  label, title, description, confirmLabel = "Confirm", color = "primary",
  disabled = false, confirmationText, onConfirm,
}: Props) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [enteredText, setEnteredText] = useState("");

  function close() {
    if (busy) return;
    setOpen(false);
    setEnteredText("");
  }

  async function confirm() {
    setBusy(true);
    try {
      await onConfirm(enteredText);
      setOpen(false);
      setEnteredText("");
    } finally { setBusy(false); }
  }
  return (
    <>
      <Button color={color} disabled={disabled} onClick={() => setOpen(true)}>{label}</Button>
      <Dialog open={open} onClose={close}>
        <DialogTitle>{title}</DialogTitle>
        <DialogContent>
          <DialogContentText>{description}</DialogContentText>
          {confirmationText !== undefined && (
            <TextField
              autoFocus
              fullWidth
              label="Competition name"
              helperText={`Type ${confirmationText} to confirm.`}
              value={enteredText}
              onChange={(event) => setEnteredText(event.target.value)}
              sx={{ mt: 2 }}
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button disabled={busy} onClick={close}>Cancel</Button>
          <Button color={color} variant="contained" disabled={busy || (confirmationText !== undefined && enteredText !== confirmationText)} onClick={() => void confirm()}>
            {busy ? "Working…" : confirmLabel}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
