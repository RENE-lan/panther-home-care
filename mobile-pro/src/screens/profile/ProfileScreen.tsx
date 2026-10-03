import React, { useState, useEffect } from 'react';
import { ScrollView, View, Text, TouchableOpacity, Alert } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { ScreenShell } from '../../components/ScreenShell';
import { Card } from '../../components/Card';
import { useAuthStore } from '../../store/authStore';
import { colors } from '../../theme/colors';
export function ProfileScreen() {
  const me = useAuthStore((s) => s.me); const [bio, setBio] = useState(false);
  useEffect(() => { (async () => setBio((await AsyncStorage.getItem('bio')) === '1'))(); }, []);
  const toggle = async () => { const nv = !bio; setBio(nv); await AsyncStorage.setItem('bio', nv ? '1' : '0'); Alert.alert('Verrouillage biometrique', nv ? 'Active.' : 'Desactive.'); };
  return (<ScreenShell title='Mon profil'><ScrollView style={{ flex: 1, padding: 14 }}>
    <Card><View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 10 }}><Text style={{ color: colors.muted }}>Nom</Text><Text style={{ fontWeight: '700', color: colors.ink }}>{me?.name}</Text></View>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 10 }}><Text style={{ color: colors.muted }}>N identification</Text><Text style={{ fontWeight: '700', color: colors.ink }}>{me?.id_number}</Text></View>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}><Text style={{ color: colors.muted }}>Role</Text><Text style={{ fontWeight: '700', color: colors.ink }}>{me?.role_label}</Text></View></Card>
    <TouchableOpacity onPress={toggle}><Card><View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}><Text style={{ fontSize: 15 }}>Verrouillage biometrique</Text><View style={{ width: 44, height: 24, borderRadius: 12, backgroundColor: bio ? colors.green : colors.line, justifyContent: 'center', paddingHorizontal: 2 }}><View style={{ width: 20, height: 20, borderRadius: 10, backgroundColor: '#fff', marginLeft: bio ? 22 : 0 }} /></View></View></Card></TouchableOpacity>
  </ScrollView></ScreenShell>);
}
