'use client'

import { motion } from 'framer-motion'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

interface SettingsProps {
  settings: {
    provider: string
    model: string
    apiKey: string
    asrProvider: string
    asrModel: string
    asrApiKey: string
    asrBaseUrl: string
    targetLength: number
    contextOverlap: number
  }
  onSettingsChange: (settings: SettingsProps['settings']) => void
}

const modelOptions: Record<string, string[]> = {
  anthropic: ['claude-3-5-sonnet-20241022', 'claude-3-opus-20240229'],
  openai: ['gpt-4o', 'gpt-4-turbo'],
  deepseek: ['deepseek-reasoner', 'deepseek-chat', 'deepseek-coder'],
}

const asrModelOptions: Record<string, string[]> = {
  whisper: ['large-v3'],
  qwen: ['qwen3-asr-flash', 'qwen-audio-asr', 'qwen3-asr-flash-filetrans'],
}

export function SettingsPanel({ settings, onSettingsChange }: Readonly<SettingsProps>) {
  const handleChange = (key: string, value: string | number) => {
    onSettingsChange({ ...settings, [key]: value })
  }

  const handleProviderChange = (nextProvider: string) => {
    const nextModel = modelOptions[nextProvider]?.[0] ?? ''
    onSettingsChange({
      ...settings,
      provider: nextProvider,
      model: nextModel,
    })
  }

  const handleAsrProviderChange = (nextProvider: string) => {
    const nextModel = asrModelOptions[nextProvider]?.[0] ?? settings.asrModel
    onSettingsChange({
      ...settings,
      asrProvider: nextProvider,
      asrModel: nextModel,
    })
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
    >
      <Card className="border-none shadow-lg bg-white/80 dark:bg-slate-900/80 backdrop-blur-md">
        <CardHeader className="pb-4">
          <CardTitle className="text-sm font-bold uppercase tracking-wider text-slate-500 flex items-center gap-2">
            <span className="text-base">⚙️</span> 全局配置
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {/* Provider */}
            <div className="space-y-3">
              <Label htmlFor="provider" className="text-xs font-bold text-slate-400 uppercase">LLM 提供商</Label>
              <div className="relative">
                <select
                  id="provider"
                  value={settings.provider}
                  onChange={(e) => handleProviderChange(e.target.value)}
                  className="flex h-11 w-full rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/50 px-4 py-2 text-sm transition-all focus:ring-2 focus:ring-blue-500/20 outline-none appearance-none cursor-pointer"
                >
                  <option value="anthropic">Anthropic</option>
                  <option value="openai">OpenAI</option>
                  <option value="deepseek">DeepSeek</option>
                </select>
                <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
                </div>
              </div>
            </div>

            {/* Model */}
            <div className="space-y-3">
              <Label htmlFor="model" className="text-xs font-bold text-slate-400 uppercase">模型选择</Label>
              <div className="relative">
                <select
                  id="model"
                  value={settings.model}
                  onChange={(e) => handleChange('model', e.target.value)}
                  className="flex h-11 w-full rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/50 px-4 py-2 text-sm transition-all focus:ring-2 focus:ring-blue-500/20 outline-none appearance-none cursor-pointer"
                >
                  {modelOptions[settings.provider]?.map((model) => (
                    <option key={model} value={model}>
                      {model}
                    </option>
                  ))}
                </select>
                <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
                </div>
              </div>
            </div>

            {/* API Key */}
            <div className="space-y-3">
              <Label htmlFor="apiKey" className="text-xs font-bold text-slate-400 uppercase">API Key</Label>
              <Input
                id="apiKey"
                type="password"
                placeholder="sk-..."
                value={settings.apiKey}
                onChange={(e) => handleChange('apiKey', e.target.value)}
                className="h-11 rounded-xl border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/50 px-4 focus:ring-2 focus:ring-blue-500/20"
              />
            </div>

            {/* ASR Provider */}
            <div className="space-y-3">
              <Label htmlFor="asrProvider" className="text-xs font-bold text-slate-400 uppercase">ASR 提供商</Label>
              <div className="relative">
                <select
                  id="asrProvider"
                  value={settings.asrProvider}
                  onChange={(e) => handleAsrProviderChange(e.target.value)}
                  className="flex h-11 w-full rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/50 px-4 py-2 text-sm transition-all focus:ring-2 focus:ring-blue-500/20 outline-none appearance-none cursor-pointer"
                >
                  <option value="whisper">本地 Whisper</option>
                  <option value="qwen">通义千问 ASR</option>
                </select>
                <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
                </div>
              </div>
            </div>

            {/* ASR Model */}
            <div className="space-y-3">
              <Label htmlFor="asrModel" className="text-xs font-bold text-slate-400 uppercase">ASR 模型</Label>
              <div className="relative">
                <select
                  id="asrModel"
                  value={settings.asrModel}
                  onChange={(e) => handleChange('asrModel', e.target.value)}
                  className="flex h-11 w-full rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/50 px-4 py-2 text-sm transition-all focus:ring-2 focus:ring-blue-500/20 outline-none appearance-none cursor-pointer"
                >
                  {(asrModelOptions[settings.asrProvider] ?? [settings.asrModel]).map((model) => (
                    <option key={model} value={model}>
                      {model}
                    </option>
                  ))}
                </select>
                <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
                </div>
              </div>
            </div>

            {/* ASR API Key */}
            <div className="space-y-3">
              <Label htmlFor="asrApiKey" className="text-xs font-bold text-slate-400 uppercase">ASR API Key (通义千问)</Label>
              <Input
                id="asrApiKey"
                type="password"
                placeholder="sk-..."
                value={settings.asrApiKey}
                onChange={(e) => handleChange('asrApiKey', e.target.value)}
                className="h-11 rounded-xl border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/50 px-4 focus:ring-2 focus:ring-blue-500/20"
                disabled={settings.asrProvider !== 'qwen'}
              />
            </div>

            {/* ASR Base URL */}
            <div className="space-y-3">
              <Label htmlFor="asrBaseUrl" className="text-xs font-bold text-slate-400 uppercase">ASR Base URL</Label>
              <Input
                id="asrBaseUrl"
                type="text"
                placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1"
                value={settings.asrBaseUrl}
                onChange={(e) => handleChange('asrBaseUrl', e.target.value)}
                className="h-11 rounded-xl border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/50 px-4 focus:ring-2 focus:ring-blue-500/20"
                disabled={settings.asrProvider !== 'qwen'}
              />
            </div>

            {/* Target Length */}
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <Label htmlFor="targetLength" className="text-xs font-bold text-slate-400 uppercase">目标字数</Label>
                <span className="text-xs font-mono font-bold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 px-2 py-0.5 rounded">
                  {settings.targetLength} 字
                </span>
              </div>
              <div className="pt-2">
                <input
                  id="targetLength"
                  type="range"
                  min="500"
                  max="5000"
                  step="100"
                  value={settings.targetLength}
                  onChange={(e) => handleChange('targetLength', Number.parseInt(e.target.value))}
                  className="w-full h-1.5 bg-slate-200 dark:bg-slate-800 rounded-lg appearance-none cursor-pointer accent-blue-600"
                />
                <div className="flex justify-between mt-2 text-[10px] text-slate-400 font-medium">
                  <span>500</span>
                  <span>2500</span>
                  <span>5000</span>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}
