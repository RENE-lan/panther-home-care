import React from 'react';
import { ScrollView, View, Text, Alert } from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import { ScreenShell } from '../../components/ScreenShell';
import { Card } from '../../components/Card';
import { Button } from '../../components/Button';
import { Loading } from '../../components/Loading';
import { useFetch } from '../../hooks/useFetch';
import { visitsApi } from '../../api/visits';
import { colors } from '../../theme/colors';
export function AssignmentScreen() {
  const route: any = useRoute(); const nav: any = useNavigation(); const visitId = route.params?.visitId;
  const { data } = useFetch(() => visitsApi.matches(visitId), [visitId]);
  const assign = async (m: any) => { try { await visitsApi.assign(visitId, m.caregiver_id); Alert.alert('Affecte', m.code + ' affecte.'); nav.goBack(); } catch (e) { Alert.alert('Erreur'); } };
  return (<ScreenShell title='Affectation'>{!data ? <Loading /> : (
    <ScrollView style={{ flex: 1, padding: 14 }}><Text style={{ fontSize: 12, fontWeight: '800', color: colors.muted, marginBottom: 10 }}>MEILLEURS PROFILS - {(data as any).client}</Text>
      {((data as any).matches || []).map((m: any, i: number) => (<Card key={i}><Text style={{ fontSize: 15.5, fontWeight: '700', color: colors.ink }}>{m.code} - {m.score}%</Text><Text style={{ color: colors.muted }}>{m.continuity} visite(s){m.km != null ? ` - ${m.km} km` : ''} - arrivee {m.arrival}%</Text><View style={{ marginTop: 10 }}><Button title={`Affecter ${m.code}`} onPress={() => assign(m)} /></View></Card>))}
    </ScrollView>)}</ScreenShell>);
}
