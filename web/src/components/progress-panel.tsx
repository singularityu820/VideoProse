'use client'

import { motion } from 'framer-motion'
import { CheckCircle2, XCircle, Loader2, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { ProcessingState } from '@/app/page'

interface ProgressPanelProps {
  state: ProcessingState
  onReset: () => void
}

const steps = [
  { id: 'fetch', label: '获取视频信息', progress: 10 },
  { id: 'transcript', label: '提取字幕/转录', progress: 30 },
  { id: 'glossary', label: '构建知识库', progress: 40 },
  { id: 'chunk', label: '语义切片', progress: 50 },
  { id: 'refine', label: '文本精修', progress: 80 },
  { id: 'assemble', label: '生成文档', progress: 100 },
]

export function ProgressPanel({ state, onReset }: ProgressPanelProps) {
  const isError = state.status === 'error'

  return (
    <Card className="overflow-hidden">
      <CardHeader className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-950/50 dark:to-purple-950/50">
        <CardTitle className="flex items-center gap-3">
          {isError ? (
            <XCircle className="w-6 h-6 text-destructive" />
          ) : (
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
            >
              <Loader2 className="w-6 h-6 text-primary" />
            </motion.div>
          )}
          {isError ? '处理出错' : '正在处理'}
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-6">
        {/* Progress Bar */}
        <div className="mb-8">
          <div className="flex justify-between text-sm mb-2">
            <span className="text-muted-foreground">{state.currentStep}</span>
            <span className="font-medium">{state.progress}%</span>
          </div>
          <Progress value={state.progress} className="h-2" />
        </div>

        {/* Steps */}
        <div className="space-y-3 mb-8">
          {steps.map((step, index) => {
            const isCompleted = state.progress >= step.progress
            const isCurrent =
              state.progress < step.progress &&
              (index === 0 || state.progress >= steps[index - 1].progress)

            return (
              <motion.div
                key={step.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className={`flex items-center gap-3 p-3 rounded-lg transition-colors ${
                  isCurrent
                    ? 'bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800'
                    : isCompleted
                    ? 'bg-green-50 dark:bg-green-950/30'
                    : 'bg-slate-50 dark:bg-slate-900'
                }`}
              >
                {isCompleted ? (
                  <CheckCircle2 className="w-5 h-5 text-green-500" />
                ) : isCurrent ? (
                  <motion.div
                    animate={{ scale: [1, 1.2, 1] }}
                    transition={{ duration: 1, repeat: Infinity }}
                  >
                    <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
                  </motion.div>
                ) : (
                  <div className="w-5 h-5 rounded-full border-2 border-slate-300 dark:border-slate-700" />
                )}
                <span
                  className={`text-sm ${
                    isCompleted
                      ? 'text-green-700 dark:text-green-400'
                      : isCurrent
                      ? 'text-blue-700 dark:text-blue-400 font-medium'
                      : 'text-muted-foreground'
                  }`}
                >
                  {step.label}
                </span>
              </motion.div>
            )
          })}
        </div>

        {/* Messages Log */}
        {state.messages.length > 0 && (
          <div className="mb-6">
            <h4 className="text-sm font-medium mb-2">处理日志</h4>
            <div className="bg-slate-950 rounded-lg p-4 max-h-60 overflow-y-auto font-mono text-xs space-y-1">
              {state.messages.map((msg, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -5 }}
                  animate={{ opacity: 1, x: 0 }}
                  className={cn(
                    "py-0.5",
                    msg.startsWith('✓') ? "text-green-400" : 
                    msg.startsWith('!') ? "text-yellow-400" : 
                    msg.startsWith('异常') ? "text-red-400" : "text-slate-300"
                  )}
                >
                  {msg}
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {/* Error Message */}
        {isError && state.error && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-destructive/10 text-destructive rounded-lg p-4 mb-6"
          >
            <p className="text-sm font-medium">错误信息</p>
            <p className="text-sm mt-1 break-all">{state.error}</p>
          </motion.div>
        )}

        {/* Actions */}
        {isError && (
          <Button onClick={onReset} variant="outline" className="w-full">
            <RotateCcw className="w-4 h-4 mr-2" />
            重新开始
          </Button>
        )}
      </CardContent>
    </Card>
  )
}

import { cn } from '@/lib/utils'
