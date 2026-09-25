import React from 'react';
import { View, Text } from 'react-native';
import { ScreenShell } from '../../components/ScreenShell';
import { EmptyState } from '../../components/EmptyState';
export function AvailabilityScreen() { return (<ScreenShell title='Disponibilite'><View style={{ flex: 1, padding: 14 }}><EmptyState text='Disponibilite - bientot disponible.' icon='clock' /></View></ScreenShell>); }
