import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, ActivityIndicator, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { colors, radius } from '../theme';
import { Card, Pill } from '../components/UI';
import { api } from '../api';

export default function CaregiversScreen() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const load = useCallback(async () => {
    try { const d = await api.personnel(); setItems(Array.isArray(d) ? d : d?.caregivers || d?.personnel || []); }
    catch {} finally { setLoading(false); setRefreshing(false); }
  }, []);
  useFocusEffect(useCallback(() => { load(); }, [load]));
  if (loading) return <SafeAreaView style={styles.center}><ActivityIndicator size="large" color={colors.primary} /></SafeAreaView>;
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={['top']}>
      <View style={{ paddingHorizontal: 16, paddingTop: 8 }}><Text style={styles.title}>Soignants</Text></View>
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 30 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} />}>
        {items.length === 0 && <Card><Text style={{ color: colors.muted }}>Aucun soignant à afficher.</Text></Card>}
        {items.map((c: any, i: number) => (
          <Card key={i} style={{ marginBottom: 10, flexDirection: 'row', alignItems: 'center' }}>
            <View style={styles.av}><Text style={styles.avT}>{(c.name || c.code || 'S')[0]}</Text></View>
            <View style={{ flex: 1 }}>
              <Text style={styles.n}>{c.code ? `${c.code} — ` : ''}{c.name || c.full_name || 'Soignant'}</Text>
              <Text style={styles.m}>{c.role || c.phone || ''}</Text>
            </View>
            <Pill text={c.active === false ? 'Inactif' : 'Actif'} bg={c.active === false ? '#eef1f6' : colors.greenSoft} color={c.active === false ? colors.muted : colors.green} />
          </Card>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}
const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.bg },
  title: { fontSize: 22, fontWeight: '800', color: colors.ink },
  av: { width: 42, height: 42, borderRadius: 999, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center', marginRight: 12 },
  avT: { color: '#fff', fontWeight: '800' },
  n: { fontSize: 14.5, fontWeight: '700', color: colors.ink },
  m: { fontSize: 12.5, color: colors.muted, marginTop: 2 },
});
