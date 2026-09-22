import React, { useState } from 'react';
import { ScrollView, View, Text, TextInput, TouchableOpacity, Alert } from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import { ScreenShell } from '../../components/ScreenShell';
import { Card } from '../../components/Card';
import { Button } from '../../components/Button';
import { SignaturePad } from '../../components/SignaturePad';
import { queuedApi } from '../../services/offlineQueue';
import { colors } from '../../theme/colors';
export function CheckOutScreen() {
  const route: any = useRoute(); const nav: any = useNavigation(); const id = route.params?.id;
  const [mood, setMood] = useState(4); const [notes, setNotes] = useState(''); const [sign, setSign] = useState(''); const [sig, setSig] = useState('');
  const opts = [[2, 'A surveiller'], [3, 'Stable'], [4, 'Ameliore']] as const;
  const submit = async () => { if (!sig) { Alert.alert('Signature', 'Signez avec votre doigt.'); return; } if (!sign.trim()) { Alert.alert('Signature', 'Entrez votre nom.'); return; } try { const r: any = await queuedApi(`/visits/${id}/checkout/`, 'POST', { mood, notes, signed_by: sign, signature: sig }); Alert.alert(r.__queued ? 'Hors-ligne' : 'Verifie', r.__queued ? 'Synchro plus tard.' : 'Visite terminee.'); nav.navigate('Tabs'); } catch (e) { Alert.alert('Erreur'); } };
  return (<ScreenShell title='Terminer la visite'><ScrollView style={{ flex: 1, padding: 14 }}>
    <Card><Text style={{ fontSize: 13, fontWeight: '700', color: colors.ink, marginBottom: 8 }}>Comment va le client ?</Text>
      {opts.map(([v, l]) => (<TouchableOpacity key={v} onPress={() => setMood(v)} style={{ flexDirection: 'row', alignItems: 'center', paddingVertical: 9 }}><View style={{ width: 22, height: 22, borderRadius: 11, borderWidth: 2, borderColor: mood === v ? colors.blue : colors.line, marginRight: 12, alignItems: 'center', justifyContent: 'center' }}>{mood === v ? <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: colors.blue }} /> : null}</View><Text>{l}</Text></TouchableOpacity>))}
      <Text style={{ fontSize: 13, fontWeight: '700', color: colors.ink, marginVertical: 8 }}>Observations</Text>
      <TextInput style={{ height: 90, borderWidth: 1, borderColor: colors.line, borderRadius: 11, padding: 12, textAlignVertical: 'top', marginBottom: 12 }} multiline placeholder='Observations...' value={notes} onChangeText={setNotes} />
      <Text style={{ fontSize: 13, fontWeight: '700', color: colors.ink, marginBottom: 8 }}>Signature (dessinez)</Text>
      <SignaturePad onChange={setSig} />
      <TextInput style={{ borderWidth: 1, borderColor: colors.line, borderRadius: 11, padding: 12, marginBottom: 12, marginTop: 8 }} placeholder='Nom du signataire' value={sign} onChangeText={setSign} />
      <Button title='Enregistrer & terminer (Check-out)' kind='green' onPress={submit} /></Card>
  </ScrollView></ScreenShell>);
}
