import React, { useState } from 'react';
import { ScrollView, View, Text, TouchableOpacity, Alert } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { ScreenShell } from '../../components/ScreenShell';
import { StatCard } from '../../components/StatCard';
import { Card } from '../../components/Card';
import { AlertCard } from '../../components/AlertCard';
import { Avatar } from '../../components/Avatar';
import { EmptyState } from '../../components/EmptyState';
import { Loading } from '../../components/Loading';
import { Button } from '../../components/Button';
import { Input } from '../../components/Input';
import { colors } from '../../theme/colors';
import { useAuthStore } from '../../store/authStore';
import { useFetch } from '../../hooks/useFetch';
import { dashboardApi } from '../../api/dashboard';
import { aiApi } from '../../api/ai';
import { api } from '../../api/client';

function OfficeHome() {
  const nav: any = useNavigation();
  const { data, refresh } = useFetch(() => dashboardApi.get(), []);
  if (!data) return <Loading />;
  const k = data.kpis || {};
  return (<ScrollView style={{ flex: 1, padding: 14 }}>
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between' }}>
      <StatCard label='Clients' value={k.clients} icon='users' tone={colors.blue} />
      <StatCard label='Soignants' value={k.caregivers} icon='user' tone={colors.navy} />
      <StatCard label='Visites' value={k.today} icon='calendar' tone={colors.blue} />
      <StatCard label='Terminees' value={k.completed} icon='check' tone={colors.green} />
      <StatCard label='Incidents' value={k.incidents} icon='alert' tone={k.incidents ? colors.red : colors.ink} />
      <StatCard label='A encaisser' value={(k.outstanding || 0) + '$'} icon='dollar' tone={k.outstanding ? colors.red : colors.green} />
    </View>
    <Text style={{ fontSize: 12, fontWeight: '800', color: colors.muted, marginVertical: 10 }}>ACTIONS RECOMMANDEES</Text>
    {(data.actions || []).length === 0 ? <EmptyState text='Rien a signaler.' icon='check' /> : (data.actions || []).map((a: any, i: number) => (
      <AlertCard key={i} action={a} onPress={() => a.visit_id && nav.navigate('Assignment', { visitId: a.visit_id })} />))}
  </ScrollView>);
}

function CaregiverHome() {
  const me = useAuthStore((s) => s.me);
  const { data } = useFetch(() => dashboardApi.cgHome(), []);
  const nav: any = useNavigation();
  if (!data) return <Loading />;
  const t = data.today || {};
  return (<ScrollView style={{ flex: 1, padding: 14 }}>
    <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 14 }}><Avatar name={data.name || me?.name} size={44} /><View style={{ marginLeft: 12 }}><Text style={{ fontSize: 20, fontWeight: '800', color: colors.ink }}>Bonjour, {data.name || me?.name}</Text><Text style={{ color: colors.muted }}>Pret pour vos visites ?</Text></View></View>
    <Card><Text style={{ fontSize: 11, fontWeight: '800', color: colors.muted }}>AUJOURD HUI</Text>
      <View style={{ flexDirection: 'row', marginTop: 8 }}>
        {[['Visites', t.total, colors.ink], ['Terminees', t.completed, colors.green], ['En cours', t.in_progress, colors.blue], ['A venir', t.upcoming, colors.orange]].map(([l, v, c]: any, i) => (
          <View key={i} style={{ flex: 1, alignItems: 'center' }}><Text style={{ fontSize: 24, fontWeight: '800', color: c }}>{v || 0}</Text><Text style={{ fontSize: 11, color: colors.muted }}>{l}</Text></View>))}
      </View></Card>
    {data.care_score ? (<TouchableOpacity onPress={() => nav.navigate('Alerts')}><Card style={{ backgroundColor: colors.navy } as any}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}><Text style={{ color: '#ffb37a', fontWeight: '800', fontSize: 12 }}>SCORE DU JOUR</Text><Text style={{ color: '#9fb0cc', fontSize: 12 }}>Voir alertes {'>'}</Text></View>
      <View style={{ flexDirection: 'row', marginTop: 8 }}>
        {[['Visites', data.care_score.visits, '#fff'], ['Conflits', data.care_score.conflicts, '#8ff0b6'], ['Retards', data.care_score.late_risks, '#ffd479'], ['Alertes', data.care_score.alerts, '#ff9a9a']].map((c: any, i: number) => (<View key={i} style={{ flex: 1 }}><Text style={{ color: c[2], fontSize: 22, fontWeight: '800' }}>{c[1]}</Text><Text style={{ color: '#9fb0cc', fontSize: 11 }}>{c[0]}</Text></View>))}
      </View></Card></TouchableOpacity>) : null}
    {data.assistant ? (() => { const a = data.assistant; const tone = a.type === 'soon' ? colors.orange : a.type === 'active' ? colors.blue : colors.green; return (
      <Card style={{ backgroundColor: '#0e1c38' } as any}>
        <Text style={{ color: '#ffb37a', fontWeight: '800', fontSize: 12 }}>ASSISTANT PANTHER IA</Text>
        <Text style={{ color: '#fff', fontWeight: '800', fontSize: 15, marginTop: 6 }}>{a.title}</Text>
        {(a.lines || []).map((l: string, i: number) => (<Text key={i} style={{ color: '#cdd9ee', marginTop: 2 }}>{l}</Text>))}
        {a.visit_id ? (<View style={{ marginTop: 10 }}><Button title={a.type === 'active' ? 'Voir la visite en cours' : 'Voir la visite'} onPress={() => nav.navigate(a.type === 'active' ? 'ActiveVisit' : 'VisitDetails', { id: a.visit_id })} /></View>) : null}
      </Card>); })() : null}
    {data.next_visit ? (<Card><Text style={{ fontSize: 15.5, fontWeight: '700', color: colors.ink }}>{data.next_visit.client} - {data.next_visit.name}</Text><Text style={{ color: colors.muted }}>{data.next_visit.time}-{data.next_visit.end} - {data.next_visit.care}</Text><View style={{ marginTop: 12 }}><Button title={data.next_visit.status === 'IN_PROGRESS' ? 'Voir la visite en cours' : 'Voir la visite'} onPress={() => nav.navigate(data.next_visit.status === 'IN_PROGRESS' ? 'ActiveVisit' : 'VisitDetails', { id: data.next_visit.id })} /></View></Card>) : null}
    {data.cert_warning ? (<Card style={{ backgroundColor: '#fdf6e3', borderColor: '#f5e2a8' } as any}><Text style={{ fontWeight: '800', color: '#8a6d1a' }}>Information importante</Text><Text style={{ color: '#8a6d1a', marginTop: 4 }}>Votre certification {data.cert_warning.name} expire dans {data.cert_warning.days} jours.</Text></Card>) : null}
  </ScrollView>);
}

function FamilyHome() {
  const me = useAuthStore((s) => s.me);
  const nav: any = useNavigation();
  const { data, refresh } = useFetch(() => aiApi.family().catch((e: any) => ({ __err: true })), []);
  const [code, setCode] = useState('');
  if (!data) return <Loading />;
  if ((data as any).__err || (data as any).detail) return (<ScrollView style={{ flex: 1, padding: 14 }}>
    <Card style={{ alignItems: 'center', paddingVertical: 22 } as any}><Avatar name={me?.name} size={56} bg={colors.blue} /><Text style={{ fontSize: 15.5, fontWeight: '700', color: colors.ink, marginTop: 12, textAlign: 'center' }}>Bienvenue, {me?.name}</Text><Text style={{ color: colors.muted, textAlign: 'center', marginTop: 6 }}>Liez votre proche avec le code fourni par l agence pour suivre ses soins.</Text></Card>
    <Card><Text style={{ fontSize: 12, fontWeight: '700', color: colors.ink, marginBottom: 8 }}>Code d invitation</Text><Input placeholder='ex. 2F4EE5' autoCapitalize='characters' value={code} onChangeText={setCode} /><Button title='Lier mon proche' onPress={async () => { try { const r: any = await aiApi.linkFamily(code); Alert.alert('Proche lie', 'Vous suivez ' + r.client); refresh(); } catch (e: any) { Alert.alert('Erreur', e.message || 'Code invalide.'); } }} /><View style={{ height: 10 }} /><Button title='Voir la demo' kind='ghost' onPress={async () => { try { const r: any = await api('/link-demo/', 'POST'); Alert.alert('Demo activee', 'Exemple lie : ' + r.client); refresh(); } catch (e: any) { Alert.alert('Erreur', e.message || ''); } }} /><Text style={{ color: colors.muted, fontSize: 12, marginTop: 8, textAlign: 'center' }}>Pas de code ? Touchez "Voir la demo" pour explorer l'app.</Text></Card>
  </ScrollView>);
  const d: any = data;
  const lo = d.loved_one || {};
  const statusColor = lo.status === 'urgent' ? colors.red : lo.status === 'attention' ? colors.orange : colors.green;
  const Flag = ({ ok, label }: any) => (<View style={{ flexDirection: 'row', alignItems: 'center', paddingVertical: 7 }}><View style={{ width: 9, height: 9, borderRadius: 5, marginRight: 10, backgroundColor: ok ? colors.green : '#c2cad6' }} /><Text style={{ color: ok ? colors.ink : colors.muted }}>{label}</Text></View>);
  return (<ScrollView style={{ flex: 1, padding: 14 }}>
    <Text style={{ fontSize: 20, fontWeight: '800', color: colors.ink, marginBottom: 12 }}>Bonjour</Text>
    <TouchableOpacity onPress={() => nav.navigate('LovedOne')}><Card>
      <Text style={{ fontSize: 11, fontWeight: '800', color: colors.muted }}>MON PROCHE</Text>
      <View style={{ flexDirection: 'row', alignItems: 'center', marginTop: 8 }}><Avatar name={lo.name} size={44} /><View style={{ marginLeft: 12, flex: 1 }}><Text style={{ fontSize: 16, fontWeight: '800', color: colors.ink }}>{lo.name}</Text><View style={{ flexDirection: 'row', alignItems: 'center', marginTop: 2 }}><View style={{ width: 9, height: 9, borderRadius: 5, backgroundColor: statusColor, marginRight: 6 }} /><Text style={{ color: statusColor, fontWeight: '700', fontSize: 13 }}>{lo.status_label}</Text></View></View><Text style={{ color: colors.muted, fontSize: 18 }}>{'>'}</Text></View>
      {lo.next_visit ? (<View style={{ marginTop: 12, borderTopWidth: 1, borderTopColor: colors.line, paddingTop: 10 }}><Text style={{ color: colors.muted, fontSize: 12 }}>Prochaine visite</Text><Text style={{ fontWeight: '700', color: colors.ink }}>{lo.next_visit.when}</Text><Text style={{ color: colors.muted }}>Soignant : {lo.next_visit.caregiver}</Text></View>) : null}
    </Card></TouchableOpacity>
    <Text style={{ fontSize: 12, fontWeight: '800', color: colors.muted, marginVertical: 10 }}>ETAT DES SOINS</Text>
    <Card><Flag ok={d.care_status?.visit_confirmed} label='Visite confirmee' /><Flag ok={d.care_status?.care_done} label='Soins effectues' /><Flag ok={d.care_status?.report_available} label='Rapport disponible' /></Card>
    <Card style={{ backgroundColor: '#eaf1fb', borderColor: '#cfe0f5' } as any}><Text style={{ fontSize: 11, fontWeight: '800', color: colors.blue }}>PANTHER CARE INSIGHTS</Text><Text style={{ color: colors.ink, marginTop: 6 }}>{d.insight}</Text></Card>
    <Button title='Voir les soins' onPress={() => nav.navigate('LovedOne')} />
    {d.wellbeing != null ? <Text style={{ textAlign: 'center', color: colors.muted, marginTop: 14 }}>Bien-etre moyen : {d.wellbeing}%</Text> : null}
  </ScrollView>);
}

export function HomeScreen() {
  const me = useAuthStore((s) => s.me);
  const role = me?.role;
  const title = role === 'FAMILY' ? 'Espace famille' : role === 'CAREGIVER' ? 'Accueil' : 'Tableau de bord';
  return (<ScreenShell title={title}>{role === 'FAMILY' ? <FamilyHome /> : role === 'CAREGIVER' ? <CaregiverHome /> : <OfficeHome />}</ScreenShell>);
}
