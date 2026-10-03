import React, { useEffect, useState } from 'react';
import {
  View, Text, TextInput, StyleSheet, Image, KeyboardAvoidingView, Platform,
  ScrollView, Alert, TouchableOpacity, ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../auth';
import { colors, radius } from '../theme';
import { API_BASE, setApiBase, loadApiBase } from '../api';

export default function LoginScreen() {
  const { signIn } = useAuth();
  const [u, setU] = useState('rene');
  const [p, setP] = useState('panther123');
  const [show, setShow] = useState(false);
  const [base, setBase] = useState(API_BASE);
  const [showCfg, setShowCfg] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  useEffect(() => { loadApiBase().then(setBase); }, []);

  const go = async () => {
    if (!u.trim() || !p) { setErr('Renseignez vos identifiants.'); return; }
    setErr(''); setBusy(true);
    try {
      if (base && base !== API_BASE) await setApiBase(base);
      await signIn(u.trim(), p);
    } catch (e: any) {
      setErr(e?.message || 'Identifiants ou adresse du serveur incorrects.');
    } finally { setBusy(false); }
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.navy }}>
      {/* decorative header band */}
      <View style={styles.band} />
      <View style={styles.bandGlow} />
      <SafeAreaView style={{ flex: 1 }}>
        <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
          <ScrollView contentContainerStyle={styles.wrap} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
            {/* Brand */}
            <View style={styles.logoWrap}>
              <Image source={require('../../assets/logo.png')} style={styles.logo} resizeMode="contain" />
            </View>
            <Text style={styles.brand}>PANTHER</Text>
            <Text style={styles.tag}>HOME CARE</Text>
            <Text style={styles.sub}>Plateforme intelligente de soins à domicile</Text>

            {/* Card */}
            <View style={styles.card}>
              <Text style={styles.h}>Bienvenue</Text>
              <Text style={styles.hSub}>Connectez-vous à votre espace</Text>

              <View style={[styles.field, err ? styles.fieldErr : null]}>
                <Ionicons name="person-outline" size={18} color={colors.muted} />
                <TextInput
                  value={u} onChangeText={(t) => { setU(t); setErr(''); }}
                  placeholder="Identifiant" placeholderTextColor={colors.muted}
                  autoCapitalize="none" autoCorrect={false} style={styles.input}
                />
              </View>

              <View style={[styles.field, err ? styles.fieldErr : null]}>
                <Ionicons name="lock-closed-outline" size={18} color={colors.muted} />
                <TextInput
                  value={p} onChangeText={(t) => { setP(t); setErr(''); }}
                  placeholder="Mot de passe" placeholderTextColor={colors.muted}
                  secureTextEntry={!show} style={styles.input} onSubmitEditing={go}
                />
                <TouchableOpacity onPress={() => setShow((s) => !s)} hitSlop={10}>
                  <Ionicons name={show ? 'eye-off-outline' : 'eye-outline'} size={19} color={colors.muted} />
                </TouchableOpacity>
              </View>

              {err ? (
                <View style={styles.errRow}>
                  <Ionicons name="alert-circle" size={15} color={colors.red} />
                  <Text style={styles.errText}>{err}</Text>
                </View>
              ) : null}

              <TouchableOpacity activeOpacity={0.9} onPress={go} disabled={busy} style={[styles.btn, busy && { opacity: 0.7 }]}>
                {busy ? <ActivityIndicator color="#fff" /> : <Text style={styles.btnText}>Se connecter</Text>}
              </TouchableOpacity>

              <TouchableOpacity onPress={() => setShowCfg((s) => !s)} style={styles.cfgBtn}>
                <Ionicons name="settings-outline" size={15} color={colors.muted} />
                <Text style={styles.cfgToggle}>{showCfg ? 'Masquer' : 'Configurer'} le serveur</Text>
              </TouchableOpacity>

              {showCfg && (
                <View style={styles.cfgBox}>
                  <Text style={styles.label}>Adresse du backend</Text>
                  <View style={styles.field}>
                    <Ionicons name="globe-outline" size={18} color={colors.muted} />
                    <TextInput
                      value={base} onChangeText={setBase} autoCapitalize="none" autoCorrect={false}
                      placeholder="http://192.168.1.20:8000" placeholderTextColor={colors.muted} style={styles.input}
                    />
                  </View>
                  <Text style={styles.hint}>Téléphone : http://IP-du-PC:8000 · Émulateur Android : http://10.0.2.2:8000</Text>
                </View>
              )}
            </View>

            <View style={styles.demoBox}>
              <Ionicons name="information-circle-outline" size={15} color="#9fb4d6" />
              <Text style={styles.demo}>Démo : rene / panther123</Text>
            </View>
            <Text style={styles.ver}>Panther Home Care · v1.0</Text>
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  band: { position: 'absolute', top: 0, left: 0, right: 0, height: '46%', backgroundColor: colors.navy2 },
  bandGlow: { position: 'absolute', top: -120, right: -80, width: 320, height: 320, borderRadius: 320, backgroundColor: '#1c3a6e', opacity: 0.5 },
  wrap: { flexGrow: 1, alignItems: 'center', justifyContent: 'center', padding: 24, paddingVertical: 40 },
  logoWrap: { width: 92, height: 92, borderRadius: 26, backgroundColor: '#fff', alignItems: 'center', justifyContent: 'center', marginBottom: 16, shadowColor: '#000', shadowOpacity: 0.25, shadowRadius: 14, shadowOffset: { width: 0, height: 8 }, elevation: 6 },
  logo: { width: 60, height: 60 },
  brand: { color: '#fff', fontSize: 28, fontWeight: '900', letterSpacing: 2 },
  tag: { color: '#8fa6cb', fontSize: 12, letterSpacing: 5, marginTop: 2 },
  sub: { color: '#9fb4d6', fontSize: 12.5, marginTop: 10, marginBottom: 26, textAlign: 'center' },
  card: { width: '100%', backgroundColor: '#fff', borderRadius: radius.xl, padding: 22, shadowColor: '#000', shadowOpacity: 0.18, shadowRadius: 24, shadowOffset: { width: 0, height: 12 }, elevation: 8 },
  h: { fontSize: 20, fontWeight: '800', color: colors.ink },
  hSub: { fontSize: 13, color: colors.muted, marginTop: 3, marginBottom: 18 },
  field: { flexDirection: 'row', alignItems: 'center', gap: 10, borderWidth: 1.4, borderColor: colors.line, borderRadius: radius.md, paddingHorizontal: 14, height: 52, backgroundColor: '#fbfcfe', marginBottom: 12 },
  fieldErr: { borderColor: '#f2b8b8' },
  input: { flex: 1, fontSize: 15.5, color: colors.ink, height: '100%' },
  errRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 6, marginTop: 2 },
  errText: { color: colors.red, fontSize: 12.5, flex: 1 },
  btn: { backgroundColor: colors.primary, borderRadius: radius.md, height: 52, alignItems: 'center', justifyContent: 'center', marginTop: 6, shadowColor: colors.primary, shadowOpacity: 0.35, shadowRadius: 12, shadowOffset: { width: 0, height: 6 }, elevation: 4 },
  btnText: { color: '#fff', fontWeight: '800', fontSize: 16, letterSpacing: 0.3 },
  cfgBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, marginTop: 16 },
  cfgToggle: { color: colors.muted, fontWeight: '600', fontSize: 13 },
  cfgBox: { marginTop: 12, borderTopWidth: 1, borderTopColor: colors.line, paddingTop: 12 },
  label: { fontSize: 12.5, fontWeight: '600', color: colors.muted, marginBottom: 6 },
  hint: { fontSize: 11, color: colors.muted, marginTop: 8, lineHeight: 15 },
  demoBox: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 22 },
  demo: { color: '#9fb4d6', fontSize: 12.5 },
  ver: { color: '#5c6f92', fontSize: 11, marginTop: 10 },
});
