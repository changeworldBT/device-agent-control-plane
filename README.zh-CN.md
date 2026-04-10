# Device Agent Control Plane

[English](README.md) | 中文

这是一个开发者预览版仓库，用于验证“受控设备代理执行核心”的控制平面。项目当前聚焦一条可验证的控制平面切片：事件驱动状态、作用域授权、显式审批、执行回执、验证、恢复以及可重放执行。

## 当前状态

这是开发者预览版，不是面向最终用户的完整产品。

目前已经可用：
- 追加式事件日志和物化状态投影器。
- 任务、节点、事实、授权、审批、回执、验证和恢复语义。
- 内置 research 与 CRM fixture 的 replay 执行。
- 先用 Python oracle runtime 证明语义。
- Rust core 在当前已验证切片上与 Python oracle 保持一致。
- 本地文件系统 CRM 场景，包含受控副作用与补偿执行。
- Mock HTTP CRM 场景，包含受控的远端风格副作用与补偿执行。
- replay、本地 CRM、mock HTTP CRM 路径的 Python/Rust parity 检查。

尚未完成：
- 超出已验证 mock HTTP CRM 切片的通用远程适配器。
- 浏览器自动化。
- 超出设计/规格层面的多代理编排。
- 打包、安装器和终端用户 UX。

## 架构

仓库刻意拆成 Python oracle runtime 和 Rust 实现两部分：

- Python oracle：当前切片的语义真值来源，便于检查行为并与 Rust 做对照。
- Rust core：面向生产方向迁移的同语义实现。
- Replay fixtures：确定性的流程输入，用来证明状态转换和 parity。
- Scenario runners：本地文件系统与 mock HTTP CRM 场景，在受作用域授权和恢复规则约束下执行真实副作用。

项目优先选择可证伪、可验证的行为，而不是宽泛声明。只有经过 schema 校验、测试覆盖，并在适用处通过 Python/Rust parity 的路径，才被视为当前已验证切片的一部分。

## 仓库结构

- `v3-design-freeze.html`：当前设计冻结快照。
- `schemas/`：JSON schema、示例和 replay fixtures。
- `runtime/`、`control/`、`domain/`、`selector/`、`verification/`：Python oracle runtime。
- `execution/`：Python 本地与 mock HTTP 执行适配器。
- `scenarios/`：Python 场景 runner 和 mock HTTP CRM server。
- `rust-core/`：Rust 实现、测试和 CLI bin。
- `sandbox/local-crm/seed/`：本地与 mock HTTP CRM 场景的确定性 seed 数据。
- `tests/`：Python 验证测试。

## 环境要求

- Python 3.13+
- 如果使用 Rust-first 路径，需要 Rust toolchain
- 当前已验证环境是 Windows

顶层脚本支持 `--backend auto|python|rust`。`auto` 会在检测到可用 cargo toolchain 时优先使用 Rust，否则回退到 Python。

## 快速开始

运行完整验证门：

```powershell
python .\check_runtime.py
```

运行 replay 摘要：

```powershell
python .\run_replays.py
python .\run_replays.py --backend python
python .\run_replays.py --backend rust
```

运行本地 CRM 场景：

```powershell
python .\run_local_crm_scenario.py
python .\run_local_crm_compensation.py
```

运行 mock HTTP CRM 场景：

```powershell
python .\run_http_crm_scenario.py
python .\run_http_crm_compensation.py
```

## 验证

规范验证命令是：

```powershell
python .\check_runtime.py
```

它会运行：
- examples 与 replay fixtures 的 schema 校验。
- Python 单元测试。
- 顶层 replay、本地 CRM、mock HTTP CRM 入口脚本。
- Rust 结构检查。
- Rust 测试。
- Python/Rust parity 检查。

GitHub Actions 会在 Windows 上对每次 push 和 pull request 运行同一套验证门。

## 发布定位

这个仓库应被视为基础设施和参考实现：

- 控制平面规格。
- replay 驱动的语义参考。
- 由 Python parity 护栏保护的 Rust 迁移。
- 有界副作用执行与恢复的开发者预览。

它目前还不是 polished product UI，也不是通用 agent runtime。

## License

MIT
