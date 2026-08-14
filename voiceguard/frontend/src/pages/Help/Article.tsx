import { Link, useParams } from 'react-router-dom'
import { ChevronLeft, MessageSquare, SearchX } from 'lucide-react'
import { PageContainer } from '@/components/layout/PageContainer'
import { Button } from '@/components/ui/button'
import { getArticleBySlug, getRelatedArticles } from './content'

function ArticleNotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[40vh] text-center px-6 py-16">
      <div className="w-14 h-14 rounded-2xl bg-chrome/5 border border-chrome/8 flex items-center justify-center mb-4">
        <SearchX className="w-6 h-6 text-text-tertiary" aria-hidden="true" />
      </div>
      <h2 className="text-heading-lg font-semibold text-text-primary mb-2">Article not found</h2>
      <p className="text-sm text-text-secondary max-w-sm mb-5">
        This help article doesn't exist or may have moved.
      </p>
      <Link to="/help">
        <Button variant="secondary" className="gap-2">
          <ChevronLeft className="w-4 h-4" aria-hidden="true" />
          Back to Help Center
        </Button>
      </Link>
    </div>
  )
}

export function HelpArticlePage() {
  const { articleSlug } = useParams<{ articleSlug: string }>()
  const article = articleSlug ? getArticleBySlug(articleSlug) : undefined

  if (!article) {
    return (
      <PageContainer maxWidth="md">
        <ArticleNotFound />
      </PageContainer>
    )
  }

  const related = getRelatedArticles(article)

  return (
    <PageContainer maxWidth="md">
      <Link
        to="/help"
        className="inline-flex items-center gap-1.5 text-sm text-text-tertiary hover:text-text-secondary transition-colors mb-6"
      >
        <ChevronLeft className="w-4 h-4" aria-hidden="true" />
        Back to Help Center
      </Link>

      <article className="card-base rounded-xl p-6 sm:p-8">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-brand">
          {article.category}
        </span>
        <h1 className="text-display-sm font-bold text-text-primary mt-2 mb-5">{article.title}</h1>
        <div className="space-y-4">
          {article.body.map((paragraph, i) => (
            <p key={i} className="text-sm text-text-secondary leading-relaxed">
              {paragraph}
            </p>
          ))}
        </div>
      </article>

      {related.length > 0 && (
        <div className="mt-8">
          <h2 className="text-heading-sm font-semibold text-text-primary mb-3">Related articles</h2>
          <div className="grid sm:grid-cols-2 gap-3">
            {related.map((r) => (
              <Link
                key={r.slug}
                to={`/help/${r.slug}`}
                className="card-base rounded-xl p-4 hover:border-brand/30 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
              >
                <h3 className="text-sm font-semibold text-text-primary mb-1">{r.title}</h3>
                <p className="text-xs text-text-secondary">{r.summary}</p>
              </Link>
            ))}
          </div>
        </div>
      )}

      <div className="mt-8 card-base rounded-xl p-6 flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h3 className="text-sm font-semibold text-text-primary">Didn't answer your question?</h3>
          <p className="text-xs text-text-secondary mt-0.5">Tell us what's missing.</p>
        </div>
        <Link to="/feedback">
          <Button size="sm" variant="secondary" className="gap-2">
            <MessageSquare className="w-3.5 h-3.5" aria-hidden="true" />
            Give feedback
          </Button>
        </Link>
      </div>
    </PageContainer>
  )
}
