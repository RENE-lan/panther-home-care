import React from 'react';
import { View, Text } from 'react-native';
import { colors } from '../theme/colors';
import { Card } from './Card';
export function AlertCard({ action, onPress }: { action: any; onPress?: () => void }) {
  const rep = action.type === 'replacement';
  return (<Card style={{ borderLeftWidth: 4, borderLeftColor: rep ? colors.red : colors.orange } as any}>
    <Text style={{ fontSize: 11, fontWeight: '800', color: colors.muted }}>{rep ? 'ACTION RECOMMANDEE' : 'REVUE CLINIQUE'}</Text>
    <Text style={{ fontSize: 15.5, fontWeight: '700', color: colors.ink }}>{action.title}</Text>
    <Text style={{ color: colors.muted, fontSize: 13 }}>{action.detail}</Text></Card>);
}
