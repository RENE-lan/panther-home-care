import React from 'react';
import Svg, { Path } from 'react-native-svg';
import { colors } from '../theme/colors';
const P: any = {
  home: 'M3 11l9-8 9 8M5 10v10h14V10',
  calendar: 'M4 6h16v14H4zM4 10h16M8 3v4M16 3v4',
  users: 'M9 12a4 4 0 100-8 4 4 0 000 8zm-6 8a6 6 0 0112 0M17 11a3 3 0 100-6M21 20a5 5 0 00-8-4',
  user: 'M12 12a4 4 0 100-8 4 4 0 000 8zm-7 8a7 7 0 0114 0',
  inbox: 'M4 13h4l2 3h4l2-3h4M4 13V6h16v7M4 13v5h16v-5',
  pin: 'M12 21s-7-6-7-11a7 7 0 0114 0c0 5-7 11-7 11zM12 10a2 2 0 100-4 2 2 0 000 4z',
  message: 'M4 5h16v11H8l-4 4z',
  file: 'M6 3h8l4 4v14H6zM14 3v4h4',
  card: 'M3 7h18v10H3zM3 11h18',
  check: 'M4 12a8 8 0 108-8M8 12l3 3 6-6',
  alert: 'M12 4l9 16H3zM12 10v4M12 17.5v.1',
  dollar: 'M12 3v18M8 7h6a2 2 0 010 4H9a2 2 0 000 4h7',
  activity: 'M3 12h4l2 6 4-14 2 8h6',
  clock: 'M12 3a9 9 0 100 18 9 9 0 000-18zM12 7v5l3 2',
  bolt: 'M13 3L4 14h7l-2 7 9-11h-7z',
  grid: 'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z',
  ai: 'M12 3l1.8 4.7L18.5 9l-4.7 1.3L12 15l-1.8-4.7L5.5 9l4.7-1.3zM18 15l.9 2.3L21 18l-2.1.7L18 21l-.9-2.3L15 18l2.1-.7z',
  send: 'M22 2L11 13M22 2l-7 20-4-9-9-4z',
};
export function Icon({ name, size = 20, color = colors.navy }: { name: string; size?: number; color?: string }) {
  return (<Svg width={size} height={size} viewBox='0 0 24 24'><Path d={P[name] || P.clock} stroke={color} strokeWidth={1.9} fill='none' strokeLinecap='round' strokeLinejoin='round' /></Svg>);
}
