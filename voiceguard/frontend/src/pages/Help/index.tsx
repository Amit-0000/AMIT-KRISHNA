import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowRight, MessageSquare, Search, SearchX } from 'lucide-react'
import { PageContainer } from '@/components/layout/PageContainer'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { HELP_ARTICLES, HELP_CATEGORIES } from './content'

export function HelpCenterPage() {
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState<string | null>(null)

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return HELP_ARTICLES.filter((a) => {
      const matchesCategory = !category || a.category === category
      const matchesQuery =
        !q ||
        a.title.toLowerCase().includes(q) ||
        a.summary.toLowerCase().includes(q) ||
        a.body.some((p) => p.toLowerCase().includes(q))
      return matchesCategory && matchesQuery
    })
  }, [query, category])

  return (
    <PageContainer
      maxWidth="lg"
      title="Help Center"
      description="Guides for uploading, understanding results, and managing your account."
    >
      <div className="mb-6 max-w-md">
        <Input
          leftIcon={<Search className="h-4 w-4" />}
          placeholder="Search help articles…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Search help articles"
        />
      </div>

      <div className="flex items-center gap-2 mb-6 overflow-x-auto -mx-1 px-1">
        <button
          onClick={() => setCategory(null)}
          className={cn(
            'flex-shrink-0 px-3.5 py-1.5 rounded-full text-sm font-medium transition-colors border',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand',
            category === null
              ? 'bg-brand text-white border-brand'
              : 'text-text-secondary border-white/10 hover:bg-white/5'
          )}
        >
          All topics
        </button>
        {HELP_CATEGORIES.map((c) => (
          <button
            key={c}
            onClick={() => setCategory(c)}
            className={cn(
              'flex-shrink-0 px-3.5 py-1.5 rounded-full text-sm font-medium transition-colors border whitespace-nowrap',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand',
              category === c
                ? 'bg-brand text-white border-brand'
                : 'text-text-secondary border-white/10 hover:bg-white/5'
            )}
          >
            {c}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center min-h-[30vh] text-center px-6 py-12">
          <div className="w-14 h-14 rounded-2xl bg-white/5 border border-white/8 flex items-center justify-center mb-4">
            <SearchX className="w-6 h-6 text-text-tertiary" aria-hidden="true" />
          </div>
          <h2 className="text-heading-md font-semibold text-text-primary mb-1">No articles found</h2>
          <p className="text-sm text-text-secondary max-w-sm mb-5">
            Try a different search term, or ask us directly.
          </p>
          <Link to="/feedback">
            <Button variant="secondary" size="sm" className="gap-2">
              <MessageSquare className="w-3.5 h-3.5" aria-hidden="true" />
              Give feedback
            </Button>
          </Link>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 gap-3">
          {filtered.map((article, i) => (
            <motion.div
              key={article.slug}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, delay: i * 0.03 }}
            >
              <Link
                to={`/help/${article.slug}`}
                className="group card-base rounded-xl p-5 flex flex-col h-full hover:border-brand/30 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
              >
                <span className="text-[10px] font-semibold uppercase tracking-wider text-brand mb-2">
                  {article.category}
                </span>
                <h3 className="text-sm font-semibold text-text-primary mb-1.5">{article.title}</h3>
                <p className="text-xs text-text-secondary leading-relaxed flex-1">{article.summary}</p>
                <span className="inline-flex items-center gap-1 text-xs font-medium text-brand mt-3 group-hover:gap-1.5 transition-all">
                  Read article
                  <ArrowRight className="w-3 h-3" aria-hidden="true" />
                </span>
              </Link>
            </motion.div>
          ))}
        </div>
      )}

      <div className="mt-10 card-base rounded-xl p-6 flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h3 className="text-sm font-semibold text-text-primary">Still need help?</h3>
          <p className="text-xs text-text-secondary mt-0.5">
            Report an issue, suggest a feature, or flag an incorrect result.
          </p>
        </div>
        <Link to="/feedback">
          <Button size="sm" className="gap-2">
            <MessageSquare className="w-3.5 h-3.5" aria-hidden="true" />
            Give feedback
          </Button>
        </Link>
      </div>
    </PageContainer>
  )
}
