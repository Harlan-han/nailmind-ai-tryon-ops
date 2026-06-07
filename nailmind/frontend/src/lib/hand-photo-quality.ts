export interface HandPhotoAnalysisResult {
  hand_detected: boolean;
  quality_score: number;
  recommendations: string[];
}

export interface HandPhotoQualityAssessment {
  ok: boolean;
  message: string | null;
}

const MIN_ACCEPTABLE_QUALITY_SCORE = 0.5;

export function assessHandPhotoQuality(result: HandPhotoAnalysisResult): HandPhotoQualityAssessment {
  if (!result.hand_detected) {
    return {
      ok: false,
      message: result.recommendations[0] || '未检测到手部，请上传包含手部的照片',
    };
  }

  if (result.quality_score < MIN_ACCEPTABLE_QUALITY_SCORE) {
    return {
      ok: false,
      message: '照片质量偏低，请重新拍摄一张更清晰的手部照片。',
    };
  }

  return {
    ok: true,
    message: null,
  };
}
