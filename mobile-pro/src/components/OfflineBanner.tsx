import React from 'react';
import { View, Text } from 'react-native';
import { colors } from '../theme/colors';
export function OfflineBanner({ visible }: { visible: boolean }) {
  if (!visible) return null;
  return (<View style={{ backgroundColor: colors.orange, paddingVertical: 6, alignItems: 'center' }}><Text style={{ color: '#fff', fontSize: 12, fontWeight: '700' }}>Hors-ligne - synchronisation en attente</Text></View>);
}
