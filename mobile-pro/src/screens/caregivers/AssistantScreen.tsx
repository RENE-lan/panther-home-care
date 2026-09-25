import React, { useState, useRef, useEffect } from 'react';
import { View, Text, TextInput, TouchableOpacity, ScrollView, KeyboardAvoidingView, Platform, ActivityIndicator } from 'react-native';
import { ScreenShell } from '../../components/ScreenShell';
import { Icon } from '../../components/Icon';
import { api } from '../../api/client';
import { colors } from '../../theme/colors';

type Msg = { role: 'user' | 'ai'; text: string; escalated?: boolean };
const CHIPS = ['Ma prochaine visite ?', 'Combien d\'heures cette semaine ?', 'Aide-moi à rédiger une note de visite', 'Bonnes pratiques hygiène des mains'];

export function AssistantScreen() {
  const [log, setLog] = useState<Msg[]>([{ role: 'ai', text: 'Bonjour 👋 Je suis votre assistant Panther. Posez-moi n\'importe quelle question — planning, notes de visite, bonnes pratiques… Pour une décision médicale, je vous oriente vers le coordinateur.' }]);
  const [q, setQ] = useState(''); const [busy, setBusy] = useState(false);
  const hist = useRef<{ role: string; content: string }[]>([]);
  const sc = useRef<ScrollView>(null);
  useEffect(() => { sc.current?.scrollToEnd({ animated: true }); }, [log, busy]);

  const send = async (text: string) => {
    const t = text.trim(); if (!t || busy) return;
    setQ(''); setLog((l) => [...l, { role: 'user', text: t }]); setBusy(true);
    try {
      const d: any = await api('/assistant/', 'POST', { question: t, history: hist.current.slice(-8) });
      setLog((l) => [...l, { role: 'ai', text: d.answer, escalated: d.escalated }]);
      hist.current.push({ role: 'user', content: t }, { role: 'assistant', content: d.answer });
    } catch (e) { setLog((l) => [...l, { role: 'ai', text: 'Désolé, une erreur est survenue.' }]); }
    setBusy(false);
  };

  return (
    <ScreenShell title="Assistant IA">
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined} keyboardVerticalOffset={90}>
        <ScrollView ref={sc} style={{ flex: 1 }} contentContainerStyle={{ padding: 14, paddingBottom: 6 }}>
          {log.map((m, i) => (
            <View key={i} style={{ flexDirection: 'row', justifyContent: m.role === 'ai' ? 'flex-start' : 'flex-end', marginBottom: 12 }}>
              {m.role === 'ai' && <View style={{ width: 30, height: 30, borderRadius: 15, backgroundColor: colors.navy, alignItems: 'center', justifyContent: 'center', marginRight: 8 }}><Icon name="ai" size={15} color="#fff" /></View>}
              <View style={{ maxWidth: '82%', backgroundColor: m.role === 'ai' ? '#fff' : colors.brand, borderWidth: m.role === 'ai' ? 1 : 0, borderColor: colors.line, borderRadius: 16, borderBottomLeftRadius: m.role === 'ai' ? 5 : 16, borderBottomRightRadius: m.role === 'ai' ? 16 : 5, paddingVertical: 11, paddingHorizontal: 14 }}>
                {m.escalated && <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 5 }}><Icon name="alert" size={13} color={colors.red} /><Text style={{ color: colors.red, fontWeight: '800', fontSize: 11, marginLeft: 5 }}>À ESCALADER</Text></View>}
                <Text style={{ color: m.role === 'ai' ? colors.ink : '#fff', fontSize: 14.5, lineHeight: 21 }}>{m.text}</Text>
              </View>
            </View>
          ))}
          {busy && <View style={{ flexDirection: 'row', alignItems: 'center', marginLeft: 38 }}><ActivityIndicator size="small" color={colors.muted} /><Text style={{ color: colors.muted, marginLeft: 8 }}>…</Text></View>}
        </ScrollView>

        {log.length <= 1 && (
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ maxHeight: 44 }} contentContainerStyle={{ paddingHorizontal: 12, gap: 8, alignItems: 'center' }}>
            {CHIPS.map((c) => (
              <TouchableOpacity key={c} onPress={() => send(c)} style={{ borderWidth: 1, borderColor: colors.line, backgroundColor: '#fff', borderRadius: 999, paddingVertical: 8, paddingHorizontal: 14 }}>
                <Text style={{ color: colors.ink, fontSize: 13 }}>{c}</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        )}

        <View style={{ flexDirection: 'row', alignItems: 'center', padding: 12, gap: 10, borderTopWidth: 1, borderTopColor: colors.line, backgroundColor: '#fff' }}>
          <TextInput value={q} onChangeText={setQ} placeholder="Écrivez votre message…" placeholderTextColor={colors.muted}
            style={{ flex: 1, backgroundColor: colors.bg, borderRadius: 14, paddingVertical: 12, paddingHorizontal: 16, fontSize: 14.5, color: colors.ink }}
            onSubmitEditing={() => send(q)} returnKeyType="send" />
          <TouchableOpacity onPress={() => send(q)} disabled={busy} style={{ width: 46, height: 46, borderRadius: 14, backgroundColor: colors.brand, alignItems: 'center', justifyContent: 'center' }}>
            <Icon name="send" size={18} color="#fff" />
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </ScreenShell>
  );
}
