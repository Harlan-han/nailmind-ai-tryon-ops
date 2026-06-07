'use client';

import { useEffect, useState } from 'react';
import { Calendar, Copy, CheckCircle, AlertTriangle, Lightbulb, Loader2, ChevronLeft, ChevronRight } from 'lucide-react';
import { api } from '@/lib/api';
import { OpsShell } from '@/components/ops-shell';

interface DailyReport {
  date: string;
  summary: string;
  highlights: string[];
  alerts: string[];
  recommendations: Array<{
    action: string;
    target: string;
    reason: string;
  }>;
  copy_for_operation: string;
}

const todayDateString = () => new Date().toISOString().split('T')[0];

export default function DailyReportPage() {
  const [report, setReport] = useState<DailyReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [currentDate, setCurrentDate] = useState<string>(todayDateString);

  async function loadReport(dateStr: string) {
    await Promise.resolve();
    setLoading(true);
    try {
      let data;
      const today = todayDateString();
      if (dateStr === today) {
        data = await api.getDailyReport();
      } else {
        data = await api.getHistoricalReport(dateStr);
      }
      setReport(data);
    } catch (error) {
      console.error('Failed to load daily report:', error);
      setReport(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void Promise.resolve().then(() => loadReport(currentDate));
  }, [currentDate]);

  const handleDateChange = (dateStr: string) => {
    setCurrentDate(dateStr);
  };

  const shiftDate = (days: number) => {
    const date = new Date(currentDate);
    date.setDate(date.getDate() + days);
    const newDateStr = date.toISOString().split('T')[0];
    handleDateChange(newDateStr);
  };

  const handleCopy = () => {
    if (report?.copy_for_operation) {
      navigator.clipboard.writeText(report.copy_for_operation);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const isToday = currentDate === todayDateString();

  return (
    <OpsShell
      title="运营日报"
      subtitle="沉淀每日核心变化、风险提醒和可复制运营文案。"
    >
      <div className="mx-auto max-w-3xl space-y-6">
        {/* Date Navigator */}
        <div className="flex items-center justify-between bg-white rounded-xl p-4 border border-gray-100">
          <button
            onClick={() => shiftDate(-1)}
            className="p-2 text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>

          <div className="flex items-center gap-2">
            <Calendar className="w-5 h-5 text-rose-500" />
            <input
              type="date"
              value={currentDate}
              max={todayDateString()}
              onChange={(e) => handleDateChange(e.target.value)}
              className="text-gray-900 font-medium bg-transparent border-none focus:outline-none cursor-pointer"
            />
            {isToday && (
              <span className="px-2 py-0.5 bg-rose-100 text-rose-600 text-xs rounded-full">
                今日
              </span>
            )}
          </div>

          <button
            onClick={() => shiftDate(1)}
            disabled={isToday}
            className="p-2 text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>

        {loading ? (
          <div className="text-center py-20">
            <Loader2 className="w-8 h-8 text-rose-400 mx-auto animate-spin" />
            <p className="mt-4 text-gray-500">加载运营日报...</p>
          </div>
        ) : report ? (
          <>
            {/* Summary */}
            <div className="bg-white rounded-xl p-6 border border-gray-100">
              <h2 className="font-semibold text-gray-900 mb-3">今日摘要</h2>
              <p className="text-gray-600">{report.summary}</p>
            </div>

            {/* Highlights */}
            <div className="bg-white rounded-xl p-6 border border-gray-100">
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle className="w-5 h-5 text-green-500" />
                <h2 className="font-semibold text-gray-900">亮点</h2>
              </div>
              {report.highlights.length > 0 ? (
                <ul className="space-y-2">
                  {report.highlights.map((highlight, index) => (
                    <li key={index} className="flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-green-500 mt-2" />
                      <span className="text-gray-600">{highlight}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-gray-400 text-sm">今日暂无亮点</p>
              )}
            </div>

            {/* Alerts */}
            <div className="bg-white rounded-xl p-6 border border-gray-100">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="w-5 h-5 text-yellow-500" />
                <h2 className="font-semibold text-gray-900">风险提醒</h2>
              </div>
              {report.alerts.length > 0 ? (
                <ul className="space-y-2">
                  {report.alerts.map((alert, index) => (
                    <li key={index} className="flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-yellow-500 mt-2" />
                      <span className="text-gray-600">{alert}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-gray-400 text-sm">今日无异常提醒</p>
              )}
            </div>

            {/* Recommendations */}
            <div className="bg-white rounded-xl p-6 border border-gray-100">
              <div className="flex items-center gap-2 mb-3">
                <Lightbulb className="w-5 h-5 text-blue-500" />
                <h2 className="font-semibold text-gray-900">推荐动作</h2>
              </div>
              {report.recommendations.length > 0 ? (
                <div className="space-y-3">
                  {report.recommendations.map((rec, index) => (
                    <div key={index} className="bg-blue-50 rounded-lg p-3">
                      <p className="font-medium text-blue-900">{rec.action}</p>
                      <p className="text-sm text-blue-700 mt-1">
                        目标：{rec.target}（{rec.reason}）
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-400 text-sm">暂无推荐动作</p>
              )}
            </div>

            {/* Copy for Operations */}
            <div className="bg-white rounded-xl p-6 border border-gray-100">
              <div className="flex items-center justify-between mb-3">
                <h2 className="font-semibold text-gray-900">可复制文案</h2>
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-2 text-sm text-rose-600 hover:text-rose-700"
                >
                  {copied ? (
                    <>
                      <CheckCircle className="w-4 h-4" />
                      已复制
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4" />
                      复制
                    </>
                  )}
                </button>
              </div>
              <pre className="bg-gray-50 rounded-lg p-4 text-sm text-gray-600 whitespace-pre-wrap">
                {report.copy_for_operation}
              </pre>
            </div>
          </>
        ) : (
          <div className="text-center py-20 bg-white rounded-xl border border-gray-100">
            <p className="text-gray-500">日报加载失败</p>
            <button
              onClick={() => loadReport(currentDate)}
              className="mt-4 text-rose-600 text-sm hover:underline"
            >
              重新加载
            </button>
          </div>
        )}
      </div>
    </OpsShell>
  );
}
