import React from 'react';
import { View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Header } from './Header';
import { colors } from '../theme/colors';
export function ScreenShell({ title, children }: { title: string; children?: any }) {
  return (<SafeAreaView edges={['top']} style={{ flex: 1, backgroundColor: colors.bg }}>
    <Header title={title} />
    <View style={{ flex: 1 }}>{children}</View></SafeAreaView>);
}
