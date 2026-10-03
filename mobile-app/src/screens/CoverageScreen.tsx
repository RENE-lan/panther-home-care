import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, ActivityIndicator, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { colors, radius } from '../theme';
import { Card, Button, Pill } from '../components/UI';
import { api } from '../api';

export default function CoverageScreen() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const d = await api.openVisits();
      setItems(Array.isArray(d) ? d : d?.visits || []);
    } catch {} finally { setLoading(false); setRefreshing(false); }
  }, []);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  if (loading) return <SafeAreaView style={styles.center}><ActivityIndicator size="large" color={colors.primary} /></SafeAreaView>;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={['bottom']}>
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 30 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} />}>
        <View style={styles.hero}>
          <Ionicons name="sparkles" size={16} color="#ffb37a" />
          <Text style={styles.heroText}>{items.length} visite(s) sans soignant confirmé. Panther classe les meilleurs remplaçants — vous approuvez.</Text>
        </View>
        {items.length === 0 && <Card><Text style={{ color: colors.muted }}>Toutes les visites sont couvertes.</Text></Card>}
        {items.map((v: any, i: number) => (
          <Card key={i} style={{ marginBottom: 12 }}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
              <Text style={styles.cName}>{v.client || v.client_code || 'Client'}</Text>
              <Pill text="Non couverte" bg={colors.redSoft} color={colors.red} />
            </View>
            <Text style={styles.cMeta}>{v.time || v.when || ''}{v.address ? ` · ${v.address}` : ''}</Text>
            {(v.matches || v.caregivers || []).slice(0, 3).map((m: any, j: number) => (
              <View key={j} style={styles.match}>
                <View style={styles.mAvatar}><Ionicons name="person" size={16} color={colors.muted} /></View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.mName}>{m.name || m.caregiver || m.code}</Text>
                  <Text style={styles.mMeta}>{m.distance_km != null ? `${m.distance_km} km` : ''}{m.score != null ? ` · ${m.score}%` : ''}{m.workload ? ` · charge ${String(m.workload).toLowerCase()}` : ''}</Text>
                </View>
                {j === 0 && <Pill text="Recommandé" bg={colors.greenSoft} color={colors.green} />}
              </View>
            ))}
            <Button title="Approuver l’affectation" kind="green" style={{ marginTop: 12 }} />
          </Card>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}
const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.bg },
  hero: { flexDirection: 'row', gap: 8, backgroundColor: colors.navy, borderRadius: radius.lg, padding: 16, marginBottom: 14 },
  heroText: { flex: 1, color: '#dbe6f7', fontSize: 13, lineHeight: 18 },
  cName: { fontSize: 15, fontWeight: '800', color: colors.ink },
  cMeta: { fontSize: 12.5, color: colors.muted, marginTop: 3, marginBottom: 6 },
  match: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 9, borderTopWidth: 1, borderTopColor: colors.line },
  mAvatar: { width: 34, height: 34, borderRadius: 999, backgroundColor: '#eef1f6', alignItems: 'center', justifyContent: 'center' },
  mName: { fontSize: 13.5, fontWeight: '700', color: colors.ink },
  mMeta: { fontSize: 12, color: colors.muted, marginTop: 1 },
});
