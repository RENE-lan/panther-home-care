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
export function NotificationsScreen() {
  const { data } = useFetch(() => api('/family/notifications/').catch(() => ({ notifications: [], linked: false })), []);
  if (!data) return <ScreenShell title='Notifications'><Loading /></ScreenShell>;
  const items = (data as any).notifications || [];
  return (<ScreenShell title='Notifications'><ScrollView style={{ flex: 1, padding: 14 }}>
    {items.length === 0 ? <EmptyState text='Aucune notification.' icon='clock' /> : items.map((n: any, i: number) => (
      <Card key={i}><View style={{ flexDirection: 'row', alignItems: 'center' }}>
        <View style={{ width: 36, height: 36, borderRadius: 18, backgroundColor: (n.tone === 'g' ? colors.green : n.tone === 'a' ? colors.orange : colors.blue) + '18', alignItems: 'center', justifyContent: 'center', marginRight: 10 }}><Icon name={n.icon} size={18} color={n.tone === 'g' ? colors.green : n.tone === 'a' ? colors.orange : colors.blue} /></View>
        <View style={{ flex: 1 }}><Text style={{ fontWeight: '700', color: colors.ink }}>{n.title}</Text><Text style={{ color: colors.muted }}>{n.text}</Text></View>
        <Text style={{ color: colors.muted, fontSize: 11 }}>{n.when}</Text></View></Card>))}
  </ScrollView></ScreenShell>);
}
