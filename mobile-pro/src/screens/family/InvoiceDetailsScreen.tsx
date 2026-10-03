import React from 'react';
import { ScrollView, View, Text, Alert } from 'react-native';
import { useRoute, useNavigation } from '@react-navigation/native';
import { ScreenShell } from '../../components/ScreenShell';
import { Card } from '../../components/Card';
import { Button } from '../../components/Button';
import { api } from '../../api/client';
import { colors } from '../../theme/colors';
export function InvoiceDetailsScreen() {
  const route: any = useRoute(); const nav: any = useNavigation(); const inv = route.params?.invoice || {};
  const pay = async () => { try { await api(`/invoices/${inv.id}/pay/`, 'POST'); Alert.alert('Paiement confirme', 'Merci !'); nav.goBack(); } catch (e) { Alert.alert('Erreur'); } };
  return (<ScreenShell title='Facture'><ScrollView style={{ flex: 1, padding: 14 }}>
    <Card><Text style={{ fontSize: 15.5, fontWeight: '800', color: colors.ink }}>{inv.number}</Text><Text style={{ color: colors.muted }}>{inv.period}</Text>
      <Text style={{ fontSize: 30, fontWeight: '800', color: colors.ink, marginTop: 10 }}>{inv.amount} $</Text>
      <Text style={{ color: inv.paid ? colors.green : colors.red, fontWeight: '700', marginTop: 4 }}>{inv.paid ? 'Payee' : 'En attente'}</Text></Card>
    {!inv.paid ? <Button title='Payer la facture' kind='green' onPress={pay} /> : null}
  </ScrollView></ScreenShell>);
}
