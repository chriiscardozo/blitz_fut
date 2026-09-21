import { alpha, createTheme } from "@mui/material/styles";


const nearWhite = "#f7f8f4";
const nearBlack = "#172019";
const pitchGreen = "#237a45";

export const theme = createTheme({
  cssVariables: true,
  palette: {
    mode: "light",
    primary: { main: pitchGreen, contrastText: nearWhite },
    background: { default: nearWhite, paper: "#ffffff" },
    text: { primary: nearBlack, secondary: alpha(nearBlack, 0.68) },
    divider: alpha(nearBlack, 0.14),
  },
  typography: {
    fontFamily:
      'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    h1: { fontWeight: 800, letterSpacing: "-0.045em" },
    h2: { fontWeight: 760, letterSpacing: "-0.035em" },
    h3: { fontWeight: 720, letterSpacing: "-0.025em" },
    button: { fontWeight: 700, textTransform: "none" },
  },
  shape: { borderRadius: 12 },
  components: {
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: { root: { minHeight: 42 } },
    },
    MuiCard: {
      defaultProps: { variant: "outlined" },
      styleOverrides: {
        root: {
          backgroundImage: "none",
          borderColor: alpha(nearBlack, 0.12),
        },
      },
    },
    MuiPaper: { styleOverrides: { root: { backgroundImage: "none" } } },
    MuiTableCell: {
      styleOverrides: { head: { fontWeight: 800, whiteSpace: "nowrap" } },
    },
  },
});
