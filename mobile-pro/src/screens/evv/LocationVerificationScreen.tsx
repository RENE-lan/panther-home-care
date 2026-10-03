import React from 'react';
import { View, Text } from 'react-native';
import { ScreenShell } from '../../components/ScreenShell';
import { EmptyState } from '../../components/EmptyState';
export function LocationVerificationScreen() { return (<ScreenShell title='Verification'><View style={{ flex: 1, padding: 14 }}><EmptyState text='Verification - bientot disponible.' icon='clock' /></View></ScreenShell>); }
