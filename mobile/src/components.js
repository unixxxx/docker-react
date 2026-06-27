// Small shared UI primitives.
import React from "react";
import { View, Text, TextInput, StyleSheet } from "react-native";
import { colors, spacing } from "./theme";

export function Card({ children, style }) {
  return <View style={[styles.card, style]}>{children}</View>;
}

export function SectionTitle({ children }) {
  return <Text style={styles.sectionTitle}>{children}</Text>;
}

export function LocationField({ value, onChangeText }) {
  return (
    <View style={styles.locWrap}>
      <Text style={styles.locLabel}>Location</Text>
      <TextInput
        style={styles.locInput}
        value={value}
        onChangeText={onChangeText}
        placeholder="Place name or lat,lon"
        placeholderTextColor={colors.textMuted}
        autoCapitalize="words"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.card,
    borderRadius: 16,
    padding: spacing.lg,
    marginBottom: spacing.md,
    shadowColor: "#000",
    shadowOpacity: 0.08,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  sectionTitle: {
    fontSize: 13,
    fontWeight: "700",
    color: colors.textMuted,
    textTransform: "uppercase",
    letterSpacing: 1,
    marginBottom: spacing.sm,
  },
  locWrap: { marginBottom: spacing.md },
  locLabel: {
    color: "#cfe3ee",
    fontSize: 12,
    fontWeight: "600",
    marginBottom: spacing.xs,
    textTransform: "uppercase",
    letterSpacing: 1,
  },
  locInput: {
    backgroundColor: colors.card,
    borderRadius: 12,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    fontSize: 16,
    color: colors.text,
  },
});
