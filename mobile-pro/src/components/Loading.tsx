import React from 'react';
import { View, ActivityIndicator } from 'react-native';
import { colors } from '../theme/colors';
export function Loading() { return (<View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', paddingVertical: 60 }}><ActivityIndicator size='large' color={colors.blue} /></View>); }
