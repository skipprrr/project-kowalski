import ItemListPage from '@/components/ItemListPage'
export default function Journal() {
  return <ItemListPage type="journal" title="Journal" icon="📔" emptyText="No journal entries yet." showCheck={false} />
}
