# Skill: Create Frontend Page / 创建前端页面

## Purpose / 目的
- Build a page in a predictable, testable flow for reading platform UI.
- 以可预测、可验证流程创建阅读平台页面。

## Inputs / 输入
- Route and user role / 路由与用户角色
- Page objective and acceptance criteria / 页面目标与验收标准
- Required APIs / 所需 API

## Steps / 步骤
1. Define page contract: route, role guard, and required API responses. / 定义页面契约：路由、角色守卫、所需响应。
2. Split UI into `page` + `feature` + `shared component` with clear responsibilities. / 按 `page` + `feature` + `shared` 分层拆分职责。
3. Define state machine: loading, empty, success, error, forbidden. / 定义状态机：加载、空态、成功、错误、无权限。
4. Bind API fields to typed view model and handle fallback values. / 将 API 字段映射到类型化视图模型并定义兜底值。
5. Verify accessibility and responsive behavior before completion. / 完成前验证可访问性与响应式行为。

## Output / 产出
- Executable page implementation checklist.
- 可执行的页面实现清单。

## Checklist / 检查清单
- [ ] Route and guard are defined / 路由与守卫已定义
- [ ] Layering is clean / 分层清晰
- [ ] All states handled / 状态完整
- [ ] A11y and responsive verified / 可访问性与响应式已验证
