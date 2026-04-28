# Skill: Create Reading Feature / 创建阅读器功能

## Purpose / 目的
- Build end-to-end reader features with stable UX and contract-driven backend integration.
- 构建端到端阅读器功能，保持体验稳定并遵循接口契约。

## Inputs / 输入
- Reader scenario / 阅读场景
- Feature acceptance criteria / 功能验收标准
- API and data dependencies / API 与数据依赖

## Steps / 步骤
1. Define reader flow: enter chapter -> render content -> interaction -> progress save. / 定义阅读流程：进入章节 -> 渲染内容 -> 交互 -> 保存进度。
2. Define feature states: loading chapter, missing chapter, paywall/permission denied, retry. / 定义状态：章节加载、章节不存在、权限/付费受限、重试。
3. Define API calls and caching policy for chapter content and reading progress. / 定义章节内容与阅读进度的 API 调用与缓存策略。
4. Define UX constraints: font settings, theme switch, chapter navigation, scroll recovery. / 定义体验约束：字体设置、主题切换、章节导航、滚动恢复。
5. Verify with scenario tests: first read, resume reading, cross-device sync failure fallback. / 用场景测试验证：首次阅读、断点续读、跨端同步失败兜底。

## Output / 产出
- Reading feature implementation checklist with scenario coverage.
- 覆盖关键场景的阅读器功能实现清单。

## Checklist / 检查清单
- [ ] Reader flow complete / 阅读流程完整
- [ ] State handling complete / 状态处理完整
- [ ] API + cache strategy clear / API 与缓存策略清晰
- [ ] Key reader scenarios verified / 核心阅读场景已验证
