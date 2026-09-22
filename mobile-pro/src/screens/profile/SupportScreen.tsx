import React from 'react';
import { ScrollView, Text } from 'react-native';
import { ScreenShell } from '../../components/ScreenShell';
import { Card } from '../../components/Card';
import { colors } from '../../theme/colors';
export function SupportScreen() {
  const faqs = [['Comment lier mon proche ?', 'Entrez le code d invitation fourni par l agence sur l ecran Accueil.'], ['Comment payer une facture ?', 'Ouvrez Factures, touchez une facture puis Payer la facture.'], ['Je ne vois pas de rapport', 'Les rapports apparaissent apres chaque visite terminee et signee.']];
  return (<ScreenShell title='Aide & Support'><ScrollView style={{ flex: 1, padding: 14 }}>
    <Card style={{ backgroundColor: colors.navy } as any}><Text style={{ color: '#fff', fontWeight: '800', fontSize: 16 }}>Besoin d aide ?</Text><Text style={{ color: '#9fb0cc', marginTop: 4 }}>Contactez votre coordinateur Panther via l onglet Messages.</Text></Card>
    <Text style={{ fontSize: 12, fontWeight: '800', color: colors.muted, marginVertical: 10 }}>QUESTIONS FREQUENTES</Text>
    {faqs.map(([q, a], i) => (<Card key={i}><Text style={{ fontWeight: '700', color: colors.ink }}>{q}</Text><Text style={{ color: colors.muted, marginTop: 4 }}>{a}</Text></Card>))}
  </ScrollView></ScreenShell>);
}
