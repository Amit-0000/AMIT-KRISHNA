import { Link } from 'react-router-dom'
import { Upload } from 'lucide-react'
import { PageContainer } from '@/components/layout/PageContainer'
import { Button } from '@/components/ui/button'
import { ScanHistoryTable } from './components/ScanHistoryTable'

export function HistoryPage() {
  return (
    <PageContainer
      maxWidth="xl"
      title="Scan history"
      description="Every file you've submitted and where it is in the pipeline."
      actions={
        <Link to="/scan/new">
          <Button className="gap-2">
            <Upload className="w-4 h-4" aria-hidden="true" />
            New scan
          </Button>
        </Link>
      }
    >
      <ScanHistoryTable />
    </PageContainer>
  )
}
