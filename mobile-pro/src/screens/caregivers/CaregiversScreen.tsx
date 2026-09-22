import React from 'react';
import { View, Text } from 'react-native';
import { ScreenShell } from '../../components/ScreenShell';
import { EmptyState } from '../../components/EmptyState';
export function CaregiversScreen() { return (<ScreenShell title='Soignants'><View style={{ flex: 1, padding: 14 }}><EmptyState text='Soignants - bientot disponible.' icon='clock' /></View></ScreenShell>); }
