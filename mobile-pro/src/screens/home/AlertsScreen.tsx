import React from 'react';
import { ScrollView, View, Text } from 'react-native';
import { ScreenShell } from '../../components/ScreenShell';
import { Card } from '../../components/Card';
import { Loading } from '../../components/Loading';
import { useFetch } from '../../hooks/useFetch';
import { api } from '../../api/client';
import { colors } from '../../theme/colors';
export function AlertsScreen() {
  const { data } = useFetch(() => api('/caregiver-alerts/').catch(() => ({ alerts: [] })), []);
  if (!data) return <ScreenShell title='Alertes'><Loading /></ScreenShell>;
  const col = (l: string) => l === 'red' ? colors.red : l === 'orange' ? colors.orange : l === 'yellow' ? '#d4a017' : colors.blue;
  return (<ScreenShell title='Alertes'><ScrollView style={{ flex: 1, padding: 14 }}>
    {((data as any).alerts || []).map((a: any, i: number) => (<Card key={i} style={{ borderLeftWidth: 4, borderLeftColor: col(a.level) } as any}>
      <Text style={{ fontWeight: '800', color: col(a.level) }}>{a.title}</Text><Text style={{ color: colors.muted, marginTop: 2 }}>{a.text}</Text></Card>))}
  </ScrollView></ScreenShell>);
}
