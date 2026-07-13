import ItemListPage from '@/components/ItemListPage'
export default function Ideas() {
  return <ItemListPage type="idea" title="Ideas" icon="💡" emptyText="No ideas captured." showCheck={false} />
}
