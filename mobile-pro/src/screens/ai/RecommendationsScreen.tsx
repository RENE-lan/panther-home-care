import React from 'react';
import { View, Text } from 'react-native';
import { ScreenShell } from '../../components/ScreenShell';
import { EmptyState } from '../../components/EmptyState';
export function RecommendationsScreen() { return (<ScreenShell title='Recommandations'><View style={{ flex: 1, padding: 14 }}><EmptyState text='Recommandations - bientot disponible.' icon='clock' /></View></ScreenShell>); }
