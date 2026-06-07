'use client';

import { FormEvent, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { Bot, Loader2, Send, Sparkles } from 'lucide-react';
import { api, type ConsumerAssistantRecommendation } from '@/lib/api';
import { MobileShell } from '@/components/mobile-shell';
import { useValidatedUser } from '@/lib/use-validated-user';

type Message = {
  role: 'assistant' | 'user';
  text: string;
  recommendations?: ConsumerAssistantRecommendation[];
};

const starterPrompts = ['我想要显白一点', '通勤短甲推荐', '约会甜美款', '帮我选不夸张但高级的'];

export default function ConsumerAssistantPage() {
  const { user, checking } = useValidatedUser('/assistant');
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      text: '我是小甲灵，你的美甲试戴助手。告诉我你的场景、肤色顾虑或想要的风格，我帮你缩小到几款可以直接试戴的模板。',
    },
  ]);
  const [input, setInput] = useState('');
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const scrollToLatest = () => {
    window.requestAnimationFrame(() => {
      scrollRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
      window.scrollTo({ top: document.documentElement.scrollHeight, behavior: 'smooth' });
    });
  };

  useEffect(() => {
    scrollToLatest();
    const timer = window.setTimeout(scrollToLatest, 120);
    return () => window.clearTimeout(timer);
  }, [messages, loading]);

  const sendMessage = async (text: string) => {
    const message = text.trim();
    if (!message || loading || checking || !user || user.user_type !== 'consumer') return;
    setMessages((current) => [...current, { role: 'user', text: message }]);
    setInput('');
    setLoading(true);
    try {
      const response = await api.chatWithConsumerAssistant({
        message,
        conversation_id: conversationId,
        context: { source: 'consumer_tab', nickname: user.nickname },
      });
      setConversationId(response.conversation_id);
      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          text: response.answer,
          recommendations: response.recommendations,
        },
      ]);
    } catch (error) {
      console.error(error);
      setMessages((current) => [
        ...current,
        { role: 'assistant', text: '小甲灵暂时连不上 AI 通道，但你可以先从热门和新品款式里挑一款试戴。' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void sendMessage(input);
  };

  return (
    <MobileShell>
      <div className="flex min-h-screen flex-col bg-[#f8f1e6]">
        <header className="sticky top-0 z-30 border-b border-stone-200/70 bg-[#f8f1e6]/90 px-5 py-4 backdrop-blur-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.26em] text-stone-400">NailMind Assistant</p>
          <div className="mt-2 flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-stone-950 text-amber-50">
              <Bot className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-stone-950">小甲灵</h1>
              <p className="text-sm text-stone-500">帮你按场景、肤色和风格选款</p>
            </div>
          </div>
        </header>

        <main className="flex-1 space-y-4 px-5 py-5 pb-40">
          <section className="rounded-[2rem] bg-stone-950 p-5 text-amber-50">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm text-amber-100/70">今日试戴灵感</p>
                <h2 className="mt-2 text-xl font-bold">先聊需求，再直接跳到可试戴模板。</h2>
              </div>
              <Sparkles className="h-6 w-6 text-amber-200" />
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {starterPrompts.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => void sendMessage(prompt)}
                  className="rounded-full bg-white/12 px-3 py-2 text-xs font-semibold text-amber-50"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </section>

          {messages.map((message, index) => (
            <article
              key={`${message.role}-${index}`}
              className={message.role === 'user' ? 'ml-10 rounded-[1.5rem] bg-white p-4 shadow-sm' : 'mr-4 rounded-[1.5rem] bg-[#fffaf0] p-4 shadow-sm'}
            >
              <p className="text-xs font-bold text-stone-400">{message.role === 'user' ? user?.nickname || '我' : '小甲灵'}</p>
              <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-stone-800">{message.text}</p>
              {message.recommendations?.length ? (
                <div className="mt-4 space-y-3">
                  {message.recommendations.map((item) => (
                    <Link key={item.id} href={`/tryon?design=${item.id}`} className="flex gap-3 rounded-2xl bg-white p-2">
                      <img src={item.image_url} alt={item.name} className="h-20 w-20 rounded-xl object-cover" onLoad={scrollToLatest} />
                      <div className="min-w-0 flex-1 py-1">
                        <p className="font-bold text-stone-950">{item.name}</p>
                        <p className="mt-1 line-clamp-2 text-xs leading-5 text-stone-500">{item.reason}</p>
                        <p className="mt-2 text-xs font-semibold text-rose-600">去试戴 →</p>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : null}
            </article>
          ))}
          {loading && (
            <div className="mr-10 flex items-center gap-2 rounded-[1.5rem] bg-[#fffaf0] p-4 text-sm text-stone-500 shadow-sm">
              <Loader2 className="h-4 w-4 animate-spin" />
              小甲灵正在挑款...
            </div>
          )}
          <div ref={scrollRef} />
        </main>

        <form onSubmit={submit} className="fixed inset-x-0 bottom-[4.65rem] z-40 mx-auto max-w-[430px] bg-[#f8f1e6]/95 px-5 py-3 backdrop-blur-2xl">
          <div className="flex gap-2 rounded-[1.5rem] border border-stone-200 bg-white p-2 shadow-lg shadow-stone-200/60">
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="问小甲灵：我适合什么款？"
              className="min-w-0 flex-1 bg-transparent px-3 text-sm outline-none"
            />
            <button
              type="submit"
              disabled={loading || checking || !user || user.user_type !== 'consumer' || !input.trim()}
              className="flex h-11 w-11 items-center justify-center rounded-2xl bg-stone-950 text-amber-50 disabled:opacity-40"
              aria-label="发送"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </button>
          </div>
        </form>
      </div>
    </MobileShell>
  );
}
