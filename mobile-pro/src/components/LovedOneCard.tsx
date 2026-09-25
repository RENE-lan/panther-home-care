import React from 'react';
import { View, Text } from 'react-native';
import { Card } from './Card';
import { Avatar } from './Avatar';
import { colors } from '../theme/colors';
export function LovedOneCard({ lovedOne }: { lovedOne: any }) {
  const c = lovedOne.status === 'urgent' ? colors.red : lovedOne.status === 'attention' ? colors.orange : colors.green;
  return (<Card><View style={{ flexDirection: 'row', alignItems: 'center' }}><Avatar name={lovedOne.name} size={44} /><View style={{ marginLeft: 12 }}><Text style={{ fontSize: 16, fontWeight: '800', color: colors.ink }}>{lovedOne.name}</Text><Text style={{ color: c, fontWeight: '700' }}>{lovedOne.status_label}</Text></View></View></Card>);
}
