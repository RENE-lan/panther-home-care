import React from 'react';
import { ScrollView, View, Text } from 'react-native';
import { ScreenShell } from '../../components/ScreenShell';
import { Card } from '../../components/Card';
import { Avatar } from '../../components/Avatar';
import { EmptyState } from '../../components/EmptyState';
import { Loading } from '../../components/Loading';
import { useFetch } from '../../hooks/useFetch';
import { api } from '../../api/client';
import { colors } from '../../theme/colors';
export function FamilyContactsScreen() {
  const { data } = useFetch(() => api('/family/team/').catch(() => ({ team: [], agency: null, linked: false })), []);
  if (!data) return <ScreenShell title='Contacts'><Loading /></ScreenShell>;
  if ((data as any).linked === false) return <ScreenShell title='Contacts'><View style={{ padding: 14 }}><EmptyState text='Liez votre proche pour voir l equipe de soins.' icon='user' /></View></ScreenShell>;
  const ag = (data as any).agency;
  return (<ScreenShell title='Contacts familiaux'><ScrollView style={{ flex: 1, padding: 14 }}>
    {ag ? <Card style={{ backgroundColor: colors.navy } as any}><Text style={{ color: '#dbe4f2' }}>Agence</Text><Text style={{ color: '#fff', fontSize: 17, fontWeight: '800' }}>{ag.name}</Text>{ag.phone ? <Text style={{ color: '#9fb0cc' }}>{ag.phone}</Text> : null}{ag.email ? <Text style={{ color: '#9fb0cc' }}>{ag.email}</Text> : null}</Card> : null}
    <Text style={{ fontSize: 12, fontWeight: '800', color: colors.muted, marginVertical: 10 }}>EQUIPE DE SOINS</Text>
    {((data as any).team || []).length === 0 ? <EmptyState text='Aucun soignant pour le moment.' icon='users' /> : ((data as any).team || []).map((t: any, i: number) => (
      <Card key={i}><View style={{ flexDirection: 'row', alignItems: 'center' }}><Avatar name={t.name} size={40} /><View style={{ marginLeft: 12, flex: 1 }}><Text style={{ fontWeight: '700', color: colors.ink }}>{t.name}</Text><Text style={{ color: colors.muted }}>{t.role} - {t.visits} visite(s){t.phone ? ' - ' + t.phone : ''}</Text></View></View></Card>))}
  </ScrollView></ScreenShell>);
}
