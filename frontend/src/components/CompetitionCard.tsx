import {
  Card,
  CardActionArea,
  CardContent,
  Stack,
  Typography,
} from "@mui/material";
import { Link } from "react-router";

import type { Competition } from "../api/types";
import { StatusChip } from "./StatusChip";


export function CompetitionCard({
  competition,
  admin = false,
}: {
  competition: Competition;
  admin?: boolean;
}) {
  const target = admin
    ? `/admin/competitions/${competition.id}`
    : `/competitions/${competition.id}`;
  return (
    <Card>
      <CardActionArea component={Link} to={target} sx={{ height: "100%" }}>
        <CardContent>
          <Stack direction="row" sx={{ justifyContent: "space-between", gap: 2, alignItems: "flex-start" }}>
            <div>
              <Typography variant="h6" component="h3">{competition.name}</Typography>
              <Typography color="text.secondary">{competition.year}</Typography>
            </div>
            <StatusChip status={competition.status} />
          </Stack>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            {competition.group_count} {competition.group_count === 1 ? "group" : "groups"}
            {" · "}{competition.total_team_count} teams
            {" · "}{competition.knockout_team_count} qualify
          </Typography>
        </CardContent>
      </CardActionArea>
    </Card>
  );
}
