import React, { useState } from 'react';
import { ScrollView, View, Text, TextInput, TouchableOpacity, Alert } from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import * as ImagePicker from 'expo-image-picker';
import { ScreenShell } from '../../components/ScreenShell';
import { Card } from '../../components/Card';
import { Button } from '../../components/Button';
import { queuedApi } from '../../services/offlineQueue';
import { colors } from '../../theme/colors';
export function ReportIncidentScreen() {
  const route: any = useRoute(); const nav: any = useNavigation(); const id = route.params?.id;
  const [type, setType] = useState('Chute'); const [sev, setSev] = useState('high'); const [desc, setDesc] = useState(''); const [photo, setPhoto] = useState<string | null>(null);
  const types = ['Chute', 'Medication', 'Probleme de sante', 'Comportement', 'Autre'];
  const pick = async () => { try { const r: any = await ImagePicker.launchCameraAsync({ base64: true, quality: 0.4 }); if (!r.canceled && r.assets) { setPhoto(r.assets[0].base64); return; } } catch (e) {} try { const r2: any = await ImagePicker.launchImageLibraryAsync({ base64: true, quality: 0.4 }); if (!r2.canceled && r2.assets) setPhoto(r2.assets[0].base64); } catch (e) {} };
  const submit = async () => { try { const r: any = await queuedApi(`/visits/${id}/incident/`, 'POST', { type, severity: sev, description: desc, photo }); Alert.alert(r.__queued ? 'Hors-ligne' : 'Incident signale', r.__queued ? 'Synchro plus tard.' : 'Le bureau a ete alerte.'); nav.goBack(); } catch (e) { Alert.alert('Erreur'); } };
  return (<ScreenShell title='Rapport d incident'><ScrollView style={{ flex: 1, padding: 14 }}><Card>
    <Text style={{ fontSize: 13, fontWeight: '700', color: colors.ink, marginBottom: 8 }}>Quel est le probleme ?</Text>
    {types.map((tp) => (<TouchableOpacity key={tp} onPress={() => setType(tp)} style={{ borderWidth: 1, borderColor: type === tp ? colors.red : colors.line, backgroundColor: type === tp ? '#fdecec' : '#fff', borderRadius: 11, paddingVertical: 13, paddingHorizontal: 14, marginBottom: 8 }}><Text style={{ fontWeight: type === tp ? '700' : '400', color: type === tp ? colors.red : colors.ink }}>{tp}</Text></TouchableOpacity>))}
    <Text style={{ fontSize: 13, fontWeight: '700', color: colors.ink, marginVertical: 8 }}>Severite</Text>
    <View style={{ flexDirection: 'row', gap: 8, marginBottom: 8 }}>{[['low', 'Faible'], ['medium', 'Moyenne'], ['high', 'Elevee']].map(([v, l]) => (<TouchableOpacity key={v} onPress={() => setSev(v)} style={{ flex: 1, borderWidth: 1, borderColor: sev === v ? 'transparent' : colors.line, backgroundColor: sev === v ? (v === 'high' ? colors.red : v === 'medium' ? colors.orange : colors.muted) : '#fff', borderRadius: 10, paddingVertical: 11, alignItems: 'center' }}><Text style={{ color: sev === v ? '#fff' : colors.ink, fontWeight: '600', fontSize: 13 }}>{l}</Text></TouchableOpacity>))}</View>
    <Button title={photo ? 'Photo jointe - remplacer' : 'Ajouter une photo'} kind='ghost' onPress={pick} />
    <Text style={{ fontSize: 13, fontWeight: '700', color: colors.ink, marginVertical: 8 }}>Description</Text>
    <TextInput style={{ height: 80, borderWidth: 1, borderColor: colors.line, borderRadius: 11, padding: 12, textAlignVertical: 'top', marginBottom: 12 }} multiline placeholder='Decrivez...' value={desc} onChangeText={setDesc} />
    <Button title='Soumettre le rapport' kind='red' onPress={submit} /></Card></ScrollView></ScreenShell>);
}
