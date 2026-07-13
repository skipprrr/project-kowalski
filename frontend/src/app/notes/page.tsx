import ItemListPage from '@/components/ItemListPage'
export default function Notes() {
  return <ItemListPage type="note" title="Notes" icon="📝" emptyText="No notes saved." showCheck={false} />
}
