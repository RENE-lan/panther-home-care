import React, { useState } from 'react';
import { View, ScrollView, Text, TextInput, TouchableOpacity, Alert } from 'react-native';
import { ScreenShell } from '../../components/ScreenShell';
import { EmptyState } from '../../components/EmptyState';
import { Loading } from '../../components/Loading';
import { useFetch } from '../../hooks/useFetch';
import { api } from '../../api/client';
import { colors } from '../../theme/colors';
export function ConversationScreen() {
  const { data, refresh } = useFetch(() => api('/messages/'), []);
  const [body, setBody] = useState('');
  const send = async () => { if (!body.trim()) return; const b = body; setBody(''); try { await api('/messages/', 'POST', { body: b }); refresh(); } catch (e: any) { Alert.alert('Message non envoye', e.message || ''); setBody(b); } };
  return (<ScreenShell title='Agence Panther'><View style={{ flex: 1 }}>
    <ScrollView style={{ flex: 1, padding: 14 }}>{!data ? <Loading /> : ((data as any).messages || []).map((m: any, i: number) => (
      <View key={i} style={{ maxWidth: '82%', padding: 11, borderRadius: 13, marginBottom: 8, alignSelf: m.from_agency ? 'flex-start' : 'flex-end', backgroundColor: m.from_agency ? '#fff' : colors.blue, borderWidth: m.from_agency ? 1 : 0, borderColor: colors.line }}>
        <Text style={{ color: m.from_agency ? colors.ink : '#fff' }}>{m.body}</Text><Text style={{ fontSize: 10, color: m.from_agency ? colors.muted : '#dbe4f2', marginTop: 3 }}>{m.from_agency ? 'Agence' : 'Vous'} - {m.at}</Text></View>))}
      {data && ((data as any).messages || []).length === 0 ? <EmptyState text='Aucun message. Ecrivez a l agence.' icon='message' /> : null}</ScrollView>
    <View style={{ flexDirection: 'row', gap: 8, padding: 10, backgroundColor: '#fff', borderTopWidth: 1, borderTopColor: colors.line, alignItems: 'center' }}>
      <TextInput style={{ flex: 1, borderWidth: 1, borderColor: colors.line, borderRadius: 11, paddingHorizontal: 14, paddingVertical: 12 }} placeholder='Votre message...' value={body} onChangeText={setBody} />
      <TouchableOpacity onPress={send} style={{ width: 46, height: 46, borderRadius: 12, backgroundColor: colors.blue, alignItems: 'center', justifyContent: 'center' }}><Text style={{ color: '#fff', fontWeight: '700' }}>OK</Text></TouchableOpacity></View>
  </View></ScreenShell>);
}
