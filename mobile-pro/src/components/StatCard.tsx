import React from 'react';
import { View, Text } from 'react-native';
import { colors } from '../theme/colors';
import { Icon } from './Icon';
export function StatCard({ label, value, icon, tone = colors.ink }: { label: string; value: any; icon?: string; tone?: string }) {
  return (<View style={{ backgroundColor: colors.card, borderRadius: 14, padding: 13, width: '31.5%', marginBottom: 10, borderWidth: 1, borderColor: colors.line, shadowColor: '#0e1c38', shadowOpacity: 0.05, shadowRadius: 6, shadowOffset: { width: 0, height: 2 }, elevation: 2 }}>
    {icon ? <View style={{ width: 26, height: 26, borderRadius: 8, backgroundColor: tone + '18', alignItems: 'center', justifyContent: 'center', marginBottom: 6 }}><Icon name={icon} size={15} color={tone} /></View> : null}
    <Text style={{ fontSize: 20, fontWeight: '800', color: tone }}>{value}</Text>
    <Text style={{ fontSize: 10, color: colors.muted, marginTop: 2 }}>{label}</Text></View>);
}
