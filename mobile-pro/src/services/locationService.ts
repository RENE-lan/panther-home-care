import * as Location from 'expo-location';
export async function getCoords() {
  try { const { status } = await Location.requestForegroundPermissionsAsync(); if (status !== 'granted') return null; const p = await Location.getCurrentPositionAsync({}); return { lat: p.coords.latitude, lng: p.coords.longitude }; } catch (e) { return null; } }
export function haversine(a: number, b: number, c: number, d: number) {
  const R = 6371000, r = Math.PI / 180; const dLat = (c - a) * r, dLng = (d - b) * r;
  const x = Math.sin(dLat / 2) ** 2 + Math.cos(a * r) * Math.cos(c * r) * Math.sin(dLng / 2) ** 2;
  return Math.round(R * 2 * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x))); }
