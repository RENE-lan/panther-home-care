import React from 'react';
import { ScrollView, View, Text, TouchableOpacity } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { ScreenShell } from '../../components/ScreenShell';
import { Card } from '../../components/Card';
import { Avatar } from '../../components/Avatar';
import { EmptyState } from '../../components/EmptyState';
import { Loading } from '../../components/Loading';
import { Icon } from '../../components/Icon';
import { useFetch } from '../../hooks/useFetch';
import { api } from '../../api/client';
import { useAuthStore } from '../../store/authStore';
import { colors } from '../../theme/colors';
export function MessagesScreen() {
  const me = useAuthStore((s) => s.me);
  const nav: any = useNavigation();
  const { data } = useFetch(() => api('/messages/'), []);
  const { data: notif } = useFetch(() => api('/family/notifications/').catch(() => ({ notifications: [] })), []);
  if (!data) return <ScreenShell title='Messages'><Loading /></ScreenShell>;
  if ((data as any).linked === false && me?.role === 'FAMILY') return <ScreenShell title='Messages'><View style={{ padding: 14 }}><EmptyState text='Liez votre proche depuis Accueil pour ecrire a l agence.' icon='message' /></View></ScreenShell>;
  const msgs = (data as any).messages || [];
  const last = msgs.length ? msgs[msgs.length - 1] : null;
  const items = ((notif as any)?.notifications || []).slice(0, 6);
  return (<ScreenShell title='Messages'><ScrollView style={{ flex: 1, padding: 14 }}>
    <TouchableOpacity onPress={() => nav.navigate('Conversation')}><Card><View style={{ flexDirection: 'row', alignItems: 'center' }}>
      <Avatar name='Agence Panther' size={44} bg={colors.blue} /><View style={{ marginLeft: 12, flex: 1 }}>
      <Text style={{ fontSize: 15.5, fontWeight: '700', color: colors.ink }}>Coordinateur Panther</Text>
      <Text style={{ color: colors.muted }} numberOfLines={1}>{last ? last.body : 'Ecrivez a votre agence de soins'}</Text></View>
      <Text style={{ color: colors.muted, fontSize: 12 }}>{last ? last.at : ''}</Text></View></Card></TouchableOpacity>
    {items.length ? <Text style={{ fontSize: 12, fontWeight: '800', color: colors.muted, marginVertical: 10 }}>ACTIVITE</Text> : null}
    {items.map((n: any, i: number) => (<Card key={i}><View style={{ flexDirection: 'row', alignItems: 'center' }}>
      <View style={{ width: 36, height: 36, borderRadius: 18, backgroundColor: (n.tone === 'g' ? colors.green : n.tone === 'a' ? colors.orange : colors.blue) + '18', alignItems: 'center', justifyContent: 'center', marginRight: 10 }}><Icon name={n.icon} size={18} color={n.tone === 'g' ? colors.green : n.tone === 'a' ? colors.orange : colors.blue} /></View>
      <View style={{ flex: 1 }}><Text style={{ fontWeight: '700', color: colors.ink }}>{n.title}</Text><Text style={{ color: colors.muted }} numberOfLines={1}>{n.text}</Text></View>
      <Text style={{ color: colors.muted, fontSize: 11 }}>{n.when}</Text></View></Card>))}
  </ScrollView></ScreenShell>);
}
