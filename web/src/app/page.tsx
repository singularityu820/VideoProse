'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { VideoInput } from '@/components/video-input'
import { ProgressPanel } from '@/components/progress-panel'
import { ResultPanel } from '@/components/result-panel'
import { SettingsPanel } from '@/components/settings-panel'
import { GlossaryEditor } from '@/components/glossary-editor'
import { Settings, FileText, Plus, Trash2, ChevronRight, LayoutDashboard } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export interface ProcessingState {
  status: 'idle' | 'processing' | 'glossary-review' | 'completed' | 'error'
  currentStep: string
  progress: number
  messages: string[]
  error?: string
}

export interface ProcessingResult {
  title: string
  author: string
  executiveSummary: string
  tableOfContents: string[]
  body: string
  highlights: string[]
}

export interface GlossaryData {
  entities: Array<{
    term: string
    translation: string
    definition: string
    entityType: string
  }>
  toneProfile: {
    style: string
    emotionKeywords: string[]
    audience: string
  }
  coreTheme: string
}

export interface TaskData {
  id: string
  url: string
  title?: string
  state: ProcessingState
  result: ProcessingResult | null
  glossary: GlossaryData | null
  createdAt: number
}

export default function Home() {
  const [showSettings, setShowSettings] = useState(false)
  const [tasks, setTasks] = useState<Record<string, TaskData>>({})
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null)
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)

  const [settings, setSettings] = useState({
    provider: 'deepseek',
    model: 'deepseek-reasoner',
    apiKey: '',
    targetLength: 1200,
    contextOverlap: 0.1,
  })

  // Load tasks from localStorage
  useEffect(() => {
    const savedTasks = localStorage.getItem('videoprose_tasks')
    if (savedTasks) {
      try {
        const parsed = JSON.parse(savedTasks)
        setTasks(parsed)
        // If there are tasks, set the most recent one as active
        const ids = Object.keys(parsed).sort((a, b) => parsed[b].createdAt - parsed[a].createdAt)
        if (ids.length > 0) {
          setActiveTaskId(ids[0])
        }
      } catch (e) {
        console.error('Failed to parse saved tasks', e)
      }
    }
  }, [])

  // Save tasks to localStorage
  useEffect(() => {
    if (Object.keys(tasks).length > 0) {
      localStorage.setItem('videoprose_tasks', JSON.stringify(tasks))
    }
  }, [tasks])

  const updateTask = useCallback((id: string, updates: Partial<TaskData> | ((prev: TaskData) => TaskData)) => {
    setTasks(prev => {
      const task = prev[id]
      if (!task) return prev
      const newContent = typeof updates === 'function' ? updates(task) : { ...task, ...updates }
      return { ...prev, [id]: newContent }
    })
  }, [])

  const pollStatus = useCallback(async (id: string) => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`/api/status/${id}`)
        if (!response.ok) throw new Error('Status check failed')
        const data = await response.json()

        setTasks(prev => {
          const task = prev[id]
          if (!task) {
            clearInterval(interval)
            return prev
          }

          const newState: ProcessingState = {
            status: data.status,
            currentStep: data.currentStep,
            progress: data.progress,
            messages: data.messages,
            error: data.error,
          }

          const updatedTask = {
            ...task,
            state: newState,
            title: data.metadata?.title || task.title,
            glossary: data.status === 'glossary-review' ? data.glossary : task.glossary,
            result: data.status === 'completed' ? data.result : task.result,
          }

          if (data.status === 'completed' || data.status === 'error' || data.status === 'glossary-review') {
            clearInterval(interval)
          }

          return { ...prev, [id]: updatedTask }
        })
      } catch (error) {
        clearInterval(interval)
        updateTask(id, task => ({
          ...task,
          state: { ...task.state, status: 'error', error: '获取状态失败' }
        }))
      }
    }, 1500)
  }, [updateTask])

  const handleSubmit = async (url: string) => {
    const tempId = `task_${Date.now()}`
    const newTask: TaskData = {
      id: tempId,
      url,
      state: {
        status: 'processing',
        currentStep: '初始化...',
        progress: 0,
        messages: [],
      },
      result: null,
      glossary: null,
      createdAt: Date.now(),
    }

    setTasks(prev => ({ ...prev, [tempId]: newTask }))
    setActiveTaskId(tempId)

    try {
      const response = await fetch('/api/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, ...settings }),
      })

      if (!response.ok) throw new Error('处理请求失败')

      const data = await response.json()
      const realId = data.taskId
      
      // Replace tempId with realId
      setTasks(prev => {
        const { [tempId]: _, ...rest } = prev
        return {
          ...rest,
          [realId]: { ...newTask, id: realId }
        }
      })
      setActiveTaskId(realId)
      pollStatus(realId)
    } catch (error) {
      updateTask(tempId, task => ({
        ...task,
        state: {
          ...task.state,
          status: 'error',
          error: error instanceof Error ? error.message : '未知错误',
        }
      }))
    }
  }

  const handleGlossaryConfirm = async (updatedGlossary: GlossaryData) => {
    if (!activeTaskId) return
    const taskId = activeTaskId

    updateTask(taskId, task => ({
      ...task,
      glossary: updatedGlossary,
      state: { ...task.state, status: 'processing', currentStep: '继续处理...' }
    }))

    try {
      await fetch(`/api/process/${taskId}/continue`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ glossary: updatedGlossary }),
      })
      pollStatus(taskId)
    } catch (error) {
      updateTask(taskId, task => ({
        ...task,
        state: { ...task.state, status: 'error', error: '继续处理失败' }
      }))
    }
  }

  const deleteTask = (id: string) => {
    setTasks(prev => {
      const { [id]: _, ...rest } = prev
      return rest
    })
    if (activeTaskId === id) {
      setActiveTaskId(null)
    }
  }

  const clearAllTasks = () => {
    if (typeof globalThis !== 'undefined' && globalThis.confirm?.('确定要清空所有任务历史吗？')) {
      setTasks({})
      setActiveTaskId(null)
      localStorage.removeItem('videoprose_tasks')
    }
  }

  const activeTask = activeTaskId ? tasks[activeTaskId] : null

  return (
    <div className="flex h-screen bg-slate-50 dark:bg-slate-950 overflow-hidden">
      {/* Sidebar */}
      <aside className={cn(
        "bg-white dark:bg-slate-900 border-r transition-all duration-300 flex flex-col",
        isSidebarOpen ? "w-72" : "w-0 -ml-72 md:ml-0 md:w-20"
      )}>
        <div className="p-4 border-b flex items-center justify-between">
          {isSidebarOpen && (
            <div className="flex items-center gap-2 font-bold text-blue-600">
              <LayoutDashboard className="w-5 h-5" />
              <span>任务列表</span>
            </div>
          )}
          <Button variant="ghost" size="icon" onClick={() => setIsSidebarOpen(!isSidebarOpen)}>
            <ChevronRight className={cn("w-4 h-4 transition-transform", isSidebarOpen && "rotate-180")} />
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-2">
          <div className="flex gap-1">
            <Button 
              variant="outline" 
              className="flex-1 justify-start gap-2 border-dashed h-9 text-xs"
              onClick={() => setActiveTaskId(null)}
            >
              <Plus className="w-3.5 h-3.5" />
              {isSidebarOpen && "新建任务"}
            </Button>
            {isSidebarOpen && Object.keys(tasks).length > 0 && (
              <Button 
                variant="ghost" 
                size="icon" 
                className="h-9 w-9 text-slate-400 hover:text-red-500"
                onClick={clearAllTasks}
                title="清空历史"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </Button>
            )}
          </div>

          <div className="mt-4 space-y-1">
            {Object.values(tasks)
              .sort((a, b) => b.createdAt - a.createdAt)
              .map(task => {
                let statusColor = "bg-slate-300"
                if (task.state.status === 'completed') statusColor = "bg-green-500"
                else if (task.state.status === 'processing') statusColor = "bg-blue-500 animate-pulse"
                else if (task.state.status === 'error') statusColor = "bg-red-500"

                return (
                  <Button 
                    key={task.id}
                    variant="ghost"
                    className={cn(
                      "w-full justify-start gap-2 p-2 h-auto font-normal group relative",
                      activeTaskId === task.id ? "bg-blue-50 dark:bg-blue-900/20 text-blue-600" : "hover:bg-slate-100 dark:hover:bg-slate-800"
                    )}
                    onClick={() => setActiveTaskId(task.id)}
                  >
                    <div className={cn("w-2 h-2 rounded-full shrink-0", statusColor)} />
                    {isSidebarOpen && (
                      <div className="flex-1 min-w-0 text-left">
                        <p className="text-sm font-medium truncate">{task.title || '未命名任务'}</p>
                        <p className="text-[10px] text-muted-foreground">{new Date(task.createdAt).toLocaleString()}</p>
                      </div>
                    )}
                    {isSidebarOpen && (
                      <button 
                        onClick={(e) => { e.stopPropagation(); deleteTask(task.id); }}
                        className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-500 transition-opacity"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    )}
                  </Button>
                )
              })}
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <header className="h-16 border-b bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm flex items-center justify-between px-6 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <FileText className="w-4 h-4 text-white" />
            </div>
            <h1 className="font-bold text-lg">VideoProse</h1>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" onClick={() => setShowSettings(!showSettings)}>
              <Settings className="w-5 h-5" />
            </Button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-5xl mx-auto">
            <AnimatePresence mode="wait">
              {showSettings && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="mb-8 overflow-hidden"
                >
                  <SettingsPanel settings={settings} onSettingsChange={setSettings} />
                </motion.div>
              )}
            </AnimatePresence>

            <AnimatePresence mode="wait">
              {activeTask ? (
                <motion.div
                  key={activeTask.id}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  className="space-y-6"
                >
                  {(() => {
                    if (activeTask.state.status === 'processing' || activeTask.state.status === 'error') {
                      return <ProgressPanel state={activeTask.state} onReset={() => setActiveTaskId(null)} />
                    }
                    if (activeTask.state.status === 'glossary-review' && activeTask.glossary) {
                      return (
                        <GlossaryEditor
                          glossary={activeTask.glossary}
                          onConfirm={handleGlossaryConfirm}
                          onCancel={() => setActiveTaskId(null)}
                        />
                      )
                    }
                    if (activeTask.state.status === 'completed' && activeTask.result) {
                      return <ResultPanel result={activeTask.result} onReset={() => setActiveTaskId(null)} />
                    }
                    return null
                  })()}
                </motion.div>
              ) : (
                <motion.div
                  key="new-task"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  className="h-full flex flex-col justify-center"
                >
                  <VideoInput onSubmit={handleSubmit} />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </main>
    </div>
  )
}
