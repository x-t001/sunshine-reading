# Skill: Create Django Model / 创建 Django 模型

## Purpose / 目的
- Create models that are migration-safe and query-aware.
- 创建迁移安全、查询友好的 Django 模型。

## Inputs / 输入
- Entity definition / 实体定义
- Relation map / 关系图
- Query and sort patterns / 查询与排序模式

## Steps / 步骤
1. Define model fields with explicit type, nullability, default, and verbose meaning. / 定义字段类型、可空、默认值与语义。
2. Add uniqueness and index constraints based on query path. / 按查询路径补充唯一约束与索引。
3. Define relations and on_delete behavior explicitly. / 明确定义关联关系与 on_delete 行为。
4. Include standard audit fields and optional soft-delete field. / 包含标准审计字段与可选软删除字段。
5. Review migration risk: data backfill, lock impact, rollback strategy. / 评审迁移风险：数据回填、锁影响、回滚策略。

## Output / 产出
- Model definition checklist ready for implementation and migration.
- 可实施且可迁移的模型定义清单。

## Checklist / 检查清单
- [ ] Field semantics are explicit / 字段语义明确
- [ ] Index/unique constraints are justified / 索引与唯一约束有依据
- [ ] Relation behavior is explicit / 关系行为明确
- [ ] Migration risk reviewed / 迁移风险已评审
