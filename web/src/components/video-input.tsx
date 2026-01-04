'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { Link, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface VideoInputProps {
  onSubmit: (url: string) => void
}

export function VideoInput({ onSubmit }: VideoInputProps) {
  const [url, setUrl] = useState('')
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
    if (!url || !isValidUrl(url)) return

    setIsValidating(true)
    // 模拟验证
    await new Promise(resolve => setTimeout(resolve, 800))
    setIsValidating(false)
    onSubmit(url)
  }

  return (
    <div className="w-full max-w-3xl mx-auto px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-10 space-y-6"
      >
        <h1 className="text-4xl md:text-6xl font-bold tracking-tight text-slate-900 dark:text-white">
          VideoProse
        </h1>
        <p className="text-lg md:text-xl text-slate-500 dark:text-slate-400 max-w-2xl mx-auto font-light">
          将视频转化为深度文章，保留每一个精彩细节
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.1 }}
        className="relative group"
      >
        {/* Glow effect */}
        <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-500 to-purple-600 rounded-2xl blur opacity-20 group-hover:opacity-40 transition duration-500" />
        
        <form
          onSubmit={handleSubmit}
          className="relative bg-white dark:bg-slate-900 rounded-2xl p-2 shadow-xl border border-slate-200 dark:border-slate-800 flex items-center"
        >
          <div className="pl-4 text-slate-400">
            <Link className="w-5 h-5" />
          </div>
          <Input
            type="url"
            placeholder="输入 Bilibili 或 YouTube 视频链接..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="flex-1 h-14 text-lg border-none bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 placeholder:text-slate-400"
          />
          <Button
            type="submit"
            disabled={!url || !isValidUrl(url) || isValidating}
            className="h-12 px-6 mr-1 text-base font-medium rounded-xl bg-slate-900 dark:bg-white dark:text-slate-900 hover:bg-slate-800 dark:hover:bg-slate-100 transition-all shadow-sm"
          >
            {isValidating ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              '生成'
            )}
          </Button>
        </form>

        {/* Validation Error */}
        <div className="absolute -bottom-8 left-0 right-0 text-center h-6">
          {url && !isValidUrl(url) && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-sm text-red-500 font-medium"
            >
              不支持该链接，请使用 B站 或 YouTube 视频
            </motion.p>
          )}
        </div>
      </motion.div>

      {/* Simple Platform Icons */}
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
