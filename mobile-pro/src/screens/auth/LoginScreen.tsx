import React, { useState } from 'react';
import { ScrollView, View, Text, Image, TouchableOpacity, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors } from '../../theme/colors';
import { Input } from '../../components/Input';
import { Button } from '../../components/Button';
import { authApi } from '../../api/auth';
import { getBase, setBase } from '../../api/client';
import { useAuthStore } from '../../store/authStore';
export function LoginScreen() {
  const setSession = useAuthStore((s) => s.setSession);
  const [mode, setMode] = useState<'login'|'signup'>('login');
  const [login, setLogin] = useState(''); const [pw, setPw] = useState('');
  const [name, setName] = useState(''); const [email, setEmail] = useState(''); const [phone, setPhone] = useState('');
  const [role, setRole] = useState<'FAMILY'|'CAREGIVER'>('FAMILY');
  const [err, setErr] = useState(''); const [busy, setBusy] = useState(false);
  const [srvOpen, setSrvOpen] = useState(false); const [srv, setSrv] = useState(getBase());
  const doLogin = async () => { setBusy(true); setErr(''); try { const d = await authApi.login(login, pw); await setSession(d); } catch (e: any) { setErr(e.status ? 'Identifiants invalides.' : 'Serveur injoignable. Verifiez l adresse et le Wi-Fi.'); } setBusy(false); };
  const doSignup = async () => { setBusy(true); setErr(''); try { const d = await authApi.signup({ name, email, phone, password: pw, role }); await setSession(d); } catch (e: any) { setErr(e.message || 'Impossible de creer le compte.'); } setBusy(false); };
  return (<SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }}><ScrollView contentContainerStyle={{ padding: 26, paddingTop: 40 }} keyboardShouldPersistTaps='handled'>
    <Image source={require('../../../assets/images/panther-logo.png')} style={{ width: 150, height: 150, alignSelf: 'center', marginBottom: 6 }} resizeMode='contain' />
    {mode === 'login' ? (<>
      <Text style={{ fontSize: 25, fontWeight: '800', color: colors.ink, textAlign: 'center' }}>Bienvenue</Text>
      <Text style={{ color: colors.muted, textAlign: 'center', marginTop: 6, marginBottom: 20 }}>Connectez-vous a votre espace de soins.</Text>
      <Input placeholder='E-mail, identifiant ou N d identification' autoCapitalize='none' value={login} onChangeText={setLogin} />
      <Input placeholder='Mot de passe' secureTextEntry value={pw} onChangeText={setPw} />
      {err ? <Text style={{ color: colors.red, textAlign: 'center', marginBottom: 10 }}>{err}</Text> : null}
      <Button title={busy ? '...' : 'Se connecter'} onPress={doLogin} />
      <TouchableOpacity onPress={() => { setMode('signup'); setErr(''); }} style={{ marginTop: 16 }}><Text style={{ textAlign: 'center', color: colors.muted }}>Pas de compte ? <Text style={{ color: colors.brand, fontWeight: '700' }}>Creer un compte</Text></Text></TouchableOpacity>
    </>) : (<>
      <Text style={{ fontSize: 25, fontWeight: '800', color: colors.ink, textAlign: 'center' }}>Creer un compte</Text>
      <Text style={{ color: colors.muted, textAlign: 'center', marginTop: 6, marginBottom: 20 }}>Inscrivez-vous pour suivre les soins en direct.</Text>
      <Input placeholder='Nom complet' value={name} onChangeText={setName} />
      <Input placeholder='E-mail' autoCapitalize='none' keyboardType='email-address' value={email} onChangeText={setEmail} />
      <Input placeholder='Telephone (optionnel)' value={phone} onChangeText={setPhone} />
      <Input placeholder='Mot de passe (8+ caracteres)' secureTextEntry value={pw} onChangeText={setPw} />
      <View style={{ flexDirection: 'row', gap: 8, marginBottom: 12 }}>
        {(['FAMILY','CAREGIVER'] as const).map((r) => (<TouchableOpacity key={r} onPress={() => setRole(r)} style={{ flex: 1, borderWidth: 1, borderColor: role === r ? colors.navy : colors.line, backgroundColor: role === r ? colors.navy : '#fff', borderRadius: 11, paddingVertical: 13, alignItems: 'center' }}><Text style={{ fontWeight: '700', color: role === r ? '#fff' : colors.ink }}>{r === 'FAMILY' ? 'Famille' : 'Soignant'}</Text></TouchableOpacity>))}
      </View>
      {err ? <Text style={{ color: colors.red, textAlign: 'center', marginBottom: 10 }}>{err}</Text> : null}
      <Button title={busy ? '...' : 'Creer mon compte'} kind='green' onPress={doSignup} />
      <TouchableOpacity onPress={() => { setMode('login'); setErr(''); }} style={{ marginTop: 16 }}><Text style={{ textAlign: 'center', color: colors.muted }}>Deja un compte ? <Text style={{ color: colors.brand, fontWeight: '700' }}>Se connecter</Text></Text></TouchableOpacity>
    </>)}
    <TouchableOpacity onPress={() => setSrvOpen(!srvOpen)} style={{ marginTop: 22 }}><Text style={{ textAlign: 'center', color: colors.muted, fontSize: 12 }}>Adresse du serveur</Text></TouchableOpacity>
    {srvOpen ? (<View style={{ marginTop: 10 }}>
      <Input placeholder='http://192.168.x.x:8000/api/mobile' autoCapitalize='none' value={srv} onChangeText={setSrv} />
      <View style={{ flexDirection: 'row', gap: 8 }}>
        <View style={{ flex: 1 }}><Button title='Enregistrer' kind='navy' onPress={async () => { await setBase(srv.trim()); Alert.alert('Serveur enregistre', srv.trim()); }} /></View>
        <View style={{ flex: 1 }}><Button title='Tester' kind='ghost' onPress={async () => { try { const r = await fetch(srv.trim().replace(/\/$/, '') + '/me/'); Alert.alert('Serveur joignable', 'Reponse HTTP ' + r.status); } catch (e) { Alert.alert('Injoignable', 'Verifiez IP, Wi-Fi et backend.'); } }} /></View>
      </View></View>) : null}
  </ScrollView></SafeAreaView>);
}
