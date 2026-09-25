import React from 'react';
import { View, Text } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors } from '../../theme/colors';
export function ForgotPasswordScreen() { return (<SafeAreaView style={{ flex: 1, backgroundColor: colors.bg, justifyContent: 'center', alignItems: 'center' }}><Text style={{ color: colors.muted }}>Mot de passe oublie - bientot disponible</Text></SafeAreaView>); }
