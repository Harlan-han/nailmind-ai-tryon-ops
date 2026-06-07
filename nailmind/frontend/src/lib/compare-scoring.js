const WARM_COLORS = new Set(['金色', '香槟色', '裸色', '米色', '棕色', '橘色', '珊瑚', '红色', '酒红']);
const COOL_COLORS = new Set(['银色', '蓝色', '紫色', '粉色', '玫红', '灰色', '黑色']);
const NEUTRAL_COLORS = new Set(['白色', '奶油白', '透明', '裸色']);

function clamp(value, min = 0, max = 1) {
  return Math.max(min, Math.min(max, value));
}

function roundScore(value) {
  return Number(clamp(value).toFixed(2));
}

function tags(value) {
  return Array.isArray(value) ? value.filter(Boolean) : [];
}

function preferenceMap(items) {
  const map = new Map();
  for (const item of Array.isArray(items) ? items : []) {
    if (item?.name) {
      map.set(item.name, typeof item.score === 'number' ? item.score : 1);
    }
  }
  return map;
}

function preferenceFit(designTags, preferences, baseScore) {
  const values = tags(designTags);
  if (values.length === 0) return baseScore;
  if (preferences.size === 0) return baseScore + Math.min(values.length, 3) * 0.025;

  const matchedScore = values.reduce((total, tag) => total + (preferences.get(tag) || 0), 0);
  return baseScore + Math.min(0.28, matchedScore * 0.14);
}

function skinToneFit(design, profile) {
  const colors = tags(design?.color_tags);
  if (colors.length === 0) return 0.7;

  const undertone = profile?.skin_undertone;
  const skinTone = profile?.skin_tone;
  let score = 0.64;

  if (undertone === 'warm') {
    score += colors.some((color) => WARM_COLORS.has(color)) ? 0.16 : 0;
  } else if (undertone === 'cool') {
    score += colors.some((color) => COOL_COLORS.has(color)) ? 0.16 : 0;
  } else if (undertone === 'neutral') {
    score += colors.some((color) => NEUTRAL_COLORS.has(color)) ? 0.14 : 0.08;
  } else {
    score += colors.some((color) => NEUTRAL_COLORS.has(color)) ? 0.08 : 0.04;
  }

  if (['fair', 'light'].includes(skinTone)) {
    score += colors.some((color) => ['粉色', '裸色', '白色', '奶油白', '银色'].includes(color)) ? 0.08 : 0;
  } else if (['medium', 'tan'].includes(skinTone)) {
    score += colors.some((color) => ['裸色', '红色', '酒红', '金色', '棕色'].includes(color)) ? 0.08 : 0;
  } else if (skinTone === 'dark') {
    score += colors.some((color) => ['金色', '银色', '红色', '酒红', '白色', '黑色'].includes(color)) ? 0.08 : 0;
  }

  score += Math.min(colors.length, 3) * 0.015;
  return score;
}

function engagementSignal(design) {
  const tryOns = Math.max(0, Number(design?.try_on_count || 0));
  const favorites = Math.max(0, Number(design?.favorite_count || 0));
  return Math.min(0.1, Math.log1p(tryOns) * 0.018 + Math.log1p(favorites) * 0.014);
}

function scoreCandidateDesign(design, profile = {}) {
  const styleFit = preferenceFit(tags(design?.style_tags), preferenceMap(profile?.preferred_styles), 0.62);
  const occasionFit = preferenceFit(tags(design?.scene_tags), preferenceMap(profile?.preferred_scenes), 0.62);
  const colorPreferenceFit = preferenceFit(tags(design?.color_tags), preferenceMap(profile?.preferred_colors), 0.62);
  const skinToneMatch = skinToneFit(design, profile);
  const engagement = engagementSignal(design);
  const overall = skinToneMatch * 0.32 + styleFit * 0.3 + occasionFit * 0.22 + colorPreferenceFit * 0.08 + engagement;

  return {
    skin_tone_match: roundScore(skinToneMatch),
    style_fit: roundScore(styleFit),
    occasion_fit: roundScore(occasionFit),
    overall: roundScore(overall),
  };
}

module.exports = {
  scoreCandidateDesign,
};
