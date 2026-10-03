import * as Notifications from 'expo-notifications';
import { notificationsApi } from '../api/notifications';
export async function registerPush() {
  try { const { status } = await Notifications.requestPermissionsAsync(); if (status !== 'granted') return; const token = (await Notifications.getExpoPushTokenAsync()).data; if (token) await notificationsApi.registerPushToken(token); } catch (e) {} }
