import React from 'react';
import { View, Text } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors } from '../../theme/colors';
export function ResetPasswordScreen() { return (<SafeAreaView style={{ flex: 1, backgroundColor: colors.bg, justifyContent: 'center', alignItems: 'center' }}><Text style={{ color: colors.muted }}>Reinitialiser - bientot disponible</Text></SafeAreaView>); }
