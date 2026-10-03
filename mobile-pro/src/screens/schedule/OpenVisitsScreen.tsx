import React, { useState } from 'react';
import { ScrollView, View, Text, TouchableOpacity, Alert } from 'react-native';
import { ScreenShell } from '../../components/ScreenShell';
import { Card } from '../../components/Card';
import { Button } from '../../components/Button';
import { EmptyState } from '../../components/EmptyState';
import { Loading } from '../../components/Loading';
import { useFetch } from '../../hooks/useFetch';
import { visitsApi } from '../../api/visits';
import { colors } from '../../theme/colors';
export function OpenVisitsScreen() {
  const { data, refresh } = useFetch(() => visitsApi.open(), []);
  const [openId, setOpenId] = useState<number | null>(null);
  const req = async (v: any) => { try { await visitsApi.request(v.id); refresh(); Alert.alert('Demande envoyee', 'En attente du bureau.'); } catch (e) { Alert.alert('Erreur'); } };
  if (!data) return <ScreenShell title='Visites ouvertes'><Loading /></ScreenShell>;
  const visits = (data as any).visits || [];
  return (<ScreenShell title='Visites ouvertes'><ScrollView style={{ flex: 1, padding: 14 }}>
    {visits.length === 0 ? <EmptyState text='Aucune visite ouverte.' icon='calendar' /> : visits.map((v: any) => {
      const sc = v.score >= 85 ? colors.green : v.score >= 65 ? colors.orange : colors.red;
      return (<Card key={v.id}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
          <View style={{ flex: 1 }}><Text style={{ fontSize: 15.5, fontWeight: '700', color: colors.ink }}>{v.client} - {v.care}</Text><Text style={{ color: colors.muted }}>{v.when}{v.km != null ? ' - ' + v.km + ' km' : ''}</Text></View>
          <View style={{ backgroundColor: sc + '1a', borderRadius: 10, paddingHorizontal: 10, paddingVertical: 6 }}><Text style={{ color: sc, fontWeight: '800', fontSize: 16 }}>{v.score}%</Text></View></View>
        <TouchableOpacity onPress={() => setOpenId(openId === v.id ? null : v.id)}><Text style={{ color: colors.blue, fontWeight: '700', marginTop: 8 }}>Pourquoi {v.score}% ? {openId === v.id ? '\u25B2' : '\u25BC'}</Text></TouchableOpacity>
        {openId === v.id ? (<View style={{ marginTop: 8, borderTopWidth: 1, borderTopColor: colors.line, paddingTop: 8 }}>
          {(v.why || []).map((w: string, i: number) => (<View key={i} style={{ flexDirection: 'row', paddingVertical: 3 }}><Text style={{ color: colors.green, marginRight: 8, fontWeight: '700' }}>{'\u2713'}</Text><Text>{w}</Text></View>))}
          {(v.reasons || []).map((w: string, i: number) => (<View key={'r'+i} style={{ flexDirection: 'row', paddingVertical: 3 }}><Text style={{ color: colors.orange, marginRight: 8, fontWeight: '700' }}>!</Text><Text style={{ color: colors.muted }}>{w}</Text></View>))}
        </View>) : null}
        <View style={{ marginTop: 10 }}>{v.pending ? <Text style={{ color: colors.orange, fontWeight: '700' }}>Demande en attente</Text> : <Button title='Demander' onPress={() => req(v)} />}</View>
      </Card>); })}
  </ScrollView></ScreenShell>);
}
