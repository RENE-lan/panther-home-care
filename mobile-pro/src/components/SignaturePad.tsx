import React, { useRef, useState } from 'react';
import { View, TouchableOpacity, Text, PanResponder } from 'react-native';
import Svg, { Path } from 'react-native-svg';
import { colors } from '../theme/colors';
export function SignaturePad({ onChange }: { onChange?: (d: string) => void }) {
  const [paths, setPaths] = useState<string[]>([]); const cur = useRef('');
  const pan = useRef(PanResponder.create({
    onStartShouldSetPanResponder: () => true, onMoveShouldSetPanResponder: () => true,
    onPanResponderGrant: (e) => { cur.current = `M${e.nativeEvent.locationX.toFixed(1)},${e.nativeEvent.locationY.toFixed(1)}`; },
    onPanResponderMove: (e) => { cur.current += ` L${e.nativeEvent.locationX.toFixed(1)},${e.nativeEvent.locationY.toFixed(1)}`; setPaths((p) => [...p.slice(0, -1), cur.current]); },
    onPanResponderStart: () => setPaths((p) => [...p, cur.current]),
    onPanResponderRelease: () => { setPaths((p) => { onChange && onChange(p.join(' ')); return p; }); },
  })).current;
  return (<View><View style={{ height: 150, borderWidth: 1, borderColor: colors.line, borderRadius: 11, backgroundColor: '#fcfdff', overflow: 'hidden' }} {...pan.panHandlers}>
    <Svg width='100%' height='100%'>{paths.map((d, i) => <Path key={i} d={d} stroke={colors.navy} strokeWidth={2.5} fill='none' strokeLinecap='round' strokeLinejoin='round' />)}</Svg></View>
    <TouchableOpacity onPress={() => { setPaths([]); cur.current = ''; onChange && onChange(''); }} style={{ alignSelf: 'flex-end', padding: 6 }}><Text style={{ color: colors.muted, fontSize: 12 }}>Effacer</Text></TouchableOpacity></View>);
}
