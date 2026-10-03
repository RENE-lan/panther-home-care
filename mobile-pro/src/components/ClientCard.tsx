import React from 'react';
import { View, Text } from 'react-native';
import { colors } from '../theme/colors';
import { Card } from './Card';
export function ClientCard({ client }: { client: any }) {
  const tone = client.pay === 'paid' ? colors.green : client.pay === 'unpaid' ? colors.red : colors.muted;
  return (<Card><View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
    <View style={{ flex: 1 }}><Text style={{ fontSize: 15.5, fontWeight: '700', color: colors.ink }}>{client.code} - {client.name}</Text><Text style={{ color: colors.muted, fontSize: 13 }}>{client.care}</Text></View>
    <Text style={{ color: tone, fontWeight: '700', fontSize: 12 }}>{client.pay === 'paid' ? 'Paye' : client.pay === 'unpaid' ? 'Impaye' : '-'}</Text></View></Card>);
}
