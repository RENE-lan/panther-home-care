import React from 'react';
import { TouchableOpacity, Text } from 'react-native';
import { colors } from '../theme/colors';
type Kind = 'primary' | 'green' | 'red' | 'navy' | 'ghost';
export function Button({ title, onPress, kind = 'primary' }: { title: string; onPress?: () => void; kind?: Kind }) {
  const bg = kind === 'primary' ? colors.blue : kind === 'green' ? colors.green : kind === 'red' ? colors.red : kind === 'navy' ? colors.navy : '#fff';
  const col = kind === 'ghost' ? colors.ink : '#fff';
  return (<TouchableOpacity onPress={onPress} style={{ backgroundColor: bg, borderRadius: 12, alignItems: 'center', justifyContent: 'center', paddingVertical: 15, borderWidth: kind === 'ghost' ? 1 : 0, borderColor: colors.line }}>
    <Text style={{ color: col, fontWeight: '700', fontSize: 15.5 }}>{title}</Text></TouchableOpacity>);
}
