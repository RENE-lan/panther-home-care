import React from 'react';
import { View, ViewStyle } from 'react-native';
import { colors } from '../theme/colors';
export function Card({ children, style }: { children?: any; style?: ViewStyle }) {
  return (<View style={[{ backgroundColor: colors.card, borderRadius: 14, padding: 15, marginBottom: 12, borderWidth: 1, borderColor: colors.line, shadowColor: '#0e1c38', shadowOpacity: 0.05, shadowRadius: 8, shadowOffset: { width: 0, height: 3 }, elevation: 2 }, style]}>{children}</View>);
}
