import React from 'react';
import { ScrollView, View, Text } from 'react-native';
import { ScreenShell } from '../../components/ScreenShell';
import { Card } from '../../components/Card';
import { StatusBadge } from '../../components/StatusBadge';
import { EmptyState } from '../../components/EmptyState';
import { Loading } from '../../components/Loading';
import { useFetch } from '../../hooks/useFetch';
import { api } from '../../api/client';
import { colors } from '../../theme/colors';
export function VisitsScreen() {
  const { data } = useFetch(() => api('/family/visits/').catch(() => ({ upcoming: [], past: [], linked: false })), []);
  if (!data) return <ScreenShell title='Planning'><Loading /></ScreenShell>;
  if ((data as any).linked === false) return <ScreenShell title='Planning'><View style={{ padding: 14 }}><EmptyState text='Liez votre proche pour voir le planning.' icon='calendar' /></View></ScreenShell>;
  const V = ({ v }: any) => (<Card><View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}><View style={{ flex: 1 }}><Text style={{ fontWeight: '700', color: colors.ink }}>{v.when}</Text><Text style={{ color: colors.muted }}>{v.caregiver} - EVV {v.evv}</Text></View><StatusBadge status={v.status} /></View></Card>);
  return (<ScreenShell title='Planning des visites'><ScrollView style={{ flex: 1, padding: 14 }}>
    <Text style={{ fontSize: 12, fontWeight: '800', color: colors.muted, marginBottom: 10 }}>A VENIR</Text>
    {((data as any).upcoming || []).length === 0 ? <EmptyState text='Aucune visite a venir.' icon='calendar' /> : ((data as any).upcoming || []).map((v: any, i: number) => <V key={i} v={v} />)}
    <Text style={{ fontSize: 12, fontWeight: '800', color: colors.muted, marginVertical: 10 }}>HISTORIQUE</Text>
    {((data as any).past || []).map((v: any, i: number) => <V key={i} v={v} />)}
  </ScrollView></ScreenShell>);
}
