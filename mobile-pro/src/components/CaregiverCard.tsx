import React from 'react';
import { View, Text } from 'react-native';
import { colors } from '../theme/colors';
import { Card } from './Card';
import { Avatar } from './Avatar';
export function CaregiverCard({ caregiver }: { caregiver: any }) {
  return (<Card><View style={{ flexDirection: 'row', alignItems: 'center' }}>
    <Avatar name={caregiver.name} size={40} /><View style={{ marginLeft: 12, flex: 1 }}>
    <Text style={{ fontSize: 15, fontWeight: '700', color: colors.ink }}>{caregiver.code} - {caregiver.name}</Text>
    <Text style={{ color: colors.muted, fontSize: 13 }}>Fiabilite {caregiver.reliability}%</Text></View></View></Card>);
}
