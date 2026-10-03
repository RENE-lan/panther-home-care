import React from 'react';
import { View, Text } from 'react-native';
import { colors } from '../theme/colors';
const MAP: any = { COMPLETED: ['Terminee', colors.green], IN_PROGRESS: ['En cours', colors.blue], UNCOVERED: ['Non couvert', colors.red], SCHEDULED: ['A venir', colors.muted] };
export function StatusBadge({ status }: { status: string }) {
  const [label, col] = MAP[status] || MAP.SCHEDULED;
  return (<View style={{ borderRadius: 20, paddingHorizontal: 11, paddingVertical: 4, backgroundColor: col + '1a' }}><Text style={{ color: col, fontWeight: '700', fontSize: 12 }}>{label}</Text></View>);
}
