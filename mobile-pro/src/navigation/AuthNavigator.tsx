import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { LoginScreen } from '../screens/auth/LoginScreen';
import { ForgotPasswordScreen } from '../screens/auth/ForgotPasswordScreen';
import { ResetPasswordScreen } from '../screens/auth/ResetPasswordScreen';
const Stack = createNativeStackNavigator();
export function AuthNavigator() {
  return (<Stack.Navigator screenOptions={{ headerShown: false }}>
    <Stack.Screen name='Login' component={LoginScreen} />
    <Stack.Screen name='ForgotPassword' component={ForgotPasswordScreen} />
    <Stack.Screen name='ResetPassword' component={ResetPasswordScreen} />
  </Stack.Navigator>);
}
