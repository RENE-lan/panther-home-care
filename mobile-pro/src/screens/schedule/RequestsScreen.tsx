import React from 'react';
import { ScrollView, View, Text, Alert } from 'react-native';
import { ScreenShell } from '../../components/ScreenShell';
import { Card } from '../../components/Card';
import { Button } from '../../components/Button';
import { EmptyState } from '../../components/EmptyState';
import { Loading } from '../../components/Loading';
import { useFetch } from '../../hooks/useFetch';
import { api } from '../../api/client';
import { colors } from '../../theme/colors';
export function RequestsScreen() {
  const { data, refresh } = useFetch(() => api('/requests/'), []);
  const decide = async (id: number, decision: string) => { try { await api(`/requests/${id}/decide/`, 'POST', { decision }); refresh(); } catch (e) { Alert.alert('Erreur'); } };
  return (<ScreenShell title='Demandes'>{!data ? <Loading /> : (
    <ScrollView style={{ flex: 1, padding: 14 }}>{((data as any).requests || []).length === 0 ? <EmptyState text='Aucune demande.' icon='inbox' /> : ((data as any).requests || []).map((r: any) => (
      <Card key={r.id}><Text style={{ fontSize: 15.5, fontWeight: '700', color: colors.ink }}>{r.caregiver} - {r.client}</Text><Text style={{ color: colors.muted }}>{r.when} - {r.score}%</Text>
        <View style={{ flexDirection: 'row', gap: 8, marginTop: 10 }}><View style={{ flex: 1 }}><Button title='Approuver' kind='green' onPress={() => decide(r.id, 'approve')} /></View><View style={{ flex: 1 }}><Button title='Refuser' kind='ghost' onPress={() => decide(r.id, 'deny')} /></View></View></Card>))}
    </ScrollView>)}</ScreenShell>);
}
