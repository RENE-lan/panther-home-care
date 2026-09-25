import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Icon } from '../components/Icon';
import { colors } from '../theme/colors';
import { useAuthStore } from '../store/authStore';
import { HomeScreen } from '../screens/home/HomeScreen';
import { ScheduleScreen } from '../screens/schedule/ScheduleScreen';
import { EVVScreen } from '../screens/evv/EVVScreen';
import { MessagesScreen } from '../screens/messages/MessagesScreen';
import { MoreScreen } from '../screens/profile/MoreScreen';
import { ClientsScreen } from '../screens/clients/ClientsScreen';
import { RequestsScreen } from '../screens/schedule/RequestsScreen';
import { ReportsScreen } from '../screens/care/ReportsScreen';
import { InvoicesScreen } from '../screens/home/InvoicesScreen';
const Tab = createBottomTabNavigator();

function tabsFor(role: string) {
  if (role === 'FAMILY') return [['Accueil', HomeScreen, 'home'], ['Rapports', ReportsScreen, 'file'], ['Factures', InvoicesScreen, 'card'], ['Messages', MessagesScreen, 'message'], ['Plus', MoreScreen, 'grid']];
  if (role === 'CAREGIVER') return [['Accueil', HomeScreen, 'home'], ['Planning', ScheduleScreen, 'calendar'], ['EVV', EVVScreen, 'pin'], ['Messages', MessagesScreen, 'message'], ['Plus', MoreScreen, 'grid']];
  return [['Accueil', HomeScreen, 'home'], ['Planning', ScheduleScreen, 'calendar'], ['Demandes', RequestsScreen, 'inbox'], ['Clients', ClientsScreen, 'users'], ['Plus', MoreScreen, 'grid']];
}

export function MainTabs() {
  const me = useAuthStore((s) => s.me);
  const tabs = tabsFor(me?.role || 'MANAGER');
  return (<Tab.Navigator screenOptions={{ headerShown: false, tabBarActiveTintColor: colors.blue, tabBarInactiveTintColor: colors.muted, tabBarStyle: { paddingTop: 4, height: 58 } }}>
    {tabs.map(([name, Comp, icon]: any) => (
      <Tab.Screen key={name} name={name} component={Comp} options={{ tabBarIcon: ({ color }) => <Icon name={icon} color={color} size={20} /> }} />
    ))}
  </Tab.Navigator>);
}
