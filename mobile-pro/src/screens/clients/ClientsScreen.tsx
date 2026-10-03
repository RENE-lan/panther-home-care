import React, { useState } from 'react';
import { FlatList } from 'react-native';
import { ScreenShell } from '../../components/ScreenShell';
import { Input } from '../../components/Input';
import { ClientCard } from '../../components/ClientCard';
import { EmptyState } from '../../components/EmptyState';
import { Loading } from '../../components/Loading';
import { useFetch } from '../../hooks/useFetch';
import { clientsApi } from '../../api/clients';
export function ClientsScreen() {
  const [q, setQ] = useState('');
  const { data } = useFetch(() => clientsApi.list(q), [q]);
  return (<ScreenShell title='Clients'>
    <FlatList style={{ flex: 1, padding: 14 }} data={(data as any)?.clients || []} keyExtractor={(c: any) => String(c.id)}
      ListHeaderComponent={<Input placeholder='Rechercher un client...' value={q} onChangeText={setQ} />}
      renderItem={({ item }) => <ClientCard client={item} />}
      ListEmptyComponent={data ? <EmptyState text='Aucun client.' icon='users' /> : <Loading />} /></ScreenShell>);
}
