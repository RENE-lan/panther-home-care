import React from 'react';
import { View, Text } from 'react-native';
import { ScreenShell } from '../../components/ScreenShell';
import { EmptyState } from '../../components/EmptyState';
export function AlertsAnalysisScreen() { return (<ScreenShell title='Analyse des alertes'><View style={{ flex: 1, padding: 14 }}><EmptyState text='Analyse des alertes - bientot disponible.' icon='clock' /></View></ScreenShell>); }
