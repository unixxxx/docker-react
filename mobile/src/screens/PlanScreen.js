// Plan — generate an AI fishing plan for the current location.
import React, { useState } from "react";
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
} from "react-native";
import { getPlan } from "../api";
import { useSession } from "../SessionContext";
import { colors, spacing, decisionColor } from "../theme";
import { Card, SectionTitle } from "../components";

const TYPES = ["freshwater", "fly", "surf"];
const SKILLS = ["beginner", "intermediate", "expert"];

function Chips({ options, value, onChange }) {
  return (
    <View style={styles.chips}>
      {options.map((opt) => (
        <TouchableOpacity
          key={opt}
          style={[styles.chip, value === opt && styles.chipActive]}
          onPress={() => onChange(opt)}
        >
          <Text style={[styles.chipText, value === opt && styles.chipTextActive]}>
            {opt}
          </Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}

export default function PlanScreen() {
  const { location } = useSession();
  const [fishingType, setFishingType] = useState("freshwater");
  const [skillLevel, setSkillLevel] = useState("beginner");
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const generate = () => {
    setLoading(true);
    setError(null);
    getPlan({ location, fishingType, skillLevel })
      .then(setPlan)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Fishing Plan</Text>
      <Text style={styles.subtitle}>{location}</Text>

      <Card>
        <SectionTitle>Fishing type</SectionTitle>
        <Chips options={TYPES} value={fishingType} onChange={setFishingType} />
        <SectionTitle>Skill level</SectionTitle>
        <Chips options={SKILLS} value={skillLevel} onChange={setSkillLevel} />
      </Card>

      <TouchableOpacity style={styles.cta} onPress={generate} disabled={loading}>
        <Text style={styles.ctaText}>
          {loading ? "Generating…" : "Generate Fishing Plan"}
        </Text>
      </TouchableOpacity>

      {loading && <ActivityIndicator color="#fff" style={{ marginTop: spacing.lg }} />}

      {error && (
        <Card>
          <Text style={styles.error}>{error}</Text>
        </Card>
      )}

      {plan && (
        <>
          <Card style={{ backgroundColor: decisionColor(plan.decision) }}>
            <Text style={styles.planDecision}>
              {plan.decision} · {Math.round(plan.probability * 100)}%
            </Text>
          </Card>
          <Card>
            <SectionTitle>Your plan</SectionTitle>
            <Text style={styles.planText}>{plan.plan}</Text>
          </Card>
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  content: { padding: spacing.md, paddingTop: spacing.xl },
  title: { color: "#fff", fontSize: 24, fontWeight: "800" },
  subtitle: { color: "rgba(255,255,255,0.8)", marginBottom: spacing.md },
  chips: { flexDirection: "row", flexWrap: "wrap", marginBottom: spacing.md },
  chip: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: 20,
    backgroundColor: colors.cardMuted,
    marginRight: spacing.sm,
    marginBottom: spacing.sm,
  },
  chipActive: { backgroundColor: colors.accent },
  chipText: { color: colors.textMuted, fontWeight: "600", textTransform: "capitalize" },
  chipTextActive: { color: "#fff" },
  cta: {
    backgroundColor: colors.accent,
    borderRadius: 14,
    padding: spacing.md,
    alignItems: "center",
  },
  ctaText: { color: "#fff", fontSize: 16, fontWeight: "700" },
  planDecision: { color: "#fff", fontSize: 22, fontWeight: "800" },
  planText: { fontSize: 16, color: colors.text, lineHeight: 24 },
  error: { color: colors.nogo },
});
