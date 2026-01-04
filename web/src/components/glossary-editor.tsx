'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { Plus, Trash2, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { GlossaryData } from '@/app/page'

interface GlossaryEditorProps {
  glossary: GlossaryData
  onConfirm: (glossary: GlossaryData) => void
  onCancel: () => void
}

export function GlossaryEditor({ glossary, onConfirm, onCancel }: GlossaryEditorProps) {
  const [editedGlossary, setEditedGlossary] = useState<GlossaryData>(glossary)

  const handleEntityChange = (
    index: number,
    field: keyof GlossaryData['entities'][0],
    value: string
  ) => {
    const newEntities = [...editedGlossary.entities]
    newEntities[index] = { ...newEntities[index], [field]: value }
    setEditedGlossary({ ...editedGlossary, entities: newEntities })
  }

  const handleAddEntity = () => {
    setEditedGlossary({
      ...editedGlossary,
      entities: [
        ...editedGlossary.entities,
        { term: '', translation: '', definition: '', entityType: 'General' },
      ],
    })
  }

  const handleRemoveEntity = (index: number) => {
    const newEntities = editedGlossary.entities.filter((_, i) => i !== index)
    setEditedGlossary({ ...editedGlossary, entities: newEntities })
  }

  const handleToneChange = (field: keyof GlossaryData['toneProfile'], value: string | string[]) => {
    setEditedGlossary({
      ...editedGlossary,
      toneProfile: { ...editedGlossary.toneProfile, [field]: value },
    })
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-5xl mx-auto space-y-8 pb-20"
    >
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <span className="text-amber-500">📚</span> 术语与风格审核
          </h2>
          <p className="text-muted-foreground mt-1">
            AI 已根据视频内容提取了以下关键信息，请在开始生成前进行校对。
          </p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={onCancel}>
            取消
          </Button>
          <Button 
            onClick={() => onConfirm(editedGlossary)}
            className="bg-slate-900 dark:bg-white dark:text-slate-900"
          >
            <Check className="w-4 h-4 mr-2" />
            确认并继续
          </Button>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          {/* Core Theme */}
          <Card className="overflow-hidden border-none shadow-md bg-slate-50/50 dark:bg-slate-900/50">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold uppercase tracking-wider text-slate-500">
                🎯 核心主题
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Input
                value={editedGlossary.coreTheme}
                onChange={(e) =>
                  setEditedGlossary({ ...editedGlossary, coreTheme: e.target.value })
                }
                placeholder="视频的核心主旨..."
                className="bg-white dark:bg-slate-950 border-slate-200 dark:border-slate-800"
              />
            </CardContent>
          </Card>

          {/* Entities */}
          <Card className="border-none shadow-md">
            <CardHeader className="flex flex-row items-center justify-between pb-4">
              <CardTitle className="text-sm font-semibold uppercase tracking-wider text-slate-500">
                📖 术语对照表
              </CardTitle>
              <Button variant="ghost" size="sm" onClick={handleAddEntity} className="h-8 text-blue-600 dark:text-blue-400">
                <Plus className="w-4 h-4 mr-1" />
                添加
              </Button>
            </CardHeader>
            <CardContent className="px-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-y border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
                      <th className="text-left py-3 px-4 font-medium text-slate-500">原词</th>
                      <th className="text-left py-3 px-4 font-medium text-slate-500">翻译</th>
                      <th className="text-left py-3 px-4 font-medium text-slate-500">类型</th>
                      <th className="w-10"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {editedGlossary.entities.map((entity, index) => (
                      <motion.tr
                        key={`${entity.term}-${index}`}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="group hover:bg-slate-50/30 dark:hover:bg-slate-900/30 transition-colors"
                      >
                        <td className="py-2 px-4">
                          <input
                            value={entity.term}
                            onChange={(e) => handleEntityChange(index, 'term', e.target.value)}
                            className="w-full bg-transparent border-none focus:ring-0 p-0 placeholder:text-slate-300"
                            placeholder="原始术语"
                          />
                        </td>
                        <td className="py-2 px-4">
                          <input
                            value={entity.translation}
                            onChange={(e) => handleEntityChange(index, 'translation', e.target.value)}
                            className="w-full bg-transparent border-none focus:ring-0 p-0 placeholder:text-slate-300"
                            placeholder="翻译"
                          />
                        </td>
                        <td className="py-2 px-4">
                          <select
                            value={entity.entityType}
                            onChange={(e) => handleEntityChange(index, 'entityType', e.target.value)}
                            className="bg-transparent border-none focus:ring-0 p-0 text-xs font-medium text-slate-500 cursor-pointer"
                          >
                            <option value="Person">人名</option>
                            <option value="Company">公司</option>
                            <option value="Technical">技术</option>
                            <option value="General">通用</option>
                          </select>
                        </td>
                        <td className="py-2 px-2">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleRemoveEntity(index)}
                            className="w-8 h-8 opacity-0 group-hover:opacity-100 text-slate-400 hover:text-red-500 transition-all"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </td>
                      </motion.tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {editedGlossary.entities.length === 0 && (
                <div className="text-center py-12 text-slate-400">
                  <p>暂无术语，点击上方按钮添加</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          {/* Tone Profile */}
          <Card className="border-none shadow-md">
            <CardHeader>
              <CardTitle className="text-sm font-semibold uppercase tracking-wider text-slate-500">
                🎭 语气特征
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <label htmlFor="style" className="text-xs font-bold text-slate-400 uppercase">写作风格</label>
                <Input
                  id="style"
                  value={editedGlossary.toneProfile.style}
                  onChange={(e) => handleToneChange('style', e.target.value)}
                  placeholder="如：专业且热情"
                  className="bg-slate-50 dark:bg-slate-900 border-none"
                />
              </div>
              <div className="space-y-2">
                <label htmlFor="emotion" className="text-xs font-bold text-slate-400 uppercase">情绪关键词</label>
                <textarea
                  id="emotion"
                  value={editedGlossary.toneProfile.emotionKeywords.join(', ')}
                  onChange={(e) =>
                    handleToneChange(
                      'emotionKeywords',
                      e.target.value.split(',').map((s) => s.trim())
                    )
                  }
                  placeholder="用逗号分隔"
                  className="w-full min-h-[80px] rounded-md bg-slate-50 dark:bg-slate-900 border-none p-3 text-sm focus:ring-1 focus:ring-slate-200 dark:focus:ring-slate-800 resize-none"
                />
              </div>
              <div className="space-y-2">
                <label htmlFor="audience" className="text-xs font-bold text-slate-400 uppercase">目标受众</label>
                <Input
                  id="audience"
                  value={editedGlossary.toneProfile.audience}
                  onChange={(e) => handleToneChange('audience', e.target.value)}
                  placeholder="如：技术爱好者"
                  className="bg-slate-50 dark:bg-slate-900 border-none"
                />
              </div>
            </CardContent>
          </Card>

          <div className="p-6 rounded-2xl bg-blue-50 dark:bg-blue-950/20 border border-blue-100 dark:border-blue-900/30">
            <h4 className="text-sm font-bold text-blue-700 dark:text-blue-400 mb-2 flex items-center gap-2">
              💡 小提示
            </h4>
            <p className="text-xs text-blue-600/80 dark:text-blue-400/80 leading-relaxed">
              准确的术语表能显著提升 AI 生成文章的专业度。特别是对于专有名词和技术术语，建议手动校对翻译。
            </p>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
