import { StatusBar } from 'expo-status-bar';
import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  AppState,
  FlatList,
  PermissionsAndroid,
  Platform,
  Pressable,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  useColorScheme,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { CheckEntry, GuardConfig, isSupported, RiskLevel, SmsGuard } from './modules/sms-guard';

const DEMO_SENDER = '+1 (202) 555-0143';
const DEMO_TEXT =
  'E-ZPass: You have an unpaid toll balance of $4.15. Avoid a $50 late fee by paying today: https://ezpass-tollpay.com/pay';

const light = {
  bg: '#f7f7f5', card: '#ffffff', fg: '#1d1d1f', muted: '#5f5f66', line: '#e3e3e0',
  accent: '#1f4fd1', onAccent: '#ffffff', HIGH: '#c62828', MEDIUM: '#9a5b00', LOW: '#2e7d32',
};
const dark: typeof light = {
  bg: '#141416', card: '#1e1e22', fg: '#ececee', muted: '#a3a3ab', line: '#2e2e33',
  accent: '#7aa2ff', onAccent: '#0d1430', HIGH: '#ef6b68', MEDIUM: '#ffb74d', LOW: '#6cc070',
};

export default function App() {
  const c = useColorScheme() === 'dark' ? dark : light;
  const s = styles(c);

  const [granted, setGranted] = useState(SmsGuard.isAccessGranted());
  const [config, setConfig] = useState<GuardConfig>(SmsGuard.getConfig());
  const [history, setHistory] = useState<CheckEntry[]>(SmsGuard.getHistory());
  const [saved, setSaved] = useState(true);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState('');

  const refresh = useCallback(() => {
    setGranted(SmsGuard.isAccessGranted());
    setHistory(SmsGuard.getHistory());
  }, []);

  useEffect(() => {
    // Re-check after the user returns from the Notification access screen.
    const sub = AppState.addEventListener('change', (st) => st === 'active' && refresh());
    const verdicts = SmsGuard.onVerdict((e) => setHistory((h) => [e, ...h].slice(0, 50)));
    if (Platform.OS === 'android' && Platform.Version >= 33) {
      PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.POST_NOTIFICATIONS);
    }
    return () => {
      sub.remove();
      verdicts?.remove();
    };
  }, [refresh]);

  const update = (patch: Partial<GuardConfig>) => {
    setConfig((cur) => ({ ...cur, ...patch }));
    setSaved(false);
  };

  const save = () => {
    SmsGuard.setConfig(config);
    setSaved(true);
  };

  const runDemo = async () => {
    setError('');
    setTesting(true);
    try {
      save();
      await SmsGuard.testCheck(DEMO_SENDER, DEMO_TEXT); // history updates via onVerdict
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setTesting(false);
    }
  };

  if (!isSupported) {
    return (
      <SafeAreaView style={s.screen}>
        <Text style={s.h1}>Scam Shield</Text>
        <Text style={s.muted}>
          Automatic checking needs Android. On iPhone, forward suspicious texts to the Scam Shield
          number instead.
        </Text>
      </SafeAreaView>
    );
  }

  const protectedNow = granted && config.enabled;

  return (
    <SafeAreaView style={s.screen}>
      <StatusBar style={c === dark ? 'light' : 'dark'} />
      <FlatList
        data={history}
        keyExtractor={(e) => `${e.at}-${e.sender}`}
        contentContainerStyle={s.list}
        ListHeaderComponent={
          <View style={{ gap: 16 }}>
            <Text style={s.h1}>Scam Shield</Text>

            <View style={s.card}>
              <Text style={[s.status, { color: protectedNow ? c.LOW : c.HIGH }]}>
                {protectedNow ? 'Protection is on' : 'Protection is off'}
              </Text>
              <Text style={s.muted}>
                {granted
                  ? 'Texts from numbers that aren’t in your contacts are checked automatically. Texts from your contacts are never read.'
                  : 'Allow notification access so Scam Shield can check new texts as they arrive.'}
              </Text>
              {!granted && (
                <Pressable style={s.button} onPress={SmsGuard.openAccessSettings}>
                  <Text style={s.buttonText}>Turn on protection</Text>
                </Pressable>
              )}
            </View>

            <View style={s.card}>
              <Text style={s.h2}>Settings</Text>
              <Text style={s.label}>Server URL</Text>
              <TextInput
                style={s.input}
                value={config.serverUrl}
                onChangeText={(serverUrl) => update({ serverUrl })}
                placeholder="https://your-tunnel.ngrok.app"
                placeholderTextColor={c.muted}
                autoCapitalize="none"
                autoCorrect={false}
                keyboardType="url"
              />
              <Text style={s.label}>My phone number (for guardian alerts)</Text>
              <TextInput
                style={s.input}
                value={config.owner}
                onChangeText={(owner) => update({ owner })}
                placeholder="+15551230001"
                placeholderTextColor={c.muted}
                keyboardType="phone-pad"
              />
              <Row label="Check automatically" value={config.enabled} onChange={(enabled) => update({ enabled })} c={c} />
              <View style={s.actions}>
                <Pressable style={[s.button, saved && s.disabled]} onPress={save} disabled={saved}>
                  <Text style={s.buttonText}>{saved ? 'Saved' : 'Save'}</Text>
                </Pressable>
                <Pressable style={s.secondary} onPress={runDemo} disabled={testing}>
                  {testing ? <ActivityIndicator color={c.accent} /> : <Text style={s.secondaryText}>Try a sample scam</Text>}
                </Pressable>
              </View>
              {!!error && <Text style={[s.muted, { color: c.HIGH }]}>{error}</Text>}
            </View>

            <View style={s.historyHead}>
              <Text style={s.h2}>Recent checks</Text>
              {history.length > 0 && (
                <Pressable
                  onPress={() => {
                    SmsGuard.clearHistory();
                    setHistory([]);
                  }}
                >
                  <Text style={s.link}>Clear</Text>
                </Pressable>
              )}
            </View>
          </View>
        }
        ListEmptyComponent={<Text style={s.muted}>No texts checked yet.</Text>}
        renderItem={({ item }) => <HistoryItem e={item} c={c} />}
      />
    </SafeAreaView>
  );
}

function Row(props: { label: string; value: boolean; onChange: (v: boolean) => void; c: typeof light }) {
  return (
    <View style={styles(props.c).row}>
      <Text style={styles(props.c).body}>{props.label}</Text>
      <Switch value={props.value} onValueChange={props.onChange} trackColor={{ true: props.c.accent }} />
    </View>
  );
}

function HistoryItem({ e, c }: { e: CheckEntry; c: typeof light }) {
  const s = styles(c);
  const color = c[e.level as RiskLevel] ?? c.muted;
  return (
    <View style={[s.card, { borderLeftColor: color, borderLeftWidth: 4 }]}>
      <View style={s.historyHead}>
        <Text style={[s.level, { color }]}>
          {e.level} {Math.round(e.score * 100)}%
        </Text>
        <Text style={s.small}>{new Date(e.at).toLocaleString()}</Text>
      </View>
      <Text style={s.body}>From {e.sender}</Text>
      <Text style={s.muted} numberOfLines={2}>
        {e.body}
      </Text>
      {!!e.summary && <Text style={s.body}>{e.summary}</Text>}
      {e.guardianAlerted && <Text style={s.small}>Your guardian was alerted.</Text>}
    </View>
  );
}

const styles = (c: typeof light) =>
  StyleSheet.create({
    screen: { flex: 1, backgroundColor: c.bg },
    list: { padding: 16, gap: 12 },
    h1: { fontSize: 28, fontWeight: '700', color: c.fg },
    h2: { fontSize: 19, fontWeight: '600', color: c.fg },
    status: { fontSize: 20, fontWeight: '700' },
    body: { fontSize: 16, color: c.fg },
    muted: { fontSize: 15, color: c.muted, lineHeight: 21 },
    small: { fontSize: 13, color: c.muted },
    label: { fontSize: 14, color: c.muted, marginTop: 4 },
    level: { fontSize: 17, fontWeight: '700' },
    card: { backgroundColor: c.card, borderRadius: 12, borderWidth: 1, borderColor: c.line, padding: 16, gap: 8 },
    input: {
      borderWidth: 1, borderColor: c.line, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10,
      fontSize: 16, color: c.fg, backgroundColor: c.bg,
    },
    row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', minHeight: 44 },
    actions: { flexDirection: 'row', gap: 12, marginTop: 4, flexWrap: 'wrap' },
    button: { backgroundColor: c.accent, borderRadius: 10, paddingHorizontal: 18, minHeight: 44, justifyContent: 'center' },
    buttonText: { color: c.onAccent, fontWeight: '600', fontSize: 16 },
    disabled: { opacity: 0.55 },
    secondary: {
      borderWidth: 1, borderColor: c.accent, borderRadius: 10, paddingHorizontal: 18, minHeight: 44, justifyContent: 'center',
    },
    secondaryText: { color: c.accent, fontWeight: '600', fontSize: 16 },
    link: { color: c.accent, fontSize: 15, fontWeight: '600' },
    historyHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  });
