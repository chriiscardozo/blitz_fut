import { Chip } from "@mui/material";
import type { CompetitionStatus } from "../api/types";

const labels: Record<CompetitionStatus, string> = {
  DRAFT: "Draft", GROUP_STAGE: "Group stage", KNOCKOUT: "Knockout", COMPLETED: "Completed",
};

export function StatusChip({ status }: { status: CompetitionStatus }) {
  return (
    <Chip
      label={labels[status]}
      color={status === "COMPLETED" ? "default" : "primary"}
      size="small"
      variant={status === "DRAFT" ? "outlined" : "filled"}
    />
  );
}
