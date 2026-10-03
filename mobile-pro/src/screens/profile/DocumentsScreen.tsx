import React from 'react';
import { ScrollView, View, Text } from 'react-native';
import { ScreenShell } from '../../components/ScreenShell';
import { Card } from '../../components/Card';
import { Icon } from '../../components/Icon';
import { EmptyState } from '../../components/EmptyState';
import { Loading } from '../../components/Loading';
import { useFetch } from '../../hooks/useFetch';
import { api } from '../../api/client';
import { colors } from '../../theme/colors';
export function DocumentsScreen() {
  const { data } = useFetch(() => api('/family/documents/').catch(() => ({ documents: [], linked: false })), []);
  if (!data) return <ScreenShell title='Documents'><Loading /></ScreenShell>;
  if ((data as any).linked === false) return <ScreenShell title='Documents'><View style={{ padding: 14 }}><EmptyState text='Liez votre proche pour voir les documents.' icon='user' /></View></ScreenShell>;
  return (<ScreenShell title='Documents'><ScrollView style={{ flex: 1, padding: 14 }}>
    {((data as any).documents || []).length === 0 ? <EmptyState text='Aucun document.' icon='file' /> : ((data as any).documents || []).map((d: any, i: number) => (
      <Card key={i}><View style={{ flexDirection: 'row', alignItems: 'center' }}><View style={{ width: 36, height: 36, borderRadius: 8, backgroundColor: colors.blue + '18', alignItems: 'center', justifyContent: 'center', marginRight: 10 }}><Icon name='file' size={18} color={colors.blue} /></View>
        <View style={{ flex: 1 }}><Text style={{ fontWeight: '700', color: colors.ink }}>{d.title}</Text><Text style={{ color: colors.muted }}>{d.subtitle}</Text></View></View></Card>))}
  </ScrollView></ScreenShell>);
}
