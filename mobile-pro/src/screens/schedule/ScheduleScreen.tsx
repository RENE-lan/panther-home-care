import React, { useState } from 'react';
import { ScrollView, TouchableOpacity, Text, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { ScreenShell } from '../../components/ScreenShell';
import { VisitCard } from '../../components/VisitCard';
import { EmptyState } from '../../components/EmptyState';
import { Loading } from '../../components/Loading';
import { useAuthStore } from '../../store/authStore';
import { useFetch } from '../../hooks/useFetch';
import { visitsApi } from '../../api/visits';
import { colors } from '../../theme/colors';
function dayKey(start: string) { return (start || '').split(' ')[0]; }
export function ScheduleScreen() {
  const me = useAuthStore((s) => s.me); const nav: any = useNavigation();
  const office = me?.role !== 'CAREGIVER' && me?.role !== 'FAMILY';
  const [tab, setTab] = useState('today');
  const { data } = useFetch(() => (office ? visitsApi.schedule(0) : visitsApi.mine()), []);
  if (!data) return <ScreenShell title='Planning'><Loading /></ScreenShell>;
  if (office) {
    const days = (data as any).days || [];
    return (<ScreenShell title='Planning'><ScrollView style={{ flex: 1, padding: 14 }}>
      <Text style={{ fontSize: 12, fontWeight: '800', color: colors.muted, marginBottom: 10 }}>{(data as any).week_label} - {(data as any).total} visites</Text>
      {days.flatMap((d: any) => d.visits.map((v: any) => (<TouchableOpacity key={v.id} onPress={() => v.status === 'UNCOVERED' && nav.navigate('Assignment', { visitId: v.id })}><VisitCard visit={{ ...v, client: v.client, care: v.caregiver || 'Non affecte', start: v.time }} /></TouchableOpacity>)))}
    </ScrollView></ScreenShell>);
  }
  const visits = (data as any).visits || [];
  const today = new Date(); const dd = String(today.getDate()).padStart(2,'0') + '/' + String(today.getMonth()+1).padStart(2,'0');
  const tom = new Date(today.getTime() + 86400000); const td = String(tom.getDate()).padStart(2,'0') + '/' + String(tom.getMonth()+1).padStart(2,'0');
  const filtered = visits.filter((v: any) => { const k = dayKey(v.start); if (tab === 'today') return k === dd; if (tab === 'tomorrow') return k === td; return true; });
  const Tab = ({ k, label }: any) => (<TouchableOpacity onPress={() => setTab(k)} style={{ flex: 1, paddingVertical: 9, borderRadius: 10, alignItems: 'center', backgroundColor: tab === k ? colors.navy : '#fff', borderWidth: 1, borderColor: tab === k ? colors.navy : colors.line }}><Text style={{ color: tab === k ? '#fff' : colors.ink, fontWeight: '700', fontSize: 13 }}>{label}</Text></TouchableOpacity>);
  return (<ScreenShell title='Planning'><ScrollView style={{ flex: 1, padding: 14 }}>
    <View style={{ flexDirection: 'row', gap: 8, marginBottom: 12 }}><Tab k='today' label='Aujourd hui' /><Tab k='tomorrow' label='Demain' /><Tab k='week' label='Semaine' /></View>
    {filtered.length === 0 ? <EmptyState text='Aucune visite.' icon='calendar' /> : filtered.map((v: any) => (<TouchableOpacity key={v.id} onPress={() => nav.navigate('VisitDetails', { id: v.id })}><VisitCard visit={v} /></TouchableOpacity>))}
  </ScrollView></ScreenShell>);
}
