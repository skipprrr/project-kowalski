import ItemListPage from '@/components/ItemListPage'
export default function Health() {
  return <ItemListPage type={"health" as any} title="Health" icon="💪" emptyText="No health logs yet." showCheck={false} />
}
