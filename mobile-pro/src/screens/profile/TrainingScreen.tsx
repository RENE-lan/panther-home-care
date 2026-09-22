import React from 'react';
import { View, Text } from 'react-native';
import { ScreenShell } from '../../components/ScreenShell';
import { EmptyState } from '../../components/EmptyState';
export function TrainingScreen() { return (<ScreenShell title='Formation'><View style={{ flex: 1, padding: 14 }}><EmptyState text='Formation - bientot disponible.' icon='clock' /></View></ScreenShell>); }
