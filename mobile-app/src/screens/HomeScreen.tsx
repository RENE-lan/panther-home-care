import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Image, TouchableOpacity, RefreshControl, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { colors, radius } from '../theme';
import { Card, StatCard, Pill, Button } from '../components/UI';
import { api } from '../api';
import { useAuth } from '../auth';

const STATUS: Record<string, { label: string; bg: string; fg: string; icon: keyof typeof Ionicons.glyphMap }> = {
  COMPLETED: { label: 'Terminée', bg: colors.greenSoft, fg: colors.green, icon: 'checkmark-circle' },
  IN_PROGRESS: { label: 'En cours', bg: colors.blueSoft, fg: colors.primary, icon: 'car' },
  SCHEDULED: { label: 'À venir', bg: '#eef1f6', fg: colors.muted, icon: 'time' },
  UNCOVERED: { label: 'Non couverte', bg: colors.redSoft, fg: colors.red, icon: 'alert-circle' },
};

export default function HomeScreen() {
  const { user } = useAuth();
  const nav = useNavigation<any>();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try { setData(await api.dashboard()); } catch {} finally { setLoading(false); setRefreshing(false); }
  }, []);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  const k = data?.kpis || {};
  const alerts = (data?.actions || []).length;
  const topAction = (data?.actions || [])[0];
  const greetHour = new Date().getHours();
  const greet = greetHour < 12 ? 'Bonjour' : greetHour < 18 ? 'Bon après-midi' : 'Bonsoir';

  const quick = [
    { icon: 'person-add', label: 'Nouveau client', to: () => nav.navigate('Clients') },
    { icon: 'calendar', label: 'Planifier', to: () => nav.navigate('Clients') },
    { icon: 'document-text', label: 'Rapports', to: () => nav.navigate('More') },
    { icon: 'location', label: 'Carte couverture', to: () => nav.navigate('Coverage') },
  ] as const;

  if (loading)
    return <SafeAreaView style={styles.center}><ActivityIndicator size="large" color={colors.primary} /></SafeAreaView>;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={['top']}>
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 30 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} />}>
        {/* Header */}
        <View style={styles.header}>
          <Image source={require('../../assets/logo.png')} style={styles.logo} resizeMode="contain" />
          <View style={{ flex: 1 }}>
            <Text style={styles.brand}>Panther</Text>
            <Text style={styles.brandSub}>Home Care</Text>
          </View>
          <View style={styles.bell}>
            <Ionicons name="notifications-outline" size={22} color={colors.ink} />
            {alerts > 0 && <View style={styles.badge}><Text style={styles.badgeText}>{alerts}</Text></View>}
          </View>
          <View style={styles.avatar}><Text style={styles.avatarText}>{(user?.name || 'R')[0]}</Text></View>
        </View>

        <Text style={styles.greet}>{greet}, {user?.name?.split(' ')[0] || 'René'}</Text>
        <Text style={styles.greetSub}>Voici ce qui se passe aujourd’hui.</Text>

        {/* Stat cards */}
        <View style={styles.statsRow}>
          <StatCard icon="calendar" iconBg={colors.blueSoft} iconColor={colors.primary} value={k.today ?? 0} label="Visites du jour" sub={`${k.completed ?? 0} terminées`} />
          <StatCard icon="people" iconBg={colors.greenSoft} iconColor={colors.green} value={k.caregivers ?? 0} label="Soignants actifs" sub="En service" />
        </View>
        <View style={[styles.statsRow, { marginTop: 10 }]}>
          <StatCard icon="warning" iconBg={colors.redSoft} iconColor={colors.red} value={alerts} label="Alertes clients" sub={alerts ? 'À examiner' : 'RAS'} subColor={alerts ? colors.red : colors.muted} />
          <StatCard icon="shield-checkmark" iconBg={colors.purpleSoft} iconColor={colors.purple} value={k.incidents ?? 0} label="Incidents" sub="Ouverts" />
        </View>

        {/* AI Care Coordinator */}
        <Card style={{ marginTop: 16 }}>
          <View style={styles.aiHead}>
            <View style={styles.aiIcon}><Ionicons name="sparkles" size={18} color={colors.primary} /></View>
            <View style={{ flex: 1 }}>
              <Text style={styles.aiTitle}>Coordinateur IA</Text>
              <Text style={styles.aiSub}>Priorités intelligentes.</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color={colors.muted} />
          </View>
          <View style={styles.aiBody}>
            <Text style={styles.aiText}>{topAction?.title ? `${topAction.title}. ${topAction.detail || ''}` : (data?.brief || 'Tout est sous contrôle aujourd’hui.')}</Text>
            {topAction?.type === 'replacement' && (
              <Button title="Voir le match" kind="primary" style={{ marginTop: 10, alignSelf: 'flex-start', paddingHorizontal: 18 }} onPress={() => nav.navigate('Coverage')} />
            )}
          </View>
        </Card>

        {/* Today's Visits */}
        <View style={styles.sectionHead}>
          <Text style={styles.sectionTitle}>Visites du jour</Text>
          <TouchableOpacity onPress={() => nav.navigate('Clients')}><Text style={styles.link}>Tout voir</Text></TouchableOpacity>
        </View>
        {(data?.today || []).length === 0 && <Card><Text style={{ color: colors.muted }}>Aucune visite aujourd’hui.</Text></Card>}
        {(data?.today || []).map((v: any, i: number) => {
          const st = STATUS[v.status] || STATUS.SCHEDULED;
          return (
            <Card key={i} style={{ marginBottom: 10, flexDirection: 'row', alignItems: 'center' }}>
              <View style={styles.vAvatar}><Ionicons name="person" size={20} color={colors.muted} /></View>
              <View style={{ flex: 1 }}>
                <Text style={styles.vName}>{v.client}{v.caregiver ? ` · ${v.caregiver}` : ''}</Text>
                <Text style={styles.vMeta}>{v.time}</Text>
              </View>
              <View style={[styles.vStatus, { backgroundColor: st.bg }]}>
                <Ionicons name={st.icon} size={13} color={st.fg} />
                <Text style={[styles.vStatusText, { color: st.fg }]}>{st.label}</Text>
              </View>
            </Card>
          );
        })}

        {/* Quick actions */}
        <Text style={[styles.sectionTitle, { marginTop: 16, marginBottom: 10 }]}>Actions rapides</Text>
        <View style={styles.quickRow}>
          {quick.map((q) => (
            <TouchableOpacity key={q.label} style={styles.quick} onPress={q.to} activeOpacity={0.8}>
              <View style={styles.quickIcon}><Ionicons name={q.icon as any} size={20} color={colors.primary} /></View>
              <Text style={styles.quickLabel}>{q.label}</Text>
            </TouchableOpacity>
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.bg },
  header: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 6 },
  logo: { width: 34, height: 34 },
  brand: { fontSize: 18, fontWeight: '900', color: colors.navy },
  brandSub: { fontSize: 10, color: colors.muted, letterSpacing: 1, marginTop: -2 },
  bell: { padding: 6 },
  badge: { position: 'absolute', top: 0, right: 0, backgroundColor: colors.red, borderRadius: 999, minWidth: 16, height: 16, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 3 },
  badgeText: { color: '#fff', fontSize: 10, fontWeight: '800' },
  avatar: { width: 38, height: 38, borderRadius: 999, backgroundColor: colors.navy, alignItems: 'center', justifyContent: 'center' },
  avatarText: { color: '#fff', fontWeight: '800' },
  greet: { fontSize: 22, fontWeight: '800', color: colors.ink, marginTop: 8 },
  greetSub: { fontSize: 13.5, color: colors.muted, marginTop: 2, marginBottom: 14 },
  statsRow: { flexDirection: 'row', gap: 10 },
  aiHead: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  aiIcon: { width: 40, height: 40, borderRadius: 12, backgroundColor: colors.blueSoft, alignItems: 'center', justifyContent: 'center' },
  aiTitle: { fontSize: 15.5, fontWeight: '800', color: colors.ink },
  aiSub: { fontSize: 12.5, color: colors.muted },
  aiBody: { backgroundColor: '#f7f9fc', borderRadius: radius.md, padding: 13, marginTop: 12 },
  aiText: { fontSize: 13.5, color: colors.ink, lineHeight: 19 },
  sectionHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 18, marginBottom: 10 },
  sectionTitle: { fontSize: 16, fontWeight: '800', color: colors.ink },
  link: { color: colors.primary, fontWeight: '600', fontSize: 13.5 },
  vAvatar: { width: 42, height: 42, borderRadius: 999, backgroundColor: '#eef1f6', alignItems: 'center', justifyContent: 'center', marginRight: 12 },
  vName: { fontSize: 14.5, fontWeight: '700', color: colors.ink },
  vMeta: { fontSize: 12.5, color: colors.muted, marginTop: 2 },
  vStatus: { flexDirection: 'row', alignItems: 'center', gap: 5, paddingHorizontal: 10, paddingVertical: 6, borderRadius: radius.pill },
  vStatusText: { fontSize: 12, fontWeight: '700' },
  quickRow: { flexDirection: 'row', gap: 10 },
  quick: { flex: 1, backgroundColor: '#fff', borderRadius: radius.md, borderWidth: 1, borderColor: colors.line, alignItems: 'center', paddingVertical: 14 },
  quickIcon: { width: 40, height: 40, borderRadius: 12, backgroundColor: colors.blueSoft, alignItems: 'center', justifyContent: 'center', marginBottom: 8 },
  quickLabel: { fontSize: 11, fontWeight: '600', color: colors.ink, textAlign: 'center' },
});
