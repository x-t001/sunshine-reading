# Skill: Debug Backend / 后端 Bug 排查

## Purpose / 目的
- Locate backend failures across validation, permission, service logic, and data layer.
- 覆盖校验、权限、服务逻辑、数据层的后端故障定位。

## Inputs / 输入
- Error log and request_id / 错误日志与 request_id
- Failing endpoint / 失败接口
- Suspected recent change / 可疑近期改动

## Steps / 步骤
1. Reproduce failure using original request payload and actor role. / 使用原始请求与角色复现失败。
2. Trace flow: view -> serializer -> service -> model/query. / 追踪链路：view -> serializer -> service -> model/query。
3. Check permission matrix and input validation before business logic. / 在业务逻辑前检查权限矩阵与输入校验。
4. Verify DB constraints/index impacts if issue is performance or integrity related. / 若涉及性能或完整性，检查数据库约束与索引影响。
5. Implement minimal fix, then verify with success/fail/forbidden/not-found tests. / 最小修复后用成功/失败/无权限/不存在用例验证。

## Output / 产出
- Backend bug diagnosis and fix verification checklist.
- 后端缺陷诊断与修复验证清单。

## Checklist / 检查清单
- [ ] Failure boundary identified / 失败边界已定位
- [ ] Permission and validation checked / 权限与校验已检查
- [ ] Data-layer impact reviewed / 数据层影响已评估
- [ ] Regression tests executed / 回归测试已执行
