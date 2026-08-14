import { useState } from 'react'
import { Share2, Copy, Check, Loader2, Ban } from 'lucide-react'
import { toast } from 'sonner'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { scanApi } from '@/services/api'
import { parseApiError } from '@/lib/apiError'

interface ShareDialogProps {
  scanId: string
}

// create_share (POST /scans/{id}/share) is idempotent server-side — it
// returns the existing active share if one exists rather than minting a
// second one — so it's safe to call on every dialog open instead of first
// fetching share state separately. Only the public result fields
// (verdict/confidence/model/timing — see api.inference.schemas.
// ScanResultResponse) are ever exposed at the shared link; no filename,
// email, or other account detail is included.
export function ShareDialog({ scanId }: ShareDialogProps) {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [revoking, setRevoking] = useState(false)
  const [copied, setCopied] = useState(false)
  const [shareUrl, setShareUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function fetchShare() {
    setLoading(true)
    setError(null)
    try {
      const { data } = await scanApi.share(scanId)
      setShareUrl(data.share_url)
    } catch (err) {
      setError(parseApiError(err).message)
    } finally {
      setLoading(false)
    }
  }

  function handleOpenChange(next: boolean) {
    setOpen(next)
    if (next && !shareUrl) {
      fetchShare()
    }
    if (!next) {
      setCopied(false)
    }
  }

  async function handleCopy() {
    if (!shareUrl) return
    try {
      await navigator.clipboard.writeText(shareUrl)
      setCopied(true)
      toast.success('Link copied to clipboard')
      setTimeout(() => setCopied(false), 2000)
    } catch {
      toast.error('Could not copy link — copy it manually instead.')
    }
  }

  async function handleRevoke() {
    setRevoking(true)
    try {
      await scanApi.unshare(scanId)
      toast.success('Share link revoked — it no longer works.')
      setShareUrl(null)
      setOpen(false)
    } catch (err) {
      toast.error(parseApiError(err).message)
    } finally {
      setRevoking(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant="secondary" className="gap-2">
          <Share2 className="w-4 h-4" aria-hidden="true" />
          Share
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Share this result</DialogTitle>
          <DialogDescription>
            Anyone with this link can view the verdict, confidence, and model details for this scan — no
            sign-in required. The audio file itself is never shared, and revoking the link disables it
            immediately.
          </DialogDescription>
        </DialogHeader>

        <div className="px-6 pb-2">
          {loading ? (
            <div className="flex items-center gap-2 text-sm text-text-secondary py-2">
              <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
              Generating link…
            </div>
          ) : error ? (
            <p className="text-sm text-ai" role="alert">
              {error}
            </p>
          ) : shareUrl ? (
            <div className="flex items-center gap-2">
              <Input readOnly value={shareUrl} onFocus={(e) => e.currentTarget.select()} className="font-mono text-xs" />
              <Button
                type="button"
                size="icon"
                variant="secondary"
                onClick={handleCopy}
                aria-label="Copy link"
              >
                {copied ? (
                  <Check className="w-4 h-4 text-human" aria-hidden="true" />
                ) : (
                  <Copy className="w-4 h-4" aria-hidden="true" />
                )}
              </Button>
            </div>
          ) : null}
        </div>

        <DialogFooter>
          {shareUrl && (
            <Button
              type="button"
              variant="destructive"
              className="gap-2"
              onClick={handleRevoke}
              loading={revoking}
            >
              <Ban className="w-4 h-4" aria-hidden="true" />
              Revoke link
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
