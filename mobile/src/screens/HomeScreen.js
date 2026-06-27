// Home — the daily "should I go fishing right now?" answer.
import React, { useCallback, useState } from "react";
import {
  View,
  Text,
  ScrollView,
  ActivityIndicator,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
} from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { getDecision } from "../api";
import { useSession } from "../SessionContext";
import { colors, spacing, decisionColor } from "../theme";
import { Card, SectionTitle, LocationField } from "../components";

export default function HomeScreen({ navigation }) {
  const { location, setLocation } = useSession();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    getDecision(location)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [location]);

  useFocusEffect(load);

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={loading} onRefresh={load} />}
    >
      <Text style={styles.brand}>🎣 Fishing Copilot</Text>
      <LocationField value={location} onChangeText={setLocation} />

      {loading && !data ? (
        <ActivityIndicator color="#fff" size="large" style={{ marginTop: spacing.xl }} />
      ) : error ? (
        <Card>
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity onPress={load}>
            <Text style={styles.retry}>Tap to retry</Text>
          </TouchableOpacity>
        </Card>
      ) : data ? (
        <>
          <Card style={{ backgroundColor: decisionColor(data.decision) }}>
            <Text style={styles.decisionLabel}>{data.decision}</Text>
            <Text style={styles.prob}>
              {Math.round(data.probability * 100)}% chance of success
            </Text>
            <Text style={styles.locLine}>{data.location}</Text>
          </Card>

          <Card>
            <SectionTitle>Why</SectionTitle>
            <Text style={styles.explanation}>{data.explanation}</Text>
          </Card>

          <Card>
            <SectionTitle>Best time windows today</SectionTitle>
            {data.time_windows.map((w) => (
              <View key={w.label} style={styles.windowRow}>
                <Text style={styles.windowLabel}>{w.label}</Text>
                <Text style={styles.windowTime}>
                  {w.start} – {w.end}
                </Text>
              </View>
            ))}
          </Card>

          <Card>
            <SectionTitle>Conditions breakdown</SectionTitle>
            {Object.entries(data.breakdown)
              .filter(([k]) => k !== "total")
              .map(([k, v]) => (
                <View key={k} style={styles.windowRow}>
                  <Text style={styles.breakKey}>{k.replace(/_/g, " ")}</Text>
                  <Text style={styles.breakVal}>{v}</Text>
                </View>
              ))}
            <Text style={styles.modelNote}>
              {data.model_used
                ? "Personalised by your trained model"
                : "Rule-based estimate (model warming up)"}
            </Text>
          </Card>

          <TouchableOpacity
            style={styles.cta}
            onPress={() => navigation.navigate("Plan")}
          >
            <Text style={styles.ctaText}>Start session → Generate plan</Text>
          </TouchableOpacity>
        </>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  content: { padding: spacing.md, paddingTop: spacing.xl },
  brand: {
    color: "#fff",
    fontSize: 24,
    fontWeight: "800",
    marginBottom: spacing.md,
  },
  decisionLabel: { color: "#fff", fontSize: 44, fontWeight: "900", letterSpacing: 1 },
  prob: { color: "#fff", fontSize: 18, fontWeight: "600", marginTop: spacing.xs },
  locLine: { color: "rgba(255,255,255,0.85)", marginTop: spacing.sm },
  explanation: { fontSize: 16, color: colors.text, lineHeight: 22 },
  windowRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: spacing.xs,
  },
  windowLabel: { fontSize: 15, color: colors.text, fontWeight: "600" },
  windowTime: { fontSize: 15, color: colors.accent, fontWeight: "700" },
  breakKey: { fontSize: 14, color: colors.textMuted, textTransform: "capitalize" },
  breakVal: { fontSize: 14, color: colors.text, fontWeight: "600" },
  modelNote: {
    marginTop: spacing.sm,
    fontSize: 12,
    color: colors.textMuted,
    fontStyle: "italic",
  },
  cta: {
    backgroundColor: colors.accent,
    borderRadius: 14,
    padding: spacing.md,
    alignItems: "center",
    marginTop: spacing.sm,
  },
  ctaText: { color: "#fff", fontSize: 16, fontWeight: "700" },
  errorText: { color: colors.nogo, fontSize: 15 },
  retry: { color: colors.accent, marginTop: spacing.sm, fontWeight: "600" },
});
