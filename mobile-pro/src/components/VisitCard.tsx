import React from 'react';
import { View, Text } from 'react-native';
import { colors } from '../theme/colors';
import { Card } from './Card';
import { StatusBadge } from './StatusBadge';
export function VisitCard({ visit }: { visit: any }) {
  const c = visit.status === 'COMPLETED' ? colors.green : visit.status === 'IN_PROGRESS' ? colors.blue : colors.line;
  return (<Card style={{ borderLeftWidth: 4, borderLeftColor: c } as any}>
    <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
      <Text style={{ fontSize: 15.5, fontWeight: '700', color: colors.ink }}>{visit.start || visit.time}</Text><StatusBadge status={visit.status} /></View>
    <Text style={{ color: colors.muted, fontSize: 13, marginTop: 2 }}>{visit.client} - {visit.care}</Text></Card>);
}
