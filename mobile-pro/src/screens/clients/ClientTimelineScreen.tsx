import React from 'react';
import { View, Text } from 'react-native';
import { ScreenShell } from '../../components/ScreenShell';
import { EmptyState } from '../../components/EmptyState';
export function ClientTimelineScreen() { return (<ScreenShell title='Historique client'><View style={{ flex: 1, padding: 14 }}><EmptyState text='Historique client - bientot disponible.' icon='clock' /></View></ScreenShell>); }
