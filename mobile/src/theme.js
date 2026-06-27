// Shared visual language for Fishing Copilot.
export const colors = {
  bg: "#0e3a53",
  card: "#ffffff",
  cardMuted: "#f1f5f8",
  text: "#0e2a38",
  textMuted: "#5a7383",
  accent: "#1c7ca8",
  go: "#2e9e5b",
  optional: "#e0a32e",
  nogo: "#d2483f",
  border: "#dce5ea",
};

export function decisionColor(decision) {
  if (decision === "GO") return colors.go;
  if (decision === "OPTIONAL") return colors.optional;
  return colors.nogo;
}

export const spacing = { xs: 6, sm: 10, md: 16, lg: 24, xl: 32 };
