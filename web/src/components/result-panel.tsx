'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  FileText,
  List,
  Quote,
  Download,
  Copy,
  Check,
  RotateCcw,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import type { ProcessingResult } from '@/app/page'

interface ResultPanelProps {
  result: ProcessingResult
  onReset: () => void
}

export function ResultPanel({ result, onReset }: ResultPanelProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    const fullMarkdown = generateFullMarkdown(result)
    await navigator.clipboard.writeText(fullMarkdown)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownload = () => {
    const fullMarkdown = generateFullMarkdown(result)
    const blob = new Blob([fullMarkdown], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${result.title}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6"
    >
      {/* Header */}
      <Card>
        <CardHeader className="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-950/30 dark:to-emerald-950/30">
          <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
            <div>
              <CardTitle className="text-2xl">{result.title}</CardTitle>
              <p className="text-muted-foreground mt-1">作者: {result.author}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" size="sm" onClick={handleCopy}>
                {copied ? (
                  <Check className="w-4 h-4 mr-2" />
                ) : (
                  <Copy className="w-4 h-4 mr-2" />
                )}
                {copied ? '已复制' : '复制'}
              </Button>
              <Button variant="outline" size="sm" onClick={handleDownload}>
                <Download className="w-4 h-4 mr-2" />
                下载
              </Button>
              <Button variant="ghost" size="sm" onClick={onReset}>
                <RotateCcw className="w-4 h-4 mr-2" />
                新任务
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Tabs Content */}
      <Tabs defaultValue="content" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="content" className="gap-2">
            <FileText className="w-4 h-4" />
            正文
          </TabsTrigger>
          <TabsTrigger value="outline" className="gap-2">
            <List className="w-4 h-4" />
            目录
          </TabsTrigger>
          <TabsTrigger value="highlights" className="gap-2">
            <Quote className="w-4 h-4" />
            金句
          </TabsTrigger>
        </TabsList>

        <TabsContent value="content" className="mt-6">
          <Card>
            <CardContent className="pt-6 prose dark:prose-invert max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {result.body}
              </ReactMarkdown>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="outline" className="mt-6">
          <Card>
            <CardContent className="pt-6 space-y-6">
              <div>
                <h3 className="text-lg font-semibold mb-3">核心要点</h3>
                <div className="bg-blue-50 dark:bg-blue-950/30 rounded-lg p-4">
                  <p className="text-sm leading-relaxed">
                    {result.executiveSummary}
                  </p>
                </div>
              </div>

              <div>
                <h3 className="text-lg font-semibold mb-3">文章目录</h3>
                <ul className="space-y-2">
                  {result.tableOfContents.map((item, i) => (
                    <motion.li
                      key={i}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="flex items-center gap-3 p-3 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors"
                    >
                      <span className="w-6 h-6 rounded-full bg-primary/10 text-primary text-xs flex items-center justify-center font-medium">
                        {i + 1}
                      </span>
                      <span>{item}</span>
                    </motion.li>
                  ))}
                </ul>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="highlights" className="mt-6">
          <Card>
            <CardContent className="pt-6">
              <div className="space-y-4">
                {result.highlights.map((highlight, i) => (
                  <motion.blockquote
                    key={i}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.1 }}
                    className="relative pl-6 py-4 border-l-4 border-primary bg-slate-50 dark:bg-slate-900 rounded-r-lg"
                  >
                    <Quote className="absolute left-2 top-2 w-4 h-4 text-primary/30" />
                    <p className="text-sm leading-relaxed italic">{highlight}</p>
                  </motion.blockquote>
                ))}
                {result.highlights.length === 0 && (
                  <p className="text-muted-foreground text-center py-8">
                    暂无金句摘录
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </motion.div>
  )
}

function generateFullMarkdown(result: ProcessingResult): string {
  const lines = [
    `# ${result.title}`,
    '',
    `**作者**: ${result.author}`,
    '',
    '---',
    '',
    '## 核心要点',
    '',
    result.executiveSummary,
    '',
    '---',
    '',
    '## 目录',
    '',
    ...result.tableOfContents.map((item) => `- ${item}`),
    '',
    '---',
    '',
    result.body,
  ]

  if (result.highlights.length > 0) {
    lines.push('', '---', '', '## 金句摘录', '')
    result.highlights.forEach((h) => {
      lines.push(`> ${h}`, '')
    })
  }

  return lines.join('\n')
}

function markdownToHtml(markdown: string): string {
  // Simple markdown to HTML conversion
  let html = markdown
    // Headers
    .replace(/^### (.*$)/gm, '<h3 class="text-lg font-semibold mt-6 mb-3">$1</h3>')
    .replace(/^## (.*$)/gm, '<h2 class="text-xl font-bold mt-8 mb-4">$1</h2>')
    .replace(/^# (.*$)/gm, '<h1 class="text-2xl font-bold mt-8 mb-4">$1</h1>')
    // Bold
    .replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold">$1</strong>')
    // Italic
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    // Paragraphs
    .replace(/\n\n/g, '</p><p class="my-4">')
    // Line breaks
    .replace(/\n/g, '<br>')

  return `<p class="my-4">${html}</p>`
}
