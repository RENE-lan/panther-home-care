import React from 'react';
import { View, Text } from 'react-native';
import { colors } from '../theme/colors';
import { Icon } from './Icon';
import { Card } from './Card';
export function EmptyState({ text, icon = 'inbox' }: { text: string; icon?: string }) {
  return (<Card style={{ alignItems: 'center', paddingVertical: 26 } as any}>
    <View style={{ width: 46, height: 46, borderRadius: 23, backgroundColor: '#eef2f7', alignItems: 'center', justifyContent: 'center', marginBottom: 10 }}><Icon name={icon} size={22} color={colors.muted} /></View>
    <Text style={{ color: colors.muted, fontSize: 13, textAlign: 'center' }}>{text}</Text></Card>);
}
