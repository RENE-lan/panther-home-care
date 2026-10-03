import React, { useState, useEffect } from 'react';
import { ScrollView, View, Text, Alert } from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import { ScreenShell } from '../../components/ScreenShell';
import { Card } from '../../components/Card';
import { Button } from '../../components/Button';
import { Icon } from '../../components/Icon';
import { getCoords, haversine } from '../../services/locationService';
import { queuedApi } from '../../services/offlineQueue';
import { colors } from '../../theme/colors';
export function EvvVerifyScreen() {
  const route: any = useRoute(); const nav: any = useNavigation(); const v = route.params?.visit || {};
  const [coords, setCoords] = useState<any>(null); const [dist, setDist] = useState<number | null>(null); const [ready, setReady] = useState(false);
  const now = new Date(); const time = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;
  useEffect(() => { (async () => { const cc = await getCoords(); setCoords(cc); if (cc && v.lat != null) setDist(haversine(cc.lat, cc.lng, v.lat, v.lng)); setReady(true); })(); }, []);
  const Row = ({ ok, label }: any) => (<View style={{ flexDirection: 'row', alignItems: 'center', paddingVertical: 10 }}><View style={{ width: 26, height: 26, borderRadius: 13, backgroundColor: (ok ? colors.green : colors.muted) + '20', alignItems: 'center', justifyContent: 'center', marginRight: 12 }}><Icon name='check' size={16} color={ok ? colors.green : colors.muted} /></View><Text style={{ fontSize: 15, color: colors.ink }}>{label}</Text></View>);
  const confirm = async () => {
    try { const res: any = await queuedApi(`/visits/${v.id}/checkin/`, 'POST', coords || {}); Alert.alert(res.__queued ? 'Hors-ligne' : 'Pointage confirmé', res.__queued ? 'Synchro plus tard.' : `Check-in ${time}`); nav.replace('ActiveVisit', { id: v.id }); }
    catch (e) { Alert.alert('Erreur'); }
  };
  const gpsOk = coords != null; const near = dist == null || dist <= 300;
  return (<ScreenShell title='Vérification EVV'><ScrollView style={{ flex: 1, padding: 14 }}>
    <Card>
      <Row ok label='Identité du soignant' />
      <Row ok label='Visite assignée' />
      <Row ok={gpsOk} label={gpsOk ? (dist != null ? `Position GPS (${dist} m)` : 'Position GPS') : 'Position GPS…'} />
      <Row ok label='Heure de début' />
    </Card>
    <Text style={{ fontSize: 40, fontWeight: '800', color: colors.ink, textAlign: 'center', marginVertical: 6 }}>{time}</Text>
    {!near ? <Text style={{ color: colors.orange, textAlign: 'center', marginBottom: 8 }}>Vous semblez éloigné du domicile ({dist} m).</Text> : null}
    <Button title={ready ? 'Confirmer le pointage' : '…'} kind='green' onPress={confirm} />
  </ScrollView></ScreenShell>);
}
