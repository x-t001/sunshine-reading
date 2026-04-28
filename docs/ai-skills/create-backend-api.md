# Skill: Create Backend API / 创建后端 API

## Purpose / 目的
- Build backend APIs that strictly follow unified response and permission rules.
- 构建严格遵循统一响应与权限规则的后端 API。

## Inputs / 输入
- Endpoint purpose / 接口目的
- Request and response schema / 请求与响应结构
- Permission requirements / 权限要求

## Steps / 步骤
1. Define endpoint contract: path, method, version, role permissions. / 定义接口契约：路径、方法、版本、角色权限。
2. Implement request validation rules (type/range/required/format). / 实现请求校验规则（类型/范围/必填/格式）。
3. Implement service logic and map output to unified response envelope. / 实现服务逻辑并映射到统一响应封装。
4. Define deterministic error codes and field-level validation errors. / 定义确定性错误码与字段级错误。
5. Verify with test cases: success, validation failure, permission denial, not found. / 用成功/校验失败/权限拒绝/不存在四类用例验证。

## Output / 产出
- API delivery checklist aligned with project contract.
- 与项目契约一致的 API 交付清单。

## Checklist / 检查清单
- [ ] Contract is explicit / 契约明确
- [ ] Response format is unified / 响应格式统一
- [ ] Permission checks included / 权限检查已包含
- [ ] Core tests are listed / 核心测试已列出
