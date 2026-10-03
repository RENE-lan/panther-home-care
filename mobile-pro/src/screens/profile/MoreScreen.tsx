import React from 'react';
import { ScrollView, TouchableOpacity, Text, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { ScreenShell } from '../../components/ScreenShell';
import { Card } from '../../components/Card';
import { Avatar } from '../../components/Avatar';
import { Button } from '../../components/Button';
import { useAuthStore } from '../../store/authStore';
import { colors } from '../../theme/colors';
export function MoreScreen() {
  const nav: any = useNavigation();
  const me = useAuthStore((s) => s.me);
  const logout = useAuthStore((s) => s.logout);
  const role = me?.role;
  const office = role !== 'CAREGIVER' && role !== 'FAMILY';
  let sections: [string, [string, string][]][] = [];
  if (role === 'CAREGIVER') sections = [
    ['MON TRAVAIL', [['Mon planning', 'Tabs'], ['Visites ouvertes', 'OpenVisits'], ['Feuille de temps', 'Timesheet'], ['Documents', 'Documents'], ['Certifications', 'Certifications'], ['Formations', 'Training'], ['Mes performances', 'Performance'], ['Disponibilite', 'Availability']]],
    ['COMMUNICATION', [['Assistant IA', 'Assistant'], ['Alertes', 'Alerts'], ['Notifications', 'Notifications'], ['Messages', 'Conversation']]],
    ['COMPTE', [['Mon profil', 'Profile'], ['Parametres', 'Settings'], ['Aide & support', 'Support']]],
  ];
  else if (role === 'FAMILY') sections = [
    ['MON PROCHE', [['Mon proche', 'LovedOne'], ['Planning des visites', 'Visits'], ['Documents', 'Documents'], ['Contacts familiaux', 'FamilyContacts']]],
    ['COMMUNICATION', [['Notifications', 'Notifications'], ['Messages', 'Conversation']]],
    ['COMPTE', [['Mon profil', 'Profile'], ['Parametres', 'Settings'], ['Aide & support', 'Support']]],
  ];
  else sections = [
    ['OPERATIONS', [['Demandes', 'Requests'], ['Personnel', 'Personnel'], ['Portail familial', 'FamilyContacts'], ['Copilote IA', 'AIAssistant']]],
    ['COMPTE', [['Mon profil', 'Profile'], ['Notifications', 'Notifications'], ['Parametres', 'Settings'], ['Aide & support', 'Support']]],
  ];
  return (<ScreenShell title='Plus'><ScrollView style={{ flex: 1, padding: 14 }}>
    <TouchableOpacity onPress={() => nav.navigate('Profile')}><Card><View style={{ flexDirection: 'row', alignItems: 'center' }}><Avatar name={me?.name} size={44} /><View style={{ marginLeft: 12, flex: 1 }}><Text style={{ fontSize: 15.5, fontWeight: '700', color: colors.ink }}>{me?.name}</Text><Text style={{ color: colors.muted }}>{me?.id_number} - {me?.role_label}</Text></View><Text style={{ color: colors.blue, fontWeight: '700' }}>Profil {'>'}</Text></View></Card></TouchableOpacity>
    {sections.map(([title, items], si) => (<View key={si}>
      <Text style={{ fontSize: 12, fontWeight: '800', color: colors.muted, marginTop: 14, marginBottom: 8 }}>{title}</Text>
      {items.map(([label, screen], i) => (<TouchableOpacity key={i} onPress={() => nav.navigate(screen)}><Card style={{ paddingVertical: 14 } as any}><View style={{ flexDirection: 'row', justifyContent: 'space-between' }}><Text style={{ fontSize: 15 }}>{label}</Text><Text style={{ color: colors.muted, fontSize: 18 }}>{'>'}</Text></View></Card></TouchableOpacity>))}
    </View>))}
    <View style={{ marginTop: 14 }}><Button title='Deconnexion' kind='ghost' onPress={logout} /></View>
    <Text style={{ textAlign: 'center', color: colors.muted, marginTop: 16 }}>Panther Home Care</Text></ScrollView></ScreenShell>);
}
