import React from 'react';
import { View } from 'react-native';
import { useAuthStore } from '../store/authStore';
import { AuthNavigator } from './AuthNavigator';
import { MainNavigator } from './MainNavigator';
import { Loading } from '../components/Loading';
export function RootNavigator() {
  const ready = useAuthStore((s) => s.ready);
  const token = useAuthStore((s) => s.token);
  if (!ready) return <View style={{ flex: 1, backgroundColor: '#f4f7fb' }}><Loading /></View>;
  return token ? <MainNavigator /> : <AuthNavigator />;
}
