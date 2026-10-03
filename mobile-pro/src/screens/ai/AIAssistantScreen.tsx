import React, { useState } from 'react';
import { View, ScrollView, Text, TextInput, TouchableOpacity } from 'react-native';
import { ScreenShell } from '../../components/ScreenShell';
import { aiApi } from '../../api/ai';
import { colors } from '../../theme/colors';
export function AIAssistantScreen() {
  const [q, setQ] = useState(''); const [log, setLog] = useState<any[]>([{ bot: true, t: 'Bonjour ! Posez une question sur les operations.' }]);
  const ask = async () => { if (!q.trim()) return; const question = q; setQ(''); setLog((l) => [...l, { bot: false, t: question }, { bot: true, t: '...' }]); try { const r: any = await aiApi.copilot(question); setLog((l) => [...l.slice(0, -1), { bot: true, t: r.answer }]); } catch (e) { setLog((l) => [...l.slice(0, -1), { bot: true, t: 'Erreur.' }]); } };
  return (<ScreenShell title='Copilote IA'><View style={{ flex: 1 }}>
    <ScrollView style={{ flex: 1, padding: 14 }}>{log.map((m, i) => (<View key={i} style={{ maxWidth: '82%', padding: 11, borderRadius: 13, marginBottom: 8, alignSelf: m.bot ? 'flex-start' : 'flex-end', backgroundColor: m.bot ? '#fff' : colors.blue, borderWidth: m.bot ? 1 : 0, borderColor: colors.line }}><Text style={{ color: m.bot ? colors.ink : '#fff' }}>{m.t}</Text></View>))}</ScrollView>
    <View style={{ flexDirection: 'row', gap: 8, padding: 10, backgroundColor: '#fff', borderTopWidth: 1, borderTopColor: colors.line, alignItems: 'center' }}><TextInput style={{ flex: 1, borderWidth: 1, borderColor: colors.line, borderRadius: 11, paddingHorizontal: 14, paddingVertical: 12 }} placeholder='Votre question...' value={q} onChangeText={setQ} /><TouchableOpacity onPress={ask} style={{ width: 46, height: 46, borderRadius: 12, backgroundColor: colors.blue, alignItems: 'center', justifyContent: 'center' }}><Text style={{ color: '#fff', fontWeight: '700' }}>OK</Text></TouchableOpacity></View>
  </View></ScreenShell>);
}
