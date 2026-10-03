import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, TextInput, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { colors, radius } from '../theme';
import { Card, Button } from '../components/UI';
import { useAuth } from '../auth';
import { API_BASE, setApiBase, loadApiBase } from '../api';

const LINKS: { icon: keyof typeof Ionicons.glyphMap; label: string }[] = [
  { icon: 'calendar', label: 'Planning' },
  { icon: 'document-text', label: 'Rapports' },
  { icon: 'cash', label: 'Facturation' },
  { icon: 'shield-checkmark', label: 'Conformité' },
  { icon: 'people', label: 'Portail familial' },
  { icon: 'settings', label: 'Paramètres' },
];

export default function MoreScreen() {
  const { user, signOut } = useAuth();
  const [base, setBase] = useState(API_BASE);
  useEffect(() => { loadApiBase().then(setBase); }, []);

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={['top']}>
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 30 }}>
        <Card style={{ flexDirection: 'row', alignItems: 'center' }}>
          <View style={styles.av}><Text style={styles.avT}>{(user?.name || 'R')[0]}</Text></View>
          <View style={{ flex: 1 }}>
            <Text style={styles.name}>{user?.name || 'Utilisateur'}</Text>
            <Text style={styles.role}>{user?.role_label || user?.role || 'Membre'}</Text>
          </View>
        </Card>

        <View style={styles.grid}>
          {LINKS.map((l) => (
            <TouchableOpacity key={l.label} style={styles.tile} activeOpacity={0.8}>
              <View style={styles.tileIcon}><Ionicons name={l.icon} size={20} color={colors.primary} /></View>
              <Text style={styles.tileLabel}>{l.label}</Text>
            </TouchableOpacity>
          ))}
        </View>

        <Text style={styles.section}>Serveur</Text>
        <Card>
          <Text style={styles.label}>Adresse du backend</Text>
          <TextInput value={base} onChangeText={setBase} autoCapitalize="none" style={styles.input} placeholderTextColor={colors.muted} />
          <Button title="Enregistrer" kind="ghost" style={{ marginTop: 10 }} onPress={async () => { await setApiBase(base); Alert.alert('Enregistré', 'Adresse mise à jour.'); }} />
        </Card>

        <Button title="Se déconnecter" kind="ghost" style={{ marginTop: 18 }} onPress={signOut} />
        <Text style={styles.ver}>Panther Home Care · v1.0</Text>
      </ScrollView>
    </SafeAreaView>
  );
}
const styles = StyleSheet.create({
  av: { width: 52, height: 52, borderRadius: 999, backgroundColor: colors.navy, alignItems: 'center', justifyContent: 'center', marginRight: 14 },
  avT: { color: '#fff', fontWeight: '800', fontSize: 20 },
  name: { fontSize: 17, fontWeight: '800', color: colors.ink },
  role: { fontSize: 13, color: colors.muted, marginTop: 2 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginTop: 16 },
  tile: { width: '31.5%', backgroundColor: '#fff', borderRadius: radius.md, borderWidth: 1, borderColor: colors.line, alignItems: 'center', paddingVertical: 16 },
  tileIcon: { width: 42, height: 42, borderRadius: 12, backgroundColor: colors.blueSoft, alignItems: 'center', justifyContent: 'center', marginBottom: 8 },
  tileLabel: { fontSize: 11.5, fontWeight: '600', color: colors.ink },
  section: { fontSize: 13, fontWeight: '800', color: colors.muted, marginTop: 20, marginBottom: 8, letterSpacing: 0.4 },
  label: { fontSize: 12.5, color: colors.muted, marginBottom: 6 },
  input: { borderWidth: 1, borderColor: colors.line, borderRadius: radius.md, paddingHorizontal: 12, paddingVertical: 11, color: colors.ink, backgroundColor: '#fbfcfe' },
  ver: { textAlign: 'center', color: colors.muted, fontSize: 12, marginTop: 18 },
});
