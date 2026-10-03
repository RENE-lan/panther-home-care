import React from 'react';
import { View, Text } from 'react-native';
import { ScreenShell } from '../../components/ScreenShell';
import { EmptyState } from '../../components/EmptyState';
export function IncidentsScreen() { return (<ScreenShell title='Incidents'><View style={{ flex: 1, padding: 14 }}><EmptyState text='Incidents - bientot disponible.' icon='clock' /></View></ScreenShell>); }
