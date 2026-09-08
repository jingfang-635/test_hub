/**
 * AI 智能模式「执行进度 → 用例明细划线」纯函数工具。
 *
 * 文件模式：后端用解析出的用例步骤直接生成 planned_tasks（与右侧明细 1:1），
 * 本模块按顺序把 planned_tasks 状态同步到展示步骤，保证划线与日志/投屏一致。
 */

const TERMINAL_STATUSES = ['completed', 'failed', 'skipped']

/** 规范化任务状态，兜底为 pending */
export function normalizeStatus(status) {
  const s = (status || '').toString().trim().toLowerCase()
  return s || 'pending'
}

/** 是否终态 */
export function isTerminalStatus(status) {
  return TERMINAL_STATUSES.includes(normalizeStatus(status))
}

/** 去掉空白与常见编号前缀，便于描述匹配 */
function normalizeDesc(text) {
  return String(text || '')
    .replace(/^\s*\d+[\.\s、:：)\-]+/, '')
    .replace(/\s+/g, '')
    .toLowerCase()
}

/**
 * 把解析出的用例构建为展示结构（含每个步骤子任务）。
 * @param {Array} cases  后端解析的用例：[{name, precondition, expected, steps: []}]
 * @param {Function} label  文案函数，接收 key 返回已翻译文本
 */
export function buildDisplayCases(cases, label = (k) => k) {
  if (!Array.isArray(cases)) return []
  return cases.map((c, i) => {
    const steps = c.steps || []
    const tasks = steps.map((s, si) => ({
      id: `${i + 1}-${si + 1}`,
      description: s,
      status: 'pending'
    }))
    // 无步骤时至少展示一条占位任务，避免空用例
    if (tasks.length === 0) {
      tasks.push({
        id: `${i + 1}-1`,
        description: c.expected
          ? `${label('expectedResult')}：${c.expected}`
          : (c.name || label('unnamedCase')),
        status: 'pending'
      })
    }
    return {
      id: i + 1,
      name: c.name || `${label('unnamedCase')}${i + 1}`,
      precondition: c.precondition || '',
      expected: c.expected || '',
      status: 'pending',
      tasks
    }
  })
}

/** 将展示用例的状态全部重置为 pending（开始执行前调用） */
export function resetDisplayCasesStatus(displayCases) {
  return (displayCases || []).map(c => ({
    ...c,
    status: 'pending',
    tasks: (c.tasks || []).map(task => ({ ...task, status: 'pending' }))
  }))
}

/** 根据子任务状态汇总用例状态 */
function refreshCaseStatuses(displayCases) {
  ;(displayCases || []).forEach(c => {
    const tasks = c.tasks || []
    if (tasks.some(task => task.status === 'failed')) {
      c.status = 'failed'
    } else if (tasks.length > 0 && tasks.every(task => task.status === 'completed')) {
      c.status = 'completed'
    } else if (tasks.some(task => task.status === 'in_progress' || task.status === 'completed')) {
      c.status = 'in_progress'
    } else {
      c.status = 'pending'
    }
  })
}

/**
 * 用后端 planned_tasks 进度同步到解析用例步骤（执行一条划线一条）。
 *
 * 同步策略：
 *  1. 数量一致 → 按序 1:1 拷贝状态（文件模式主路径）
 *  2. 数量不一致 → 按描述相似度顺序匹配；剩余用「已完成数量」作为前沿推进
 *
 * @param {Array} displayCases  当前展示用例（会被就地修改）
 * @param {Array} planned  backend planned_tasks（[{id, status, description, ...}]）
 * @returns {Array} 更新后的 displayCases
 */
export function syncDisplayCasesStatus(displayCases, planned) {
  const flatTasks = (displayCases || []).flatMap(c => c.tasks || [])
  if (!flatTasks.length) return displayCases

  const list = Array.isArray(planned) ? planned : []
  if (list.length === 0) {
    flatTasks.forEach(task => { task.status = 'pending' })
    refreshCaseStatuses(displayCases)
    return displayCases
  }

  // 主路径：文件模式 planned_tasks 与明细步骤 1:1
  if (list.length === flatTasks.length) {
    flatTasks.forEach((task, i) => {
      task.status = normalizeStatus(list[i]?.status)
    })
    refreshCaseStatuses(displayCases)
    return displayCases
  }

  // 兜底：描述匹配 + 完成前沿，避免 LLM 拆分后数量不一致时进度漂移
  flatTasks.forEach(task => { task.status = 'pending' })
  const used = new Set()

  list.forEach((pt) => {
    const status = normalizeStatus(pt.status)
    if (status === 'pending') return
    const pDesc = normalizeDesc(pt.description)
    let matched = -1
    for (let i = 0; i < flatTasks.length; i++) {
      if (used.has(i)) continue
      const tDesc = normalizeDesc(flatTasks[i].description)
      if (!tDesc || !pDesc) continue
      if (tDesc === pDesc || tDesc.includes(pDesc) || pDesc.includes(tDesc)) {
        matched = i
        break
      }
    }
    if (matched >= 0) {
      flatTasks[matched].status = status
      used.add(matched)
    }
  })

  // 若匹配偏少，用「已完成/进行中」数量作为前沿，保证至少能逐条推进
  const settledCount = list.filter(t => isTerminalStatus(t.status)).length
  const hasInProgress = list.some(t => normalizeStatus(t.status) === 'in_progress')
  const matchedSettled = flatTasks.filter(t => isTerminalStatus(t.status)).length
  if (matchedSettled < settledCount) {
    let need = settledCount - matchedSettled
    for (let i = 0; i < flatTasks.length && need > 0; i++) {
      if (!isTerminalStatus(flatTasks[i].status)) {
        flatTasks[i].status = 'completed'
        need--
      }
    }
  }
  if (hasInProgress) {
    const next = flatTasks.find(t => t.status === 'pending')
    if (next) next.status = 'in_progress'
  }

  refreshCaseStatuses(displayCases)
  return displayCases
}
