import React from 'react';
import { View, Text } from 'react-native';
import { colors } from '../theme/colors';
export function Avatar({ name, size = 40, bg = colors.navy }: { name?: string; size?: number; bg?: string }) {
  const initials = (name || '?').trim().split(' ').map((w) => w[0]).slice(0, 2).join('').toUpperCase();
  return (<View style={{ width: size, height: size, borderRadius: size / 2, backgroundColor: bg, alignItems: 'center', justifyContent: 'center' }}>
    <Text style={{ color: '#fff', fontWeight: '700', fontSize: size * 0.38 }}>{initials}</Text></View>);
}
