import React from 'react';
import { View, Text } from 'react-native';
import { ScreenShell } from '../../components/ScreenShell';
import { EmptyState } from '../../components/EmptyState';
export function CaregiverDetailsScreen() { return (<ScreenShell title='Detail soignant'><View style={{ flex: 1, padding: 14 }}><EmptyState text='Detail soignant - bientot disponible.' icon='clock' /></View></ScreenShell>); }
