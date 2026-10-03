import React from 'react';
import { TextInput, TextInputProps } from 'react-native';
import { colors } from '../theme/colors';
export function Input(props: TextInputProps) {
  return (<TextInput placeholderTextColor={colors.muted} {...props} style={[{ backgroundColor: '#fff', borderWidth: 1, borderColor: colors.line, borderRadius: 11, paddingHorizontal: 14, paddingVertical: 12, fontSize: 15, marginBottom: 12, color: colors.ink }, props.style]} />);
}
