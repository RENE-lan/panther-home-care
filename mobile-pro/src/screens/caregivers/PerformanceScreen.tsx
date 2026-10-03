import React from 'react';
import { View, Text } from 'react-native';
import { ScreenShell } from '../../components/ScreenShell';
import { EmptyState } from '../../components/EmptyState';
export function PerformanceScreen() { return (<ScreenShell title='Performance'><View style={{ flex: 1, padding: 14 }}><EmptyState text='Performance - bientot disponible.' icon='clock' /></View></ScreenShell>); }
