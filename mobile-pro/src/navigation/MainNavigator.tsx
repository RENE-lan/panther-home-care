import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { MainTabs } from './MainTabs';
import { LovedOneScreen } from '../screens/family/LovedOneScreen';
import { ReportDetailsScreen } from '../screens/family/ReportDetailsScreen';
import { InvoiceDetailsScreen } from '../screens/family/InvoiceDetailsScreen';
import { FamilyContactsScreen } from '../screens/clients/FamilyContactsScreen';
import { VisitDetailsScreen } from '../screens/schedule/VisitDetailsScreen';
import { OpenVisitsScreen } from '../screens/schedule/OpenVisitsScreen';
import { AssignmentScreen } from '../screens/schedule/AssignmentScreen';
import { CheckInScreen } from '../screens/evv/CheckInScreen';
import { ActiveVisitScreen } from '../screens/evv/ActiveVisitScreen';
import { CheckOutScreen } from '../screens/evv/CheckOutScreen';
import { CareNotesScreen } from '../screens/care/CareNotesScreen';
import { ReportIncidentScreen } from '../screens/incidents/ReportIncidentScreen';
import { ClientDetailsScreen } from '../screens/clients/ClientDetailsScreen';
import { CaregiverDetailsScreen } from '../screens/caregivers/CaregiverDetailsScreen';
import { ConversationScreen } from '../screens/messages/ConversationScreen';
import { NotificationsScreen } from '../screens/notifications/NotificationsScreen';
import { AIAssistantScreen } from '../screens/ai/AIAssistantScreen';
import { AssistantScreen } from '../screens/caregivers/AssistantScreen';
import { DocumentsScreen } from '../screens/profile/DocumentsScreen';
import { CertificationsScreen } from '../screens/profile/CertificationsScreen';
import { TrainingScreen } from '../screens/profile/TrainingScreen';
import { SettingsScreen } from '../screens/profile/SettingsScreen';
import { SupportScreen } from '../screens/profile/SupportScreen';
import { ProfileScreen } from '../screens/profile/ProfileScreen';
import { EVVResultScreen } from '../screens/evv/EVVResultScreen';
const Stack = createNativeStackNavigator();
export function MainNavigator() {
  return (<Stack.Navigator screenOptions={{ headerShown: false }}>
    <Stack.Screen name='Tabs' component={MainTabs} />
    <Stack.Screen name='LovedOne' component={LovedOneScreen} />
    <Stack.Screen name='ReportDetails' component={ReportDetailsScreen} />
    <Stack.Screen name='InvoiceDetails' component={InvoiceDetailsScreen} />
    <Stack.Screen name='FamilyContacts' component={FamilyContactsScreen} />
    <Stack.Screen name='VisitDetails' component={VisitDetailsScreen} />
    <Stack.Screen name='OpenVisits' component={OpenVisitsScreen} />
    <Stack.Screen name='Assignment' component={AssignmentScreen} />
    <Stack.Screen name='CheckIn' component={CheckInScreen} />
    <Stack.Screen name='ActiveVisit' component={ActiveVisitScreen} />
    <Stack.Screen name='CheckOut' component={CheckOutScreen} />
    <Stack.Screen name='CareNotes' component={CareNotesScreen} />
    <Stack.Screen name='ReportIncident' component={ReportIncidentScreen} />
    <Stack.Screen name='ClientDetails' component={ClientDetailsScreen} />
    <Stack.Screen name='CaregiverDetails' component={CaregiverDetailsScreen} />
    <Stack.Screen name='Conversation' component={ConversationScreen} />
    <Stack.Screen name='Notifications' component={NotificationsScreen} />
    <Stack.Screen name='AIAssistant' component={AIAssistantScreen} />
    <Stack.Screen name='Assistant' component={AssistantScreen} />
    <Stack.Screen name='Documents' component={DocumentsScreen} />
    <Stack.Screen name='Certifications' component={CertificationsScreen} />
    <Stack.Screen name='Training' component={TrainingScreen} />
    <Stack.Screen name='Settings' component={SettingsScreen} />
    <Stack.Screen name='Support' component={SupportScreen} />
    <Stack.Screen name='Profile' component={ProfileScreen} />
    <Stack.Screen name='Timesheet' component={EVVResultScreen} />
  </Stack.Navigator>);
}
