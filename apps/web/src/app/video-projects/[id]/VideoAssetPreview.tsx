"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import { downloadVideoAsset } from "@/lib/api/video-projects";
import type {
  VideoAsset,
  VideoAudioReviewDecision,
  VideoVisualReviewDecision,
  VideoVisualReviewIssueCode,
} from "@/types/video-project";

const visualIssueOptions: Array<{ value: VideoVisualReviewIssueCode; label: string }> = [
  { value: "identity_drift", label: "人物身份漂移" },
  { value: "wardrobe_drift", label: "服装或形象变化" },
  { value: "scene_drift", label: "场景或光线不一致" },
  { value: "prop_state_error", label: "道具或状态错误" },
  { value: "anatomy_error", label: "肢体结构异常" },
  { value: "collision_or_clipping", label: "穿模或接触错误" },
  { value: "motion_or_physics_error", label: "运动不符合常理" },
  { value: "continuity_break", label: "前后镜头不连贯" },
  { value: "composition_error", label: "构图或主体错误" },
  { value: "other", label: "其他画面问题" },
];

const visualIssueLabels = Object.fromEntries(
  visualIssueOptions.map((item) => [item.value, item.label]),
) as Record<VideoVisualReviewIssueCode, string>;

type VideoAssetPreviewProps = {
  asset: VideoAsset;
  sceneNo?: number;
  reviewingAudio?: boolean;
  reviewingVisual?: boolean;
  onAudioReview?: (asset: VideoAsset, decision: VideoAudioReviewDecision) => void;
  onVisualReview?: (
    asset: VideoAsset,
    decision: VideoVisualReviewDecision,
    issueCodes?: VideoVisualReviewIssueCode[],
  ) => void;
};

export default function VideoAssetPreview({
  asset,
  sceneNo,
  reviewingAudio = false,
  reviewingVisual = false,
  onAudioReview,
  onVisualReview,
}: VideoAssetPreviewProps) {
  const [visualIssueCode, setVisualIssueCode] = useState<VideoVisualReviewIssueCode>("identity_drift");
  const assetVersion = `${asset.id}:${asset.updated_at}`;
  const [preview, setPreview] = useState<{
    assetVersion: string;
    objectUrl: string | null;
    failed: boolean;
  }>({ assetVersion: "", objectUrl: null, failed: false });

  useEffect(() => {
    let active = true;
    let nextObjectUrl: string | null = null;

    void downloadVideoAsset(asset.id, asset.file_name)
      .then((file) => {
        nextObjectUrl = window.URL.createObjectURL(file.blob);
        if (active) {
          setPreview({ assetVersion, objectUrl: nextObjectUrl, failed: false });
        } else {
          window.URL.revokeObjectURL(nextObjectUrl);
        }
      })
      .catch(() => {
        if (active) {
          setPreview({ assetVersion, objectUrl: null, failed: true });
        }
      });

    return () => {
      active = false;
      if (nextObjectUrl) {
        window.URL.revokeObjectURL(nextObjectUrl);
      }
    };
  }, [asset.file_name, asset.id, asset.updated_at, assetVersion]);

  const objectUrl = preview.assetVersion === assetVersion ? preview.objectUrl : null;
  const failed = preview.assetVersion === assetVersion && preview.failed;

  if (failed) {
    return <p className="text-xs text-amber-700">预览加载失败，可直接下载素材。</p>;
  }

  const isVideo = asset.asset_type === "video" || asset.asset_type === "final_video";
  const mediaWidth = asset.asset_type === "final_video" ? "w-44 sm:w-56" : "w-28 sm:w-36";

  if (!objectUrl) {
    return asset.asset_type === "image" || isVideo ? (
      <div className={`aspect-[9/16] animate-pulse rounded-md bg-zinc-100 ${mediaWidth}`} />
    ) : (
      <div className="h-10 w-full max-w-sm animate-pulse rounded-md bg-zinc-100" />
    );
  }

  if (asset.asset_type === "image" || isVideo) {
    const media = asset.asset_type === "image" ? (
      <Image
        className="aspect-[9/16] h-auto w-28 rounded-md border border-zinc-200 object-cover sm:w-36"
        src={objectUrl}
        alt={`分镜 ${sceneNo} 画面`}
        width={144}
        height={256}
        unoptimized
      />
    ) : (
      <video
        className={`aspect-[9/16] h-auto rounded-md border border-zinc-200 bg-black object-cover ${mediaWidth}`}
        controls
        playsInline
        preload="metadata"
        src={objectUrl}
      />
    );
    if (asset.asset_type === "final_video") {
      return media;
    }

    const visualReview = asset.metadata.visual_review;
    const reviewStatus = visualReview?.status || "pending";
    const issueLabels = (visualReview?.issue_codes || [])
      .map((issueCode) => visualIssueLabels[issueCode])
      .filter(Boolean)
      .join("、");
    const reviewTone = reviewStatus === "passed"
      ? "text-emerald-700"
      : reviewStatus === "rejected"
        ? "text-red-700"
        : "text-amber-700";
    const reviewLabel = reviewStatus === "passed"
      ? "人工视觉复核已通过，可进入成片。"
      : reviewStatus === "rejected"
        ? `已标记需要重拍${issueLabels ? `：${issueLabels}` : "。"}`
        : "待人工视觉复核，尚不能进入成片。";

    return (
      <div className="w-full max-w-sm space-y-2">
        {media}
        <p className={`text-xs leading-5 ${reviewTone}`}>{reviewLabel}</p>
        {reviewStatus !== "passed" && visualReview?.required_checks?.length ? (
          <p className="text-xs leading-5 text-zinc-500">
            检查：{visualReview.required_checks.join("、")}
          </p>
        ) : null}
        {onVisualReview ? (
          <div className="flex flex-wrap items-center gap-2">
            <button
              className="rounded-md border border-emerald-300 px-2.5 py-1.5 text-xs font-medium text-emerald-700 disabled:border-zinc-200 disabled:text-zinc-400"
              type="button"
              disabled={reviewingVisual || reviewStatus === "passed"}
              onClick={() => onVisualReview(asset, "approved", [])}
            >
              {reviewingVisual ? "处理中..." : "画面通过"}
            </button>
            <select
              className="max-w-40 rounded-md border border-zinc-300 bg-white px-2 py-1.5 text-xs text-zinc-700 disabled:text-zinc-400"
              aria-label="选择画面问题"
              value={visualIssueCode}
              disabled={reviewingVisual}
              onChange={(event) => setVisualIssueCode(event.target.value as VideoVisualReviewIssueCode)}
            >
              {visualIssueOptions.map((option) => (
                <option value={option.value} key={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <button
              className="rounded-md border border-red-300 px-2.5 py-1.5 text-xs font-medium text-red-700 disabled:border-zinc-200 disabled:text-zinc-400"
              type="button"
              disabled={reviewingVisual || reviewStatus === "rejected"}
              onClick={() => onVisualReview(asset, "rejected", [visualIssueCode])}
            >
              需要重拍
            </button>
          </div>
        ) : null}
      </div>
    );
  }

  const audioQuality = asset.metadata.audio_quality;
  const qualityMetrics = audioQuality?.metrics;
  const qualityDetails = [
    typeof qualityMetrics?.duration_seconds === "number" ? `${qualityMetrics.duration_seconds.toFixed(1)} 秒` : "",
    typeof qualityMetrics?.rms_dbfs === "number" ? `RMS ${qualityMetrics.rms_dbfs.toFixed(1)} dBFS` : "",
    typeof qualityMetrics?.silence_ratio === "number" ? `静音 ${(qualityMetrics.silence_ratio * 100).toFixed(0)}%` : "",
  ].filter(Boolean).join(" · ");
  const qualityTone = !audioQuality
    ? "text-amber-700"
    : audioQuality.status === "passed"
      ? audioQuality.issues.length > 0
        ? "text-amber-700"
        : "text-emerald-700"
      : "text-red-700";
  const qualityLabel = !audioQuality
    ? "未执行音频质检，重新生成后才能进入成片。"
    : audioQuality.status === "passed"
      ? `音频质检通过${qualityDetails ? ` · ${qualityDetails}` : ""}`
      : audioQuality.issues[0]?.message || "音频质检未通过，请重新生成。";
  const speechQuality = asset.metadata.speech_quality;
  const audioReview = asset.metadata.audio_review;
  const speechTone = audioReview?.status === "rejected"
    ? "text-red-700"
    : audioReview?.status === "approved" || speechQuality?.status === "passed"
      ? "text-emerald-700"
      : "text-amber-700";
  const speechLabel = audioReview?.status === "rejected"
    ? "人工试听已标记异常，请重新生成旁白。"
    : audioReview?.status === "approved"
      ? "人工试听已确认清晰。"
      : speechQuality?.status === "passed"
        ? `ASR 语义一致性通过${typeof speechQuality.similarity === "number" ? ` · ${(speechQuality.similarity * 100).toFixed(0)}%` : ""}`
        : speechQuality?.issues[0]?.message || "旁白尚未完成语义确认，请人工试听。";

  return (
    <div className="w-full max-w-sm space-y-1.5">
      <audio className="h-10 w-full" controls preload="metadata" src={objectUrl} />
      <p className={`text-xs leading-5 ${qualityTone}`}>{qualityLabel}</p>
      <p className={`text-xs leading-5 ${speechTone}`}>{speechLabel}</p>
      {speechQuality?.transcript ? (
        <p className="break-words text-xs leading-5 text-zinc-500">ASR 转写：{speechQuality.transcript}</p>
      ) : null}
      {onAudioReview ? (
        <div className="flex flex-wrap gap-2 pt-1">
          <button
            className="rounded-md border border-emerald-300 px-2.5 py-1.5 text-xs font-medium text-emerald-700 disabled:border-zinc-200 disabled:text-zinc-400"
            type="button"
            disabled={reviewingAudio || audioQuality?.status !== "passed" || audioReview?.status === "approved"}
            onClick={() => onAudioReview(asset, "approved")}
          >
            {reviewingAudio ? "处理中..." : "确认清晰"}
          </button>
          <button
            className="rounded-md border border-red-300 px-2.5 py-1.5 text-xs font-medium text-red-700 disabled:border-zinc-200 disabled:text-zinc-400"
            type="button"
            disabled={reviewingAudio || audioReview?.status === "rejected"}
            onClick={() => onAudioReview(asset, "rejected")}
          >
            标记异常
          </button>
        </div>
      ) : null}
    </div>
  );
}
