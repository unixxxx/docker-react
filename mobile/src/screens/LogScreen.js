// Log — quick catch logging (the data flywheel) + recent history.
import React, { useState, useCallback } from "react";
import {
  View,
  Text,
  TextInput,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
} from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { logResult, getHistory } from "../api";
import { useSession } from "../SessionContext";
import { colors, spacing } from "../theme";
import { Card, SectionTitle } from "../components";

export default function LogScreen() {
  const { session } = useSession();
  const [bait, setBait] = useState("");
  const [notes, setNotes] = useState("");
  const [status, setStatus] = useState(null);
  const [history, setHistory] = useState([]);

  const refreshHistory = useCallback(() => {
    getHistory()
      .then((h) => setHistory(h.sessions || []))
      .catch(() => {});
  }, []);

  useFocusEffect(refreshHistory);

  const submit = (result) => {
    if (!session) {
      setStatus("Session not ready yet — try again in a moment.");
      return;
    }
    logResult({ sessionId: session.id, result, bait, notes })
      .then(() => {
        setStatus(result === "caught" ? "Logged a catch! 🐟" : "Logged: no bite.");
        setBait("");
        setNotes("");
        refreshHistory();
      })
      .catch((e) => setStatus(e.message));
  };

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Quick Log</Text>

      <Card>
        <SectionTitle>Bait (optional)</SectionTitle>
        <TextInput
          style={styles.input}
          value={bait}
          onChangeText={setBait}
          placeholder="e.g. worm, spinner, fly"
          placeholderTextColor={colors.textMuted}
        />
        <SectionTitle>Note (optional)</SectionTitle>
        <TextInput
          style={[styles.input, styles.notes]}
          value={notes}
          onChangeText={setNotes}
          placeholder="What happened?"
          placeholderTextColor={colors.textMuted}
          multiline
        />
        <View style={styles.row}>
          <TouchableOpacity
            style={[styles.btn, { backgroundColor: colors.go }]}
            onPress={() => submit("caught")}
          >
            <Text style={styles.btnText}>👍 Caught</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.btn, { backgroundColor: colors.nogo }]}
            onPress={() => submit("no_bite")}
          >
            <Text style={styles.btnText}>👎 No bite</Text>
          </TouchableOpacity>
        </View>
        {status && <Text style={styles.status}>{status}</Text>}
      </Card>

      <SectionTitleLight>Recent sessions</SectionTitleLight>
      {history.length === 0 ? (
        <Text style={styles.empty}>No sessions logged yet.</Text>
      ) : (
        history.map((s) => (
          <Card key={s.id}>
            <Text style={styles.histLoc}>{s.location_text}</Text>
            <Text style={styles.histDate}>
              {new Date(s.start_time).toLocaleString()}
            </Text>
            {s.catches.length === 0 ? (
              <Text style={styles.histNone}>No catches logged</Text>
            ) : (
              s.catches.map((c) => (
                <Text key={c.id} style={styles.histCatch}>
                  {c.success ? "🐟" : "—"} {c.bait || "no bait noted"}
                  {c.notes ? ` · ${c.notes}` : ""}
                </Text>
              ))
            )}
          </Card>
        ))
      )}
    </ScrollView>
  );
}

function SectionTitleLight({ children }) {
  return <Text style={styles.lightTitle}>{children}</Text>;
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  content: { padding: spacing.md, paddingTop: spacing.xl },
  title: { color: "#fff", fontSize: 24, fontWeight: "800", marginBottom: spacing.md },
  input: {
    backgroundColor: colors.cardMuted,
    borderRadius: 12,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    fontSize: 16,
    color: colors.text,
    marginBottom: spacing.md,
  },
  notes: { height: 70, textAlignVertical: "top" },
  row: { flexDirection: "row", justifyContent: "space-between" },
  btn: {
    flex: 1,
    padding: spacing.md,
    borderRadius: 12,
    alignItems: "center",
    marginHorizontal: spacing.xs,
  },
  btnText: { color: "#fff", fontSize: 16, fontWeight: "700" },
  status: { marginTop: spacing.md, color: colors.text, textAlign: "center" },
  lightTitle: {
    color: "rgba(255,255,255,0.85)",
    fontSize: 13,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 1,
    marginVertical: spacing.md,
  },
  empty: { color: "rgba(255,255,255,0.7)" },
  histLoc: { fontSize: 16, fontWeight: "700", color: colors.text },
  histDate: { fontSize: 12, color: colors.textMuted, marginBottom: spacing.sm },
  histNone: { fontSize: 14, color: colors.textMuted, fontStyle: "italic" },
  histCatch: { fontSize: 14, color: colors.text, paddingVertical: 2 },
});
