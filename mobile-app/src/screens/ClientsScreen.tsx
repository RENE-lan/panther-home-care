import React, { useCallback, useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, ActivityIndicator, RefreshControl, TextInput,
  TouchableOpacity, LayoutAnimation, Platform, UIManager, Linking,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { colors, radius } from '../theme';
import { api } from '../api';

if (Platform.OS === 'android' && UIManager.setLayoutAnimationEnabledExperimental) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}

const RISK: Record<string, { bg: string; fg: string; label: string }> = {
  HIGH: { bg: colors.redSoft, fg: colors.red, label: 'Risque élevé' },
  CRITICAL: { bg: colors.redSoft, fg: colors.red, label: 'Risque critique' },
  MEDIUM: { bg: '#fdf1dc', fg: colors.amber, label: 'Risque moyen' },
  LOW: { bg: colors.greenSoft, fg: colors.green, label: 'Risque faible' },
};

export default function ClientsScreen() {
  const [items, setItems] = useState<any[]>([]);
  const [q, setQ] = useState('');
  const [open, setOpen] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const d = await api.get('clients/').catch(() => api.get('family-portals/')).catch(() => api.dashboard());
      const list = Array.isArray(d) ? d : d?.clients || d?.portals || [];
      setItems(list);
    } catch {} finally { setLoading(false); setRefreshing(false); }
  }, []);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  const toggle = (i: number) => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setOpen((cur) => (cur === i ? null : i));
  };

  const filtered = items.filter((c: any) => JSON.stringify(c).toLowerCase().includes(q.toLowerCase()));
  if (loading)
    return <SafeAreaView style={styles.center}><ActivityIndicator size="large" color={colors.primary} /></SafeAreaView>;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={['top']}>
      <View style={styles.top}>
        <Text style={styles.title}>Clients</Text>
        <Text style={styles.count}>{filtered.length} dossier{filtered.length > 1 ? 's' : ''}</Text>
      </View>
      <View style={styles.search}>
        <Ionicons name="search" size={16} color={colors.muted} />
        <TextInput value={q} onChangeText={setQ} placeholder="Rechercher un client…" placeholderTextColor={colors.muted} style={{ flex: 1, marginLeft: 8, color: colors.ink }} />
        {q ? <TouchableOpacity onPress={() => setQ('')}><Ionicons name="close-circle" size={17} color={colors.muted} /></TouchableOpacity> : null}
      </View>

      <ScrollView contentContainerStyle={{ padding: 16, paddingTop: 4, paddingBottom: 30 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} />}>
        {filtered.length === 0 && (
          <View style={styles.empty}><Ionicons name="people-outline" size={30} color={colors.muted} /><Text style={styles.emptyT}>Aucun client</Text></View>
        )}

        {filtered.map((c: any, i: number) => {
          const name = c.name || c.client || c.full_name || 'Client';
          const code = c.code || '';
          const risk = RISK[(c.risk_level || c.risk || '').toUpperCase()];
          const phone = (c.phone || c.contact || c.contact_phone || c.primary_phone || '').toString();
          const isOpen = open === i;
          return (
            <View key={i} style={[styles.card, isOpen && styles.cardOpen]}>
              {/* Compact header — tap to expand */}
              <TouchableOpacity activeOpacity={0.7} style={styles.head} onPress={() => toggle(i)}>
                <View style={styles.av}><Text style={styles.avT}>{name[0]}</Text></View>
                <View style={{ flex: 1, minWidth: 0 }}>
                  <Text style={styles.n} numberOfLines={1}>{code ? `${code} — ` : ''}{name}</Text>
                  <Text style={styles.m} numberOfLines={1}>{c.care_type || 'Soins à domicile'}</Text>
                </View>
                {phone ? (
                  <TouchableOpacity style={styles.callBtn} onPress={() => Linking.openURL(`tel:${phone.replace(/\s+/g, '')}`)} hitSlop={8}>
                    <Ionicons name="call" size={17} color="#fff" />
                  </TouchableOpacity>
                ) : null}
                {risk && <View style={[styles.riskDot, { backgroundColor: risk.fg }]} />}
                <Ionicons name={isOpen ? 'chevron-up' : 'chevron-down'} size={18} color={colors.muted} />
              </TouchableOpacity>

              {/* Expanded detail — hidden until tapped */}
              {isOpen && (
                <View style={styles.body}>
                  {risk && (
                    <View style={[styles.pill, { backgroundColor: risk.bg, alignSelf: 'flex-start', marginBottom: 10 }]}>
                      <Text style={[styles.pillT, { color: risk.fg }]}>{risk.label}</Text>
                    </View>
                  )}
                  <Row icon="medkit-outline" label="Type de soins" value={c.care_type || '—'} />
                  <Row icon="location-outline" label="Adresse" value={c.address || '—'} />
                  <Row icon="language-outline" label="Langue" value={c.language || c.preferred_language || '—'} />
                  {phone ? <Row icon="call-outline" label="Contact" value={phone} /> : null}
                  <Row icon="pulse-outline" label="Statut" value={c.status || (c.active === false ? 'Inactif' : 'Actif')} />

                  <View style={styles.actions}>
                    {phone ? (
                      <TouchableOpacity style={styles.act} onPress={() => Linking.openURL(`tel:${phone.replace(/\s+/g, '')}`)}>
                        <Ionicons name="call" size={16} color={colors.primary} /><Text style={styles.actT}>Appeler</Text>
                      </TouchableOpacity>
                    ) : null}
                    <TouchableOpacity style={styles.act}>
                      <Ionicons name="document-text-outline" size={16} color={colors.primary} /><Text style={styles.actT}>Dossier</Text>
                    </TouchableOpacity>
                    <TouchableOpacity style={styles.act}>
                      <Ionicons name="chatbubble-ellipses-outline" size={16} color={colors.primary} /><Text style={styles.actT}>Message</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              )}
            </View>
          );
        })}
      </ScrollView>
    </SafeAreaView>
  );
}

function Row({ icon, label, value }: { icon: keyof typeof Ionicons.glyphMap; label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Ionicons name={icon} size={15} color={colors.muted} style={{ width: 20 }} />
      <Text style={styles.rLabel}>{label}</Text>
      <Text style={styles.rValue} numberOfLines={2}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.bg },
  top: { paddingHorizontal: 16, paddingTop: 8, flexDirection: 'row', alignItems: 'baseline', justifyContent: 'space-between' },
  title: { fontSize: 22, fontWeight: '800', color: colors.ink },
  count: { fontSize: 12.5, color: colors.muted, fontWeight: '600' },
  search: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', margin: 16, marginBottom: 6, borderRadius: radius.md, borderWidth: 1, borderColor: colors.line, paddingHorizontal: 12, paddingVertical: 10 },
  empty: { alignItems: 'center', paddingVertical: 50, gap: 8 },
  emptyT: { color: colors.muted, fontSize: 14 },
  card: { backgroundColor: '#fff', borderRadius: radius.md, borderWidth: 1, borderColor: colors.line, marginBottom: 10, overflow: 'hidden' },
  cardOpen: { borderColor: '#c9d6ee', shadowColor: '#0f1e38', shadowOpacity: 0.08, shadowRadius: 10, shadowOffset: { width: 0, height: 4 }, elevation: 2 },
  head: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 13 },
  av: { width: 42, height: 42, borderRadius: 999, backgroundColor: colors.navy, alignItems: 'center', justifyContent: 'center' },
  avT: { color: '#fff', fontWeight: '800' },
  n: { fontSize: 14.5, fontWeight: '700', color: colors.ink },
  m: { fontSize: 12.5, color: colors.muted, marginTop: 2 },
  riskDot: { width: 10, height: 10, borderRadius: 5 },
  callBtn: { width: 36, height: 36, borderRadius: 999, backgroundColor: colors.green, alignItems: 'center', justifyContent: 'center' },
  body: { paddingHorizontal: 14, paddingBottom: 14, borderTopWidth: 1, borderTopColor: '#f2f4f8', paddingTop: 12 },
  pill: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: radius.pill },
  pillT: { fontSize: 11.5, fontWeight: '700' },
  row: { flexDirection: 'row', alignItems: 'flex-start', paddingVertical: 6, gap: 6 },
  rLabel: { width: 110, color: colors.muted, fontSize: 13 },
  rValue: { flex: 1, color: colors.ink, fontSize: 13.5, fontWeight: '600' },
  actions: { flexDirection: 'row', gap: 8, marginTop: 12 },
  act: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, backgroundColor: colors.blueSoft, borderRadius: radius.sm, paddingVertical: 10 },
  actT: { color: colors.primary, fontWeight: '700', fontSize: 12.5 },
});
