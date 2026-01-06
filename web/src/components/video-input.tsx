'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { Link, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from './ui/textarea'

export type VideoInputPayload = {
  url: string
  sourceType: 'auto' | 'local-audio' | 'local-video' | 'subtitle'
  subtitleText?: string
}

interface VideoInputProps {
  onSubmit: (payload: VideoInputPayload) => void
}

export function VideoInput({ onSubmit }: Readonly<VideoInputProps>) {
  const [url, setUrl] = useState('')
  const [sourceType, setSourceType] = useState<VideoInputPayload['sourceType']>('auto')
  const [subtitleText, setSubtitleText] = useState('')
  const [isValidating, setIsValidating] = useState(false)

  const isValidUrl = (input: string) => {
    const lower = input.toLowerCase()
    return (
      lower.includes('bilibili.com') ||
      lower.includes('b23.tv') ||
      lower.includes('youtube.com') ||
      lower.includes('youtu.be')
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (sourceType === 'subtitle') {
      if (!subtitleText.trim()) return
    } else if (!url) {
      return
    } else if (sourceType === 'auto' && !isValidUrl(url)) {
      return
    }

    setIsValidating(true)
    // 模拟验证
    await new Promise(resolve => setTimeout(resolve, 800))
    setIsValidating(false)
    onSubmit({ url, sourceType, subtitleText: subtitleText.trim() || undefined })
  }

  const helperText = (() => {
    if (sourceType === 'subtitle') return '不会进行关键帧截取 / 音频处理'
    if (sourceType === 'local-audio') return '仅音频：不会进行关键帧截取'
    return '视频源：后续可用于关键帧截取'
  })()

  return (
    <div className="w-full max-w-3xl mx-auto px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-10 space-y-6"
      >
        <h1 className="text-4xl md:text-6xl font-semibold tracking-tight text-slate-900 dark:text-white">
          VideoProse
        </h1>
        <p className="text-lg md:text-xl text-slate-600 dark:text-slate-300 max-w-2xl mx-auto font-light">
          让长视频自然地变成好读的长文
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.1 }}
        className="relative group"
      >
        <div className="absolute -inset-0.5 bg-gradient-to-r from-cyan-400 via-emerald-400 to-amber-300 rounded-2xl blur opacity-25 group-hover:opacity-50 transition duration-500" />

        <form
          onSubmit={handleSubmit}
          className="relative bg-white/90 dark:bg-slate-900/90 backdrop-blur rounded-2xl p-4 md:p-6 shadow-xl border border-slate-200/70 dark:border-slate-800 space-y-4"
        >
          <div className="flex flex-wrap gap-2 text-sm font-medium text-slate-600 dark:text-slate-300">
            <button
              type="button"
              onClick={() => setSourceType('auto')}
              className={`px-3 py-1 rounded-full border ${sourceType === 'auto' ? 'border-blue-500 text-blue-600 bg-blue-50' : 'border-slate-200 dark:border-slate-700'}`}
            >
              视频链接
            </button>
            <button
              type="button"
              onClick={() => setSourceType('local-video')}
              className={`px-3 py-1 rounded-full border ${sourceType === 'local-video' ? 'border-blue-500 text-blue-600 bg-blue-50' : 'border-slate-200 dark:border-slate-700'}`}
            >
              本地视频路径
            </button>
            <button
              type="button"
              onClick={() => setSourceType('local-audio')}
              className={`px-3 py-1 rounded-full border ${sourceType === 'local-audio' ? 'border-blue-500 text-blue-600 bg-blue-50' : 'border-slate-200 dark:border-slate-700'}`}
            >
              本地音频路径
            </button>
            <button
              type="button"
              onClick={() => setSourceType('subtitle')}
              className={`px-3 py-1 rounded-full border ${sourceType === 'subtitle' ? 'border-blue-500 text-blue-600 bg-blue-50' : 'border-slate-200 dark:border-slate-700'}`}
            >
              字幕
            </button>
          </div>

          {sourceType === 'subtitle' ? (
            <div className="space-y-2">
              <Textarea
                placeholder="粘贴已有字幕文本（纯文本）"
                value={subtitleText}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setSubtitleText(e.target.value)}
                className="min-h-[140px] text-sm"
              />
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <div className="pl-1 text-slate-400">
                <Link className="w-5 h-5" />
              </div>
              <Input
                type="text"
                placeholder={sourceType === 'auto' ? '输入 Bilibili / YouTube 链接' : '输入本地绝对路径，例如 D:/media/video.mp4 或 file://...'}
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                className="flex-1 h-12 text-base border-none bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 placeholder:text-slate-400"
              />
            </div>
          )}

            <div className="flex justify-between items-center text-xs text-slate-500">
            <span>{helperText}</span>
            <span className="text-emerald-600">本地路径需后端可访问</span>
          </div>

          <div className="flex justify-end">
            <Button
              type="submit"
              disabled={isValidating || (sourceType === 'subtitle' ? !subtitleText.trim() : !url)}
              className="h-11 px-6 text-base font-medium rounded-xl bg-gradient-to-r from-cyan-500 to-emerald-500 text-white shadow-lg shadow-cyan-500/25 hover:shadow-xl hover:shadow-emerald-500/30 transition-all"
            >
              {isValidating ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                '开始处理'
              )}
            </Button>
          </div>
        </form>
      </motion.div>

      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="flex items-center justify-center gap-6 mt-12 opacity-60 grayscale hover:grayscale-0 transition-all duration-500"
      >
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-[#FB7299]" viewBox="0 0 24 24" fill="currentColor"><path d="M17.813 4.653h.854c1.51.054 2.769.578 3.773 1.574 1.004.995 1.524 2.249 1.56 3.76v7.36c-.036 1.51-.556 2.769-1.56 3.773s-2.262 1.524-3.773 1.56H5.333c-1.51-.036-2.769-.556-3.773-1.56S.036 18.858 0 17.347v-7.36c.036-1.511.556-2.765 1.56-3.76 1.004-.996 2.262-1.52 3.773-1.574h.774l-1.174-1.12a1.234 1.234 0 0 1-.373-.906c0-.356.124-.658.373-.907l.027-.027c.267-.249.573-.373.92-.373.347 0 .653.124.92.373L9.653 4.44c.071.071.134.142.187.213h4.267a1.623 1.623 0 0 1 .213-.213l3.427-3.253c.267-.249.573-.373.92-.373.347 0 .653.124.92.373l.027.027c.249.249.373.551.373.907 0 .355-.124.657-.373.906L17.813 4.653zM5.333 7.24c-.746.018-1.373.276-1.88.773-.506.498-.769 1.13-.786 1.894v7.52c.017.764.28 1.395.786 1.893.507.498 1.134.756 1.88.773h13.334c.746-.017 1.373-.275 1.88-.773.506-.498.769-1.129.786-1.893v-7.52c-.017-.765-.28-1.396-.786-1.894-.507-.497-1.134-.755-1.88-.773H5.333zM8 11.107c.373 0 .684.124.933.373.25.249.383.569.4.96v1.173c-.017.391-.15.711-.4.96-.249.25-.56.374-.933.374s-.684-.125-.933-.374c-.25-.249-.383-.569-.4-.96V12.44c0-.391.133-.711.4-.96.249-.249.56-.373.933-.373zm8 0c.373 0 .684.124.933.373.25.249.383.569.4.96v1.173c-.017.391-.15.711-.4.96-.249.25-.56.374-.933.374s-.684-.125-.933-.374c-.25-.249-.383-.569-.4-.96V12.44c0-.391.133-.711.4-.96.249-.249.56-.373.933-.373z"/></svg>
          <span className="text-sm font-medium">Bilibili</span>
        </div>
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-[#FF0000]" viewBox="0 0 24 24" fill="currentColor"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>
          <span className="text-sm font-medium">YouTube</span>
        </div>
      </motion.div>
    </div>
  )
}
