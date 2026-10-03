import React from 'react';
import { ScrollView, View, Text } from 'react-native';
import { useRoute } from '@react-navigation/native';
import { ScreenShell } from '../../components/ScreenShell';
import { Card } from '../../components/Card';
import { colors } from '../../theme/colors';
export function ReportDetailsScreen() {
  const route: any = useRoute(); const r = route.params?.report || {};
  const Row = ({ l, v }: any) => (<View style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 7 }}><Text style={{ color: colors.muted }}>{l}</Text><Text style={{ fontWeight: '700', color: colors.ink }}>{v}</Text></View>);
  return (<ScreenShell title='Rapport de visite'><ScrollView style={{ flex: 1, padding: 14 }}>
    <Card><Text style={{ fontSize: 15.5, fontWeight: '700', color: colors.ink }}>{r.date} - {r.time}</Text>{r.signed ? <Text style={{ color: colors.green, fontWeight: '700', marginTop: 4 }}>EVV verifie - signe</Text> : null}</Card>
    <Card><Row l='Soignant' v={r.caregiver} /><Row l='Arrivee' v={r.arrival || '-'} /><Row l='Depart' v={r.departure || '-'} /><Row l='EVV' v={r.evv} /><Row l='Humeur' v={r.mood} /></Card>
    {(r.tasks && r.tasks.length) ? (<Card><Text style={{ fontSize: 12, fontWeight: '800', color: colors.muted, marginBottom: 6 }}>TACHES REALISEES</Text>{r.tasks.map((t: string, i: number) => (<View key={i} style={{ flexDirection: 'row', paddingVertical: 5 }}><Text style={{ color: colors.green, marginRight: 8 }}>{'\u2713'}</Text><Text>{t}</Text></View>))}</Card>) : null}
    {r.notes ? (<Card><Text style={{ fontSize: 12, fontWeight: '800', color: colors.muted, marginBottom: 6 }}>OBSERVATIONS</Text><Text>{r.notes}</Text></Card>) : null}
  </ScrollView></ScreenShell>);
}
