import React from 'react';
import { View, Text } from 'react-native';
import { ScreenShell } from '../../components/ScreenShell';
import { EmptyState } from '../../components/EmptyState';
export function ClientDetailsScreen() { return (<ScreenShell title='Detail client'><View style={{ flex: 1, padding: 14 }}><EmptyState text='Detail client - bientot disponible.' icon='clock' /></View></ScreenShell>); }
