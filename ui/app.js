const roles = ["planner", "classifier", "summarizer", "verifier"];
const translations = {
  en: {
    activeProvider: "Active provider",
    advancedProviderManagement: "Advanced provider management",
    advancedJsonEditor: "Advanced JSON editor",
    agentMode: "Agent mode",
    agentTeam: "Agent Team",
    agentsMapped: "{count} agent(s) mapped",
    allChannelsSummary: "All channels",
    allProvidersSummary: "All providers, agents, and route preview",
    apiKeyConfigured: "api key configured",
    apiKeyNotConfigured: "api key not configured",
    applySelectedModel: "Use selected model",
    botChannels: "Bot Channels",
    botCopy:
      "Mainstream bot channels share one preview gateway. Live credentials stay in environment variables; QQ is treated as gateway/SDK-only until a dedicated adapter is added.",
    botPreviewFailed: "Bot channel preview failed.",
    botPreviewReady: "Bot channel dry-run ready: {channel}",
    botTitle: "Telegram, WhatsApp, QQ, Feishu",
    channel: "Channel",
    cliSurface: "CLI Surface",
    cliSurfaceShort: "CLI",
    cliTitle: "Machine-readable commands stay clean",
    dashboardAttentionCopy: "Only actionable local setup gaps are listed here.",
    dashboardAttentionTitle: "Attention",
    dashboardBotConfig: "Bot config",
    dashboardBotMode: "Bot mode",
    dashboardBotSource: "Bot source",
    dashboardChannelFields: "Channel values",
    dashboardChannels: "Channels",
    dashboardConfigPath: "Model config",
    dashboardConfigSource: "Config source",
    dashboardEnvFields: ".env values",
    dashboardEnvPath: ".env file",
    dashboardMissingChannelFields: "{count} channel value(s) are missing.",
    dashboardMissingProviderFields: "{count} provider value(s) are missing.",
    dashboardNoAttention: "No blocking local setup gap detected.",
    dashboardOverview: "Overview",
    dashboardProviderFields: "Provider values",
    dashboardProviders: "Providers",
    dashboardRoutes: "Routes",
    dashboardRoutesMissing: "Route preview has no entries.",
    dashboardRoutesReady: "{count} route(s) ready",
    dashboardSnapshotCopy:
      "Live status is assembled from the local config, bot-channel config, route preview, and .env ownership map.",
    dashboardSnapshotTitle: "Local dashboard snapshot",
    dashboardSourcesCopy: "File paths used by this localhost console.",
    dashboardSourcesTitle: "Local sources",
    dashboardUsingExampleBotConfig: "Bot channel config is using the checked-in example file.",
    dashboardUsingExampleConfig: "Model provider config is using the checked-in example file.",
    disabled: "disabled",
    draft: "draft",
    dryRun: "dry-run",
    dryRunPreview: "Dry-run preview",
    enabled: "enabled",
    envLoaded: "Loaded {count} local value(s): {path}",
    envSaveFailed: "Failed to save local values.",
    envSaved: "Saved {count} local value(s): {path}",
    addProvider: "Add provider",
    failedLoadBotChannels: "Failed to load bot channels.",
    fetchModels: "Fetch models",
    filesFound: "{count} file(s) found",
    gatewaySdk: "gateway/sdk",
    gatewayAuthorityCopy: "Provider keys and bot tokens stay outside checked-in config.",
    gatewayAuthorityTitle: "Authority",
    gatewayLanguageCopy: "Language preference is stored in this browser only.",
    gatewayLanguageTitle: "Language",
    gatewayStatusCopy: "This UI talks to the local Python backend on localhost.",
    gatewayStatusTitle: "Status",
    heroLede: "A compact cockpit for switching between CLI work and visual model-provider configuration.",
    heroTitle: "Choose a surface. Keep authority local.",
    interfaceMode: "Interface mode",
    invalidJson: "Invalid JSON: {message}",
    jsonSafe: "JSON safe",
    jsonUnsaved: "JSON editor has unsaved changes.",
    languageLabel: "Language",
    languageUpdated: "Language updated.",
    loadConfigFailed: "Failed to load configuration.",
    loadGeneratedConfig: "Load generated config into editor",
    loadedConfig: "Loaded {source} config: {path}",
    loading: "loading",
    mapChannelsCopy: "Bot dispatch previews.",
    mapChannelsTitle: "Channels",
    mapChatCopy: "Live route conversation.",
    mapChatTitle: "Chat",
    mapCliCopy: "Command surface.",
    mapCliTitle: "CLI",
    mapDashboardCopy: "Status, access, and runtime switches.",
    mapDashboardTitle: "Dashboard",
    mapGatewayCopy: "Language and local authority.",
    mapGatewayTitle: "Gateway Access",
    mapMigrationCopy: "OpenClaw candidate import.",
    mapMigrationTitle: "Migration",
    mapModelsCopy: "Provider and agent routes.",
    mapModelsTitle: "Models",
    mapRawCopy: "JSON escape hatch.",
    mapRawTitle: "Raw Config",
    launchpadDiagnostics: "Diagnostics and local status",
    launchpadDiagnosticsCopy: "Expand this only when you need route counts, source files, or setup warnings.",
    localConfig: "local config",
    modelMode: "Model mode",
    modelViaAgent: "model via agent",
    noCapabilities: "no capabilities",
    noEnvFields: "No values in this group.",
    noModelRefs: "no model refs",
    noModelsLoaded: "No models loaded.",
    none: "none",
    notes: "Notes",
    navGroupAgent: "Agent",
    navGroupChat: "Chat",
    navGroupControl: "Control",
    navGroupSettings: "Settings",
    workbenchKicker: "Local workspace",
    workbenchSourceLabel: "Config source",
    workbenchMetaAgent: "Agent mode",
    workbenchMetaMode: "Model mode",
    workbenchMetaProvider: "Provider",
    openclawConfig: "OpenClaw config",
    openclawConfigLoaded: "Generated OpenClaw config loaded into editor. Use Preview routes, then Save local config.",
    openclawCopy:
      "Reads OpenClaw JSON5-style config and workspace evidence, skips credentials/sessions, and produces a reviewed local config draft.",
    openclawMigration: "OpenClaw Migration",
    openclawPreviewFailed: "OpenClaw preview failed.",
    openclawPreviewFirst: "Run OpenClaw migration preview first.",
    openclawPreviewReady: "OpenClaw migration preview generated. Review before loading into editor.",
    openclawTitle: "Smooth import, candidate-only by default",
    payload: "Payload",
    previewMigration: "Preview migration",
    previewRoutes: "Preview routes",
    productName: "Device Agent Control Plane",
    providerDefault: "provider default",
    providerRouting: "Provider and agent routing",
    providers: "Providers",
    quickModelCopy: "Read the model list for the current provider, choose one, then jump straight into chat testing.",
    quickModelTitle: "Model",
    quickOpenChat: "Open chat test",
    quickProviderLabel: "Provider",
    quickProviderValuesTitle: "Current provider values",
    quickRouteLabel: "Current test route",
    quickRouteReady: "Ready",
    quickRouteStep1: "1. Choose the provider you actually want to test.",
    quickRouteStep2: "2. Fill only Base URL, API Key, and Model for that provider.",
    quickRouteStep3: "3. Click Open chat test and send a short message.",
    quickStartCopy: "To test a model call, only set Provider, Base URL/API Key, and Model. Everything else can stay unchanged.",
    quickStartEyebrow: "Quick Start",
    quickStartTitle: "3-step model test",
    reload: "Reload",
    reloadValues: "Reload values",
    routePreview: "Route Preview",
    routePreviewFailed: "Route preview failed.",
    routePreviewUpdated: "Route preview updated.",
    saveFailed: "Save failed.",
    saveValues: "Save values",
    saveLocalConfig: "Save local config",
    savedLocalConfig: "Saved local config: {path}",
    chatContextLoaded: "Loaded {count} saved message(s) from {path}",
    chatBreadcrumbRoot: "Device Agent",
    chatClearSession: "Clear session",
    chatChipAgent: "Agent",
    chatChipMode: "Mode",
    chatChipModel: "Model",
    chatChipProvider: "Provider",
    chatChipRole: "Role",
    chatSetup: "Setup and route controls",
    chatSetupCopy: "Change provider, role, or model only when you need to test a different route.",
    chatSetupToggle: "Setup",
    chatCurrentSessionLabel: "Active session",
    chatComposerNote: "Press Enter to send. Use Shift + Enter for a newline. Each turn is saved to the local session file.",
    chatDryRunNote: "Chat uses the current route and saves each turn locally.",
    chatEmpty: "Start a message. The current route will call the selected provider when the route is live.",
    chatPlaceholder: "Send a real model test message...",
    chatRecentSessions: "Recent sessions",
    chatRouteContext: "Current route context",
    chatRouteContextCopy: "These values are what the current chat send will use right now.",
    chatRole: "Role",
    chatRoutePending: "route pending",
    chatRouteUpdated: "Chat route updated.",
    chatSendFailed: "Chat request failed.",
    chatSending: "calling model...",
    chatSessionNoTurns: "No saved turns yet",
    chatSessionUpdated: "Updated {time}",
    chatTurnError: "error",
    chatTurnPending: "running",
    chatTurnPrompt: "Prompt",
    chatTurnResult: "Response",
    chatModelRejected: "Provider {provider} rejected configured model `{model}`.",
    chatModelRejectedTried: "Tried transport IDs: {models}",
    chatModelRejectedProviderMessage: "Provider said: {message}",
    chatModelRejectedHintTransport: "Suggested transport model: {model}",
    chatModelRejectedHintFetch: "Fetch /models and select a listed model if this endpoint expects a different transport model ID.",
    chatSessions: "Sessions",
    chatWorkbenchEyebrow: "Live Chat",
    chatWorkbenchTitle: "Fixed workspace",
    chatUserLabel: "You",
    chatAssistantLabel: "Device Agent",
    chatResponseReady: "Chat response ready: {provider} / {model}",
    chatSessionClearFailed: "Failed to clear saved session.",
    chatSessionCleared: "Cleared session: {session}",
    chatSessionTurns: "{count} turn(s)",
    chatSessionsLoadFailed: "Failed to load saved sessions.",
    defaultSession: "Default session",
    localOnlyNote: "Local console. Secrets stay in env vars and local JSON.",
    sendMessage: "Send",
    selectedChannelValues: "Selected channel local values",
    selectedProviderConfig: "Selected Provider",
    selectedProviderConfigTitle: "Provider config and values",
    selectedProviderValues: "Selected provider local values",
    sourceExample: "example",
    sourceEnvFile: ".env",
    sourcePending: "pending save",
    sourceLocal: "local",
    sourceProcess: "process",
    sourceUnset: "unset",
    statusLoading: "Loading configuration...",
    testMessage: "Test message",
    uiSurface: "UI",
    unassigned: "unassigned",
    unset: "unset",
    valueConfigured: "configured",
    valueMissing: "missing",
    visualConfig: "Visual Config",
    botValues: "Bot channels",
    otherValues: "Other .env values",
    otherValuesCopy: "Values that are in .env but are not referenced by provider, channel, or runtime config.",
    providerApiKeyEnv: "API key env",
    providerApiKeyValue: "API key value",
    providerBaseUrlEnv: "Base URL env",
    providerBaseUrlValue: "Base URL value",
    providerId: "Provider ID",
    providerKind: "Provider kind",
    providerLocalValues: "Provider values",
    providerLocalValuesCopy:
      "These are the local values referenced by provider config. They are shown in plaintext on this localhost UI.",
    providerLocalValuesTitle: "Base URLs, API keys, and default models",
    providerManagement: "Provider management",
    providerManagementCopy:
      "Providers are grouped by vendor when a model ref has a vendor prefix. Local and hand-written entries are grouped as custom.",
    providerManagementTitle: "Vendor and custom providers",
    providerModel: "Default model",
    providerModelDiscovery: "Model discovery",
    providerModelDiscoveryCopy:
      "For OpenAI-compatible providers, call the selected provider's /models endpoint using the current base URL and API key.",
    providerModelList: "Models",
    providerModelsApplied: "Applied selected model: {model}",
    providerModelsFailed: "Failed to fetch models: {message}",
    providerModelsLoaded: "Loaded {count} model(s).",
    providerModelsNeedValues: "Base URL and API key are required before fetching models.",
    providerModelsUnsupported: "Model discovery is only available for OpenAI-compatible providers.",
    runtimeValues: "Runtime overrides",
    runtimeValuesCopy: "These values override model mode, active provider, and agent routing for this local process.",
    runtimeAdvancedCopy: "These overrides are for local troubleshooting. Leave them unchanged for normal chat tests.",
    runtimeValuesTitle: "Local runtime switches",
    channelLocalValues: "Channel local values",
    viewChannelsDescription: "Configure outbound bot channels and inspect safe dry-run dispatch payloads.",
    viewChannelsEyebrow: "Channels",
    viewChannelsTitle: "Bot channel gateway",
    viewChatDescription: "Send a message first. Open setup only when you need to change routes.",
    viewChatEyebrow: "WebChat",
    viewChatTitle: "Chat interaction",
    viewCliDescription: "Run deterministic command-line entrypoints for replay, CRM scenarios, and UI launch.",
    viewCliEyebrow: "CLI",
    viewCliTitle: "Command surface",
    viewGatewayDescription: "Language, local access, and safety boundaries for this control console.",
    viewGatewayEyebrow: "Gateway Access",
    viewGatewayTitle: "Quick start console",
    viewMigrationDescription: "Import OpenClaw-like workspace evidence into candidate-only local config.",
    viewMigrationEyebrow: "Migration",
    viewMigrationTitle: "OpenClaw migration",
    viewModelsDescription: "Switch provider mode, agent mode, and inspect role routing.",
    viewModelsEyebrow: "Models",
    viewModelsTitle: "Provider and agent routing",
    viewRawDescription: "Edit validated JSON directly when the form surface is not enough.",
    viewRawEyebrow: "Config",
    viewRawTitle: "Raw JSON editor",
    warning: "Warning",
    workspaceMap: "Console sections",
    workspaceEvidence: "Workspace evidence",
    workspaceOverride: "Workspace override",
  },
  "zh-CN": {
    activeProvider: "当前 Provider",
    advancedProviderManagement: "高级 Provider 管理",
    advancedJsonEditor: "高级 JSON 编辑器",
    agentMode: "Agent 模式",
    agentTeam: "Agent 团队",
    agentsMapped: "已映射 {count} 个 agent",
    allChannelsSummary: "全部渠道",
    allProvidersSummary: "全部 Provider、Agent 和路由预览",
    apiKeyConfigured: "API key 已配置",
    apiKeyNotConfigured: "API key 未配置",
    applySelectedModel: "使用所选模型",
    botChannels: "Bot 渠道",
    botCopy: "主流 bot 渠道共用同一个预览网关。真实凭据只放在环境变量里；QQ 在专用适配器加入前只按 gateway/SDK 处理。",
    botPreviewFailed: "Bot 渠道预览失败。",
    botPreviewReady: "Bot 渠道 dry-run 已生成：{channel}",
    botTitle: "Telegram、WhatsApp、QQ、飞书",
    channel: "渠道",
    cliSurface: "CLI 界面",
    cliSurfaceShort: "CLI",
    cliTitle: "机器可读命令保持干净",
    dashboardAttentionCopy: "这里仅列出需要你处理的本地配置缺口。",
    dashboardAttentionTitle: "待处理",
    dashboardBotConfig: "Bot 配置",
    dashboardBotMode: "Bot 模式",
    dashboardBotSource: "Bot 来源",
    dashboardChannelFields: "渠道值",
    dashboardChannels: "渠道数",
    dashboardConfigPath: "模型配置",
    dashboardConfigSource: "配置来源",
    dashboardEnvFields: ".env 值",
    dashboardEnvPath: ".env 文件",
    dashboardMissingChannelFields: "还有 {count} 个渠道配置值缺失。",
    dashboardMissingProviderFields: "还有 {count} 个 Provider 配置值缺失。",
    dashboardNoAttention: "当前未发现阻塞性的本地配置缺口。",
    dashboardOverview: "总览",
    dashboardProviderFields: "Provider 值",
    dashboardProviders: "Provider 数",
    dashboardRoutes: "路由",
    dashboardRoutesMissing: "路由预览暂无条目。",
    dashboardRoutesReady: "{count} 条路由已就绪",
    dashboardSnapshotCopy: "状态来自本地模型配置、Bot 渠道配置、路由预览和 .env 归属表。",
    dashboardSnapshotTitle: "本地 Dashboard 快照",
    dashboardSourcesCopy: "当前 localhost 控制台实际读取的文件路径。",
    dashboardSourcesTitle: "本地来源",
    dashboardUsingExampleBotConfig: "Bot 渠道配置仍在使用仓库示例文件。",
    dashboardUsingExampleConfig: "模型 Provider 配置仍在使用仓库示例文件。",
    disabled: "未启用",
    draft: "草稿",
    dryRun: "dry-run",
    dryRunPreview: "Dry-run 预览",
    enabled: "已启用",
    envLoaded: "已加载 {count} 个本地值：{path}",
    envSaveFailed: "保存本地配置值失败。",
    envSaved: "已保存 {count} 个本地值：{path}",
    addProvider: "添加 Provider",
    failedLoadBotChannels: "加载 bot 渠道失败。",
    fetchModels: "读取模型列表",
    filesFound: "找到 {count} 个文件",
    gatewaySdk: "gateway/sdk",
    gatewayAuthorityCopy: "Provider key 和 bot token 保存在本机 .env，分别在模型和渠道页面按归属管理，不写入提交配置。",
    gatewayAuthorityTitle: "权限边界",
    gatewayLanguageCopy: "语言偏好只保存在当前浏览器。",
    gatewayLanguageTitle: "语言",
    gatewayStatusCopy: "这个 UI 只连接 localhost 上的本地 Python 后端。",
    gatewayStatusTitle: "状态",
    heroLede: "一个轻量控制台，用于在 CLI 工作流和可视化模型 Provider 配置之间切换。",
    heroTitle: "选择界面，权限留在本地。",
    interfaceMode: "界面模式",
    invalidJson: "JSON 无效：{message}",
    jsonSafe: "JSON 安全",
    jsonUnsaved: "JSON 编辑器有未保存修改。",
    languageLabel: "语言",
    languageUpdated: "语言已更新。",
    loadConfigFailed: "加载配置失败。",
    loadGeneratedConfig: "载入生成配置到编辑器",
    loadedConfig: "已加载 {source} 配置：{path}",
    loading: "加载中",
    mapChannelsCopy: "Bot 渠道配置和预览。",
    mapChannelsTitle: "渠道",
    mapChatCopy: "真实路由对话。",
    mapChatTitle: "对话",
    mapCliCopy: "命令行操作入口。",
    mapCliTitle: "命令行",
    mapDashboardCopy: "状态、入口和运行开关。",
    mapDashboardTitle: "总览",
    mapGatewayCopy: "语言和本地权限。",
    mapGatewayTitle: "本地入口",
    mapMigrationCopy: "OpenClaw 候选导入。",
    mapMigrationTitle: "迁移",
    mapModelsCopy: "Provider 与 Agent 路由。",
    mapModelsTitle: "模型",
    mapRawCopy: "JSON 逃生口。",
    mapRawTitle: "原始配置",
    launchpadDiagnostics: "诊断与本地状态",
    launchpadDiagnosticsCopy: "只有在需要查看路由计数、来源文件或配置告警时再展开。",
    modelMode: "模型模式",
    modelViaAgent: "通过 agent 设置模型",
    noCapabilities: "无能力声明",
    noEnvFields: "这一组暂无配置值。",
    noModelRefs: "无模型引用",
    noModelsLoaded: "尚未读取模型列表。",
    none: "无",
    notes: "说明",
    navGroupAgent: "Agent",
    navGroupChat: "对话",
    navGroupControl: "控制",
    navGroupSettings: "设置",
    workbenchKicker: "本地工作区",
    workbenchSourceLabel: "配置来源",
    workbenchMetaAgent: "Agent 模式",
    workbenchMetaMode: "模型模式",
    workbenchMetaProvider: "Provider",
    openclawConfig: "OpenClaw 配置",
    openclawConfigLoaded: "已把 OpenClaw 生成配置载入编辑器。请先预览路由，再保存本地配置。",
    openclawCopy: "读取 OpenClaw JSON5 风格配置和 workspace 证据，跳过 credentials/sessions，并生成待审核的本地配置草稿。",
    openclawMigration: "OpenClaw 迁移",
    openclawPreviewFailed: "OpenClaw 预览失败。",
    openclawPreviewFirst: "请先运行 OpenClaw 迁移预览。",
    openclawPreviewReady: "OpenClaw 迁移预览已生成。载入编辑器前请先审核。",
    openclawTitle: "丝滑导入，默认仅生成候选配置",
    payload: "载荷",
    previewMigration: "预览迁移",
    previewRoutes: "预览路由",
    productName: "Device Agent 控制平面",
    providerDefault: "Provider 默认值",
    providerRouting: "Provider 与 Agent 路由",
    providers: "Provider 列表",
    quickModelCopy: "读取当前 Provider 的模型列表，选中一个模型后，直接跳到对话测试。",
    quickModelTitle: "模型",
    quickOpenChat: "去对话测试",
    quickProviderLabel: "Provider",
    quickProviderValuesTitle: "当前 Provider 三项配置",
    quickRouteLabel: "当前测试路由",
    quickRouteReady: "可测试",
    quickRouteStep1: "1. 先选中你真正要测试的 Provider。",
    quickRouteStep2: "2. 只填写这个 Provider 的 Base URL、API Key、Model。",
    quickRouteStep3: "3. 点击“去对话测试”，发一条短消息即可。",
    quickStartCopy: "测试模型调用其实只需要三项：Provider、Base URL/API Key、Model。其余配置都可以先不动。",
    quickStartEyebrow: "快速开始",
    quickStartTitle: "3 步测试模型",
    reload: "重新加载",
    reloadValues: "重新加载配置值",
    routePreview: "路由预览",
    routePreviewFailed: "路由预览失败。",
    routePreviewUpdated: "路由预览已更新。",
    saveFailed: "保存失败。",
    saveValues: "保存配置值",
    saveLocalConfig: "保存本地配置",
    savedLocalConfig: "已保存本地配置：{path}",
    chatContextLoaded: "已从 {path} 加载 {count} 条已保存消息",
    chatBreadcrumbRoot: "Device Agent",
    chatClearSession: "清空会话",
    chatChipAgent: "Agent",
    chatChipMode: "模式",
    chatChipModel: "模型",
    chatChipProvider: "Provider",
    chatChipRole: "角色",
    chatSetup: "设置与路由控制",
    chatSetupCopy: "只有在要测试另一条路由时，才改 Provider、角色或模型。",
    chatSetupToggle: "设置",
    chatCurrentSessionLabel: "当前会话",
    chatComposerNote: "直接按 Enter 发送，Shift + Enter 换行。每轮消息都会保存到本机会话文件。",
    chatDryRunNote: "Chat 使用当前路由，并会把每轮对话保存到本地。",
    chatEmpty: "输入一条消息。当前路由若处于 live，会直接调用所选 Provider。",
    chatPlaceholder: "发送一条真实模型测试消息...",
    chatRecentSessions: "最近会话",
    chatRouteContext: "当前路由上下文",
    chatRouteContextCopy: "这里显示当前发送消息时实际会使用的路由值。",
    chatRole: "角色",
    chatRoutePending: "路由待预览",
    chatRouteUpdated: "Chat 路由已更新。",
    chatSendFailed: "Chat 请求失败。",
    chatSending: "正在调用模型...",
    chatSessionNoTurns: "还没有已保存轮次",
    chatSessionUpdated: "更新于 {time}",
    chatTurnError: "异常",
    chatTurnPending: "运行中",
    chatTurnPrompt: "输入",
    chatTurnResult: "结果",
    chatModelRejected: "Provider {provider} 拒绝了当前配置模型 `{model}`。",
    chatModelRejectedTried: "已尝试的 transport model ID：{models}",
    chatModelRejectedProviderMessage: "Provider 返回：{message}",
    chatModelRejectedHintTransport: "建议改用 transport model：{model}",
    chatModelRejectedHintFetch: "如果这个端点使用不同的 transport model ID，请先读取 /models 再从列表中选择。",
    chatSessions: "会话",
    chatWorkbenchEyebrow: "实时对话",
    chatWorkbenchTitle: "固定工作台",
    chatUserLabel: "你",
    chatAssistantLabel: "Device Agent",
    chatResponseReady: "Chat 响应已返回：{provider} / {model}",
    chatSessionClearFailed: "清空已保存会话失败。",
    chatSessionCleared: "已清空会话：{session}",
    chatSessionTurns: "{count} 轮",
    chatSessionsLoadFailed: "加载已保存会话失败。",
    defaultSession: "默认会话",
    localOnlyNote: "本地控制台。配置值保存在本机 .env 和本地 JSON。",
    sendMessage: "发送",
    selectedChannelValues: "当前渠道本地值",
    selectedProviderConfig: "当前 Provider",
    selectedProviderConfigTitle: "Provider 配置和值",
    selectedProviderValues: "当前 Provider 本地值",
    sourceExample: "示例",
    sourceEnvFile: ".env 文件",
    sourcePending: "待保存",
    sourceLocal: "本地",
    sourceProcess: "当前进程",
    sourceUnset: "未设置",
    statusLoading: "正在加载配置...",
    testMessage: "测试消息",
    uiSurface: "UI",
    unassigned: "未分配",
    unset: "未设置",
    valueConfigured: "已配置",
    valueMissing: "缺失",
    visualConfig: "可视化配置",
    botValues: "Bot 渠道",
    otherValues: "其他 .env 值",
    otherValuesCopy: ".env 中存在、但没有被 Provider、渠道或运行配置引用的值。",
    providerApiKeyEnv: "API Key 环境变量",
    providerApiKeyValue: "API Key 值",
    providerBaseUrlEnv: "Base URL 环境变量",
    providerBaseUrlValue: "Base URL 值",
    providerId: "Provider ID",
    providerKind: "Provider 类型",
    providerLocalValues: "Provider 本地值",
    providerLocalValuesCopy: "这些值来自 Provider 配置引用的本机 .env。本页面运行在 localhost，按你的要求明文显示。",
    providerLocalValuesTitle: "Base URL、API Key 与默认模型",
    providerManagement: "Provider 管理",
    providerManagementCopy: "模型引用带厂商前缀时按厂商分组；本地、手写或 mock provider 归到自定义。",
    providerManagementTitle: "厂商与自定义 Provider",
    providerModel: "默认模型",
    providerModelDiscovery: "模型列表读取",
    providerModelDiscoveryCopy: "OpenAI-compatible Provider 会使用当前 Base URL 和 API Key 调用 /models 列表。",
    providerModelList: "模型列表",
    providerModelsApplied: "已应用模型：{model}",
    providerModelsFailed: "读取模型列表失败：{message}",
    providerModelsLoaded: "已读取 {count} 个模型。",
    providerModelsNeedValues: "读取模型列表前需要 Base URL 和 API Key。",
    providerModelsUnsupported: "模型列表读取仅支持 OpenAI-compatible Provider。",
    runtimeValues: "运行时覆盖",
    runtimeValuesCopy: "这些值只覆盖本地进程的模型模式、当前 Provider 和 Agent 路由。",
    runtimeAdvancedCopy: "这些覆盖项主要用于本地排障。正常聊天测试时不要改。",
    runtimeValuesTitle: "本地运行开关",
    channelLocalValues: "渠道本地值",
    viewChannelsDescription: "配置出站 Bot 渠道，并检查 dry-run dispatch payload。",
    viewChannelsEyebrow: "渠道",
    viewChannelsTitle: "Bot 渠道网关",
    viewChatDescription: "先发一条消息。只有在需要改路由时再打开设置。",
    viewChatEyebrow: "对话",
    viewChatTitle: "Chat 交互",
    viewCliDescription: "运行 replay、CRM 场景和 UI 启动等确定性命令行入口。",
    viewCliEyebrow: "命令行",
    viewCliTitle: "命令行界面",
    viewGatewayDescription: "控制台语言、本地访问和安全边界。",
    viewGatewayEyebrow: "本地入口",
    viewGatewayTitle: "快速开始控制台",
    viewMigrationDescription: "把 OpenClaw 风格 workspace 证据导入成候选本地配置。",
    viewMigrationEyebrow: "迁移",
    viewMigrationTitle: "配置迁移",
    viewModelsDescription: "切换 provider 模式、agent 模式，并检查 role 路由。",
    viewModelsEyebrow: "模型",
    viewModelsTitle: "Provider 与 Agent 路由",
    viewRawDescription: "当表单不够用时，直接编辑通过校验的 JSON。",
    viewRawEyebrow: "Config",
    viewRawTitle: "Raw JSON 编辑器",
    warning: "警告",
    workspaceMap: "控制台分区",
    workspaceEvidence: "Workspace 证据",
    workspaceOverride: "Workspace 覆盖",
  },
};

const viewMeta = {
  gatewayView: {
    eyebrow: "viewGatewayEyebrow",
    title: "viewGatewayTitle",
    description: "viewGatewayDescription",
  },
  modelsView: {
    eyebrow: "viewModelsEyebrow",
    title: "viewModelsTitle",
    description: "viewModelsDescription",
  },
  channelsView: {
    eyebrow: "viewChannelsEyebrow",
    title: "viewChannelsTitle",
    description: "viewChannelsDescription",
  },
  chatView: {
    eyebrow: "viewChatEyebrow",
    title: "viewChatTitle",
    description: "viewChatDescription",
  },
  migrationView: {
    eyebrow: "viewMigrationEyebrow",
    title: "viewMigrationTitle",
    description: "viewMigrationDescription",
  },
  rawConfigView: {
    eyebrow: "viewRawEyebrow",
    title: "viewRawTitle",
    description: "viewRawDescription",
  },
  cliView: {
    eyebrow: "viewCliEyebrow",
    title: "viewCliTitle",
    description: "viewCliDescription",
  },
};

let locale = initialLocale();
let activeView = "chatView";
let state = { config: null, routes: [] };

const elements = {
  shell: document.querySelector("#appShell"),
  shellNavBackdrop: document.querySelector("#shellNavBackdrop"),
  navCollapseButton: document.querySelector("#navCollapseButton"),
  navDrawerToggleButton: document.querySelector("#navDrawerToggleButton"),
  topbarViewTitle: document.querySelector("#topbarViewTitle"),
  topbarViewDescription: document.querySelector("#topbarViewDescription"),
  topbarSummaryLabel: document.querySelector("#topbarSummaryLabel"),
  topbarSummaryBadge: document.querySelector("#topbarSummaryBadge"),
  topbarSourceBadge: document.querySelector("#topbarSourceBadge"),
  topbarModeBadge: document.querySelector("#topbarModeBadge"),
  viewEyebrow: document.querySelector("#viewEyebrow"),
  viewTitle: document.querySelector("#viewTitle"),
  viewDescription: document.querySelector("#viewDescription"),
  workbenchViewMeta: document.querySelector("#workbenchViewMeta"),
  workbenchProviderCount: document.querySelector("#workbenchProviderCount"),
  workbenchRouteCount: document.querySelector("#workbenchRouteCount"),
  workbenchChannelCount: document.querySelector("#workbenchChannelCount"),
  languageSelect: document.querySelector("#languageSelect"),
  modeSelect: document.querySelector("#modeSelect"),
  agentModeSelect: document.querySelector("#agentModeSelect"),
  providerSelect: document.querySelector("#providerSelect"),
  quickProviderSelect: document.querySelector("#quickProviderSelect"),
  quickProviderBadge: document.querySelector("#quickProviderBadge"),
  quickRouteSummary: document.querySelector("#quickRouteSummary"),
  quickProviderFields: document.querySelector("#quickProviderFields"),
  quickProviderModelSelect: document.querySelector("#quickProviderModelSelect"),
  quickFetchModelsButton: document.querySelector("#quickFetchModelsButton"),
  quickApplyModelButton: document.querySelector("#quickApplyModelButton"),
  quickOpenChatButton: document.querySelector("#quickOpenChatButton"),
  quickProviderModelStatus: document.querySelector("#quickProviderModelStatus"),
  dashboardSourceBadge: document.querySelector("#dashboardSourceBadge"),
  dashboardSnapshotList: document.querySelector("#dashboardSnapshotList"),
  dashboardAttentionList: document.querySelector("#dashboardAttentionList"),
  dashboardSourcesList: document.querySelector("#dashboardSourcesList"),
  providersList: document.querySelector("#providersList"),
  selectedProviderDetail: document.querySelector("#selectedProviderDetail"),
  providerModelSelect: document.querySelector("#providerModelSelect"),
  fetchProviderModelsButton: document.querySelector("#fetchProviderModelsButton"),
  applyProviderModelButton: document.querySelector("#applyProviderModelButton"),
  providerModelStatus: document.querySelector("#providerModelStatus"),
  agentsList: document.querySelector("#agentsList"),
  routesList: document.querySelector("#routesList"),
  envValuesBadge: document.querySelector("#envValuesBadge"),
  envFilePath: document.querySelector("#envFilePath"),
  envRuntimeFields: document.querySelector("#envRuntimeFields"),
  envModelFields: document.querySelector("#envModelFields"),
  envBotFields: document.querySelector("#envBotFields"),
  envOtherFields: document.querySelector("#envOtherFields"),
  customProviderId: document.querySelector("#customProviderId"),
  customProviderKind: document.querySelector("#customProviderKind"),
  customProviderModel: document.querySelector("#customProviderModel"),
  customProviderModelSelect: document.querySelector("#customProviderModelSelect"),
  customProviderBaseUrlEnv: document.querySelector("#customProviderBaseUrlEnv"),
  customProviderApiKeyEnv: document.querySelector("#customProviderApiKeyEnv"),
  customProviderBaseUrlValue: document.querySelector("#customProviderBaseUrlValue"),
  customProviderApiKeyValue: document.querySelector("#customProviderApiKeyValue"),
  fetchCustomProviderModelsButton: document.querySelector("#fetchCustomProviderModelsButton"),
  customProviderModelStatus: document.querySelector("#customProviderModelStatus"),
  jsonEditor: document.querySelector("#jsonEditor"),
  statusLine: document.querySelector("#statusLine"),
  sourceBadge: document.querySelector("#sourceBadge"),
  openclawConfigPath: document.querySelector("#openclawConfigPath"),
  openclawWorkspacePath: document.querySelector("#openclawWorkspacePath"),
  openclawReport: document.querySelector("#openclawReport"),
  botChannelBadge: document.querySelector("#botChannelBadge"),
  botChannelSelect: document.querySelector("#botChannelSelect"),
  botChannelText: document.querySelector("#botChannelText"),
  selectedChannelDetail: document.querySelector("#selectedChannelDetail"),
  botChannelsList: document.querySelector("#botChannelsList"),
  botChannelPreview: document.querySelector("#botChannelPreview"),
  chatModeSelect: document.querySelector("#chatModeSelect"),
  chatAgentModeSelect: document.querySelector("#chatAgentModeSelect"),
  chatProviderSelect: document.querySelector("#chatProviderSelect"),
  chatRoleSelect: document.querySelector("#chatRoleSelect"),
  chatProviderModelSelect: document.querySelector("#chatProviderModelSelect"),
  chatFetchModelsButton: document.querySelector("#chatFetchModelsButton"),
  chatApplyModelButton: document.querySelector("#chatApplyModelButton"),
  chatSessionSelect: document.querySelector("#chatSessionSelect"),
  chatSessionList: document.querySelector("#chatSessionList"),
  chatSessionSummary: document.querySelector("#chatSessionSummary"),
  chatClearSessionButton: document.querySelector("#chatClearSessionButton"),
  chatSessionBadge: document.querySelector("#chatSessionBadge"),
  chatRouteBadge: document.querySelector("#chatRouteBadge"),
  chatCurrentRoute: document.querySelector("#chatCurrentRoute"),
  chatLog: document.querySelector("#chatLog"),
  chatComposerForm: document.querySelector("#chatComposerForm"),
  chatInput: document.querySelector("#chatInput"),
  chatSendButton: document.querySelector("#chatSendButton"),
};

let openclawReport = null;
let botChannelState = null;
let botChannelPreviewPayload = null;
let envValueState = null;
let chatMessages = [];
let chatSessionId = "default";
let chatSessions = [];
let providerModelCatalog = {};
let customProviderModels = [];
let navCollapsed = initialNavCollapsed();
let navDrawerOpen = false;

document.querySelectorAll(".nav-item").forEach((button) => {
  button.addEventListener("click", () => {
    closeNavDrawer();
    showView(button.dataset.view);
  });
});

elements.navCollapseButton?.addEventListener("click", () => {
  setNavCollapsed(!navCollapsed);
});

elements.navDrawerToggleButton?.addEventListener("click", () => {
  setNavDrawerOpen(!navDrawerOpen);
});

elements.shellNavBackdrop?.addEventListener("click", () => {
  closeNavDrawer();
});

document.querySelector("#reloadButton").addEventListener("click", loadConfig);
document.querySelector("#previewButton").addEventListener("click", () => previewRoutes());
document.querySelector("#saveButton").addEventListener("click", saveConfig);
document.querySelector("#openclawPreviewButton").addEventListener("click", previewOpenClawMigration);
document.querySelector("#openclawApplyButton").addEventListener("click", applyOpenClawGeneratedConfig);
document.querySelector("#botChannelPreviewButton").addEventListener("click", previewBotChannel);
document.querySelector("#addProviderButton").addEventListener("click", addCustomProvider);
elements.fetchProviderModelsButton.addEventListener("click", fetchSelectedProviderModels);
elements.applyProviderModelButton.addEventListener("click", applySelectedProviderModel);
elements.quickFetchModelsButton.addEventListener("click", fetchSelectedProviderModels);
elements.quickApplyModelButton.addEventListener("click", applySelectedProviderModel);
elements.chatFetchModelsButton.addEventListener("click", fetchSelectedProviderModels);
elements.chatApplyModelButton.addEventListener("click", applySelectedProviderModel);
elements.quickOpenChatButton.addEventListener("click", () => showView("chatView"));
elements.fetchCustomProviderModelsButton.addEventListener("click", fetchCustomProviderModels);
elements.customProviderModelSelect.addEventListener("change", () => {
  if (elements.customProviderModelSelect.value) {
    elements.customProviderModel.value = elements.customProviderModelSelect.value;
  }
});
elements.providerModelSelect.addEventListener("change", () => syncProviderModelSelects(elements.providerModelSelect.value, "provider"));
elements.quickProviderModelSelect.addEventListener("change", () => syncProviderModelSelects(elements.quickProviderModelSelect.value, "quick"));
elements.chatProviderModelSelect.addEventListener("change", () => syncProviderModelSelects(elements.chatProviderModelSelect.value, "chat"));
elements.chatSessionSelect.addEventListener("change", () => {
  void selectChatSession(elements.chatSessionSelect.value || "default");
});
elements.chatSessionList.addEventListener("click", (event) => {
  const button = event.target.closest("[data-session-id]");
  if (!button) return;
  void selectChatSession(button.dataset.sessionId || "default");
});
elements.chatClearSessionButton.addEventListener("click", clearChatSession);
document.querySelectorAll(".env-reload-button").forEach((button) => button.addEventListener("click", loadEnvValues));
document.querySelectorAll(".env-save-button").forEach((button) => button.addEventListener("click", saveEnvValues));
elements.chatComposerForm?.addEventListener("submit", (event) => {
  event.preventDefault();
  void sendChatMessage();
});
elements.chatInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    void sendChatMessage();
  }
});
elements.chatRoleSelect.addEventListener("change", updateChatRouteBadge);
elements.quickProviderSelect.addEventListener("change", () => {
  applyRoutingControls({ provider: elements.quickProviderSelect.value });
});
for (const select of [elements.chatModeSelect, elements.chatAgentModeSelect, elements.chatProviderSelect]) {
  select.addEventListener("change", () => {
    applyRoutingControls({
      mode: elements.chatModeSelect.value,
      agentMode: elements.chatAgentModeSelect.value,
      provider: elements.chatProviderSelect.value,
    });
  });
}
elements.languageSelect.addEventListener("change", () => {
  locale = elements.languageSelect.value;
  localStorage.setItem("device-agent-ui-language", locale);
  translatePage();
  renderAll({ keepEditor: true });
  if (openclawReport) renderOpenClawReport(openclawReport);
  if (botChannelState) renderBotChannels(botChannelState);
  if (botChannelPreviewPayload) renderBotChannelPreview(botChannelPreviewPayload);
  if (envValueState) renderEnvValues(envValueState);
  renderChat();
  renderChatSessions();
  renderDashboard();
  updateViewHeader();
  setStatus(t("languageUpdated"));
});

syncShellChrome();

for (const select of [elements.modeSelect, elements.agentModeSelect, elements.providerSelect]) {
  select.addEventListener("change", () => {
    applyRoutingControls({
      mode: elements.modeSelect.value,
      agentMode: elements.agentModeSelect.value,
      provider: elements.providerSelect.value,
    });
  });
}

elements.botChannelSelect.addEventListener("change", () => {
  if (botChannelState) renderBotChannels(botChannelState);
  if (envValueState) renderEnvValues(envValueState);
});

elements.jsonEditor.addEventListener("input", () => {
  setStatus(t("jsonUnsaved"));
});

async function loadConfig() {
  setStatus(t("statusLoading"));
  const response = await fetch("/api/config");
  const payload = await response.json();
  if (!response.ok) {
    setStatus(payload.error || t("loadConfigFailed"));
    return;
  }
  state = payload;
  renderAll();
  setStatus(t("loadedConfig", { source: sourceLabel(payload.source), path: payload.path }));
}

async function loadOpenClawDefaults() {
  const response = await fetch("/api/openclaw/defaults");
  const payload = await response.json();
  if (!response.ok) return;
  elements.openclawConfigPath.value = payload.config_path || "";
  elements.openclawWorkspacePath.value = payload.workspace_path || "";
}

async function loadBotChannels() {
  const response = await fetch("/api/bot-channels");
  const payload = await response.json();
  if (!response.ok) {
    setStatus(payload.error || t("failedLoadBotChannels"));
    return;
  }
  botChannelState = payload;
  renderBotChannels(payload);
}

async function loadEnvValues() {
  const response = await fetch("/api/env");
  const payload = await response.json();
  if (!response.ok) {
    setStatus(payload.error || t("loadConfigFailed"));
    return;
  }
  envValueState = payload;
  renderEnvValues(payload);
  if (state.config) {
    void previewRoutesForConfig(state.config, { silent: true });
  }
  setStatus(t("envLoaded", { count: (payload.fields || []).length, path: payload.path }));
}

async function saveEnvValues() {
  const values = {};
  document.querySelectorAll("[data-env-key]").forEach((input) => {
    values[input.dataset.envKey] = input.value;
  });

  const response = await fetch("/api/env", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ values }),
  });
  const payload = await response.json();
  if (!response.ok) {
    setStatus(payload.error || t("envSaveFailed"));
    return;
  }
  envValueState = payload;
  renderEnvValues(payload);
  await refreshConfigFromServer();
  setStatus(t("envSaved", { count: (payload.fields || []).length, path: payload.path }));
}

async function refreshConfigFromServer() {
  const response = await fetch("/api/config");
  if (!response.ok) return;
  state = await response.json();
  renderAll();
}

async function previewRoutes() {
  const config = configFromEditor();
  if (!config) return;
  applyControlsToConfig(config);
  state.config = config;
  await previewRoutesForConfig(config);
}

async function previewRoutesForConfig(config, { silent = false } = {}) {
  const response = await fetch("/api/route-preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ config, env_values: collectEnvInputValues() }),
  });
  const payload = await response.json();
  if (!response.ok) {
    if (!silent) setStatus(payload.error || t("routePreviewFailed"));
    return false;
  }
  state.routes = payload.routes;
  renderAll({ keepEditor: true });
  if (!silent) setStatus(t("routePreviewUpdated"));
  return true;
}

async function saveConfig() {
  const config = configFromEditor();
  if (!config) return;
  applyControlsToConfig(config);
  const response = await fetch("/api/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ config }),
  });
  const payload = await response.json();
  if (!response.ok) {
    setStatus(payload.error || t("saveFailed"));
    return;
  }
  state = payload;
  renderAll();
  setStatus(t("savedLocalConfig", { path: payload.local_config_path }));
}

async function previewOpenClawMigration() {
  const response = await fetch("/api/openclaw/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      config_path: elements.openclawConfigPath.value,
      workspace_path: elements.openclawWorkspacePath.value,
    }),
  });
  const payload = await response.json();
  if (!response.ok) {
    setStatus(payload.error || t("openclawPreviewFailed"));
    return;
  }
  openclawReport = payload;
  renderOpenClawReport(payload);
  setStatus(t("openclawPreviewReady"));
}

function applyOpenClawGeneratedConfig() {
  if (!openclawReport || !openclawReport.generated_config) {
    setStatus(t("openclawPreviewFirst"));
    return;
  }
  state.config = openclawReport.generated_config;
  state.routes = [];
  elements.jsonEditor.value = JSON.stringify(openclawReport.generated_config, null, 2);
  renderAll({ keepEditor: true });
  setStatus(t("openclawConfigLoaded"));
}

async function previewBotChannel() {
  const response = await fetch("/api/bot-channels/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      channel: elements.botChannelSelect.value,
      text: elements.botChannelText.value,
    }),
  });
  const payload = await response.json();
  if (!response.ok) {
    setStatus(payload.error || t("botPreviewFailed"));
    return;
  }
  botChannelPreviewPayload = payload;
  renderBotChannelPreview(payload);
  setStatus(t("botPreviewReady", { channel: payload.channel }));
}

async function fetchSelectedProviderModels() {
  const config = state.config;
  const providerName = selectedProviderName(config);
  const provider = selectedProvider(config);
  if (!provider) return;
  if (provider.kind !== "openai_compatible") {
    setProviderModelStatus(t("providerModelsUnsupported"));
    return;
  }

  const baseUrl = envInputValue(provider.base_url_env);
  const apiKey = envInputValue(provider.api_key_env);
  if (!baseUrl || !apiKey) {
    setProviderModelStatus(t("providerModelsNeedValues"));
    return;
  }

  const payload = await requestProviderModels({ providerId: providerName, baseUrl, apiKey });
  if (!payload.ok) {
    setProviderModelStatus(t("providerModelsFailed", { message: payload.error }));
    return;
  }
  providerModelCatalog[providerName] = payload.models;
  renderProviderModelState(providerName, provider);
}

async function fetchCustomProviderModels() {
  if (elements.customProviderKind.value !== "openai_compatible") {
    elements.customProviderModelStatus.textContent = t("providerModelsUnsupported");
    return;
  }
  const baseUrl = elements.customProviderBaseUrlValue.value.trim();
  const apiKey = elements.customProviderApiKeyValue.value.trim();
  if (!baseUrl || !apiKey) {
    elements.customProviderModelStatus.textContent = t("providerModelsNeedValues");
    return;
  }

  const payload = await requestProviderModels({ providerId: "", baseUrl, apiKey });
  if (!payload.ok) {
    elements.customProviderModelStatus.textContent = t("providerModelsFailed", { message: payload.error });
    return;
  }
  customProviderModels = payload.models;
  renderModelOptions(elements.customProviderModelSelect, customProviderModels, elements.customProviderModel.value);
  if (!elements.customProviderModel.value && customProviderModels.length) {
    elements.customProviderModel.value = customProviderModels[0];
  }
  elements.customProviderModelStatus.textContent = t("providerModelsLoaded", { count: payload.models.length });
}

async function requestProviderModels({ providerId, baseUrl, apiKey }) {
  const response = await fetch("/api/providers/models", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      provider_id: providerId,
      base_url: baseUrl,
      api_key: apiKey,
    }),
  });
  const payload = await response.json();
  if (!response.ok) {
    return { ok: false, error: payload.error || response.statusText, models: [] };
  }
  return { ok: true, models: payload.models || [] };
}

function applySelectedProviderModel() {
  const config = state.config;
  const providerName = selectedProviderName(config);
  const provider = selectedProvider(config);
  const model = elements.chatProviderModelSelect.value || elements.quickProviderModelSelect.value || elements.providerModelSelect.value;
  if (!provider || !model) return;

  if (provider.default_model_env) {
    setEnvFieldValue({
      key: provider.default_model_env,
      value: model,
      category: "provider",
      owner: providerName,
      setting: "Default model",
      configKey: "default_model_env",
    });
  } else {
    provider.default_model = model;
    elements.jsonEditor.value = JSON.stringify(config, null, 2);
    renderAll({ keepEditor: true });
  }
  syncProviderModelSelects(model, "chat");
  setStatus(t("providerModelsApplied", { model }));
}

function addCustomProvider() {
  if (!state.config) return;
  const providerId = slugId(elements.customProviderId.value);
  if (!providerId) {
    setStatus(t("invalidJson", { message: "provider id is required" }));
    return;
  }
  if (state.config.providers[providerId]) {
    setStatus(t("invalidJson", { message: `provider already exists: ${providerId}` }));
    return;
  }

  const envPrefix = `DEVICE_AGENT_PROVIDER_${providerId.toUpperCase()}`;
  const provider = {
    kind: elements.customProviderKind.value || "openai_compatible",
    capabilities: [...roles],
  };
  const model = elements.customProviderModel.value.trim();
  if (model) provider.default_model = model;
  if (provider.kind !== "mock") {
    provider.base_url_env = elements.customProviderBaseUrlEnv.value.trim() || `${envPrefix}_BASE_URL`;
    provider.api_key_env = elements.customProviderApiKeyEnv.value.trim() || `${envPrefix}_API_KEY`;
  }

  state.config.providers[providerId] = provider;
  state.config.active_provider = providerId;
  elements.providerSelect.value = providerId;
  addPendingProviderEnvFields(providerId, provider, {
    base_url_env: elements.customProviderBaseUrlValue.value.trim(),
    api_key_env: elements.customProviderApiKeyValue.value.trim(),
  });
  renderAll();
  elements.jsonEditor.value = JSON.stringify(state.config, null, 2);
  setStatus(t("routePreviewUpdated"));
}

function renderAll(options = {}) {
  const config = state.config;
  if (!config) return;

  elements.sourceBadge.textContent = state.source ? sourceLabel(state.source) : t("draft");
  fillProviderSelect(config);
  elements.modeSelect.value = config.mode;
  elements.agentModeSelect.value = config.agents.mode;
  elements.providerSelect.value = config.active_provider || config.default_provider;
  elements.chatModeSelect.value = elements.modeSelect.value;
  elements.chatAgentModeSelect.value = elements.agentModeSelect.value;
  elements.quickProviderSelect.value = elements.providerSelect.value;
  elements.chatProviderSelect.value = elements.providerSelect.value;
  renderSelectedProvider(config);
  renderProviders(config);
  renderAgents(config);
  renderRoutes(state.routes || []);
  renderQuickStart(config);
  updateChatRouteBadge();
  renderDashboard();
  renderWorkbenchHeaderState();
  if (envValueState) renderEnvValues(envValueState);

  if (!options.keepEditor) {
    elements.jsonEditor.value = JSON.stringify(config, null, 2);
  }
}

function showView(viewId) {
  activeView = viewMeta[viewId] ? viewId : "chatView";
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.toggle("active", item.dataset.view === activeView));
  document.querySelectorAll(".view-panel").forEach((item) => item.classList.toggle("active", item.id === activeView));
  if (elements.shell) {
    elements.shell.dataset.activeView = activeView;
  }
  updateViewHeader();
}

function updateViewHeader() {
  const meta = viewMeta[activeView];
  elements.viewEyebrow.textContent = t(meta.eyebrow);
  elements.viewTitle.textContent = t(meta.title);
  elements.viewDescription.textContent = t(meta.description);
  elements.topbarViewTitle.textContent = t(meta.title);
  elements.topbarViewDescription.textContent = t(meta.description);
  renderWorkbenchHeaderState();
}

function renderWorkbenchHeaderState() {
  const config = state.config;
  const providerCount = Object.keys(config?.providers || {}).length;
  const routeCount = (state.routes || []).length;
  const channelCount = (botChannelState?.channels || []).length;
  elements.workbenchProviderCount.textContent = String(providerCount);
  elements.workbenchRouteCount.textContent = String(routeCount);
  elements.workbenchChannelCount.textContent = String(channelCount);

  if (!config) {
    elements.workbenchViewMeta.innerHTML = "";
    elements.topbarSummaryLabel.textContent = t("workbenchKicker");
    elements.topbarSummaryBadge.textContent = t("draft");
    elements.topbarSourceBadge.textContent = state.source ? sourceLabel(state.source) : t("draft");
    elements.topbarModeBadge.textContent = t("unset");
    return;
  }

  const provider = config.active_provider || config.default_provider || t("unset");
  const mode = config.mode || t("unset");
  const agentMode = config.agents?.mode || t("unset");
  elements.workbenchViewMeta.innerHTML = [
    renderWorkbenchMetaChip("workbenchMetaProvider", provider),
    renderWorkbenchMetaChip("workbenchMetaMode", mode),
    renderWorkbenchMetaChip("workbenchMetaAgent", agentMode),
  ].join("");
  elements.topbarSummaryLabel.textContent = provider;
  elements.topbarSummaryBadge.textContent = agentMode;
  elements.topbarSourceBadge.textContent = state.source ? sourceLabel(state.source) : t("draft");
  elements.topbarModeBadge.textContent = mode;
}

function renderWorkbenchMetaChip(labelKey, value) {
  return `
    <span class="workbench-meta-chip">
      <b>${escapeHtml(t(labelKey))}</b>
      <span>${escapeHtml(value)}</span>
    </span>
  `;
}

function initialNavCollapsed() {
  try {
    return localStorage.getItem("device-agent-ui-nav-collapsed") === "1";
  } catch {
    return false;
  }
}

function syncShellChrome() {
  if (!elements.shell) return;
  elements.shell.classList.toggle("shell--nav-collapsed", navCollapsed);
  elements.shell.classList.toggle("shell--nav-drawer-open", navDrawerOpen);
  elements.shell.dataset.activeView = activeView;
  if (elements.navCollapseButton) {
    elements.navCollapseButton.setAttribute("aria-expanded", String(!navCollapsed));
  }
  if (elements.navDrawerToggleButton) {
    elements.navDrawerToggleButton.setAttribute("aria-expanded", String(navDrawerOpen));
  }
}

function setNavCollapsed(collapsed) {
  navCollapsed = Boolean(collapsed);
  try {
    localStorage.setItem("device-agent-ui-nav-collapsed", navCollapsed ? "1" : "0");
  } catch {}
  syncShellChrome();
}

function setNavDrawerOpen(open) {
  navDrawerOpen = Boolean(open);
  syncShellChrome();
}

function closeNavDrawer() {
  if (!navDrawerOpen) return;
  navDrawerOpen = false;
  syncShellChrome();
}

function fillProviderSelect(config) {
  const selected = elements.providerSelect.value || config.active_provider || config.default_provider;
  const options = Object.keys(config.providers)
    .map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`)
    .join("");
  elements.providerSelect.innerHTML = options;
  elements.quickProviderSelect.innerHTML = options;
  elements.chatProviderSelect.innerHTML = options;
  const resolved = config.providers[selected] ? selected : config.default_provider;
  elements.providerSelect.value = resolved;
  elements.quickProviderSelect.value = resolved;
  elements.chatProviderSelect.value = resolved;
}

function selectedProviderName(config = state.config) {
  if (!config) return "";
  const selected = elements.providerSelect.value || config.active_provider || config.default_provider;
  return config.providers?.[selected] ? selected : config.default_provider;
}

function selectedProvider(config = state.config) {
  const name = selectedProviderName(config);
  return name && config?.providers ? config.providers[name] : null;
}

function renderSelectedProvider(config) {
  const name = selectedProviderName(config);
  const provider = selectedProvider(config);
  if (!provider) {
    elements.selectedProviderDetail.innerHTML = "";
    return;
  }
  const caps = (provider.capabilities || []).join(", ") || t("none");
  elements.selectedProviderDetail.innerHTML = renderConfigDetails([
    ["Provider", name],
    ["kind", provider.kind],
    ["default_model", provider.default_model || t("unset")],
    ["default_model_env", provider.default_model_env || t("unset")],
    ["base_url_env", provider.base_url_env || t("unset")],
    ["api_key_env", provider.api_key_env || t("unset")],
    ["capabilities", caps],
  ]);
  renderProviderModelState(name, provider);
}

function renderQuickStart(config) {
  const name = selectedProviderName(config);
  const provider = selectedProvider(config);
  if (!provider) {
    elements.quickProviderBadge.textContent = t("loading");
    elements.quickRouteSummary.innerHTML = "";
    return;
  }

  const route = findRoute(elements.chatRoleSelect.value || "planner");
  elements.quickProviderBadge.textContent = name;
  elements.quickRouteSummary.innerHTML = `
    <div class="quick-route-label">${escapeHtml(t("quickRouteLabel"))}</div>
    <div class="quick-route-main">${escapeHtml(route ? formatRoute(route) : t("chatRoutePending"))}</div>
    <div class="quick-route-steps">
      <span>${escapeHtml(t("quickRouteStep1"))}</span>
      <span>${escapeHtml(t("quickRouteStep2"))}</span>
      <span>${escapeHtml(t("quickRouteStep3"))}</span>
    </div>
  `;
  renderProviderModelState(name, provider);
}

function renderProviders(config) {
  const groups = providerGroups(config.providers);
  elements.providersList.innerHTML = Object.entries(groups)
    .map(([group, providers]) => {
      const items = providers
        .map(([name, provider]) => {
          const caps = (provider.capabilities || []).join(", ") || t("none");
          const model = provider.default_model || provider.default_model_env || t("modelViaAgent");
          const active = name === (config.active_provider || config.default_provider) ? ` · ${t("activeProvider")}` : "";
          return `<div class="item provider-item"><strong>${escapeHtml(name)}${escapeHtml(active)}</strong><span>${escapeHtml(provider.kind)} | ${escapeHtml(model)}</span><span>${escapeHtml(caps)}</span></div>`;
        })
        .join("");
      return `<section class="provider-group"><h3>${escapeHtml(group)}</h3>${items}</section>`;
    })
    .join("");
}

function renderAgents(config) {
  elements.agentsList.innerHTML = Object.entries(config.agents.members)
    .map(([name, agent]) => {
      const provider = agent.provider || config.active_provider || config.default_provider;
      const roleList = (agent.roles || []).join(", ") || t("unassigned");
      const model = agent.model || agent.model_env || t("providerDefault");
      return `<div class="item"><strong>${escapeHtml(name)}</strong><span>${escapeHtml(provider)} | ${escapeHtml(model)}</span><span>${escapeHtml(roleList)}</span></div>`;
    })
    .join("");
}

function renderRoutes(routes) {
  elements.routesList.innerHTML = routes
    .map((route) => {
      const key = `${route.role} -> ${route.agent_id}`;
      const value = `${route.provider_name} | ${route.model || route.model_env || t("unset")}`;
      const secret = route.api_key_configured ? t("apiKeyConfigured") : t("apiKeyNotConfigured");
      return `<div class="item"><strong>${escapeHtml(key)}</strong><span>${escapeHtml(value)}</span><span>${escapeHtml(secret)}</span></div>`;
    })
    .join("");
}

function renderDashboard() {
  const config = state.config;
  if (!config || !elements.dashboardSnapshotList) return;

  const fields = envValueState?.fields || [];
  const providerFields = fields.filter((field) => field.category === "provider" || field.category === "agent" || field.category === "model");
  const channelFields = fields.filter((field) => field.category === "channel" || field.category === "bot");
  const providerMissing = providerFields.filter((field) => !field.configured).length;
  const channelMissing = channelFields.filter((field) => !field.configured).length;
  const providers = Object.keys(config.providers || {});
  const channels = botChannelState?.channels || [];
  const routes = state.routes || [];
  const activeProvider = config.active_provider || config.default_provider || t("unset");
  const botMode = botChannelState?.config?.mode || t("unset");

  elements.dashboardSourceBadge.textContent = state.source ? sourceLabel(state.source) : t("draft");
  elements.dashboardSnapshotList.innerHTML = [
    dashboardMetric(t("dashboardConfigSource"), state.source ? sourceLabel(state.source) : t("draft")),
    dashboardMetric(t("modelMode"), config.mode || t("unset")),
    dashboardMetric(t("activeProvider"), activeProvider),
    dashboardMetric(t("agentMode"), config.agents?.mode || t("unset")),
    dashboardMetric(t("dashboardProviders"), providers.length),
    dashboardMetric(t("dashboardChannels"), channels.length),
    dashboardMetric(
      t("dashboardProviderFields"),
      providerFields.length ? `${providerFields.length - providerMissing}/${providerFields.length} ${t("valueConfigured")}` : t("noEnvFields"),
    ),
    dashboardMetric(
      t("dashboardChannelFields"),
      channelFields.length ? `${channelFields.length - channelMissing}/${channelFields.length} ${t("valueConfigured")}` : t("noEnvFields"),
    ),
    dashboardMetric(t("dashboardRoutes"), routes.length ? t("dashboardRoutesReady", { count: routes.length }) : t("dashboardRoutesMissing")),
    dashboardMetric(t("dashboardBotMode"), botMode),
  ].join("");

  const attention = [];
  if (state.source === "example") attention.push(t("dashboardUsingExampleConfig"));
  if (botChannelState?.source === "example") attention.push(t("dashboardUsingExampleBotConfig"));
  if (providerMissing > 0) attention.push(t("dashboardMissingProviderFields", { count: providerMissing }));
  if (channelMissing > 0) attention.push(t("dashboardMissingChannelFields", { count: channelMissing }));
  if (routes.length === 0) attention.push(t("dashboardRoutesMissing"));

  elements.dashboardAttentionList.innerHTML = attention.length
    ? attention.map((item) => dashboardAttention(item, "warn")).join("")
    : dashboardAttention(t("dashboardNoAttention"), "ok");

  elements.dashboardSourcesList.innerHTML = [
    dashboardSource(t("dashboardConfigPath"), state.path || t("unset")),
    dashboardSource(t("dashboardBotConfig"), botChannelState?.path || envValueState?.bot_path || t("unset")),
    dashboardSource(t("dashboardEnvPath"), envValueState?.path || ".env"),
    dashboardSource(t("dashboardBotSource"), botChannelState?.source ? sourceLabel(botChannelState.source) : t("sourceUnset")),
    dashboardSource(t("dashboardEnvFields"), fields.length),
  ].join("");
}

function dashboardMetric(label, value) {
  return `<div class="dashboard-metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
}

function dashboardAttention(value, kind) {
  return `<div class="attention-item ${escapeHtml(kind)}">${escapeHtml(value)}</div>`;
}

function dashboardSource(label, value) {
  return `<div class="source-row"><span>${escapeHtml(label)}</span><code>${escapeHtml(value)}</code></div>`;
}

function renderEnvValues(payload) {
  const fields = payload.fields || [];
  const providerName = selectedProviderName();
  const channelName = selectedChannelName();
  elements.envValuesBadge.textContent = `${fields.length} .env`;
  elements.envFilePath.textContent = payload.path || ".env";
  renderEnvFieldGroup(elements.envRuntimeFields, fields.filter((field) => field.category === "runtime"));
  const selectedProviderFields = fields.filter((field) => selectedProviderField(field, providerName));
  renderEnvFieldGroup(elements.envModelFields, selectedProviderFields);
  renderEnvFieldGroup(elements.quickProviderFields, selectedProviderFields);
  renderEnvFieldGroup(elements.envBotFields, fields.filter((field) => selectedOwnerField(field, channelName) && (field.category === "channel" || field.category === "bot")));
  renderEnvFieldGroup(elements.envOtherFields, fields.filter((field) => field.category === "other"));
  renderDashboard();
}

function selectedProviderField(field, providerName) {
  if (!providerName) return false;
  if (field.category === "provider" || field.category === "model") {
    return selectedOwnerField(field, providerName);
  }
  if (field.category !== "agent") return false;
  return selectedAgentOwners(providerName).has(field.owner);
}

function selectedAgentOwners(providerName) {
  const config = state.config;
  const owners = new Set();
  if (!config?.agents?.members) return owners;
  Object.entries(config.agents.members).forEach(([agentName, agent]) => {
    const provider = agent.provider || config.active_provider || config.default_provider;
    if (provider === providerName) owners.add(`agent:${agentName}`);
  });
  return owners;
}

function selectedOwnerField(field, owner) {
  if (!owner) return false;
  return field.owner === owner || (field.owners || []).includes(owner);
}

function renderEnvFieldGroup(container, fields) {
  if (fields.length === 0) {
    container.innerHTML = `<p class="empty-note">${escapeHtml(t("noEnvFields"))}</p>`;
    return;
  }
  container.innerHTML = fields.map(renderEnvField).join("");
}

function renderEnvField(field) {
  const owner = field.owners && field.owners.length > 1 ? `${field.owner} +${field.owners.length - 1}` : field.owner;
  const stateLabel = field.configured ? t("valueConfigured") : t("valueMissing");
  const source = envSourceLabel(field.source);
  const marker = field.secret_like ? "sensitive" : field.config_key || field.category;
  return `
    <label class="env-field">
      <span>
        ${escapeHtml(owner)}
        <small>${escapeHtml(field.setting)} · ${escapeHtml(field.key)} · ${escapeHtml(source)}</small>
      </span>
      <input data-env-key="${escapeHtml(field.key)}" type="text" value="${escapeHtml(field.value || "")}" autocomplete="off" spellcheck="false" />
      <em class="${field.configured ? "configured" : "missing"}">${escapeHtml(stateLabel)} · ${escapeHtml(marker)}</em>
    </label>
  `;
}

function envInputValue(key) {
  if (!key) return "";
  let value = "";
  document.querySelectorAll("[data-env-key]").forEach((input) => {
    if (input.dataset.envKey === key) value = input.value.trim();
  });
  if (value) return value;
  const field = (envValueState?.fields || []).find((item) => item.key === key);
  return field?.value?.trim() || "";
}

function setEnvFieldValue({ key, value, category, owner, setting, configKey }) {
  if (!envValueState) {
    envValueState = { fields: [] };
  }
  const existing = (envValueState.fields || []).find((field) => field.key === key);
  if (existing) {
    existing.value = value;
    existing.configured = Boolean(value);
  } else {
    envValueState.fields = [
      ...(envValueState.fields || []),
      {
        key,
        category,
        owner,
        owners: [owner],
        setting,
        config_key: configKey,
        value,
        configured: Boolean(value),
        source: "pending",
        secret_like: /KEY|TOKEN|SECRET|PASSWORD/i.test(key),
      },
    ];
  }
  renderEnvValues(envValueState);
}

function renderModelOptions(select, models, selected = "") {
  const modelList = models || [];
  select.innerHTML = modelList.length
    ? modelList.map((model) => `<option value="${escapeHtml(model)}">${escapeHtml(model)}</option>`).join("")
    : `<option value="">${escapeHtml(t("noModelsLoaded"))}</option>`;
  select.disabled = modelList.length === 0;
  if (selected && modelList.includes(selected)) select.value = selected;
}

function renderProviderModelState(providerName, provider) {
  const modelList = providerModelCatalog[providerName] || [];
  const selected = provider.default_model || envInputValue(provider.default_model_env);
  renderModelOptions(elements.providerModelSelect, modelList, selected);
  renderModelOptions(elements.quickProviderModelSelect, modelList, selected);
  renderModelOptions(elements.chatProviderModelSelect, modelList, selected);
  const status = modelList.length ? t("providerModelsLoaded", { count: modelList.length }) : t("noModelsLoaded");
  elements.providerModelStatus.textContent = status;
  elements.quickProviderModelStatus.textContent = status;
}

function setProviderModelStatus(message) {
  elements.providerModelStatus.textContent = message;
  elements.quickProviderModelStatus.textContent = message;
}

function syncProviderModelSelects(value, source) {
  if (!value) return;
  const providerOptions = Array.from(elements.providerModelSelect.options || []).map((option) => option.value);
  const quickOptions = Array.from(elements.quickProviderModelSelect.options || []).map((option) => option.value);
  const chatOptions = Array.from(elements.chatProviderModelSelect.options || []).map((option) => option.value);
  if (source !== "provider" && providerOptions.includes(value)) {
    elements.providerModelSelect.value = value;
  }
  if (source !== "quick" && quickOptions.includes(value)) {
    elements.quickProviderModelSelect.value = value;
  }
  if (source !== "chat" && chatOptions.includes(value)) {
    elements.chatProviderModelSelect.value = value;
  }
}

function renderConfigDetails(entries) {
  return entries
    .map(([label, value]) => `<div class="config-detail"><span>${escapeHtml(label)}</span><code>${escapeHtml(value || t("unset"))}</code></div>`)
    .join("");
}

function addPendingProviderEnvFields(providerId, provider, seedValues = {}) {
  if (!envValueState) return;
  const existing = new Set((envValueState.fields || []).map((field) => field.key));
  const nextFields = [];
  [
    ["base_url_env", "Base URL"],
    ["api_key_env", "API key"],
    ["default_model_env", "Default model"],
  ].forEach(([configKey, setting]) => {
    const key = provider[configKey];
    if (!key) return;
    if (existing.has(key)) {
      const existingField = envValueState.fields.find((field) => field.key === key);
      if (existingField && seedValues[configKey]) {
        existingField.value = seedValues[configKey];
        existingField.configured = true;
      }
      return;
    }
    existing.add(key);
    const value = seedValues[configKey] || "";
    nextFields.push({
      key,
      category: "provider",
      owner: providerId,
      owners: [providerId],
      setting,
      config_key: configKey,
      value,
      configured: Boolean(value),
        source: "pending",
      secret_like: /KEY|TOKEN|SECRET|PASSWORD/i.test(key),
    });
  });
  if (nextFields.length === 0) return;
  envValueState.fields = [...(envValueState.fields || []), ...nextFields];
  renderEnvValues(envValueState);
}

function renderOpenClawReport(report) {
  const agents = report.imported_agents || [];
  const warnings = report.warnings || [];
  elements.openclawReport.innerHTML = [
    `<div class="item"><strong>${escapeHtml(t("agentsMapped", { count: agents.length }))}</strong><span>${escapeHtml((report.model_refs || []).join(", ") || t("noModelRefs"))}</span></div>`,
    `<div class="item"><strong>${escapeHtml(t("workspaceEvidence"))}</strong><span>${escapeHtml(t("filesFound", { count: (report.workspace_files_found || []).length }))}</span><span>${escapeHtml((report.skipped_secret_paths || []).join(" | "))}</span></div>`,
    ...warnings.map((warning) => `<div class="item"><strong>${escapeHtml(t("warning"))}</strong><span>${escapeHtml(warning)}</span></div>`),
  ].join("");
}

function renderBotChannels(payload) {
  const channels = payload.channels || [];
  const defaultChannel = payload.config.default_channel;
  const selected = elements.botChannelSelect.value || defaultChannel;
  elements.botChannelBadge.textContent = payload.source ? sourceLabel(payload.source) : t("sourceExample");
  elements.botChannelSelect.innerHTML = channels
    .map((channel) => `<option value="${escapeHtml(channel.name)}">${escapeHtml(channel.name)} · ${escapeHtml(channel.kind)}</option>`)
    .join("");
  elements.botChannelSelect.value = channels.find((channel) => channel.name === selected)?.name || channels.find((channel) => channel.name === defaultChannel)?.name || channels[0]?.name || "";
  renderSelectedChannel();
  elements.botChannelsList.innerHTML = channels
    .map((channel) => {
      const status = channel.enabled ? t("enabled") : t("disabled");
      const caps = (channel.capabilities || []).join(", ") || t("noCapabilities");
      return `<div class="item"><strong>${escapeHtml(channel.name)} · ${escapeHtml(channel.kind)}</strong><span>${escapeHtml(status)}</span><span>${escapeHtml(caps)}</span></div>`;
    })
    .join("");
  renderDashboard();
  renderWorkbenchHeaderState();
}

function selectedChannelName() {
  const channels = botChannelState?.channels || [];
  const selected = elements.botChannelSelect.value || botChannelState?.config?.default_channel;
  return channels.find((channel) => channel.name === selected)?.name || channels[0]?.name || "";
}

function renderSelectedChannel() {
  const channelName = selectedChannelName();
  const channel = botChannelState?.config?.channels?.[channelName];
  if (!channel) {
    elements.selectedChannelDetail.innerHTML = "";
    return;
  }
  elements.selectedChannelDetail.innerHTML = renderConfigDetails([
    ["channel", channelName],
    ["kind", channel.kind],
    ["enabled", channel.enabled ? t("enabled") : t("disabled")],
    ["token_env", channel.token_env || t("unset")],
    ["target_env", channel.target_env || t("unset")],
    ["webhook_url_env", channel.webhook_url_env || t("unset")],
    ["secret_env", channel.secret_env || t("unset")],
    ["phone_number_id_env", channel.phone_number_id_env || t("unset")],
    ["api_version_env", channel.api_version_env || t("unset")],
    ["app_id_env", channel.app_id_env || t("unset")],
    ["target_kind", channel.target_kind || t("unset")],
    ["capabilities", (channel.capabilities || []).join(", ") || t("none")],
  ]);
}

function renderBotChannelPreview(payload) {
  elements.botChannelPreview.innerHTML = [
    `<div class="item"><strong>${escapeHtml(payload.channel)} · ${escapeHtml(payload.kind)}</strong><span>${escapeHtml(payload.method)} ${escapeHtml(payload.endpoint || t("gatewaySdk"))}</span></div>`,
    `<div class="item"><strong>${escapeHtml(t("payload"))}</strong><span>${escapeHtml(JSON.stringify(payload.body))}</span></div>`,
    `<div class="item"><strong>${escapeHtml(t("notes"))}</strong><span>${escapeHtml((payload.notes || []).join(" | "))}</span></div>`,
  ].join("");
}

function renderChatSessions() {
  const sessions = chatSessions.length
    ? chatSessions
    : [{ session_id: "default", count: 0, preview: "", provider_name: null, model: null }];
  elements.chatSessionSelect.innerHTML = sessions
    .map((session) => {
      const title = displaySessionTitle(session.session_id);
      const count = Number(session.count || 0);
      return `<option value="${escapeHtml(session.session_id)}">${escapeHtml(`${title} (${count})`)}</option>`;
    })
    .join("");
  if (sessions.some((session) => session.session_id === chatSessionId)) {
    elements.chatSessionSelect.value = chatSessionId;
  }
  elements.chatSessionList.innerHTML = sessions
    .map((session) => {
      const active = session.session_id === chatSessionId ? " active" : "";
      const title = displaySessionTitle(session.session_id);
      const count = t("chatSessionTurns", { count: session.count || 0 });
      const updated = formatCompactTimestamp(session.last_updated);
      const detail = [count, updated].filter(Boolean).join(" · ");
      return `
        <button class="session-pill${active}" type="button" data-session-id="${escapeHtml(session.session_id)}">
          <span class="session-pill__title">${escapeHtml(title)}</span>
          <small>${escapeHtml(detail)}</small>
        </button>
      `;
    })
    .join("");
  const activeSession = sessions.find((session) => session.session_id === chatSessionId);
  elements.chatSessionBadge.textContent = activeSession ? displaySessionTitle(activeSession.session_id) : t("defaultSession");
  elements.chatSessionSummary.innerHTML = activeSession ? renderChatSessionSummary(activeSession) : "";
  elements.chatClearSessionButton.disabled = !activeSession || Number(activeSession.count || 0) === 0;
}

async function loadChatSessions() {
  const response = await fetch("/api/chat/sessions");
  const payload = await response.json();
  if (!response.ok) {
    setStatus(payload.error || t("chatSessionsLoadFailed"));
    return;
  }

  chatSessions = Array.isArray(payload.sessions) ? payload.sessions : [];
  const previousSessionId = chatSessionId;
  if (!chatSessions.some((session) => session.session_id === chatSessionId)) {
    chatSessionId = chatSessions[0]?.session_id || "default";
  }
  renderChatSessions();
  if (chatSessionId !== previousSessionId) {
    await loadChatSession();
  }
}

async function loadChatSession({ announce = true } = {}) {
  const response = await fetch(`/api/chat/session?session_id=${encodeURIComponent(chatSessionId)}`);
  const payload = await response.json();
  if (!response.ok) {
    setStatus(payload.error || t("chatSendFailed"));
    return;
  }
  chatMessages = Array.isArray(payload.messages) ? payload.messages : [];
  renderChat();
  renderChatSessions();
  if (announce && payload.path) {
    setStatus(t("chatContextLoaded", { count: chatMessages.length, path: payload.path }));
  }
}

async function selectChatSession(sessionId) {
  const nextSessionId = (sessionId || "default").trim() || "default";
  if (nextSessionId === chatSessionId) return;
  chatSessionId = nextSessionId;
  renderChatSessions();
  await loadChatSession();
}

async function clearChatSession() {
  const response = await fetch("/api/chat/session/clear", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: chatSessionId }),
  });
  const payload = await response.json();
  if (!response.ok) {
    setStatus(payload.error || t("chatSessionClearFailed"));
    return;
  }

  chatSessions = Array.isArray(payload.sessions) ? payload.sessions : [];
  if (!chatSessions.some((session) => session.session_id === chatSessionId)) {
    chatSessionId = chatSessions[0]?.session_id || "default";
  }
  chatMessages = [];
  renderChat();
  renderChatSessions();
  await loadChatSession({ announce: false });
  setStatus(t("chatSessionCleared", { session: payload.session_id || chatSessionId }));
}

function formatChatError(payload, fallbackMessage) {
  const fallback = payload?.error || fallbackMessage || t("chatSendFailed");
  if (!payload || payload.error_kind !== "provider_model_rejected") {
    return fallback;
  }

  const lines = [
    t("chatModelRejected", {
      provider: payload.provider_name || t("unset"),
      model: payload.model || payload.configured_model || t("unset"),
    }),
  ];

  if (payload.provider_message) {
    lines.push(t("chatModelRejectedProviderMessage", { message: payload.provider_message }));
  }
  if (Array.isArray(payload.tried_models) && payload.tried_models.length) {
    lines.push(t("chatModelRejectedTried", { models: payload.tried_models.join(", ") }));
  }
  if (payload.suggested_transport_model) {
    lines.push(t("chatModelRejectedHintTransport", { model: payload.suggested_transport_model }));
  }
  lines.push(t("chatModelRejectedHintFetch"));
  return lines.join("\n");
}

async function sendChatMessage() {
  const message = elements.chatInput.value.trim();
  if (!message) return;
  const role = elements.chatRoleSelect.value;
  const requestTimestamp = new Date().toISOString();
  chatMessages.push({ sender: "user", text: message, role, timestamp: requestTimestamp });
  const placeholder = { sender: "assistant", role, text: t("chatSending"), pending: true, timestamp: requestTimestamp };
  chatMessages.push(placeholder);
  elements.chatInput.value = "";
  renderChat();
  elements.chatSendButton.disabled = true;

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: chatSessionId,
        role,
        message,
        config: state.config,
        env_values: collectEnvInputValues(),
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      const error = new Error(formatChatError(payload, t("chatSendFailed")));
      error.payload = payload;
      throw error;
    }

    placeholder.pending = false;
    placeholder.text = payload.reply || "";
    placeholder.mode = payload.mode;
    placeholder.route = payload.route || null;
    placeholder.role = role;
    placeholder.timestamp = new Date().toISOString();
    renderChat();
    elements.chatRouteBadge.textContent = payload.route ? formatRoute(payload.route) : t("chatRoutePending");
    setStatus(t("chatResponseReady", { provider: payload.provider_name || t("unset"), model: payload.model || t("unset") }));
    await loadChatSessions();
  } catch (error) {
    placeholder.pending = false;
    placeholder.error = true;
    placeholder.text = error.message || t("chatSendFailed");
    placeholder.route = error.payload?.route || findRoute(role);
    placeholder.mode = error.payload?.route?.mode || placeholder.route?.mode || "live";
    placeholder.timestamp = new Date().toISOString();
    renderChat();
    elements.chatRouteBadge.textContent = placeholder.route ? formatRoute(placeholder.route) : t("chatRoutePending");
    setStatus(placeholder.text);
  } finally {
    elements.chatSendButton.disabled = false;
    elements.chatInput.focus();
  }
}

function renderChat() {
  if (chatMessages.length === 0) {
    elements.chatLog.innerHTML = `<div class="chat-empty">${escapeHtml(t("chatEmpty"))}</div>`;
    return;
  }
  elements.chatLog.innerHTML = chatMessages
    .map((message, index) => renderChatMessageGroup(message, index))
    .join("");
  elements.chatLog.scrollTop = elements.chatLog.scrollHeight;
}

function displaySessionTitle(sessionId) {
  return sessionId === "default" ? t("defaultSession") : sessionId;
}

function renderChatSessionSummary(session) {
  const updated = formatCompactTimestamp(session.last_updated);
  const summary = [
    displaySessionTitle(session.session_id),
    t("chatSessionTurns", { count: session.count || 0 }),
    updated ? t("chatSessionUpdated", { time: updated }) : "",
  ]
    .filter(Boolean)
    .join(" · ");
  return `
    <p class="chat-session-summary-line">${escapeHtml(summary)}</p>
  `;
}

function formatCompactTimestamp(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat(locale === "zh-CN" ? "zh-CN" : "en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function renderChatMessageGroup(message, index) {
  const kind = message.sender === "user" ? "user" : "assistant";
  const classes = ["chat-group", kind];
  if (message.pending) classes.push("pending");
  if (message.error) classes.push("error");

  return `
    <article class="${classes.join(" ")}">
      <div class="chat-avatar ${kind}" aria-hidden="true">${renderChatAvatar(kind)}</div>
      <div class="chat-group-messages">
        <div class="chat-bubble">${renderChatTextBlock(message.text || "")}</div>
        <div class="chat-group-footer">
          <span class="chat-sender-name">${escapeHtml(resolveChatSenderName(message, index))}</span>
          ${renderChatFooterTimestamp(message)}
          ${renderChatStatePill(message)}
        </div>
      </div>
    </article>
  `;
}

function renderChatAvatar(kind) {
  if (kind === "user") {
    return `
      <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
        <circle cx="12" cy="8" r="4"></circle>
        <path d="M20 21a8 8 0 1 0-16 0"></path>
      </svg>
    `;
  }
  return `
    <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
      <path d="M12 15.5A3.5 3.5 0 0 1 8.5 12 3.5 3.5 0 0 1 12 8.5a3.5 3.5 0 0 1 3.5 3.5 3.5 3.5 0 0 1-3.5 3.5m7.43-2.53a7.76 7.76 0 0 0 .07-1 7.76 7.76 0 0 0-.07-.97l2.11-1.63a.5.5 0 0 0 .12-.64l-2-3.46a.5.5 0 0 0-.61-.22l-2.49 1a7.15 7.15 0 0 0-1.69-.98l-.38-2.65A.49.49 0 0 0 14 2h-4a.49.49 0 0 0-.49.42l-.38 2.65a7.15 7.15 0 0 0-1.69.98l-2.49-1a.5.5 0 0 0-.61.22l-2 3.46a.49.49 0 0 0 .12.64L4.57 11a7.9 7.9 0 0 0 0 1.94l-2.11 1.69a.49.49 0 0 0-.12.64l2 3.46a.5.5 0 0 0 .61.22l2.49-1c.52.4 1.08.72 1.69.98l.38 2.65c.05.24.26.42.49.42h4c.23 0 .44-.18.49-.42l.38-2.65a7.15 7.15 0 0 0 1.69-.98l2.49 1a.5.5 0 0 0 .61-.22l2-3.46a.49.49 0 0 0-.12-.64z"></path>
    </svg>
  `;
}

function renderChatContextCard(message) {
  if (message.sender === "user") return "";
  const route = message.route;
  if (!route) return "";

  const detail = [route.provider_name, route.model || route.model_env, message.role || route.role].filter(Boolean).join(" · ");
  const summary = [route.agent_id, message.mode || route.mode].filter(Boolean).join(" · ");
  const stateLabel = message.error ? t("chatTurnError") : message.pending ? t("chatTurnPending") : message.mode || route.mode || t("unset");

  return `
    <div class="chat-tool-card">
      <div class="chat-tool-card__header">
        <div class="chat-tool-card__title">
          <span class="chat-tool-card__icon" aria-hidden="true">
            <svg viewBox="0 0 24 24">
              <path d="M19.439 7.85c-.049.322.059.648.289.878l1.568 1.568c.47.47.706 1.087.706 1.704s-.235 1.233-.706 1.704l-1.611 1.611a.98.98 0 0 1-.837.276c-.47-.07-.802-.48-.968-.925a2.501 2.501 0 1 0-3.214 3.214c.446.166.855.497.925.968a.979.979 0 0 1-.276.837l-1.61 1.61a2.404 2.404 0 0 1-1.705.707 2.402 2.402 0 0 1-1.704-.706l-1.568-1.568a1.026 1.026 0 0 0-.877-.29c-.493.074-.84.504-1.02.968a2.5 2.5 0 1 1-3.237-3.237c.464-.18.894-.527.967-1.02a1.026 1.026 0 0 0-.289-.877l-1.568-1.568A2.402 2.402 0 0 1 1.998 12c0-.617.236-1.234.706-1.704L4.23 8.77c.24-.24.581-.353.917-.303.515.076.874.54 1.02 1.02a2.5 2.5 0 1 0 3.237-3.237c-.48-.146-.944-.505-1.02-1.02a.98.98 0 0 1 .303-.917l1.526-1.526A2.402 2.402 0 0 1 11.998 2c.617 0 1.234.236 1.704.706l1.568 1.568c.23.23.556.338.877.29.493-.074.84-.504 1.02-.968a2.5 2.5 0 1 1 3.236 3.236c-.464.18-.894.527-.967 1.02Z"></path>
            </svg>
          </span>
          <span>${escapeHtml(t("chatRouteContext"))}</span>
        </div>
        <span class="chat-tool-card__action">${escapeHtml(stateLabel)}</span>
      </div>
      ${detail ? `<div class="chat-tool-card__detail">${escapeHtml(detail)}</div>` : ""}
      ${summary ? `<div class="chat-tool-card__inline">${escapeHtml(summary)}</div>` : ""}
    </div>
  `;
}

function renderChatTextBlock(text) {
  const safe = escapeHtml(text || "").replace(/\n/g, "<br>");
  return `<div class="chat-text">${safe}</div>`;
}

function resolveChatSenderName(message, index) {
  if (message.sender === "user") {
    return t("chatUserLabel");
  }
  return t("chatAssistantLabel");
}

function renderChatFooterTimestamp(message) {
  const timestamp = formatMessageTimestamp(message.timestamp);
  return timestamp ? `<span class="chat-group-timestamp">${escapeHtml(timestamp)}</span>` : "";
}

function renderChatFooterMeta(message) {
  if (message.sender === "user") {
    const role = message.role || "";
    if (!role) return "";
    return `<span class="msg-meta"><span class="msg-meta__item">${escapeHtml(`role:${role}`)}</span></span>`;
  }

  const route = message.route || {};
  const parts = [
    route.provider_name ? `provider:${route.provider_name}` : "",
    route.model || route.model_env ? `model:${route.model || route.model_env}` : "",
    message.role || route.role ? `role:${message.role || route.role}` : "",
    message.mode || route.mode ? `mode:${message.mode || route.mode}` : "",
  ].filter(Boolean);

  if (!parts.length) return "";
  return `<span class="msg-meta">${parts.map((part) => `<span class="msg-meta__item">${escapeHtml(part)}</span>`).join("")}</span>`;
}

function renderChatStatePill(message) {
  if (!message.pending && !message.error) return "";
  const label = message.error ? t("chatTurnError") : t("chatTurnPending");
  const stateClass = message.error ? " error" : " pending";
  return `<span class="chat-group-state${stateClass}">${escapeHtml(label)}</span>`;
}

function formatMessageTimestamp(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat(locale === "zh-CN" ? "zh-CN" : "en-US", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function renderChatDetailChip(labelKey, value) {
  return `
    <span class="chat-detail-chip">
      <b>${escapeHtml(t(labelKey))}</b>
      <span>${escapeHtml(value)}</span>
    </span>
  `;
}

function updateChatRouteBadge() {
  const route = findRoute(elements.chatRoleSelect.value);
  elements.chatRouteBadge.textContent = route ? formatRoute(route) : t("chatRoutePending");
  elements.chatCurrentRoute.innerHTML = route
    ? `
        <div class="chat-route-inline">
          <strong>${escapeHtml(t("chatRouteContext"))}</strong>
          <div class="chat-route-inline__chips">
            ${renderRouteStatCard(route.provider_name || t("unset"))}
            ${renderRouteStatCard(route.model || route.model_env || t("unset"))}
            ${renderRouteStatCard(route.role || t("unset"))}
            ${renderRouteStatCard(route.mode || t("unset"))}
            ${renderRouteStatCard(route.agent_id || t("unset"))}
          </div>
        </div>
      `
    : `<p class="empty-note">${escapeHtml(t("chatRoutePending"))}</p>`;
  if (state.config) {
    renderQuickStart(state.config);
  }
}

function renderRouteStatCard(value) {
  return `
    <span class="chat-route-chip">${escapeHtml(value)}</span>
  `;
}

function findRoute(role) {
  return (state.routes || []).find((route) => route.role === role) || null;
}

function formatRoute(route) {
  if (!route) return t("chatRoutePending");
  return `${route.agent_id} -> ${route.provider_name} / ${route.model || route.model_env || t("unset")}`;
}

function collectEnvInputValues() {
  const values = {};
  document.querySelectorAll("[data-env-key]").forEach((input) => {
    values[input.dataset.envKey] = input.value;
  });
  return values;
}

function providerGroups(providers) {
  return Object.entries(providers).reduce((groups, entry) => {
    const group = providerGroupName(entry[1]);
    groups[group] = groups[group] || [];
    groups[group].push(entry);
    return groups;
  }, {});
}

function providerGroupName(provider) {
  const model = provider.default_model || "";
  const kind = provider.kind || "custom";
  if (kind === "mock" || /(^|[/_-])(local|custom|ollama|lmstudio|vllm)([/_-]|$)/i.test(model)) {
    return "custom";
  }
  if (model.includes("/")) return model.split("/", 1)[0] || "custom";
  return kind;
}

function applyControlsToConfig(config = state.config) {
  if (!config) return;
  config.mode = elements.modeSelect.value;
  config.agents.mode = elements.agentModeSelect.value;
  config.active_provider = elements.providerSelect.value;
}

function applyRoutingControls({ mode, agentMode, provider } = {}) {
  if (mode) {
    elements.modeSelect.value = mode;
    elements.chatModeSelect.value = mode;
  }
  if (agentMode) {
    elements.agentModeSelect.value = agentMode;
    elements.chatAgentModeSelect.value = agentMode;
  }
  if (provider) {
    elements.providerSelect.value = provider;
    elements.quickProviderSelect.value = provider;
    elements.chatProviderSelect.value = provider;
  }
  applyControlsToConfig();
  renderAll({ keepEditor: true });
  if (envValueState) renderEnvValues(envValueState);
  if (state.config) {
    void previewRoutesForConfig(state.config, { silent: true });
  }
}

function slugId(value) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function configFromEditor() {
  try {
    return JSON.parse(elements.jsonEditor.value);
  } catch (error) {
    setStatus(t("invalidJson", { message: error.message }));
    return null;
  }
}

function setStatus(message) {
  elements.statusLine.textContent = message;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function initialLocale() {
  const saved = localStorage.getItem("device-agent-ui-language");
  if (saved === "en" || saved === "zh-CN") return saved;
  return "zh-CN";
}

function sourceLabel(source) {
  if (source === "local") return t("sourceLocal");
  if (source === "example") return t("sourceExample");
  return source || t("draft");
}

function envSourceLabel(source) {
  if (source === "env_file") return t("sourceEnvFile");
  if (source === "process") return t("sourceProcess");
  if (source === "pending") return t("sourcePending");
  if (source === "unset") return t("sourceUnset");
  return source || t("sourceUnset");
}

function translatePage() {
  document.documentElement.lang = locale;
  elements.languageSelect.value = locale;
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-aria-label]").forEach((node) => {
    node.setAttribute("aria-label", t(node.dataset.i18nAriaLabel));
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
    node.setAttribute("placeholder", t(node.dataset.i18nPlaceholder));
  });
}

function t(key, params = {}) {
  const table = translations[locale] || translations.en;
  const template = table[key] || translations.en[key] || key;
  return Object.entries(params).reduce((text, [name, value]) => text.replaceAll(`{${name}}`, String(value)), template);
}

translatePage();
renderModelOptions(elements.providerModelSelect, []);
renderModelOptions(elements.customProviderModelSelect, []);
renderChatSessions();
showView(activeView);
renderChat();
loadOpenClawDefaults();
loadBotChannels();
loadEnvValues();
loadConfig();
loadChatSessions();
loadChatSession();
