import { clearAuthSession, getAuthToken, type AuthUser } from './auth';
import { API_BASE_URL } from './config';

export { API_BASE_URL };

export class ApiError extends Error {
  status: number;
  endpoint: string;

  constructor(status: number, endpoint: string, message?: string) {
    super(message || `API error: ${status}`);
    this.name = 'ApiError';
    this.status = status;
    this.endpoint = endpoint;
  }
}

function formatApiDetail(detail: unknown): string | null {
  if (!detail) return null;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === 'string') return item;
        if (!item || typeof item !== 'object') return null;
        const record = item as { loc?: unknown[]; msg?: unknown };
        const field = Array.isArray(record.loc) ? record.loc[record.loc.length - 1] : null;
        const msg = typeof record.msg === 'string' ? record.msg : null;
        if (!msg) return null;
        return typeof field === 'string' ? `${field}: ${msg}` : msg;
      })
      .filter(Boolean);
    return messages.length ? messages.join('; ') : null;
  }
  return null;
}

function redirectForAuth(endpoint: string) {
  if (typeof window === 'undefined') return;
  if (endpoint.startsWith('/auth/')) return;
  const currentPath = `${window.location.pathname}${window.location.search}`;
  if (currentPath.startsWith('/admin') || currentPath.startsWith('/merchant')) {
    if (!currentPath.startsWith('/admin/login')) {
      window.location.href = '/admin/login';
    }
    return;
  }
  if (!currentPath.startsWith('/login')) {
    window.location.href = `/login?next=${encodeURIComponent(currentPath)}`;
  }
}

export interface TryOnRecord {
  id: number;
  user_id: number;
  hand_photo_id: number;
  nail_design_id: number;
  result_image_url: string | null;
  status: 'pending' | 'processing' | 'completed' | 'fallback_completed' | 'failed';
  error_message: string | null;
  is_favorite: boolean;
  is_candidate: boolean;
  has_booking_intent: boolean;
  created_at: string;
  completed_at: string | null;
  nail_design?: {
    id: number;
    name: string;
    image_url: string;
    style_tags: string[];
    color_tags?: string[];
    scene_tags?: string[];
    description?: string;
    try_on_count?: number;
    favorite_count?: number;
    shape?: string;
  };
}

export interface AuthCodeResponse {
  status: string;
  expires_in_seconds: number;
  debug_code?: string | null;
}

export interface AuthLoginResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export interface TryOnProgress {
  try_on_id: number;
  status: TryOnRecord['status'];
  progress: number;
  phase: string;
  message: string;
  result_image_url: string | null;
  error_message: string | null;
  started_at: string;
  elapsed_seconds: number;
  updated_at: string;
}

export interface OperationsAssistantEvidence {
  label: string;
  value: string;
  source: string;
}

export interface OperationsAssistantAction {
  title: string;
  reason: string;
  priority: string;
  risk: string | null;
  requires_confirmation: boolean;
}

export interface OperationsAssistantToolTrace {
  tool: string;
  status: string;
  summary: string | null;
}

export interface OperationsAssistantResponse {
  answer: string;
  evidence: OperationsAssistantEvidence[];
  recommended_actions: OperationsAssistantAction[];
  tool_trace: OperationsAssistantToolTrace[];
  confidence: string;
}

export interface OperationsAssistantExternalReply {
  channel: string;
  delivery_channel?: string;
  delivery_status?: 'sent' | 'mock_sent' | 'failed';
  delivery_detail?: string | null;
  sender: string;
  reply_text: string;
  evidence: OperationsAssistantEvidence[];
  recommended_actions: OperationsAssistantAction[];
  tool_trace: OperationsAssistantToolTrace[];
  created_at: string;
}

export interface OperationsAssistantSchedule {
  enabled: boolean;
  time: string;
  channels: string[];
  prompt: string;
  next_run_at?: string | null;
  manual_trigger_path?: string;
  configure_path?: string;
  commands?: string[];
  last_run?: {
    task: string;
    status: string;
    run_at: string;
    deliveries: OperationsAssistantExternalReply[];
  } | null;
}

export interface OperationsAssistantChannel {
  label: string;
  mode: string;
  status?: 'connected' | 'simulated' | string;
  configured: boolean;
  inbound?: string;
  outbound?: string;
  required_env?: string[];
  description: string;
  setup_steps?: string[];
  message_examples?: string[];
}

export interface OperationsAssistantSchedules {
  daily_report: OperationsAssistantSchedule;
  deliveries: Array<Record<string, unknown>>;
  available_channels: string[];
  channels?: Record<string, OperationsAssistantChannel>;
}

export interface OperationsAssistantStatus {
  runtime: {
    entrypoint: string;
    version: string;
    llm_provider: string;
    llm_configured?: boolean;
    model?: string;
    tool_calling: boolean;
    scheduler: string;
  };
  openclaw_patterns: string[];
  channels: Record<string, OperationsAssistantChannel>;
  gateway?: {
    primary_inbox: string;
    webhook_paths: string[];
    connectors: Record<string, OperationsAssistantChannel>;
    quick_setup?: Array<{
      channel: string;
      title: string;
      webhook_url: string;
      outbound_env?: string | null;
      recommended_for: string;
    }>;
    security: string[];
  };
  scheduled_tasks: {
    daily_report: OperationsAssistantSchedule;
  };
  recent_deliveries: Array<Record<string, unknown>>;
  suggested_commands: string[];
  automation_playbook?: {
    commands: string[];
    safe_actions: string[];
    blocked_actions: string[];
  };
  safety: {
    execution_policy: string[];
    write_actions: string[];
  };
}

export interface ConsumerAssistantRecommendation {
  id: number;
  name: string;
  image_url: string;
  reason: string;
  style_tags: string[];
}

export interface ConsumerAssistantResponse {
  persona: string;
  answer: string;
  recommendations: ConsumerAssistantRecommendation[];
  chips: string[];
  conversation_id: string;
  confidence: string;
}

export interface ConsumerAssistantInsights {
  total_messages: number;
  active_users: number;
  top_intents: Array<{ name: string; count: number }>;
  top_tags: Array<{ name: string; count: number }>;
  recent_messages: Array<{
    user_id: number;
    user_name: string;
    message: string;
    recommended_designs: string[];
    top_tags: string[];
    created_at: string;
  }>;
}

export interface OperationsAssistantCapabilities {
  version: string;
  features: Record<string, boolean>;
  channels: Record<string, OperationsAssistantChannel>;
}

export interface OperationsSuggestion {
  id: string;
  type: 'hot' | 'cold' | 'new' | 'promo' | 'agent';
  priority: 'high' | 'medium' | 'low';
  title: string;
  description: string;
  target: string;
  reason: string;
  expected_impact: string;
  risk?: string | null;
  requires_confirmation?: boolean;
  source?: string;
  source_message?: string | null;
  evidence?: OperationsAssistantEvidence[];
  status: 'pending' | 'accepted' | 'rejected' | 'completed';
  created_at: string;
}

export interface OperationsSuggestionActionResult {
  id: string;
  status: OperationsSuggestion['status'];
  applied_action: 'promote_hot_design' | 'demote_hot_design' | 'status_only';
  design_id?: number;
  is_hot?: boolean;
}

export interface TodayWorkbenchActionCard {
  id: string;
  type: 'booking_followup' | 'conversion_gap' | 'suggestion_review';
  priority: 'high' | 'medium' | 'low';
  title: string;
  description: string;
  metric: string;
  target_url: string;
  created_at: string | null;
}

export interface TodayWorkbench {
  summary: {
    today_try_ons: number;
    today_favorites: number;
    today_booking_intents: number;
    hot_designs_count: number;
    pending_booking_count: number;
    conversion_gap_count: number;
    pending_suggestion_count: number;
  };
  action_cards: TodayWorkbenchActionCard[];
  trending_styles: Array<{ style: string; count: number }>;
}

export interface MerchantOverview {
  total_designs: number;
  active_designs: number;
  total_views: number;
  total_try_ons: number;
  failed_try_ons: number;
  total_favorites: number;
  conversion_rate: number;
  hot_designs: Array<{
    id: number;
    name: string;
    image_url: string;
    try_on_count: number;
  }>;
  recent_bookings: number;
  recent_activity: Array<{
    event_key: string;
    action: string;
    detail: string;
    time: string;
    created_at: string | null;
  }>;
}

export interface OperationsConfig {
  styleTags: string[];
  colorTags: string[];
  sceneTags: string[];
  hotThreshold: number;
  newThreshold: number;
  trendingDays: number;
  designsPerPage: number;
  maxCandidates: number;
  enableAiInsights: boolean;
  enableNotifications: boolean;
}

export interface BookingIntent {
  id: number;
  user_id: number;
  user_name: string;
  phone: string;
  try_on_record_id: number;
  nail_design_id: number;
  design_name: string;
  design_image_url: string | null;
  try_on_result_image_url: string | null;
  preferred_date: string | null;
  notes: string | null;
  status: 'pending' | 'contacted' | 'confirmed' | 'completed' | 'cancelled';
  created_at: string | null;
}

export interface HandPhotoPreset {
  id: string;
  name: string;
  image_url: string;
  tags: string[];
  crop_ratio: '1:1' | '4:5' | '3:4';
}

type NailDesignPayload = {
  name: string;
  description?: string;
  image_url: string;
  style_tags?: string[];
  color_tags?: string[];
  scene_tags?: string[];
  length?: string;
  shape?: string;
};

type SeasonalPayload = Record<string, unknown>;
type FestivalPayload = Record<string, unknown>;

async function fetchAPI(endpoint: string, options: RequestInit = {}) {
  const token = getAuthToken();
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    if ((response.status === 401 || response.status === 403) && !endpoint.startsWith('/auth/')) {
      clearAuthSession();
      redirectForAuth(endpoint);
    }
    let message = `API error: ${response.status}`;
    try {
      const body = await response.json();
      message = formatApiDetail(body?.detail) || message;
    } catch {
      // Keep the generic status message when the server does not return JSON.
    }
    throw new ApiError(response.status, endpoint, message);
  }

  return response.json();
}

export const api = {
  // Auth
  requestLoginCode: (data: { phone: string; nickname?: string; user_type?: string }) =>
    fetchAPI('/auth/request-code', { method: 'POST', body: JSON.stringify(data) }) as Promise<AuthCodeResponse>,
  login: (data: { phone: string; code: string; nickname?: string; user_type?: string }) =>
    fetchAPI('/auth/login', { method: 'POST', body: JSON.stringify(data) }) as Promise<AuthLoginResponse>,
  getMe: () => fetchAPI('/auth/me') as Promise<AuthUser>,

  // Users
  createUser: (data: { phone: string; nickname?: string }) =>
    fetchAPI('/users/', { method: 'POST', body: JSON.stringify(data) }),
  getUser: (id: number) => fetchAPI(`/users/${id}`),
  getUserByPhone: (phone: string) => fetchAPI(`/users/phone/${phone}`),

  // Hand Photos
  uploadHandPhoto: (_userId: number, data: { image_url: string }) =>
    fetchAPI('/users/me/hand-photos', { method: 'POST', body: JSON.stringify(data) }),
  getUserHandPhotos: (_userId: number) => fetchAPI('/users/me/hand-photos'),
  uploadMyHandPhoto: (data: { image_url: string }) =>
    fetchAPI('/users/me/hand-photos', { method: 'POST', body: JSON.stringify(data) }),
  getMyHandPhotos: () => fetchAPI('/users/me/hand-photos'),
  getHandPhotoPresets: () => fetchAPI('/users/me/hand-photo-presets') as Promise<HandPhotoPreset[]>,
  useHandPhotoPreset: (presetId: string) =>
    fetchAPI(`/users/me/hand-photo-presets/${presetId}/use`, { method: 'POST' }),
  updateMyHandPhoto: (photoId: number, data: { name?: string; crop_ratio?: '1:1' | '4:5' | '3:4' }) =>
    fetchAPI(`/users/me/hand-photos/${photoId}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteMyHandPhoto: (photoId: number) =>
    fetchAPI(`/users/me/hand-photos/${photoId}`, { method: 'DELETE' }),

  // Designs
  listDesigns: (params?: Record<string, string>) => {
    const query = params ? new URLSearchParams(params).toString() : '';
    return fetchAPI(query ? `/designs/?${query}` : '/designs/');
  },
  getHotDesigns: () => fetchAPI('/designs/hot'),
  getNewDesigns: () => fetchAPI('/designs/new'),
  getDesign: (id: number) => fetchAPI(`/designs/${id}`),

  // Admin - Designs CRUD
  createDesign: (data: NailDesignPayload) => fetchAPI('/designs/', { method: 'POST', body: JSON.stringify(data) }),
  updateDesign: (id: number, data: NailDesignPayload) => fetchAPI(`/designs/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteDesign: (id: number) => fetchAPI(`/designs/${id}`, { method: 'DELETE' }),
  updateDesignStatus: (id: number, status: string) =>
    fetchAPI(`/designs/${id}/status?status=${status}`, { method: 'PATCH' }),
  toggleDesignHot: (id: number, isHot: boolean) =>
    fetchAPI(`/designs/${id}/hot?is_hot=${isHot}`, { method: 'PATCH' }),
  toggleDesignNew: (id: number, isNew: boolean) =>
    fetchAPI(`/designs/${id}/new?is_new=${isNew}`, { method: 'PATCH' }),
  getStyleTags: () => fetchAPI('/designs/tags/styles'),
  getColorTags: () => fetchAPI('/designs/tags/colors'),
  getSceneTags: () => fetchAPI('/designs/tags/scenes'),

  // Try On
  createTryOn: (data: { hand_photo_id: number; nail_design_id: number }) =>
    fetchAPI('/tryon/', { method: 'POST', body: JSON.stringify(data) }) as Promise<TryOnRecord>,
  getTryOn: (id: number) => fetchAPI(`/tryon/${id}`) as Promise<TryOnRecord>,
  getTryOnProgress: (id: number) => fetchAPI(`/tryon/${id}/progress`) as Promise<TryOnProgress>,
  getUserTryOns: (_userId: number) => fetchAPI('/tryon/me/records') as Promise<TryOnRecord[]>,
  getMyTryOns: () => fetchAPI('/tryon/me/records') as Promise<TryOnRecord[]>,
  getMyCandidateTryOns: () => fetchAPI('/tryon/me/candidates') as Promise<TryOnRecord[]>,
  toggleFavorite: (tryOnId: number) =>
    fetchAPI(`/tryon/${tryOnId}/favorite`, { method: 'POST' }),
  toggleCandidate: (tryOnId: number) =>
    fetchAPI(`/tryon/${tryOnId}/candidate`, { method: 'POST' }),

  // Recommendations
  getRecommendations: (tryOnId: number) =>
    fetchAPI('/recommendations/similar', { method: 'POST', body: JSON.stringify({ try_on_id: tryOnId }) }),
  getTrending: () => fetchAPI('/recommendations/trending'),

  // Operations
  getOverview: () => fetchAPI('/operations/overview'),
  getMerchantOverview: () => fetchAPI('/operations/merchant-overview') as Promise<MerchantOverview>,
  getTodayWorkbench: () => fetchAPI('/operations/today-workbench') as Promise<TodayWorkbench>,
  getOperationsConfig: () => fetchAPI('/operations/config') as Promise<OperationsConfig>,
  updateOperationsConfig: (data: OperationsConfig) =>
    fetchAPI('/operations/config', { method: 'PUT', body: JSON.stringify(data) }) as Promise<OperationsConfig>,
  getTrends: (days = 30) => fetchAPI(`/operations/trends?days=${days}`),
  getHotCandidates: () => fetchAPI('/operations/hot-candidates'),
  getDailyReport: () => fetchAPI('/operations/daily-report'),

  // Cold Alert
  getColdDesigns: () => fetchAPI('/operations/cold-designs'),

  // Suggestions
  getSuggestions: (status?: string) => fetchAPI(`/operations/suggestions${status ? `?status=${status}` : ''}`),
  acceptSuggestion: (id: string) =>
    fetchAPI(`/operations/suggestions/${id}/accept`, { method: 'POST' }) as Promise<OperationsSuggestionActionResult>,
  rejectSuggestion: (id: string) => fetchAPI(`/operations/suggestions/${id}/reject`, { method: 'POST' }),

  // Admin Analytics
  getStyleAnalysis: (days?: number) => fetchAPI(`/operations/style-analysis?days=${days || 30}`),
  getSceneAnalysis: (days?: number) => fetchAPI(`/operations/scene-analysis?days=${days || 30}`),
  getColorAnalysis: (days?: number) => fetchAPI(`/operations/color-analysis?days=${days || 30}`),
  getFunnel: (days?: number) => fetchAPI(`/operations/funnel?days=${days || 30}`),
  getHistoricalReport: (dateStr: string) => fetchAPI(`/operations/daily-report/historical?date_str=${dateStr}`),

  // AI Agent
  getAIInsights: () => fetchAPI('/operations/ai-insights'),
  getPredictions: (days?: number) => fetchAPI(`/operations/predictions?days_ahead=${days || 7}`),
  getEmergingStyles: () => fetchAPI('/operations/emerging-styles'),
  getInventoryRecommendations: () => fetchAPI('/operations/inventory-recommendations'),
  getAnomalies: () => fetchAPI('/operations/anomalies'),
  getActionPlan: () => fetchAPI('/operations/action-plan'),
  getAssistantCapabilities: () =>
    fetchAPI('/operations/assistant/capabilities') as Promise<OperationsAssistantCapabilities>,
  getAssistantStatus: () => fetchAPI('/operations/assistant/status') as Promise<OperationsAssistantStatus>,
  chatWithOperationsAssistant: (data: { message: string; conversation_id?: string; context?: Record<string, unknown> }) =>
    fetchAPI('/operations/assistant/chat', { method: 'POST', body: JSON.stringify(data) }) as Promise<OperationsAssistantResponse>,
  applyAssistantCommand: (data: { message: string; assistant_payload: OperationsAssistantResponse }) =>
    fetchAPI('/operations/assistant/command', { method: 'POST', body: JSON.stringify(data) }) as Promise<{
      status: string;
      action: string;
      created_count?: number;
      message: string;
    }>,
  sendExternalAgentMessage: (data: { channel: string; sender?: string; message: string; context?: Record<string, unknown> }) =>
    fetchAPI('/operations/assistant/external-message', { method: 'POST', body: JSON.stringify(data) }) as Promise<OperationsAssistantExternalReply>,
  getAssistantSchedules: () => fetchAPI('/operations/assistant/schedules') as Promise<OperationsAssistantSchedules>,
  updateDailyReportSchedule: (data: { enabled: boolean; time: string; channels: string[]; prompt: string }) =>
    fetchAPI('/operations/assistant/schedules/daily-report', { method: 'PUT', body: JSON.stringify(data) }) as Promise<OperationsAssistantSchedule>,
  runDailyReportSchedule: () =>
    fetchAPI('/operations/assistant/schedules/daily-report/run', { method: 'POST' }) as Promise<{
      task: string;
      status: string;
      run_at: string;
      deliveries: OperationsAssistantExternalReply[];
    }>,
  syncAssistantSuggestions: (data: {
    source_message?: string;
    answer?: string;
    evidence?: OperationsAssistantEvidence[];
    actions: OperationsAssistantAction[];
  }) =>
    fetchAPI('/operations/assistant/suggestions', { method: 'POST', body: JSON.stringify(data) }) as Promise<OperationsSuggestion[]>,

  // Consumer Assistant
  chatWithConsumerAssistant: (data: { message: string; conversation_id?: string; context?: Record<string, unknown> }) =>
    fetchAPI('/consumer-assistant/chat', { method: 'POST', body: JSON.stringify(data) }) as Promise<ConsumerAssistantResponse>,
  getConsumerAssistantInsights: () => fetchAPI('/consumer-assistant/insights') as Promise<ConsumerAssistantInsights>,

  // Booking Intent
  createBookingIntent: (data: { try_on_record_id: number; nail_design_id: number; phone: string; preferred_date?: string; notes?: string }) =>
    fetchAPI('/operations/booking-intents', { method: 'POST', body: JSON.stringify(data) }),
  getBookingIntents: (status?: string) =>
    fetchAPI(`/operations/booking-intents${status ? `?status=${status}` : ''}`) as Promise<BookingIntent[]>,
  updateBookingIntentStatus: (id: number, status: BookingIntent['status']) =>
    fetchAPI(`/operations/booking-intents/${id}/status?status=${status}`, { method: 'PATCH' }) as Promise<BookingIntent>,

  // Seasonal/Festival Themes
  getCurrentThemes: () => fetchAPI('/seasonal/current'),
  getUpcomingThemes: (days?: number) => fetchAPI(`/seasonal/upcoming?days=${days || 30}`),
  getAllThemes: () => fetchAPI('/seasonal/all'),

  // Season Admin
  createSeason: (data: SeasonalPayload) => fetchAPI('/seasonal/seasons', { method: 'POST', body: JSON.stringify(data) }),
  updateSeason: (id: string, data: SeasonalPayload) => fetchAPI(`/seasonal/seasons/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteSeason: (id: string) => fetchAPI(`/seasonal/seasons/${id}`, { method: 'DELETE' }),

  // Festival Admin
  createFestival: (data: FestivalPayload) => fetchAPI('/seasonal/festivals', { method: 'POST', body: JSON.stringify(data) }),
  updateFestival: (id: string, data: FestivalPayload) => fetchAPI(`/seasonal/festivals/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteFestival: (id: string) => fetchAPI(`/seasonal/festivals/${id}`, { method: 'DELETE' }),
  toggleFestival: (id: string) => fetchAPI(`/seasonal/festivals/${id}/toggle`, { method: 'PATCH' }),

  // User Preferences
  getUserPreferences: (_userId: number) => fetchAPI('/preferences/me'),
  getPersonalizedRecommendations: (_userId: number) => fetchAPI('/preferences/me/recommendations'),
  getMyPreferences: () => fetchAPI('/preferences/me'),
  getMyPersonalizedRecommendations: () => fetchAPI('/preferences/me/recommendations'),
  updateSkinTone: (skinTone: string, undertone: string | undefined, _userId: number) =>
    fetchAPI(`/preferences/me/skin-tone?skin_tone=${skinTone}${undertone ? `&skin_undertone=${undertone}` : ''}`, { method: 'PUT' }),
  updateMySkinTone: (skinTone: string, undertone?: string) =>
    fetchAPI(`/preferences/me/skin-tone?skin_tone=${skinTone}${undertone ? `&skin_undertone=${undertone}` : ''}`, { method: 'PUT' }),
};
