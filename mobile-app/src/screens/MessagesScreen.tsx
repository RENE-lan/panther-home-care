import React, { useRef, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TextInput, TouchableOpacity, KeyboardAvoidingView, Platform, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { colors, radius } from '../theme';
import { api } from '../api';

type Msg = { who: 'me' | 'bot'; text: string };

export default function MessagesScreen() {
  const [msgs, setMsgs] = useState<Msg[]>([{ who: 'bot', text: 'Bonjour, je suis votre copilote. Posez-moi une question sur l’agence, un calcul, ou autre.' }]);
  const [q, setQ] = useState('');
  const [busy, setBusy] = useState(false);
  const scRef = useRef<ScrollView>(null);
  const hist = useRef<any[]>([]);

  const send = async () => {
    const text = q.trim(); if (!text || busy) return;
    setQ(''); setMsgs((m) => [...m, { who: 'me', text }]); setBusy(true);
    try {
      const r = await api.copilot(text, hist.current);
      const a = r?.answer || 'Désolé, je n’ai pas de réponse.';
      setMsgs((m) => [...m, { who: 'bot', text: a }]);
      hist.current = [...hist.current, { role: 'user', content: text }, { role: 'assistant', content: a }].slice(-16);
    } catch {
      setMsgs((m) => [...m, { who: 'bot', text: 'Erreur de connexion au serveur.' }]);
    } finally { setBusy(false); setTimeout(() => scRef.current?.scrollToEnd({ animated: true }), 80); }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={['top']}>
      <View style={styles.top}><Text style={styles.title}>Copilote IA</Text></View>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined} keyboardVerticalOffset={80}>
        <ScrollView ref={scRef} contentContainerStyle={{ padding: 16, paddingBottom: 20 }} onContentSizeChange={() => scRef.current?.scrollToEnd({ animated: true })}>
          {msgs.map((m, i) => (
            <View key={i} style={[styles.row, m.who === 'me' ? { justifyContent: 'flex-end' } : null]}>
              <View style={[styles.bub, m.who === 'me' ? styles.me : styles.bot]}>
                <Text style={[styles.bText, m.who === 'me' ? { color: '#fff' } : { color: colors.ink }]}>{m.text}</Text>
              </View>
            </View>
          ))}
          {busy && <ActivityIndicator color={colors.primary} style={{ marginTop: 8 }} />}
        </ScrollView>
        <View style={styles.compose}>
          <TextInput value={q} onChangeText={setQ} placeholder="Écrivez un message…" placeholderTextColor={colors.muted} style={styles.input} onSubmitEditing={send} />
          <TouchableOpacity style={styles.send} onPress={send}><Ionicons name="send" size={18} color="#fff" /></TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
const styles = StyleSheet.create({
  top: { paddingHorizontal: 16, paddingTop: 8 },
  title: { fontSize: 22, fontWeight: '800', color: colors.ink },
  row: { flexDirection: 'row', marginBottom: 10 },
  bub: { maxWidth: '82%', borderRadius: radius.lg, paddingHorizontal: 14, paddingVertical: 10 },
  me: { backgroundColor: colors.primary, borderBottomRightRadius: 5 },
  bot: { backgroundColor: '#fff', borderWidth: 1, borderColor: colors.line, borderBottomLeftRadius: 5 },
  bText: { fontSize: 14, lineHeight: 20 },
  compose: { flexDirection: 'row', alignItems: 'center', gap: 10, padding: 12, borderTopWidth: 1, borderTopColor: colors.line, backgroundColor: '#fff' },
  input: { flex: 1, backgroundColor: '#f4f6fa', borderRadius: radius.md, paddingHorizontal: 14, paddingVertical: 11, color: colors.ink },
  send: { width: 44, height: 44, borderRadius: radius.md, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
});
