import React from 'react';
import { ScrollView, TouchableOpacity, View, Text } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { ScreenShell } from '../../components/ScreenShell';
import { Card } from '../../components/Card';
import { EmptyState } from '../../components/EmptyState';
import { Loading } from '../../components/Loading';
import { useFetch } from '../../hooks/useFetch';
import { aiApi } from '../../api/ai';
import { colors } from '../../theme/colors';
export function InvoicesScreen() {
  const nav: any = useNavigation();
  const { data } = useFetch(() => aiApi.family().catch(() => ({ __err: true })), []);
  if (!data) return <ScreenShell title='Factures'><Loading /></ScreenShell>;
  if ((data as any).__err || (data as any).detail) return <ScreenShell title='Factures'><View style={{ padding: 14 }}><EmptyState text='Liez votre proche depuis Accueil pour voir vos factures.' icon='user' /></View></ScreenShell>;
  const d: any = data;
  const invoices = d.invoices || [];
  const pending = invoices.filter((i: any) => !i.paid);
  const history = invoices.filter((i: any) => i.paid);
  return (<ScreenShell title='Factures'><ScrollView style={{ flex: 1, padding: 14 }}>
    <Card style={{ alignItems: 'center' } as any}><Text style={{ color: colors.muted }}>Solde actuel</Text><Text style={{ fontSize: 34, fontWeight: '800', color: d.outstanding ? colors.red : colors.green }}>{d.outstanding} $</Text></Card>
    {pending.map((i: any, k: number) => (<TouchableOpacity key={k} onPress={() => nav.navigate('InvoiceDetails', { invoice: i })}><Card>
      <Text style={{ fontSize: 15.5, fontWeight: '800', color: colors.ink }}>Facture {i.number}</Text><Text style={{ color: colors.muted }}>{i.period}</Text><Text style={{ fontSize: 18, fontWeight: '700', color: colors.ink, marginVertical: 4 }}>{i.amount} $</Text>
      <Text style={{ color: colors.orange, fontWeight: '700' }}>En attente</Text><Text style={{ color: colors.blue, fontWeight: '700', marginTop: 8 }}>Voir la facture {'>'}</Text></Card></TouchableOpacity>))}
    {history.length ? <Text style={{ fontSize: 12, fontWeight: '800', color: colors.muted, marginVertical: 10 }}>HISTORIQUE</Text> : null}
    {history.map((i: any, k: number) => (<TouchableOpacity key={k} onPress={() => nav.navigate('InvoiceDetails', { invoice: i })}><Card><View style={{ flexDirection: 'row', justifyContent: 'space-between' }}><Text style={{ color: colors.ink }}>{i.period}</Text><Text style={{ color: colors.green, fontWeight: '700' }}>Paye</Text></View></Card></TouchableOpacity>))}
  </ScrollView></ScreenShell>);
}
