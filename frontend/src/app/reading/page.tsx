import ItemListPage from '@/components/ItemListPage'
export default function Reading() {
  return <ItemListPage type={"read" as any} title="Reading List" icon="📚" emptyText="Nothing on the reading list yet." showCheck={false} />
}
