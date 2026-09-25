import React from 'react';
import { View, Text } from 'react-native';
import { ScreenShell } from '../../components/ScreenShell';
import { EmptyState } from '../../components/EmptyState';
export function CareNotesScreen() { return (<ScreenShell title='Notes de soins'><View style={{ flex: 1, padding: 14 }}><EmptyState text='Notes de soins - bientot disponible.' icon='clock' /></View></ScreenShell>); }
