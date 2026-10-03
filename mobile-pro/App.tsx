import React, { useEffect } from 'react';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { NavigationContainer } from '@react-navigation/native';
import { StatusBar } from 'expo-status-bar';
import { RootNavigator } from './src/navigation/RootNavigator';
import { useAuthStore } from './src/store/authStore';
import { flushQueue } from './src/services/offlineQueue';
import { registerPush } from './src/services/notificationService';

export default function App() {
  const restore = useAuthStore((s) => s.restore);
  const token = useAuthStore((s) => s.token);
  useEffect(() => { restore(); }, []);
  useEffect(() => { if (token) { flushQueue(); registerPush(); } }, [token]);
  return (
    <SafeAreaProvider>
      <StatusBar style='light' />
      <NavigationContainer><RootNavigator /></NavigationContainer>
    </SafeAreaProvider>
  );
}
