import React from 'react';
import { ScrollView, View, Text } from 'react-native';
import { ScreenShell } from '../../components/ScreenShell';
import { Card } from '../../components/Card';
import { Avatar } from '../../components/Avatar';
import { Loading } from '../../components/Loading';
import { useFetch } from '../../hooks/useFetch';
import { aiApi } from '../../api/ai';
import { colors } from '../../theme/colors';
export function LovedOneScreen() {
  const { data } = useFetch(() => aiApi.family(), []);
  if (!data) return <ScreenShell title='Mon proche'><Loading /></ScreenShell>;
  const lo: any = (data as any).loved_one || {};
  const statusColor = lo.status === 'urgent' ? colors.red : lo.status === 'attention' ? colors.orange : colors.green;
  return (<ScreenShell title='Mon proche'><ScrollView style={{ flex: 1, padding: 14 }}>
    <View style={{ alignItems: 'center', marginVertical: 10 }}><Avatar name={lo.name} size={72} /><Text style={{ fontSize: 20, fontWeight: '800', color: colors.ink, marginTop: 10 }}>{lo.name}</Text><View style={{ flexDirection: 'row', alignItems: 'center', marginTop: 4 }}><View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: statusColor, marginRight: 6 }} /><Text style={{ color: statusColor, fontWeight: '700' }}>{lo.status_label}</Text></View></View>
    <Text style={{ fontSize: 12, fontWeight: '800', color: colors.muted, marginVertical: 10 }}>INFORMATIONS</Text>
    <Card>{lo.next_visit ? (<View style={{ marginBottom: 10 }}><Text style={{ color: colors.muted, fontSize: 12 }}>Prochain soin</Text><Text style={{ fontWeight: '700', color: colors.ink }}>{lo.next_visit.when} - {lo.next_visit.caregiver}</Text></View>) : null}{lo.last_visit ? (<View><Text style={{ color: colors.muted, fontSize: 12 }}>Derniere visite</Text><Text style={{ fontWeight: '700', color: colors.ink }}>{lo.last_visit.when} - {lo.last_visit.caregiver}</Text></View>) : null}</Card>
    <Text style={{ fontSize: 12, fontWeight: '800', color: colors.muted, marginVertical: 10 }}>PLAN DE SOINS</Text>
    <Card>{(lo.care_plan || []).map((t: string, i: number) => (<View key={i} style={{ flexDirection: 'row', paddingVertical: 7 }}><Text style={{ color: colors.green, marginRight: 8, fontWeight: '700' }}>{'\u2713'}</Text><Text>{t}</Text></View>))}</Card>
  </ScrollView></ScreenShell>);
}
