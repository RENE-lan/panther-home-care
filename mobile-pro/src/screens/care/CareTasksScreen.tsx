import React from 'react';
import { View, Text } from 'react-native';
import { ScreenShell } from '../../components/ScreenShell';
import { EmptyState } from '../../components/EmptyState';
export function CareTasksScreen() { return (<ScreenShell title='Taches de soins'><View style={{ flex: 1, padding: 14 }}><EmptyState text='Taches de soins - bientot disponible.' icon='clock' /></View></ScreenShell>); }
