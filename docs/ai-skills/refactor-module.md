# Skill: Refactor Module / 模块重构

## Purpose / 目的
- Refactor a module safely while preserving behavior and interfaces.
- 在保持行为与接口兼容的前提下安全重构模块。

## Inputs / 输入
- Refactor objective / 重构目标
- Current module boundaries / 当前模块边界
- Compatibility constraints / 兼容性约束

## Steps / 步骤
1. Define what must stay behavior-compatible. / 明确定义必须保持兼容的行为。
2. Split refactor into small, reviewable steps. / 将重构拆分为小步、可评审变更。
3. Preserve public interfaces until migration is complete. / 在迁移完成前保持公共接口稳定。
4. Add/adjust tests before risky structural changes. / 高风险结构调整前先补充或调整测试。
5. Remove obsolete paths only after verification. / 验证通过后再移除旧路径。

## Output / 产出
- Controlled refactor plan with safety checkpoints.
- 带安全检查点的可控重构方案。

## Checklist / 检查清单
- [ ] Compatibility constraints documented / 兼容性约束已文档化
- [ ] Steps are incremental / 步骤可增量执行
- [ ] Tests protect behavior / 测试可保护行为
- [ ] Old paths removed safely / 旧路径已安全清理
