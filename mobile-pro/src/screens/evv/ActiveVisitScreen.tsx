import React, { useState, useEffect } from 'react';
import { ScrollView, View, Text, TouchableOpacity } from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import { ScreenShell } from '../../components/ScreenShell';
import { Card } from '../../components/Card';
import { Button } from '../../components/Button';
import { Icon } from '../../components/Icon';
import { Loading } from '../../components/Loading';
import { useFetch } from '../../hooks/useFetch';
import { visitsApi } from '../../api/visits';
import { colors } from '../../theme/colors';
function fmt(s: number) { const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), ss = s % 60; return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(ss).padStart(2,'0')}`; }
export function ActiveVisitScreen() {
  const route: any = useRoute(); const nav: any = useNavigation(); const id = route.params?.id;
  const { data } = useFetch(() => visitsApi.detail(id), [id]);
  const [elapsed, setElapsed] = useState(0);
  const [done, setDone] = useState<Record<string, boolean>>({});
  useEffect(() => { const t = setInterval(() => setElapsed((e) => e + 1), 1000); return () => clearInterval(t); }, []);
  if (!data) return <ScreenShell title='Visite en cours'><Loading /></ScreenShell>;
  const tasks = (data as any).tasks || [];
  const nb = Object.values(done).filter(Boolean).length;
  const Action = ({ icon, label, onPress }: any) => (<TouchableOpacity onPress={onPress} style={{ flex: 1, alignItems: 'center', paddingVertical: 12 }}><View style={{ width: 44, height: 44, borderRadius: 22, backgroundColor: colors.bg, alignItems: 'center', justifyContent: 'center' }}><Icon name={icon} size={20} color={colors.navy} /></View><Text style={{ fontSize: 11, color: colors.muted, marginTop: 4 }}>{label}</Text></TouchableOpacity>);
  return (<ScreenShell title='Visite en cours'><ScrollView style={{ flex: 1, padding: 14 }}>
    <Card style={{ alignItems: 'center', borderColor: colors.green, borderWidth: 1.5 } as any}><Text style={{ color: colors.green, fontWeight: '800' }}>VISITE EN COURS</Text><Text style={{ fontSize: 17, fontWeight: '800', color: colors.ink, marginTop: 6 }}>{(data as any).client} - {(data as any).name}</Text><Text style={{ fontSize: 34, fontWeight: '800', color: colors.ink, marginTop: 8 }}>{fmt(elapsed)}</Text><Text style={{ color: colors.muted }}>Temps ecoule</Text></Card>
    <Text style={{ fontSize: 12, fontWeight: '800', color: colors.muted, marginVertical: 10 }}>TACHES DE SOINS ({nb}/{tasks.length})</Text>
    <Card>{tasks.map((t: any, i: number) => { const k = String(i); const on = !!done[k]; return (<TouchableOpacity key={i} onPress={() => setDone({ ...done, [k]: !on })} style={{ flexDirection: 'row', alignItems: 'center', paddingVertical: 9 }}><View style={{ width: 22, height: 22, borderRadius: 6, borderWidth: 2, borderColor: on ? colors.green : colors.line, backgroundColor: on ? colors.green : '#fff', marginRight: 12, alignItems: 'center', justifyContent: 'center' }}>{on ? <Text style={{ color: '#fff', fontWeight: '800' }}>{'\u2713'}</Text> : null}</View><Text style={{ color: on ? colors.ink : colors.muted }}>{t.label}</Text></TouchableOpacity>); })}</Card>
    <Card><View style={{ flexDirection: 'row' }}>
      <Action icon='alert' label='Incident' onPress={() => nav.navigate('ReportIncident', { id })} />
      <Action icon='message' label='Message' onPress={() => nav.navigate('Conversation')} />
      <Action icon='file' label='Note' onPress={() => nav.navigate('CheckOut', { id })} />
    </View></Card>
    <Button title='Terminer & signer (Check-out)' kind='green' onPress={() => nav.navigate('CheckOut', { id, tasksDone: nb })} />
  </ScrollView></ScreenShell>);
}
