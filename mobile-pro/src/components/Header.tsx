import React from 'react';
import { View, Text, TouchableOpacity, Image } from 'react-native';
import { colors } from '../theme/colors';
import { useAuthStore } from '../store/authStore';
export function Header({ title }: { title: string }) {
  const me = useAuthStore((s) => s.me); const logout = useAuthStore((s) => s.logout);
  return (<View style={{ backgroundColor: colors.navy, paddingHorizontal: 14, paddingVertical: 12, flexDirection: 'row', alignItems: 'center' }}>
    <Image source={require('../../assets/images/panther-logo.png')} style={{ width: 30, height: 30, marginRight: 8, borderRadius: 6, backgroundColor: '#fff' }} resizeMode='contain' />
    <View style={{ flex: 1 }}><Text style={{ color: '#fff', fontSize: 17, fontWeight: '800' }}>{title}</Text><Text style={{ color: '#9fb0cc', fontSize: 11 }}>{me?.name} - {me?.role_label}</Text></View>
    <TouchableOpacity onPress={logout} style={{ borderWidth: 1, borderColor: '#33456a', borderRadius: 8, paddingHorizontal: 10, paddingVertical: 6 }}><Text style={{ color: '#cdd9ee', fontSize: 12, fontWeight: '600' }}>Sortir</Text></TouchableOpacity>
  </View>);
}
