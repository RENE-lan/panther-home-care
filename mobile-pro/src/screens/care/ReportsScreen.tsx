import React, { useState } from 'react';
import { ScrollView, TouchableOpacity, View, Text } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { ScreenShell } from '../../components/ScreenShell';
import { Card } from '../../components/Card';
import { EmptyState } from '../../components/EmptyState';
import { Loading } from '../../components/Loading';
import { useFetch } from '../../hooks/useFetch';
import { careApi } from '../../api/care';
import { colors } from '../../theme/colors';
function within(iso: string, filter: string) {
  if (filter === 'all') return true;
  if (!iso) return false;
  const d = new Date(iso + 'T00:00:00'); const now = new Date();
  const days = (now.getTime() - d.getTime()) / 86400000;
  if (filter === 'today') return days < 1;
  if (filter === 'week') return days < 7;
  return true;
}
export function ReportsScreen() {
  const nav: any = useNavigation();
  const [filter, setFilter] = useState('all');
  const { data } = useFetch(() => careApi.reports(), []);
  if (!data) return <ScreenShell title='Rapports'><Loading /></ScreenShell>;
  if ((data as any).linked === false) return <ScreenShell title='Rapports'><View style={{ padding: 14 }}><EmptyState text='Liez votre proche depuis Accueil pour voir l historique.' icon='user' /></View></ScreenShell>;
  const all = (data as any).reports || [];
  const reports = all.filter((r: any) => within(r.iso, filter));
  const Tab = ({ k, label }: any) => (<TouchableOpacity onPress={() => setFilter(k)} style={{ flex: 1, paddingVertical: 9, borderRadius: 10, alignItems: 'center', backgroundColor: filter === k ? colors.navy : '#fff', borderWidth: 1, borderColor: filter === k ? colors.navy : colors.line }}><Text style={{ color: filter === k ? '#fff' : colors.ink, fontWeight: '700', fontSize: 13 }}>{label}</Text></TouchableOpacity>);
  return (<ScreenShell title='Rapports'><ScrollView style={{ flex: 1, padding: 14 }}>
    <View style={{ flexDirection: 'row', gap: 8, marginBottom: 12 }}><Tab k='today' label='Aujourd hui' /><Tab k='week' label='Cette semaine' /><Tab k='all' label='Tout' /></View>
    {reports.length === 0 ? <EmptyState text='Aucun rapport sur cette periode.' icon='file' /> : reports.map((r: any, i: number) => (
      <TouchableOpacity key={i} onPress={() => nav.navigate('ReportDetails', { report: r })}><Card>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
          <View style={{ flex: 1 }}><Text style={{ color: colors.green, fontWeight: '700' }}>Rapport de visite{r.signed ? '  (signe)' : ''}</Text><Text style={{ fontSize: 15.5, fontWeight: '700', color: colors.ink }}>{r.caregiver}</Text><Text style={{ color: colors.muted }}>{r.date} - {r.time} - Soins termines</Text></View>
          <Text style={{ color: colors.blue, fontWeight: '700' }}>Voir {'>'}</Text></View></Card></TouchableOpacity>))}
  </ScrollView></ScreenShell>);
}
