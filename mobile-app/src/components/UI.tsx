import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ViewStyle } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, radius } from '../theme';

export function Card({ children, style }: { children: React.ReactNode; style?: ViewStyle }) {
  return <View style={[styles.card, style]}>{children}</View>;
}

export function StatCard({ icon, iconBg, iconColor, value, label, sub, subColor }: {
  icon: keyof typeof Ionicons.glyphMap; iconBg: string; iconColor: string;
  value: string | number; label: string; sub?: string; subColor?: string;
}) {
  return (
    <View style={styles.stat}>
      <View style={[styles.statIcon, { backgroundColor: iconBg }]}>
        <Ionicons name={icon} size={18} color={iconColor} />
      </View>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
      {sub ? <Text style={[styles.statSub, subColor ? { color: subColor } : null]}>{sub}</Text> : null}
    </View>
  );
}

export function Pill({ text, bg, color }: { text: string; bg: string; color: string }) {
  return (
    <View style={[styles.pill, { backgroundColor: bg }]}>
      <Text style={[styles.pillText, { color }]}>{text}</Text>
    </View>
  );
}

export function Button({ title, onPress, kind = 'primary', style }: {
  title: string; onPress?: () => void; kind?: 'primary' | 'ghost' | 'green'; style?: ViewStyle;
}) {
  const bg = kind === 'green' ? colors.green : kind === 'ghost' ? '#fff' : colors.primary;
  const fg = kind === 'ghost' ? colors.ink : '#fff';
  const border = kind === 'ghost' ? { borderWidth: 1, borderColor: colors.line } : null;
  return (
    <TouchableOpacity onPress={onPress} activeOpacity={0.85} style={[styles.btn, { backgroundColor: bg }, border, style]}>
      <Text style={[styles.btnText, { color: fg }]}>{title}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: colors.card, borderRadius: radius.lg, padding: 16, borderWidth: 1, borderColor: colors.line,
    shadowColor: '#0f1e38', shadowOpacity: 0.05, shadowRadius: 8, shadowOffset: { width: 0, height: 3 }, elevation: 1 },
  stat: { flex: 1, backgroundColor: colors.card, borderRadius: radius.md, padding: 12, borderWidth: 1, borderColor: colors.line,
    shadowColor: '#0f1e38', shadowOpacity: 0.04, shadowRadius: 6, shadowOffset: { width: 0, height: 2 }, elevation: 1 },
  statIcon: { width: 34, height: 34, borderRadius: 10, alignItems: 'center', justifyContent: 'center', marginBottom: 8 },
  statValue: { fontSize: 22, fontWeight: '800', color: colors.ink },
  statLabel: { fontSize: 11.5, color: colors.muted, marginTop: 1 },
  statSub: { fontSize: 10.5, color: colors.green, marginTop: 4, fontWeight: '600' },
  pill: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: radius.pill, alignSelf: 'flex-start' },
  pillText: { fontSize: 11.5, fontWeight: '700' },
  btn: { borderRadius: radius.md, paddingVertical: 13, alignItems: 'center', justifyContent: 'center' },
  btnText: { fontWeight: '700', fontSize: 14.5 },
});
