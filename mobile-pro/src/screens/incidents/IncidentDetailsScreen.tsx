import React from 'react';
import { View, Text } from 'react-native';
import { ScreenShell } from '../../components/ScreenShell';
import { EmptyState } from '../../components/EmptyState';
export function IncidentDetailsScreen() { return (<ScreenShell title='Detail incident'><View style={{ flex: 1, padding: 14 }}><EmptyState text='Detail incident - bientot disponible.' icon='clock' /></View></ScreenShell>); }
