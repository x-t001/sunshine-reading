import type { VideoAgentWorkflow } from "@/types/video-project";

type VideoAgentWorkflowPanelProps = {
  workflow: VideoAgentWorkflow;
};

const workflowStatusLabels: Record<string, string> = {
  succeeded: "已完成",
  passed: "通过",
  needs_review: "需复核",
  failed: "失败",
  stale: "已失效",
};

const visualRelationshipLabels: Record<string, string> = {
  opening: "建立视觉基准",
  continuous_action: "连续动作",
  same_location_subject_change: "同场景切换主体",
  location_transition: "地点转场",
  look_transition: "形象转场",
};

const shotScaleLabels: Record<string, string> = {
  establishing_wide: "建立全景",
  wide: "全景",
  medium: "中景",
  medium_close_up: "近景",
  close_up: "特写",
  extreme_close_up: "大特写",
};

export default function VideoAgentWorkflowPanel({ workflow }: VideoAgentWorkflowPanelProps) {
  const stages = workflow.stages || [];
  const productionPlan = workflow.production_plan || {};
  const visualWorldModel = workflow.visual_world_model || {};
  const qualityReport = workflow.quality_report || {};
  const issues = qualityReport.issues || [];
  const characters = productionPlan.characters || [];
  const characterLooks = productionPlan.character_looks || [];
  const locations = productionPlan.locations || [];
  const props = productionPlan.props || [];
  const dialogueUnits = productionPlan.dialogue_units || [];
  const continuityRules = productionPlan.continuity_rules || [];
  const characterModels = visualWorldModel.character_models || [];
  const sceneModels = visualWorldModel.scene_models || [];
  const propModels = visualWorldModel.prop_models || [];
  const styleBible = visualWorldModel.style_bible || {};
  const visualContinuityPlan = visualWorldModel.visual_continuity_plan || {};
  const continuityGroups = visualContinuityPlan.continuity_groups || [];
  const continuityShots = visualContinuityPlan.shots || [];
  const physicalRules = visualWorldModel.physical_rules || [];
  const logicRules = visualWorldModel.logic_rules || [];
  const framePolicy = visualWorldModel.frame_policy || {};
  const characterById = new Map(characters.map((character) => [character.id, character]));
  const locationById = new Map(locations.map((location) => [location.id, location]));
  const needsReview = workflow.stale || qualityReport.status === "needs_review" || qualityReport.status === "stale";

  return (
    <section className="rounded-lg bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-zinc-900">导演工作流</h2>
          <p className="mt-1 text-xs text-zinc-500">
            版本 {workflow.version || "-"}
            {workflow.generated_at ? ` · ${new Date(workflow.generated_at).toLocaleString("zh-CN")}` : ""}
          </p>
        </div>
        <div className="flex items-baseline gap-2">
          <span className={needsReview ? "text-sm font-medium text-amber-700" : "text-sm font-medium text-emerald-700"}>
            {workflow.stale ? "设定已失效" : workflowStatusLabels[qualityReport.status || ""] || "待质检"}
          </span>
          {typeof qualityReport.score === "number" ? (
            <span className="text-2xl font-semibold text-zinc-900">{qualityReport.score}</span>
          ) : null}
        </div>
      </div>

      <div className="mt-4 grid gap-4 border-t border-zinc-100 pt-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {stages.map((stage, index) => (
          <div className="border-l-2 border-emerald-500 pl-3" key={stage.id}>
            <p className="text-xs text-zinc-500">阶段 {index + 1}</p>
            <p className="mt-1 text-sm font-medium text-zinc-900">{stage.label}</p>
            <p className="mt-1 text-xs text-zinc-500">
              {workflowStatusLabels[stage.status] || stage.status} · {stage.executor === "local" ? "本地" : stage.model}
            </p>
            {stage.subagents?.length ? (
              <p className="mt-2 text-xs leading-5 text-zinc-600">
                {stage.subagents.map((subagent) => subagent.label).join("、")}
              </p>
            ) : null}
            {stage.id === "schema_repair" ? (
              <p className="mt-2 text-xs leading-5 text-zinc-600">
                首次制作设定未通过契约校验，已执行一次有界修复。
              </p>
            ) : null}
            {stage.id === "dialogue_repair" ? (
              <p className="mt-2 text-xs leading-5 text-zinc-600">
                台词正文超出单镜朗读预算，已在保留剧情含义的前提下执行一次精编。
              </p>
            ) : null}
            {stage.id === "shot_director" && Number(stage.metrics?.batch_count || 0) > 0 ? (
              <p className="mt-2 text-xs leading-5 text-zinc-600">
                按每批最多 {Number(stage.metrics?.batch_size || 0)} 镜串行生成，共完成{" "}
                {Number(stage.metrics?.batch_count || 0)} 批；批次定向修复{" "}
                {Number(stage.metrics?.repair_call_count || 0)} 次。
              </p>
            ) : null}
            {stage.id === "visual_modeler" ? (
              <p className="mt-2 text-xs leading-5 text-zinc-600">
                固定 {Number(stage.metrics?.character_model_count || 0)} 个人物形象模型、{" "}
                {Number(stage.metrics?.scene_model_count || 0)} 个场景空间模型、{" "}
                {Number(stage.metrics?.prop_model_count || 0)} 个道具模型；成片统一为{" "}
                {Number(stage.metrics?.target_fps || 0)} FPS。
              </p>
            ) : null}
            {stage.id === "visual_sequence_planner" ? (
              <p className="mt-2 text-xs leading-5 text-zinc-600">
                划分 {Number(stage.metrics?.continuity_group_count || 0)} 个连续镜头组，建立{" "}
                {Number(stage.metrics?.linked_shot_count || 0)} 条相邻镜头继承关系。
              </p>
            ) : null}
            {stage.id === "schema_guard" && (
              Number(stage.metrics?.removed_out_of_range_dialogue_units || 0)
              + Number(stage.metrics?.rewritten_beat_dialogue_references || 0)
              + Number(stage.metrics?.normalized_dialogue_timing_beats || 0)
              + Number(stage.metrics?.normalized_dialogue_timing_units || 0)
              + Number(stage.metrics?.generated_missing_character_looks || 0)
              + Number(stage.metrics?.removed_unknown_look_references || 0)
              + Number(stage.metrics?.rewritten_beat_look_references || 0)
            ) > 0 ? (
              <p className="mt-2 break-words text-xs leading-5 text-zinc-600">
                台词：清理 {Number(stage.metrics?.removed_out_of_range_dialogue_units || 0)} 个越界单元，
                重建 {Number(stage.metrics?.rewritten_beat_dialogue_references || 0)} 个引用，归一化{" "}
                {Number(stage.metrics?.normalized_dialogue_timing_beats || 0)} 个节拍、{" "}
                {Number(stage.metrics?.normalized_dialogue_timing_units || 0)} 个台词单元的时长。形象：补齐{" "}
                {Number(stage.metrics?.generated_missing_character_looks || 0)} 个版本，清理{" "}
                {Number(stage.metrics?.removed_unknown_look_references || 0)} 个无定义引用，重建{" "}
                {Number(stage.metrics?.rewritten_beat_look_references || 0)} 个节拍引用。
              </p>
            ) : null}
          </div>
        ))}
      </div>

      <div className="mt-5 grid gap-5 border-t border-zinc-100 pt-4 lg:grid-cols-2">
        <div>
          <h3 className="text-sm font-semibold text-zinc-900">剧情与视觉基线</h3>
          {productionPlan.logline ? <p className="mt-2 text-sm leading-6 text-zinc-700">{productionPlan.logline}</p> : null}
          <dl className="mt-3 space-y-2 text-xs">
            {productionPlan.theme ? (
              <div><dt className="text-zinc-500">主题</dt><dd className="mt-1 text-zinc-700">{productionPlan.theme}</dd></div>
            ) : null}
            {productionPlan.visual_style ? (
              <div><dt className="text-zinc-500">视觉风格</dt><dd className="mt-1 text-zinc-700">{productionPlan.visual_style}</dd></div>
            ) : null}
            {styleBible.canonical_prompt ? (
              <div><dt className="text-zinc-500">规范视觉锚点</dt><dd className="mt-1 text-zinc-700">{styleBible.canonical_prompt}</dd></div>
            ) : null}
          </dl>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-zinc-900">制作设定规模</h3>
          <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-2 text-xs sm:grid-cols-4">
            <div><dt className="text-zinc-500">角色</dt><dd className="mt-1 font-medium text-zinc-900">{characters.length}</dd></div>
            <div><dt className="text-zinc-500">形象版本</dt><dd className="mt-1 font-medium text-zinc-900">{characterLooks.length}</dd></div>
            <div><dt className="text-zinc-500">场景</dt><dd className="mt-1 font-medium text-zinc-900">{locations.length}</dd></div>
            <div><dt className="text-zinc-500">道具</dt><dd className="mt-1 font-medium text-zinc-900">{props.length}</dd></div>
          </dl>
          {continuityRules.length ? (
            <div className="mt-3 space-y-1 text-xs leading-5 text-zinc-700">
              {continuityRules.map((rule) => <p key={rule}>· {rule}</p>)}
            </div>
          ) : null}
          {characterModels.length || sceneModels.length ? (
            <p className="mt-3 text-xs text-zinc-500">
              人物模型 {characterModels.length} · 场景空间模型 {sceneModels.length} · 道具模型 {propModels.length}
              {continuityGroups.length ? ` · 连续镜头组 ${continuityGroups.length}` : ""}
              {framePolicy.target_fps ? ` · 固定 ${framePolicy.target_fps} FPS 成片` : ""}
            </p>
          ) : null}
        </div>
      </div>

      {physicalRules.length || logicRules.length ? (
        <div className="mt-5 grid gap-6 border-t border-zinc-100 pt-4 lg:grid-cols-2">
          <div>
            <h3 className="text-sm font-semibold text-zinc-900">物理与防穿模约束</h3>
            <div className="mt-2 space-y-1 text-xs leading-5 text-zinc-700">
              {physicalRules.map((rule) => <p key={rule}>· {rule}</p>)}
            </div>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-zinc-900">剧情状态约束</h3>
            <div className="mt-2 space-y-1 text-xs leading-5 text-zinc-700">
              {logicRules.map((rule) => <p key={rule}>· {rule}</p>)}
            </div>
          </div>
        </div>
      ) : null}

      {continuityGroups.length ? (
        <div className="mt-5 border-t border-zinc-100 pt-4">
          <h3 className="text-sm font-semibold text-zinc-900">视觉连续性计划</h3>
          <p className="mt-1 text-xs leading-5 text-zinc-500">
            同组镜头原样复用视觉圣经和规范资产锚点，只允许剧情动作、景别与机位发生计划内变化。
          </p>
          <div className="mt-2 divide-y divide-zinc-100 text-xs">
            {continuityGroups.map((group) => {
              const groupShots = continuityShots.filter((shot) => shot.continuity_group_id === group.id);
              const location = group.location_id ? locationById.get(group.location_id) : undefined;
              return (
                <div className="grid gap-2 py-3 lg:grid-cols-[160px_220px_minmax(0,1fr)]" key={group.id}>
                  <div>
                    <p className="font-medium text-zinc-900">
                      连续组 {group.id.replace("sequence_", "")}
                    </p>
                    <p className="mt-1 text-zinc-500">分镜 {group.scene_nos.join("、")}</p>
                  </div>
                  <div>
                    <p className="text-zinc-700">{location?.name || group.location_id || "未命名场景"}</p>
                    <p className="mt-1 text-zinc-500">
                      人物模型 {group.character_model_ids?.length || 0}
                      {group.scene_model_id ? " · 场景模型已锁定" : ""}
                    </p>
                  </div>
                  <div className="space-y-1 leading-5 text-zinc-700">
                    {groupShots.map((shot) => (
                      <p key={shot.scene_no}>
                        镜头 {shot.scene_no} · {visualRelationshipLabels[shot.relationship_to_previous] || shot.relationship_to_previous}
                        {shot.composition?.shot_scale
                          ? ` · ${shotScaleLabels[shot.composition.shot_scale] || shot.composition.shot_scale}`
                          : ""}
                        {shot.inherits_from_scene_no ? ` · 承接镜头 ${shot.inherits_from_scene_no}` : ""}
                      </p>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}

      {characters.length || characterLooks.length ? (
        <div className="mt-5 border-t border-zinc-100 pt-4">
          <h3 className="text-sm font-semibold text-zinc-900">角色与形象拆解</h3>
          <div className="mt-2 grid gap-x-6 lg:grid-cols-2">
            {characters.map((character) => {
              const looks = characterLooks.filter((look) => look.character_id === character.id);
              return (
                <div className="border-b border-zinc-100 py-3" key={character.id}>
                  <p className="text-sm font-medium text-zinc-900">
                    {character.name}{character.story_role ? ` · ${character.story_role}` : ""}
                  </p>
                  {character.identity ? <p className="mt-1 text-xs text-zinc-500">{character.identity}</p> : null}
                  <p className="mt-2 text-xs leading-5 text-zinc-700">{character.appearance}</p>
                  {character.wardrobe ? <p className="mt-1 text-xs leading-5 text-zinc-700">{character.wardrobe}</p> : null}
                  {looks.map((look) => (
                    <div className="mt-2 border-l-2 border-zinc-200 pl-3 text-xs leading-5 text-zinc-700" key={look.id}>
                      <p className="font-medium text-zinc-900">{look.label}</p>
                      <p>{look.wardrobe}；{look.hair_makeup}</p>
                      <p>{look.signature_features}；{look.color_palette}</p>
                      {characterModels.find((model) => model.look_id === look.id) ? (
                        <p className="mt-1 text-zinc-500">
                          模型 {characterModels.find((model) => model.look_id === look.id)?.id} · 身份、体态、面容与服装已锁定
                        </p>
                      ) : null}
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      ) : null}

      {locations.length || props.length ? (
        <div className="mt-5 grid gap-6 border-t border-zinc-100 pt-4 lg:grid-cols-2">
          <div>
            <h3 className="text-sm font-semibold text-zinc-900">场景拆解</h3>
            <div className="mt-2 space-y-3 text-xs leading-5 text-zinc-700">
              {locations.map((location) => (
                <div className="border-b border-zinc-100 pb-3" key={location.id}>
                  <p className="font-medium text-zinc-900">{location.name}</p>
                  {location.geography ? <p className="mt-1">{location.geography}</p> : null}
                  <p>{location.visual_anchor}</p>
                  <p>{[location.time_of_day, location.weather, location.lighting].filter(Boolean).join("；")}</p>
                  {sceneModels.find((model) => model.location_id === location.id) ? (
                    <>
                      <p className="mt-1 text-zinc-500">
                        空间模型 {sceneModels.find((model) => model.location_id === location.id)?.id}
                      </p>
                      <p>{sceneModels.find((model) => model.location_id === location.id)?.camera_axis_rule}</p>
                    </>
                  ) : null}
                </div>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-zinc-900">道具拆解</h3>
            <div className="mt-2 space-y-3 text-xs leading-5 text-zinc-700">
              {props.map((prop) => (
                <div className="border-b border-zinc-100 pb-3" key={prop.id}>
                  <p className="font-medium text-zinc-900">
                    {prop.name}
                    {prop.owner_character_id && characterById.get(prop.owner_character_id)
                      ? ` · ${characterById.get(prop.owner_character_id)?.name}`
                      : ""}
                  </p>
                  <p className="mt-1">{prop.visual_anchor}</p>
                  <p>初始状态：{prop.initial_state}</p>
                  <p>连续性：{prop.continuity_rule}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : null}

      {dialogueUnits.length ? (
        <div className="mt-5 border-t border-zinc-100 pt-4">
          <h3 className="text-sm font-semibold text-zinc-900">台词与配音拆解</h3>
          <div className="mt-2 divide-y divide-zinc-100 text-xs">
            {dialogueUnits.map((unit) => (
              <div className="grid gap-1 py-3 sm:grid-cols-[64px_96px_minmax(0,1fr)_120px] sm:items-start sm:gap-3" key={unit.id}>
                <p className="text-zinc-500">镜头 {unit.beat_no}</p>
                <p className="font-medium text-zinc-900">
                  {unit.speaker_id === "narrator" ? "旁白" : characterById.get(unit.speaker_id)?.name || unit.speaker_id}
                </p>
                <p className="break-words leading-5 text-zinc-700">{unit.text}</p>
                <p className="text-zinc-500">{unit.emotion} · {unit.target_duration_ms / 1000} 秒</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {issues.length > 0 ? (
        <div className="mt-5 border-t border-zinc-100 pt-4">
          <h3 className="text-sm font-semibold text-zinc-900">质量问题</h3>
          <ul className="mt-2 space-y-2 text-xs">
            {issues.map((issue, index) => (
              <li className={issue.severity === "error" ? "text-red-700" : "text-amber-700"} key={`${issue.code}-${issue.scene_no || 0}-${index}`}>
                {issue.scene_no ? `分镜 ${issue.scene_no} · ` : ""}{issue.message}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
