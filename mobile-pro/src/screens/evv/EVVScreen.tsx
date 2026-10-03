import React, { useEffect, useState } from 'react';
import { ScrollView, View, Text } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { ScreenShell } from '../../components/ScreenShell';
import { Card } from '../../components/Card';
import { Button } from '../../components/Button';
import { EmptyState } from '../../components/EmptyState';
import { Loading } from '../../components/Loading';
import { StatusBadge } from '../../components/StatusBadge';
import { useFetch } from '../../hooks/useFetch';
import { visitsApi } from '../../api/visits';
import { getCoords, haversine } from '../../services/locationService';
import { colors } from '../../theme/colors';
export function EVVScreen() {
  const nav: any = useNavigation();
  const { data } = useFetch(() => visitsApi.mine(), []);
  const [dist, setDist] = useState<number | null>(null);
  const visits = (data as any)?.visits || [];
  const active = visits.find((v: any) => v.status === 'IN_PROGRESS');
  const next = visits.find((v: any) => v.status === 'SCHEDULED');
  useEffect(() => { (async () => { if (next && next.lat != null) { const cc = await getCoords(); if (cc) setDist(haversine(cc.lat, cc.lng, next.lat, next.lng)); } })(); }, [!!next]);
  return (<ScreenShell title='EVV'>{!data ? <Loading /> : (
    <ScrollView style={{ flex: 1, padding: 14 }}>
      {active ? (
        <Card style={{ borderColor: colors.green, borderWidth: 1.5 } as any}><Text style={{ color: colors.green, fontWeight: '800' }}>VISITE EN COURS</Text><Text style={{ fontSize: 15.5, fontWeight: '700', color: colors.ink, marginTop: 8 }}>{active.client}</Text><Text style={{ color: colors.muted }}>{active.start}-{active.end}</Text>
          <View style={{ marginTop: 12 }}><Button title='Voir la visite en cours' onPress={() => nav.navigate('ActiveVisit', { id: active.id })} /></View>
          <View style={{ marginTop: 8 }}><Button title='Terminer & signer' kind='green' onPress={() => nav.navigate('CheckOut', { id: active.id })} /></View></Card>
      ) : next ? (
        <><Text style={{ fontSize: 12, fontWeight: '800', color: colors.muted, marginBottom: 10 }}>VISITE À POINTER</Text>
        <Card>
          <Text style={{ fontSize: 16, fontWeight: '800', color: colors.ink }}>{next.client}</Text>
          <Text style={{ color: colors.muted, marginTop: 2 }}>{next.start} — {next.end}</Text>
          <View style={{ marginTop: 12, borderTopWidth: 1, borderTopColor: colors.line, paddingTop: 10 }}>
            <Text style={{ color: colors.muted, fontSize: 12 }}>Distance</Text><Text style={{ fontWeight: '700', color: dist != null && dist <= 300 ? colors.green : colors.ink }}>{dist != null ? (dist <= 300 ? '\u2713 ' : '') + dist + ' m' : 'Localisation…'}</Text>
            <Text style={{ color: colors.muted, fontSize: 12, marginTop: 8 }}>Statut</Text><Text style={{ fontWeight: '700', color: colors.green }}>Prête à démarrer</Text>
          </View>
          <View style={{ marginTop: 14 }}><Button title='Démarrer la visite' onPress={() => nav.navigate('EvvVerify', { visit: next })} /></View>
        </Card></>
      ) : <EmptyState text='Aucune visite à pointer pour le moment.' icon='pin' />}
      <Text style={{ fontSize: 12, fontWeight: '800', color: colors.muted, marginVertical: 10 }}>AUJOURD HUI</Text>
      {visits.map((v: any) => (<Card key={v.id}><View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}><Text style={{ fontWeight: '700', color: colors.ink }}>{v.start} - {v.client}</Text><StatusBadge status={v.status} /></View></Card>))}
    </ScrollView>)}</ScreenShell>);
}
