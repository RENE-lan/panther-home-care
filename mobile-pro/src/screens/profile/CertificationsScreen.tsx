import React from 'react';
import { View, Text } from 'react-native';
import { ScreenShell } from '../../components/ScreenShell';
import { EmptyState } from '../../components/EmptyState';
export function CertificationsScreen() { return (<ScreenShell title='Certifications'><View style={{ flex: 1, padding: 14 }}><EmptyState text='Certifications - bientot disponible.' icon='clock' /></View></ScreenShell>); }
