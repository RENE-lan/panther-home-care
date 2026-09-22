import React from 'react';
import { ScrollView, View, Text, Alert, Linking } from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import { ScreenShell } from '../../components/ScreenShell';
import { Card } from '../../components/Card';
import { Button } from '../../components/Button';
import { Loading } from '../../components/Loading';
import { useFetch } from '../../hooks/useFetch';
import { visitsApi } from '../../api/visits';
import { getCoords, haversine } from '../../services/locationService';
import { queuedApi } from '../../services/offlineQueue';
import { colors } from '../../theme/colors';
export function VisitDetailsScreen() {
  const route: any = useRoute(); const nav: any = useNavigation(); const id = route.params?.id;
  const { data } = useFetch(() => visitsApi.detail(id), [id]);
  const checkin = async () => { const coords = await getCoords(); let geo = ''; if (coords && (data as any).lat != null) { const dist = haversine(coords.lat, coords.lng, (data as any).lat, (data as any).lng); geo = `Distance ${dist} m. `; if (dist > 300) { const go = await new Promise((r) => Alert.alert('Hors zone', `Vous etes a ${dist} m. Pointer quand meme ?`, [{ text: 'Annuler', onPress: () => r(false) }, { text: 'Pointer', onPress: () => r(true) }])); if (!go) return; } } try { const res: any = await queuedApi(`/visits/${id}/checkin/`, 'POST', coords || {}); Alert.alert(res.__queued ? 'Hors-ligne' : 'Arrivee pointee', (res.__queued ? 'Synchro plus tard.' : geo + 'Localisation verifiee.')); nav.goBack(); } catch (e) { Alert.alert('Erreur'); } };
  return (<ScreenShell title='Detail de la visite'>{!data ? <Loading /> : (
    <ScrollView style={{ flex: 1, padding: 14 }}>
      <Card><Text style={{ fontSize: 15.5, fontWeight: '700', color: colors.ink }}>{(data as any).client} - {(data as any).name}</Text><Text style={{ color: colors.muted }}>{(data as any).time}-{(data as any).end}</Text><Text style={{ color: colors.muted }}>{(data as any).address}</Text>        <View style={{ marginTop: 10 }}><Button title='Ouvrir dans Maps' kind='ghost' onPress={() => { const q = (data as any).lat != null ? `${(data as any).lat},${(data as any).lng}` : encodeURIComponent((data as any).address || ''); Linking.openURL(`https://maps.google.com/?q=${q}`); }} /></View></Card>
      <Text style={{ fontSize: 12, fontWeight: '800', color: colors.muted, marginVertical: 10 }}>PLAN DE SOINS</Text>
      <Card>{((data as any).tasks || []).map((t: any, i: number) => (<View key={i} style={{ flexDirection: 'row', paddingVertical: 8 }}><Text style={{ color: colors.green, marginRight: 8 }}>{'\u2713'}</Text><Text style={{ flex: 1 }}>{t.label}</Text></View>))}</Card>
      <Card><Text>{(data as any).note}</Text></Card>
      <View style={{ marginTop: 12 }}>{(data as any).status === 'IN_PROGRESS' ? <Button title='Terminer & signer' kind='green' onPress={() => nav.navigate('CheckOut', { id, client: (data as any).client })} /> : <Button title='Commencer (Check-in)' onPress={checkin} />}</View>
      <View style={{ marginTop: 8 }}><Button title='Signaler un incident' kind='ghost' onPress={() => nav.navigate('ReportIncident', { id })} /></View>
    </ScrollView>)}</ScreenShell>);
}
