import React from 'react';
import { View, Text } from 'react-native';
import { ScreenShell } from '../../components/ScreenShell';
import { EmptyState } from '../../components/EmptyState';
export function EVVResultScreen() { return (<ScreenShell title='Feuille de temps'><View style={{ flex: 1, padding: 14 }}><EmptyState text='Feuille de temps - bientot disponible.' icon='clock' /></View></ScreenShell>); }
