'use client';

import { FormEvent, useEffect, useMemo, useRef, useState } from 'react';
import {
  Bot,
  CalendarClock,
  CheckCircle2,
  ClipboardCheck,
  ExternalLink,
  Loader2,
  MessageSquareText,
  Radio,
  Send,
  ShieldCheck,
  type LucideIcon,
  Wand2,
} from 'lucide-react';
import {
  api,
  OperationsAssistantCapabilities,
  OperationsAssistantExternalReply,
  OperationsAssistantResponse,
  OperationsAssistantSchedules,
  OperationsAssistantStatus,
} from '@/lib/api';
import { OpsShell } from '@/components/ops-shell';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  response?: OperationsAssistantResponse;
}

const quickQuestions = [
  '今天最该推哪 3 个款？',
  '哪些款试戴高但预约低？',
  '哪些试戴图带来了预约？',
  '今天有什么异常？',
  '生成今日运营日报',
  '生成本周运营周报',
  '生成推荐位调整建议',
];

const priorityLabel: Record<string, string> = {
  high: '高优先级',
  medium: '中优先级',
  low: '低优先级',
};

const channelLabel: Record<string, string> = {
  feishu: '飞书',
  wechat: '微信',
  qq: 'QQ',
};

const deliveryLabel: Record<string, string> = {
  sent: '真实推送成功',
  mock_sent: '模拟送达',
  failed: '推送失败',
};

const patternLabel: Record<string, string> = {
  multi_channel_gateway: '多端消息网关',
  tool_workspace: '工具工作区',
  scheduled_trigger: '定时触发器',
  safe_action_approval: '安全审批',
};

const safetyLabel: Record<string, string> = {
  read_only_data_tools: '只读数据工具',
  safe_action_approval: '动作卡审批',
  manual_confirmation_required: '人工确认执行',
};

type SidePanel = 'actions' | 'tools' | 'runtime' | 'external' | 'schedule';

const sidePanelTabs = [
  { id: 'actions', label: '动作卡', icon: CheckCircle2 },
  { id: 'tools', label: '数据', icon: ClipboardCheck },
  { id: 'runtime', label: '状态', icon: ShieldCheck },
  { id: 'external', label: '端外', icon: ExternalLink },
  { id: 'schedule', label: '日报', icon: CalendarClock },
] satisfies Array<{ id: SidePanel; label: string; icon: LucideIcon }>;

export default function OperationsAssistantPage() {
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content:
        '我是甲感运营 Agent。你可以直接问我爆款推荐、转化断层、异常诊断、日报生成，所有结论都会尽量附上数据证据和可执行动作。',
    },
  ]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [lastUserMessage, setLastUserMessage] = useState('');
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [externalMessage, setExternalMessage] = useState('生成今日运营日报');
  const [externalChannel, setExternalChannel] = useState('feishu');
  const [externalLoading, setExternalLoading] = useState(false);
  const [externalReply, setExternalReply] = useState<OperationsAssistantExternalReply | null>(null);
  const [schedules, setSchedules] = useState<OperationsAssistantSchedules | null>(null);
  const [capabilities, setCapabilities] = useState<OperationsAssistantCapabilities | null>(null);
  const [agentStatus, setAgentStatus] = useState<OperationsAssistantStatus | null>(null);
  const [runtimeWarning, setRuntimeWarning] = useState<string | null>(null);
  const [webhookBaseUrl, setWebhookBaseUrl] = useState('');
  const [scheduleDraft, setScheduleDraft] = useState({
    enabled: true,
    time: '09:30',
    channels: ['feishu'],
    prompt: '生成今日运营日报',
  });
  const [scheduleSaving, setScheduleSaving] = useState(false);
  const [scheduleRunning, setScheduleRunning] = useState(false);
  const [scheduleMessage, setScheduleMessage] = useState<string | null>(null);
  const [activePanel, setActivePanel] = useState<SidePanel>('actions');
  const [showQuickPrompts, setShowQuickPrompts] = useState(false);
  const messageEndRef = useRef<HTMLDivElement | null>(null);

  const latestResponse = useMemo(
    () => [...messages].reverse().find((item) => item.response)?.response,
    [messages],
  );
  const runtimeText = agentStatus
    ? `${agentStatus.runtime.version} · ${agentStatus.runtime.llm_provider} · ${agentStatus.runtime.model || 'default'} · ${agentStatus.runtime.scheduler}`
    : `${capabilities?.version || 'checking'} · deepseek · in_process`;
  const llmStatusText = agentStatus?.runtime.llm_configured
    ? 'DeepSeek 已连接'
    : 'DeepSeek 未连接 · 当前使用规则兜底';

  useEffect(() => {
    void Promise.resolve().then(() => {
      setWebhookBaseUrl(`${window.location.protocol}//${window.location.hostname}:8004/api/operations/assistant`);
    });
    api.getAssistantStatus()
      .then((data) => {
        setAgentStatus(data);
        setSchedules({
          daily_report: data.scheduled_tasks.daily_report,
          deliveries: data.recent_deliveries,
          available_channels: Object.keys(data.channels),
          channels: data.channels,
        });
      })
      .catch(() => {
        setRuntimeWarning('当前 8004 后端还没有新版 Agent 状态接口，请重启后端服务。');
      });
    api.getAssistantSchedules()
      .then((data) => {
        setSchedules(data);
        setScheduleDraft({
          enabled: data.daily_report.enabled,
          time: data.daily_report.time,
          channels: data.daily_report.channels,
          prompt: data.daily_report.prompt,
        });
      })
      .catch(() => setSchedules(null));
    api.getAssistantCapabilities()
      .then((data) => {
        setCapabilities(data);
        if (data.version !== 'agent-v2') {
          setRuntimeWarning('当前后端不是新版 Agent 服务，请重启 8004 后再验收。');
        }
      })
      .catch(() => {
        setRuntimeWarning('当前 8004 后端还没有新版 Agent 能力接口，请重启后端服务。');
      });
  }, []);

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, loading]);

  const refreshAgentStatus = async () => {
    try {
      const data = await api.getAssistantStatus();
      setAgentStatus(data);
      setSchedules({
        daily_report: data.scheduled_tasks.daily_report,
        deliveries: data.recent_deliveries,
        available_channels: Object.keys(data.channels),
        channels: data.channels,
      });
    } catch (err) {
      console.error(err);
    }
  };

  const sendMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    setError(null);
    setSyncMessage(null);
    setLoading(true);
    setMessage('');
    setShowQuickPrompts(false);
    setLastUserMessage(trimmed);
    setMessages((current) => [...current, { role: 'user', content: trimmed }]);

    if (latestResponse && /同步|建议中心|保存建议|生成建议/.test(trimmed)) {
      try {
        const result = await api.applyAssistantCommand({
          message: trimmed,
          assistant_payload: latestResponse,
        });
        const content = result.message || '操作已提交';
        setSyncMessage(content);
        setMessages((current) => [...current, { role: 'assistant', content }]);
      } catch (err) {
        console.error(err);
        setError('执行 Agent 操作失败，请稍后再试。');
      } finally {
        setLoading(false);
      }
      return;
    }

    try {
      const response = await api.chatWithOperationsAssistant({
        message: trimmed,
        context: { days: 30 },
      });
      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          content: response.answer,
          response,
        },
      ]);
    } catch (err) {
      console.error(err);
      setError('运营 Agent 暂时不可用，请检查后端服务、DeepSeek Key 或运营账号权限。');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    sendMessage(message);
  };

  const syncLatestSuggestions = async () => {
    if (!latestResponse?.recommended_actions?.length || syncing) return;

    setSyncing(true);
    setError(null);
    setSyncMessage(null);
    try {
      const saved = await api.syncAssistantSuggestions({
        source_message: lastUserMessage,
        answer: latestResponse.answer,
        evidence: latestResponse.evidence,
        actions: latestResponse.recommended_actions,
      });
      setSyncMessage(`已同步 ${saved.length} 条建议到建议中心，等待人工确认。`);
    } catch (err) {
      console.error(err);
      setError('同步到建议中心失败，请稍后再试。');
    } finally {
      setSyncing(false);
    }
  };

  const sendExternalMessage = async () => {
    if (!externalMessage.trim() || externalLoading) return;

    setExternalLoading(true);
    setError(null);
    try {
      const reply = await api.sendExternalAgentMessage({
        channel: externalChannel,
        sender: 'demo_operator',
        message: externalMessage,
      });
      setExternalReply(reply);
      await refreshAgentStatus();
    } catch (err) {
      console.error(err);
      setError('端外 Agent 消息发送失败，请检查后端服务和运营账号权限。');
    } finally {
      setExternalLoading(false);
    }
  };

  const updateDailySchedule = async () => {
    setScheduleSaving(true);
    setScheduleMessage(null);
    try {
      const updated = await api.updateDailyReportSchedule(scheduleDraft);
      setSchedules((value) => ({
        daily_report: updated,
        deliveries: value?.deliveries || [],
        available_channels: value?.available_channels || ['feishu', 'wechat', 'qq'],
        channels: value?.channels,
      }));
      await refreshAgentStatus();
      setScheduleMessage('定时日报任务已更新。');
    } catch (err) {
      console.error(err);
      setError('保存定时任务失败。');
    } finally {
      setScheduleSaving(false);
    }
  };

  const runDailySchedule = async () => {
    setScheduleRunning(true);
    setScheduleMessage(null);
    try {
      const result = await api.runDailyReportSchedule();
      await refreshAgentStatus();
      setScheduleMessage(
        `已推送到 ${result.deliveries.map((item) => channelLabel[item.channel] || item.channel).join('、')}`,
      );
    } catch (err) {
      console.error(err);
      setError('手动触发日报推送失败。');
    } finally {
      setScheduleRunning(false);
    }
  };

  const channelEntries = Object.entries(agentStatus?.gateway?.connectors || schedules?.channels || {});
  const feishuWebhookUrl = webhookBaseUrl
    ? `${webhookBaseUrl}/webhook/feishu`
    : '/api/operations/assistant/webhook/feishu';
  const genericWebhookUrl = webhookBaseUrl ? `${webhookBaseUrl}/webhook` : '/api/operations/assistant/webhook';
  const automationCommands = agentStatus?.automation_playbook?.commands || schedules?.daily_report.commands || [
    '开启日报 09:30',
    '日报状态',
    '立即推送日报',
    '关闭日报',
  ];

  return (
    <OpsShell
      title="Chat"
      subtitle="运营 Agent 主工作台：对话查数、生成建议、同步行动卡、推送日报。"
      action={
        <div className="flex items-center gap-2 rounded-full bg-stone-950 px-4 py-2 text-sm text-amber-50">
          <ShieldCheck className="h-4 w-4" />
          任何执行动作都需要人工确认
        </div>
      }
    >
      <div className="chat-page-shell -mx-4 -my-6 grid h-[calc(100vh-10.125rem)] min-h-0 grid-cols-[minmax(0,1fr)_5.5rem] overflow-hidden bg-[#f7f1e7] md:-mx-6 md:h-[calc(100vh-8.5rem)] xl:-mx-8 xl:grid-cols-[minmax(0,880px)_22rem] xl:justify-center">
        <section className="chat-main-column flex min-w-0 flex-col overflow-hidden">
          <div className="shrink-0 px-4 pt-4 md:px-8">
            <div className="mx-auto flex w-full max-w-[820px] flex-wrap items-center justify-between gap-3 text-xs text-stone-500">
              <span className="flex items-center gap-2 font-semibold text-stone-800">
                <Bot className="h-4 w-4" />
                运营 Agent 正在读取运营工具
              </span>
              <span>
                {capabilities?.version || '检测中'} · 置信度：{latestResponse?.confidence || '等待提问'}
              </span>
            </div>
          </div>

          {runtimeWarning && (
            <p className="mx-auto w-full max-w-[820px] px-4 pt-4 text-sm leading-6 text-amber-800 md:px-8">
              {runtimeWarning}
            </p>
          )}

          <div className="chat-message-stream min-h-0 flex-1 space-y-5 overflow-y-auto px-4 pb-6 pt-5 md:px-8">
            {messages.map((item, index) => (
              <div
                key={`${item.role}-${index}`}
                className={item.role === 'user' ? 'mx-auto flex w-full max-w-[820px] justify-end' : 'mx-auto flex w-full max-w-[820px] justify-start'}
              >
                <div
                  className={
                    item.role === 'user'
                      ? 'max-w-[82%] rounded-3xl bg-stone-950 px-5 py-4 text-sm leading-6 text-amber-50'
                      : 'max-w-[90%] rounded-3xl bg-white/85 px-5 py-4 text-sm leading-6 text-stone-800'
                  }
                >
                  <div className="mb-2 flex items-center gap-2 text-xs font-medium opacity-70">
                    {item.role === 'user' ? <MessageSquareText className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                    {item.role === 'user' ? '你' : '运营 Agent'}
                  </div>
                  <p className="whitespace-pre-wrap">{item.content}</p>

                  {item.response && item.response.evidence.length > 0 && (
                    <div className="mt-4 grid gap-2 md:grid-cols-2">
                      {item.response.evidence.slice(0, 4).map((evidence, evidenceIndex) => (
                        <div key={`${evidence.source}-${evidenceIndex}`} className="rounded-2xl bg-amber-50 px-4 py-3">
                          <p className="text-xs font-semibold text-stone-500">{evidence.source}</p>
                          <p className="mt-1 font-medium text-stone-900">{evidence.label}</p>
                          <p className="text-stone-600">{evidence.value}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="mx-auto flex w-full max-w-[820px] justify-start">
                <div className="flex items-center gap-3 rounded-3xl bg-white/85 px-5 py-4 text-sm text-stone-600">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  正在选择工具、读取运营数据并生成建议...
                </div>
              </div>
            )}
            <div ref={messageEndRef} className="h-8" />
          </div>

          <div className="chat-input-dock sticky bottom-0 z-30 border-t border-stone-200/70 bg-[#f7f1e7]/95 px-4 py-3 backdrop-blur-xl">
            {error && <p className="mx-auto mb-3 max-w-[820px] rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
            <div className="relative mx-auto max-w-[820px]">
              {showQuickPrompts && (
                <div className="quick-prompt-overlay absolute bottom-[calc(100%+0.75rem)] left-0 right-0 z-40 max-h-72 overflow-y-auto rounded-3xl bg-stone-950/95 p-3 text-amber-50 shadow-2xl shadow-stone-950/20 backdrop-blur-xl">
                  <div className="mb-2 flex items-center justify-between gap-3 px-1">
                    <p className="text-xs font-semibold text-amber-100/80">选择一个预设问题</p>
                    <button
                      type="button"
                      onClick={() => setShowQuickPrompts(false)}
                      className="text-xs font-medium text-amber-100/60 transition hover:text-amber-50"
                    >
                      收起
                    </button>
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {quickQuestions.map((question) => (
                      <button
                        key={question}
                        type="button"
                        onClick={() => sendMessage(question)}
                        disabled={loading}
                        className="rounded-2xl bg-amber-50/10 px-3 py-2.5 text-left text-xs font-medium leading-5 text-amber-50 transition hover:bg-amber-50 hover:text-stone-950 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {question}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              <form onSubmit={handleSubmit} className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setShowQuickPrompts((value) => !value)}
                  className="shrink-0 rounded-2xl border border-stone-200 bg-white px-4 py-3 text-sm font-semibold text-stone-700 transition hover:border-stone-950 hover:text-stone-950"
                >
                  预设问题
                </button>
              <input
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                placeholder="例如：哪个款试戴高但预约低？今天有什么异常？生成推荐位调整建议..."
                className="min-w-0 flex-1 rounded-2xl border border-stone-200 bg-white px-4 py-3 text-sm outline-none transition focus:border-stone-950"
              />
              <button
                type="submit"
                disabled={loading || !message.trim()}
                className="flex items-center gap-2 rounded-2xl bg-stone-950 px-5 py-3 text-sm font-medium text-amber-50 transition hover:bg-stone-800 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Send className="h-4 w-4" />
                发送
              </button>
              </form>
            </div>
          </div>
        </section>

        <section className="agent-side-rail grid min-w-0 grid-cols-[5.5rem_0] overflow-hidden border-l border-stone-200/70 bg-[#f7f1e7] xl:grid-cols-[4.75rem_minmax(0,1fr)]">
          <div className="flex flex-col items-center gap-2 px-2 py-4">
            {sidePanelTabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActivePanel(tab.id)}
                  className={
                    activePanel === tab.id
                      ? 'flex h-14 w-14 flex-col items-center justify-center gap-1 rounded-2xl bg-stone-950 text-[11px] font-semibold text-amber-50'
                      : 'flex h-14 w-14 flex-col items-center justify-center gap-1 rounded-2xl text-[11px] font-medium text-stone-500 transition hover:bg-white/70 hover:text-stone-900'
                  }
                >
                  <Icon className="h-4 w-4" />
                  {tab.label}
                </button>
              );
            })}
          </div>

          <div className="hidden min-w-0 overflow-y-auto px-4 py-4 xl:block">
            {activePanel === 'actions' && (
          <section className="space-y-4 py-2">
            <div className="mb-4 flex items-center justify-between gap-3">
              <h2 className="flex items-center gap-2 font-bold text-stone-950">
                <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                运营动作卡
              </h2>
              <button
                type="button"
                onClick={syncLatestSuggestions}
                disabled={!latestResponse?.recommended_actions?.length || syncing}
                className="flex items-center gap-2 rounded-full bg-emerald-600 px-3 py-2 text-xs font-medium text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {syncing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ClipboardCheck className="h-3.5 w-3.5" />}
                同步到建议中心
              </button>
            </div>
            {syncMessage && (
              <p className="mb-3 rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{syncMessage}</p>
            )}
            <div className="space-y-3">
              {latestResponse?.recommended_actions?.length ? (
                latestResponse.recommended_actions.map((action, index) => (
                  <div key={`${action.title}-${index}`} className="rounded-3xl bg-white/60 p-4">
                    <div className="mb-2 flex items-center justify-between gap-3">
                      <h3 className="font-semibold text-stone-950">{action.title}</h3>
                      <span className="shrink-0 rounded-full bg-amber-100 px-3 py-1 text-xs text-amber-800">
                        {priorityLabel[action.priority] || action.priority}
                      </span>
                    </div>
                    <p className="text-sm text-stone-600">{action.reason}</p>
                    {action.risk && <p className="mt-2 text-xs text-stone-500">风险：{action.risk}</p>}
                    {action.requires_confirmation && (
                      <p className="mt-3 text-xs font-medium text-stone-500">需要人工确认后执行</p>
                    )}
                  </div>
                ))
              ) : (
                <p className="rounded-3xl bg-white/45 p-5 text-sm text-stone-500">
                  提问后这里会显示可执行建议，例如推荐位调整、预约跟进、冷门款修复。
                </p>
              )}
            </div>
          </section>
          )}

          {activePanel === 'tools' && (
          <section className="space-y-4 py-2">
            <h2 className="mb-4 font-bold text-stone-950">使用了哪些数据</h2>
            <div className="space-y-2">
              {latestResponse?.tool_trace?.length ? (
                latestResponse.tool_trace.map((trace, index) => {
                  const statusClass = trace.status === 'success'
                    ? 'text-emerald-600'
                    : trace.status === 'fallback'
                      ? 'text-amber-600'
                      : 'text-red-600';
                  return (
                    <div key={`${trace.tool}-${index}`} className="rounded-2xl bg-stone-50 px-4 py-3 text-sm">
                      <div className="flex items-center justify-between gap-3">
                        <span className="font-medium text-stone-800">{trace.tool}</span>
                        <span className={statusClass}>{trace.status === 'fallback' ? '兜底' : trace.status}</span>
                      </div>
                      {trace.summary && <p className="mt-1 text-xs text-stone-500">{trace.summary}</p>}
                    </div>
                  );
                })
              ) : (
                <p className="text-sm text-stone-500">暂无工具调用。Agent 回答后会显示读取过的运营工具。</p>
              )}
            </div>
          </section>
          )}

          {activePanel === 'runtime' && (
            <section className="space-y-4 py-2">
              <h2 className="mb-4 flex items-center gap-2 font-bold text-stone-950">
                <ShieldCheck className="h-5 w-5 text-stone-700" />
                Agent 运行状态
              </h2>
              <div className="grid gap-3">
                <div className="rounded-3xl bg-stone-50 p-4">
                  <p className="text-xs font-bold text-stone-400">Runtime</p>
                  <p className="mt-2 text-sm leading-6 text-stone-700">{runtimeText}</p>
                  <p className={`mt-2 text-xs font-semibold ${agentStatus?.runtime.llm_configured ? 'text-emerald-700' : 'text-amber-700'}`}>
                    {llmStatusText}
                  </p>
                </div>
                {!agentStatus?.runtime.llm_configured && (
                  <div className="rounded-3xl border border-amber-200 bg-amber-50 p-4 text-xs leading-5 text-amber-900">
                    <p className="font-bold">DeepSeek 未连接</p>
                    <p className="mt-1">
                      当前后端进程没有读到 <span className="font-mono">DEEPSEEK_API_KEY</span>。本地修复：执行{' '}
                      <span className="font-mono">nailmind\\scripts\\set-local-secrets.ps1 -DeepSeekOnly</span> 后，用{' '}
                      <span className="font-mono">nailmind\\scripts\\start-local.ps1</span> 重启预览服务。
                    </p>
                  </div>
                )}
                <div className="rounded-3xl bg-stone-50 p-4">
                  <p className="text-xs font-bold text-stone-400">安全边界</p>
                  <p className="mt-2 text-sm leading-6 text-stone-700">
                    {(agentStatus?.safety.execution_policy || ['manual_confirmation_required'])
                      .map((item) => safetyLabel[item] || item)
                      .join(' / ')}
                  </p>
                </div>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {(agentStatus?.openclaw_patterns || ['multi_channel_gateway', 'tool_workspace', 'scheduled_trigger']).map((pattern) => (
                  <span key={pattern} className="rounded-full bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-800">
                    {patternLabel[pattern] || pattern}
                  </span>
                ))}
              </div>
              <div className="mt-4 grid gap-2">
                {(agentStatus?.suggested_commands || ['今天有什么异常？', '生成今日运营日报', '开启日报 09:30', '立即推送日报']).slice(0, 5).map((command) => (
                  <button
                    key={command}
                    type="button"
                    onClick={() => sendMessage(command)}
                    className="flex items-center justify-between rounded-2xl bg-[#fffaf0] px-4 py-3 text-left text-sm text-stone-700 transition hover:bg-amber-50"
                  >
                    <span>{command}</span>
                    <Send className="h-3.5 w-3.5 text-stone-400" />
                  </button>
                ))}
              </div>
            </section>
          )}

          {activePanel === 'external' && (
            <section className="space-y-4 py-2">
              <h2 className="mb-4 flex items-center gap-2 font-bold text-stone-950">
                <ExternalLink className="h-5 w-5 text-stone-700" />
                端外 Agent
              </h2>
              <p className="mb-4 text-sm leading-6 text-stone-500">
                飞书作为真实手机端入口，微信/QQ 先走统一 Webhook 模拟，所有写动作仍需要人工确认。
              </p>
              <div className="mb-4 grid gap-2">
                {channelEntries.map(([channel, info]) => (
                  <button
                    key={channel}
                    type="button"
                    onClick={() => setExternalChannel(channel)}
                    className={
                      externalChannel === channel
                        ? 'rounded-3xl border border-stone-950 bg-stone-950 p-4 text-left text-amber-50 shadow-sm'
                        : 'rounded-3xl border border-stone-200 bg-white p-4 text-left text-stone-700 transition hover:border-stone-400'
                    }
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-semibold">{channelLabel[channel] || info.label}</p>
                      <span
                        className={
                          info.configured
                            ? 'rounded-full bg-emerald-100 px-3 py-1 text-xs font-medium text-emerald-700'
                            : 'rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800'
                        }
                      >
                        {info.configured ? '真实接通' : '模拟可验收'}
                      </span>
                    </div>
                    <p className={externalChannel === channel ? 'mt-2 text-xs text-amber-100/75' : 'mt-2 text-xs text-stone-500'}>
                      入站：{info.inbound || info.mode} · 出站：{info.outbound || info.mode}
                    </p>
                  </button>
                ))}
              </div>
              <div className="mb-4 grid gap-2">
                <div className="rounded-2xl bg-white px-4 py-3 text-xs leading-5 text-stone-500">
                  <p className="font-semibold text-stone-800">飞书事件订阅 URL</p>
                  <p className="mt-1 break-all font-mono text-stone-600">{feishuWebhookUrl}</p>
                </div>
                <div className="rounded-2xl bg-white px-4 py-3 text-xs leading-5 text-stone-500">
                  <p className="font-semibold text-stone-800">通用 Webhook</p>
                  <p className="mt-1 break-all font-mono text-stone-600">{genericWebhookUrl}</p>
                </div>
              </div>
              <textarea
                value={externalMessage}
                onChange={(event) => setExternalMessage(event.target.value)}
                className="h-24 w-full resize-none rounded-2xl border border-stone-200 bg-white px-4 py-3 text-sm outline-none focus:border-stone-950"
              />
              <button
                type="button"
                onClick={sendExternalMessage}
                disabled={externalLoading || !externalMessage.trim()}
                className="mt-3 flex w-full items-center justify-center gap-2 rounded-2xl bg-stone-950 px-4 py-3 text-sm font-semibold text-amber-50 disabled:opacity-40"
              >
                {externalLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Radio className="h-4 w-4" />}
                发送端外消息
              </button>
              {externalReply && (
                <div className="mt-4 rounded-3xl bg-white p-4 text-sm text-stone-700">
                  <div className="mb-2 flex items-center justify-between gap-3">
                    <p className="text-xs font-bold text-stone-400">{channelLabel[externalReply.channel]} 返回内容</p>
                    {externalReply.delivery_status && (
                      <span className="rounded-full bg-stone-100 px-3 py-1 text-xs text-stone-600">
                        {deliveryLabel[externalReply.delivery_status] || externalReply.delivery_status}
                      </span>
                    )}
                  </div>
                  <p className="whitespace-pre-wrap leading-6">{externalReply.reply_text}</p>
                </div>
              )}
            </section>
          )}

          {activePanel === 'schedule' && (
            <section className="space-y-4 py-2">
              <h2 className="mb-4 flex items-center gap-2 font-bold text-stone-950">
                <CalendarClock className="h-5 w-5 text-stone-700" />
                自动运营日报
              </h2>
              <div className="space-y-3">
                <div className="grid gap-2">
                  {automationCommands.map((command) => (
                    <button
                      key={command}
                      type="button"
                      onClick={() => setExternalMessage(command)}
                      className="rounded-2xl bg-stone-50 px-4 py-3 text-left text-xs font-medium text-stone-700 transition hover:bg-amber-50"
                    >
                      {command}
                    </button>
                  ))}
                </div>
                <label className="flex items-center justify-between rounded-2xl bg-stone-50 px-4 py-3 text-sm">
                  <span className="font-medium text-stone-700">启用每日推送</span>
                  <input
                    type="checkbox"
                    checked={scheduleDraft.enabled}
                    onChange={(event) => setScheduleDraft((value) => ({ ...value, enabled: event.target.checked }))}
                  />
                </label>
                <label className="block text-sm">
                  <span className="mb-1 block font-medium text-stone-700">推送时间</span>
                  <input
                    value={scheduleDraft.time}
                    onChange={(event) => setScheduleDraft((value) => ({ ...value, time: event.target.value }))}
                    className="w-full rounded-2xl border border-stone-200 px-4 py-3 outline-none focus:border-stone-950"
                  />
                </label>
                <label className="block text-sm">
                  <span className="mb-1 block font-medium text-stone-700">日报 Prompt</span>
                  <input
                    value={scheduleDraft.prompt}
                    onChange={(event) => setScheduleDraft((value) => ({ ...value, prompt: event.target.value }))}
                    className="w-full rounded-2xl border border-stone-200 px-4 py-3 outline-none focus:border-stone-950"
                  />
                </label>
                {schedules?.daily_report.next_run_at && (
                  <p className="rounded-2xl bg-amber-50 px-4 py-3 text-xs text-amber-800">
                    下次计划推送：{new Date(schedules.daily_report.next_run_at).toLocaleString()}
                  </p>
                )}
                <div className="grid gap-3 sm:grid-cols-2">
                  <button
                    type="button"
                    onClick={updateDailySchedule}
                    disabled={scheduleSaving}
                    className="flex items-center justify-center gap-2 rounded-2xl border border-stone-200 bg-white px-4 py-3 text-sm font-semibold text-stone-800 disabled:opacity-40"
                  >
                    {scheduleSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <CalendarClock className="h-4 w-4" />}
                    保存任务
                  </button>
                  <button
                    type="button"
                    onClick={runDailySchedule}
                    disabled={scheduleRunning || scheduleSaving}
                    className="flex items-center justify-center gap-2 rounded-2xl bg-emerald-600 px-4 py-3 text-sm font-semibold text-white disabled:opacity-40"
                  >
                    {scheduleRunning ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />}
                    立即推送
                  </button>
                </div>
                {scheduleMessage && <p className="rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{scheduleMessage}</p>}
                {schedules?.daily_report.last_run && (
                  <p className="text-xs leading-5 text-stone-400">
                    上次推送：{new Date(schedules.daily_report.last_run.run_at).toLocaleString()} · {schedules.daily_report.last_run.status}
                  </p>
                )}
              </div>
            </section>
          )}
          </div>
        </section>
      </div>

    </OpsShell>
  );
}
