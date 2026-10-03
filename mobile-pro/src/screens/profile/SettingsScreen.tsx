import React, { useState, useEffect } from 'react';
import { ScrollView, View, Text, TouchableOpacity, Alert } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { ScreenShell } from '../../components/ScreenShell';
import { Card } from '../../components/Card';
import { colors } from '../../theme/colors';
function Toggle({ label, k, msg }: any) {
  const [on, setOn] = useState(false);
  useEffect(() => { (async () => setOn((await AsyncStorage.getItem(k)) === '1'))(); }, []);
  const t = async () => { const nv = !on; setOn(nv); await AsyncStorage.setItem(k, nv ? '1' : '0'); Alert.alert(label, nv ? 'Active.' : 'Desactive.'); };
  return (<TouchableOpacity onPress={t}><Card><View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}><Text style={{ fontSize: 15 }}>{label}</Text><View style={{ width: 44, height: 24, borderRadius: 12, backgroundColor: on ? colors.green : colors.line, justifyContent: 'center', paddingHorizontal: 2 }}><View style={{ width: 20, height: 20, borderRadius: 10, backgroundColor: '#fff', marginLeft: on ? 22 : 0 }} /></View></View></Card></TouchableOpacity>);
}
export function SettingsScreen() {
  return (<ScreenShell title='Parametres'><ScrollView style={{ flex: 1, padding: 14 }}>
    <Text style={{ fontSize: 12, fontWeight: '800', color: colors.muted, marginBottom: 10 }}>SECURITE</Text>
    <Toggle label='Verrouillage biometrique' k='bio' />
    <Text style={{ fontSize: 12, fontWeight: '800', color: colors.muted, marginVertical: 10 }}>NOTIFICATIONS</Text>
    <Toggle label='Notifications push' k='notif_push' />
    <Toggle label='Rappels de visite' k='notif_visits' />
  </ScrollView></ScreenShell>);
}
