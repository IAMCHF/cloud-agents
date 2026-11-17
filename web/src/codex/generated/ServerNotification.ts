/**
 * 本文件由 scripts/codex-schema.mjs 自动生成，请勿手改。
 * 来源：codex-cli 0.167.0 `app-server generate-json-schema`。
 * 重新生成：`pnpm codex:schema`；漂移校验：`pnpm codex:schema:check`。
 */

/**
 * Notification sent from the server to the client.
 */
export type ServerNotification = {
  /**
   * Unix timestamp (in milliseconds) when app-server emitted this notification.
   */
  emittedAtMs?: number;
} & (
  | ErrorNotification
  | ThreadStartedNotification
  | ThreadStatusChangedNotification
  | ThreadReadStateChangedNotification
  | ThreadArchivedNotification
  | ThreadDeletedNotification
  | ThreadUnarchivedNotification
  | ThreadClosedNotification
  | ThreadRevertedNotification
  | SkillsChangedNotification
  | ThreadNameUpdatedNotification
  | ThreadSectionChangedNotification
  | ThreadAttachmentUpdatedNotification
  | ThreadGoalUpdatedNotification
  | ThreadPredictionUpdatedNotification
  | ThreadGoalClearedNotification
  | ThreadQueueChangedNotification
  | ProjectChangedNotification
  | ThreadProjectUpdatedNotification
  | ThreadEnvironmentConnectedNotification
  | ThreadEnvironmentDisconnectedNotification
  | ThreadSettingsUpdatedNotification
  | ThreadTokenUsageUpdatedNotification
  | TurnStartedNotification
  | HookStartedNotification
  | TurnCompletedNotification
  | HookCompletedNotification
  | TurnDiffUpdatedNotification
  | TurnPlanUpdatedNotification
  | ItemStartedNotification
  | ItemAutoApprovalReviewStartedNotification
  | ItemAutoApprovalReviewCompletedNotification
  | AutoApprovalReviewStrictReviewRequiredNotification
  | ItemCompletedNotification
  | ItemAgentMessageDeltaNotification
  | ItemPlanDeltaNotification
  | CommandExecOutputDeltaNotification
  | ProcessOutputDeltaNotification
  | ProcessExitedNotification
  | ItemCommandExecutionOutputDeltaNotification
  | ItemCommandExecutionTerminalInteractionNotification
  | ItemFileChangeOutputDeltaNotification
  | ItemFileChangePatchUpdatedNotification
  | ServerRequestResolvedNotification
  | ItemMcpToolCallProgressNotification
  | McpServerOauthLoginCompletedNotification
  | McpServerStartupStatusUpdatedNotification
  | McpServerEventStreamNotificationNotification
  | AccountUpdatedNotification
  | AccountGatewayOAuthChangedNotification
  | AccountRateLimitsUpdatedNotification
  | AppListUpdatedNotification
  | RemoteControlStatusChangedNotification
  | ExternalAgentConfigImportProgressNotification
  | ExternalAgentConfigImportCompletedNotification
  | FsChangedNotification
  | ItemReasoningSummaryTextDeltaNotification
  | ItemReasoningSummaryPartAddedNotification
  | ItemReasoningTextDeltaNotification
  | ThreadCompactedNotification
  | ModelReroutedNotification
  | ModelVerificationNotification
  | ModelProviderAuthRecoveryStartedNotification
  | ModelProviderAuthRecoveryCompletedNotification
  | TurnModerationMetadataNotification
  | ModelSafetyBufferingUpdatedNotification
  | WarningNotification
  | GuardianWarningNotification
  | DeprecationNoticeNotification
  | ConfigWarningNotification
  | FuzzyFileSearchSessionUpdatedNotification
  | FuzzyFileSearchSessionCompletedNotification
  | ThreadRealtimeStartedNotification
  | ThreadRealtimeItemAddedNotification
  | ThreadRealtimeItemStartedNotification
  | ThreadRealtimeItemTranscriptDeltaNotification
  | ThreadRealtimeItemCompletedNotification
  | ThreadRealtimeTranscriptDeltaNotification
  | ThreadRealtimeTranscriptDoneNotification
  | ThreadRealtimeOutputAudioDeltaNotification
  | ThreadRealtimeSdpNotification
  | ThreadRealtimeErrorNotification
  | ThreadRealtimeClosedNotification
  | WindowsWorldWritableWarningNotification
  | WindowsSandboxSetupCompletedNotification
  | AccountLoginCompletedNotification
);
export type ErrorNotificationMethod = "error";
/**
 * This translation layer make sure that we expose codex error code in camel case.
 *
 * When an upstream HTTP status is available (for example, from the Responses API or a provider), it is forwarded in `httpStatusCode` on the relevant `codexErrorInfo` variant.
 */
export type CodexErrorInfo =
  | (
      | "contextWindowExceeded"
      | "sessionBudgetExceeded"
      | "usageLimitExceeded"
      | "rateLimitExceeded"
      | "flexUnavailable"
      | "serverOverloaded"
      | "modelNotFound"
      | "policyCapacityUnavailable"
      | "cyberPolicy"
      | "misalignmentPolicyViolation"
      | "tooManyDenials"
      | "internalServerError"
      | "unauthorized"
      | "badRequest"
      | "threadRollbackFailed"
      | "sandboxError"
      | "other"
    )
  | HttpConnectionFailedCodexErrorInfo
  | ResponseStreamConnectionFailedCodexErrorInfo
  | ResponseStreamDisconnectedCodexErrorInfo
  | ResponseTooManyFailedAttemptsCodexErrorInfo
  | ActiveTurnNotSteerableCodexErrorInfo
  | (string | {});
export type NonSteerableTurnKind = "review" | "compact";
export type ThreadStartedNotificationMethod = "thread/started";
/**
 * A path that is guaranteed to be absolute and normalized (though it is not guaranteed to be canonicalized or exist on the filesystem).
 *
 * IMPORTANT: When deserializing an `AbsolutePathBuf`, a base path must be set using [AbsolutePathBufGuard::new]. If no base path is set, the deserialization will fail unless the path being deserialized is already absolute.
 */
export type AbsolutePathBuf = string;
export type ThreadHistoryMode = "legacy" | "paginated";
/**
 * A non-empty reasoning effort value advertised by the model.
 */
export type ReasoningEffort = string;
export type SessionSource =
  ("cli" | "vscode" | "exec" | "appServer" | "unknown") | CustomSessionSource | SubAgentSessionSource;
export type SubAgentSource =
  ("review" | "compact" | "memory_consolidation") | ThreadSpawnSubAgentSource | OtherSubAgentSource;
export type AgentPath = string;
export type ThreadId = string;
export type ThreadStatus = NotLoadedThreadStatus | IdleThreadStatus | SystemErrorThreadStatus | ActiveThreadStatus;
export type NotLoadedThreadStatusType = "notLoaded";
export type IdleThreadStatusType = "idle";
export type SystemErrorThreadStatusType = "systemError";
export type ThreadActiveFlag = "waitingOnApproval" | "waitingOnUserInput";
export type ActiveThreadStatusType = "active";
export type ThreadSource = string;
/**
 * A thread item and its recorded lifecycle times. The payload stays flat on the wire.
 */
export type ThreadItem = {
  /**
   * Unix timestamp in milliseconds when the item completed, if recorded.
   */
  completedAtMs?: number | null;
  /**
   * Unix timestamp in milliseconds when the item started, if recorded.
   */
  startedAtMs?: number | null;
} & ThreadItem1;
export type ThreadItem1 =
  | UserMessageThreadItem
  | HookPromptThreadItem
  | AgentMessageThreadItem
  | FunctionCallOutputThreadItem
  | PlanThreadItem
  | ReasoningThreadItem
  | CommandExecutionThreadItem
  | FileChangeThreadItem
  | McpToolCallThreadItem
  | DynamicToolCallThreadItem
  | CollabAgentToolCallThreadItem
  | SubAgentActivityThreadItem
  | WebSearchThreadItem
  | ImageViewThreadItem
  | SleepThreadItem
  | ImageGenerationThreadItem
  | EnteredReviewModeThreadItem
  | ExitedReviewModeThreadItem
  | ContextCompactionThreadItem;
export type UserInput =
  | TextUserInput
  | ImageUserInput
  | LocalImageUserInput
  | AudioUserInput
  | LocalAudioUserInput
  | SkillUserInput
  | MentionUserInput;
export type TextUserInputType = "text";
export type ImageUserInput = (UrlUserInput | FileIdUserInput) & {
  detail?: ImageDetail | null;
  type: ImageUserInputType;
};
export type ImageDetail = "auto" | "low" | "high" | "original";
export type ImageUserInputType = "image";
export type LocalImageUserInputType = "localImage";
export type AudioUserInput = (UrlUserInput1 | FileIdUserInput1) & {
  type: AudioUserInputType;
};
export type AudioUserInputType = "audio";
export type LocalAudioUserInputType = "localAudio";
export type SkillUserInputType = "skill";
export type MentionUserInputType = "mention";
export type UserMessageThreadItemType = "userMessage";
export type HookPromptThreadItemType = "hookPrompt";
export type AgentMessageDelivery = "async";
/**
 * Classifies assistant text as commentary, a partial answer, or a terminal answer.
 *
 * Providers do not emit this consistently, so callers must treat `None` as "phase unknown" and keep compatibility behavior for legacy models.
 */
export type MessagePhase = "commentary" | "partial_answer" | "final_answer";
export type AgentMessageThreadItemType = "agentMessage";
export type FunctionCallOutputBody = string | FunctionCallOutputContentItem[];
/**
 * Responses API compatible content items that can be returned by a tool call. This is a subset of ContentItem with the types we support as function call outputs.
 */
export type FunctionCallOutputContentItem =
  | InputTextFunctionCallOutputContentItem
  | InputImageFunctionCallOutputContentItem
  | InputAudioFunctionCallOutputContentItem
  | EncryptedContentFunctionCallOutputContentItem;
export type InputTextFunctionCallOutputContentItemType = "input_text";
export type InputImageFunctionCallOutputContentItem = (
  ImageUrlFunctionCallOutputContentItem | FileIdFunctionCallOutputContentItem
) & {
  detail?: ImageDetail | null;
  type: InputImageFunctionCallOutputContentItemType;
};
export type InputImageFunctionCallOutputContentItemType = "input_image";
export type InputAudioFunctionCallOutputContentItemType = "input_audio";
export type EncryptedContentFunctionCallOutputContentItemType = "encrypted_content";
export type FunctionCallOutputThreadItemType = "functionCallOutput";
export type PlanThreadItemType = "plan";
export type ReasoningThreadItemType = "reasoning";
export type CommandAction = ReadCommandAction | ListFilesCommandAction | SearchCommandAction | UnknownCommandAction;
export type LegacyAppPathString = string;
export type ReadCommandActionType = "read";
export type ListFilesCommandActionType = "listFiles";
export type SearchCommandActionType = "search";
export type UnknownCommandActionType = "unknown";
export type CommandExecutionSource = "agent" | "userShell" | "unifiedExecStartup" | "unifiedExecInteraction";
export type CommandExecutionStatus = "inProgress" | "completed" | "failed" | "declined";
export type CommandExecutionThreadItemType = "commandExecution";
export type PatchChangeKind = AddPatchChangeKind | DeletePatchChangeKind | UpdatePatchChangeKind;
export type AddPatchChangeKindType = "add";
export type DeletePatchChangeKindType = "delete";
export type UpdatePatchChangeKindType = "update";
export type PatchApplyStatus = "inProgress" | "completed" | "failed" | "declined";
export type FileChangeThreadItemType = "fileChange";
export type McpAppDisplayMode = "inline" | "fullscreen";
export type McpToolCallStatus = "inProgress" | "completed" | "failed";
export type McpToolCallThreadItemType = "mcpToolCall";
export type DynamicToolCallOutputContentItem =
  | InputTextDynamicToolCallOutputContentItem
  | InputImageDynamicToolCallOutputContentItem
  | InputAudioDynamicToolCallOutputContentItem;
export type InputTextDynamicToolCallOutputContentItemType = "inputText";
export type InputImageDynamicToolCallOutputContentItemType = "inputImage";
export type InputAudioDynamicToolCallOutputContentItemType = "inputAudio";
export type DynamicToolCallStatus = "inProgress" | "completed" | "failed";
export type DynamicToolCallThreadItemType = "dynamicToolCall";
export type CollabAgentStatus =
  "pendingInit" | "running" | "interrupted" | "completed" | "errored" | "shutdown" | "notFound";
export type CollabAgentToolCallStatus = "inProgress" | "completed" | "failed" | "interrupted";
export type CollabAgentTool =
  | "spawnAgent"
  | "sendInput"
  | "resumeAgent"
  | "wait"
  | "closeAgent"
  | "sendMessage"
  | "followupTask"
  | "interruptAgent"
  | "listAgents";
export type CollabAgentToolCallThreadItemType = "collabAgentToolCall";
export type SubAgentActivityKind = "started" | "interacted" | "interrupted" | "completed";
export type SubAgentActivityThreadItemType = "subAgentActivity";
export type WebSearchAction =
  SearchWebSearchAction | OpenPageWebSearchAction | FindInPageWebSearchAction | OtherWebSearchAction;
export type SearchWebSearchActionType = "search";
export type OpenPageWebSearchActionType = "openPage";
export type FindInPageWebSearchActionType = "findInPage";
export type OtherWebSearchActionType = "other";
export type WebSearchThreadItemType = "webSearch";
export type ImageViewThreadItemType = "imageView";
export type SleepThreadItemType = "sleep";
/**
 * Either inline generated-image data or its durable attachment-store identity.
 *
 * `File` must remain first so rollouts written during the migration, which contain both an empty `result` and a `fileId`, retain the file reference when deserialized.
 */
export type ImageGenerationThreadItem = (FileIdThreadItem | ResultThreadItem) & {
  failure?: ImageGenerationFailure | null;
  /**
   * Image generation identifier for the generated image, when provided by the image backend.
   */
  generationId?: string | null;
  id: string;
  /**
   * Observed local inputs for a completed generation, absent on older items.
   */
  inputImages?: ImageGenerationInputImage[];
  revisedPrompt?: string | null;
  savedPath?: AbsolutePathBuf | null;
  status: string;
  transparentBackground?: boolean | null;
  type: ImageGenerationThreadItemType;
};
export type ImageGenerationFailure = UsageLimitExceededImageGenerationFailure;
export type UsageLimitExceededImageGenerationFailureType = "usageLimitExceeded";
export type ImageGenerationThreadItemType = "imageGeneration";
export type EnteredReviewModeThreadItemType = "enteredReviewMode";
export type ExitedReviewModeThreadItemType = "exitedReviewMode";
export type ContextCompactionThreadItemType = "contextCompaction";
export type TurnItemsView = "notLoaded" | "summary" | "full";
export type TurnStatus = "completed" | "interrupted" | "failed" | "inProgress";
export type ThreadStatusChangedNotificationMethod = "thread/status/changed";
export type ThreadReadStateChangedNotificationMethod = "thread/readState/changed";
export type ThreadUnreadPosition = ThreadStartThreadUnreadPosition | TurnThreadUnreadPosition;
export type ThreadStartThreadUnreadPositionType = "threadStart";
export type TurnThreadUnreadPositionType = "turn";
export type ThreadArchivedNotificationMethod = "thread/archived";
export type ThreadDeletedNotificationMethod = "thread/deleted";
export type ThreadUnarchivedNotificationMethod = "thread/unarchived";
export type ThreadClosedNotificationMethod = "thread/closed";
export type ThreadRevertedNotificationMethod = "thread/reverted";
export type SkillsChangedNotificationMethod = "skills/changed";
export type ThreadNameUpdatedNotificationMethod = "thread/name/updated";
export type ThreadSectionChangedNotificationMethod = "thread/section/changed";
export type ThreadAttachmentUpdatedNotificationMethod = "thread/attachment/updated";
/**
 * The persisted attachment change represented by a notification.
 */
export type ThreadAttachmentOperation = "created" | "deleted";
export type ThreadGoalUpdatedNotificationMethod = "thread/goal/updated";
export type ThreadGoalStatus = "active" | "paused" | "blocked" | "usageLimited" | "budgetLimited" | "complete";
export type ThreadPredictionUpdatedNotificationMethod = "thread/prediction/updated";
export type ThreadPredictionResult = CompletedThreadPredictionResult | FailedThreadPredictionResult;
export type CompletedThreadPredictionResultType = "completed";
export type FailedThreadPredictionResultType = "failed";
export type ThreadGoalClearedNotificationMethod = "thread/goal/cleared";
export type ThreadQueueChangedNotificationMethod = "thread/queue/changed";
export type ProjectChangedNotificationMethod = "project/changed";
export type ProjectChangeType = "created" | "updated" | "deleted";
export type ThreadProjectUpdatedNotificationMethod = "thread/project/updated";
export type ThreadEnvironmentConnectedNotificationMethod = "thread/environment/connected";
export type ThreadEnvironmentDisconnectedNotificationMethod = "thread/environment/disconnected";
export type ThreadSettingsUpdatedNotificationMethod = "thread/settings/updated";
export type AskForApproval = ("untrusted" | "on-request" | "never") | GranularAskForApproval;
/**
 * Configures who approval requests are routed to for review. Examples include sandbox escapes, blocked network access, MCP approval prompts, and ARC escalations. Defaults to `user`. `auto_review` uses a carefully prompted subagent to gather relevant context and apply a risk-based decision framework before approving or denying the request. The legacy value `guardian_subagent` is accepted for compatibility.
 */
export type ApprovalsReviewer = "user" | "auto_review" | "guardian_subagent";
/**
 * Initial collaboration mode to use when the TUI starts.
 */
export type ModeKind = "plan" | "default";
/**
 * Deprecated: `friendly` and `pragmatic` no longer select a style.
 */
export type Personality = "none" | "friendly" | "pragmatic";
export type SandboxPolicy =
  DangerFullAccessSandboxPolicy | ReadOnlySandboxPolicy | ExternalSandboxSandboxPolicy | WorkspaceWriteSandboxPolicy;
export type DangerFullAccessSandboxPolicyType = "dangerFullAccess";
export type ReadOnlySandboxPolicyType = "readOnly";
export type NetworkAccess = "restricted" | "enabled";
export type ExternalSandboxSandboxPolicyType = "externalSandbox";
export type WorkspaceWriteSandboxPolicyType = "workspaceWrite";
/**
 * A summary of the reasoning performed by the model. This can be useful for debugging and understanding the model's reasoning process. See https://platform.openai.com/docs/guides/reasoning?api-mode=responses#reasoning-summaries
 */
export type ReasoningSummary = ("auto" | "concise" | "detailed") | "none";
export type ThreadTokenUsageUpdatedNotificationMethod = "thread/tokenUsage/updated";
export type TurnStartedNotificationMethod = "turn/started";
export type HookStartedNotificationMethod = "hook/started";
export type HookOutputEntryKind = "warning" | "stop" | "feedback" | "context" | "error";
export type HookEventName =
  | "preModelRequest"
  | "postModelRequest"
  | "preToolUse"
  | "permissionRequest"
  | "postToolUse"
  | "preCompact"
  | "postCompact"
  | "sessionStart"
  | "sessionEnd"
  | "userPromptSubmit"
  | "subagentStart"
  | "subagentStop"
  | "stop"
  | "interrupt";
export type HookExecutionMode = "sync" | "async";
export type HookHandlerType = "command" | "mcpTool" | "prompt" | "agent";
export type HookScope = "thread" | "turn";
export type HookSource =
  | "system"
  | "user"
  | "project"
  | "mdm"
  | "sessionFlags"
  | "plugin"
  | "cloudRequirements"
  | "cloudManagedConfig"
  | "legacyManagedConfigFile"
  | "legacyManagedConfigMdm"
  | "unknown";
export type HookRunStatus = "running" | "completed" | "failed" | "blocked" | "stopped";
export type TurnCompletedNotificationMethod = "turn/completed";
export type HookCompletedNotificationMethod = "hook/completed";
export type TurnDiffUpdatedNotificationMethod = "turn/diff/updated";
export type TurnPlanUpdatedNotificationMethod = "turn/plan/updated";
export type TurnPlanStepStatus = "pending" | "inProgress" | "completed";
export type ItemStartedNotificationMethod = "item/started";
export type ItemAutoApprovalReviewStartedNotificationMethod = "item/autoApprovalReview/started";
export type GuardianApprovalReviewAction =
  | CommandGuardianApprovalReviewAction
  | ExecveGuardianApprovalReviewAction
  | WriteStdinGuardianApprovalReviewAction
  | ApplyPatchGuardianApprovalReviewAction
  | NetworkAccessGuardianApprovalReviewAction
  | McpToolCallGuardianApprovalReviewAction
  | RequestPermissionsGuardianApprovalReviewAction;
export type GuardianCommandSource = "shell" | "unifiedExec";
export type CommandGuardianApprovalReviewActionType = "command";
export type ExecveGuardianApprovalReviewActionType = "execve";
export type WriteStdinGuardianApprovalReviewActionType = "writeStdin";
export type ApplyPatchGuardianApprovalReviewActionType = "applyPatch";
export type NetworkApprovalProtocol = "http" | "https" | "socks5Tcp" | "socks5Udp";
export type NetworkAccessGuardianApprovalReviewActionType = "networkAccess";
export type McpToolCallGuardianApprovalReviewActionType = "mcpToolCall";
export type FileSystemAccessMode = "read" | "write" | "deny";
export type FileSystemPath = PathFileSystemPath | GlobPatternFileSystemPath | SpecialFileSystemPath;
export type PathFileSystemPathType = "path";
export type GlobPatternFileSystemPathType = "glob_pattern";
export type SpecialFileSystemPathType = "special";
export type FileSystemSpecialPath =
  | RootFileSystemSpecialPath
  | MinimalFileSystemSpecialPath
  | KindFileSystemSpecialPath
  | TmpdirFileSystemSpecialPath
  | SlashTmpFileSystemSpecialPath
  | {
      kind: "unknown";
      path: string;
      subpath?: LegacyAppPathString | null;
    };
export type RequestPermissionsGuardianApprovalReviewActionType = "requestPermissions";
/**
 * [UNSTABLE] Risk level assigned by approval auto-review.
 */
export type GuardianRiskLevel = "low" | "medium" | "high" | "critical";
/**
 * [UNSTABLE] Lifecycle state for an approval auto-review.
 */
export type GuardianApprovalReviewStatus = "inProgress" | "approved" | "denied" | "timedOut" | "aborted";
/**
 * [UNSTABLE] Authorization level assigned by approval auto-review.
 */
export type GuardianUserAuthorization = "unknown" | "low" | "medium" | "high";
export type ItemAutoApprovalReviewCompletedNotificationMethod = "item/autoApprovalReview/completed";
/**
 * [UNSTABLE] Source that produced a terminal approval auto-review decision.
 */
export type AutoReviewDecisionSource = "agent";
export type AutoApprovalReviewStrictReviewRequiredNotificationMethod = "autoApprovalReview/strictReviewRequired";
export type ItemCompletedNotificationMethod = "item/completed";
export type ItemAgentMessageDeltaNotificationMethod = "item/agentMessage/delta";
export type ItemPlanDeltaNotificationMethod = "item/plan/delta";
export type CommandExecOutputDeltaNotificationMethod = "command/exec/outputDelta";
/**
 * Stream label for `command/exec/outputDelta` notifications.
 */
export type CommandExecOutputStream = "stdout" | "stderr";
export type ProcessOutputDeltaNotificationMethod = "process/outputDelta";
/**
 * Stream label for `process/outputDelta` notifications.
 */
export type ProcessOutputStream = "stdout" | "stderr";
export type ProcessExitedNotificationMethod = "process/exited";
export type ItemCommandExecutionOutputDeltaNotificationMethod = "item/commandExecution/outputDelta";
export type ItemCommandExecutionTerminalInteractionNotificationMethod = "item/commandExecution/terminalInteraction";
export type ItemFileChangeOutputDeltaNotificationMethod = "item/fileChange/outputDelta";
export type ItemFileChangePatchUpdatedNotificationMethod = "item/fileChange/patchUpdated";
export type ServerRequestResolvedNotificationMethod = "serverRequest/resolved";
export type RequestId = string | number;
export type ItemMcpToolCallProgressNotificationMethod = "item/mcpToolCall/progress";
export type McpServerOauthLoginCompletedNotificationMethod = "mcpServer/oauthLogin/completed";
export type McpServerStartupStatusUpdatedNotificationMethod = "mcpServer/startupStatus/updated";
export type McpServerStartupFailureReason = "reauthenticationRequired";
export type McpServerStartupState = "starting" | "ready" | "failed" | "cancelled";
export type McpServerEventStreamNotificationNotificationMethod = "mcpServer/event/stream/notification";
export type AccountUpdatedNotificationMethod = "account/updated";
/**
 * Authentication mode for OpenAI-backed providers.
 */
export type AuthMode =
  | "apikey"
  | "chatgpt"
  | "chatgptAuthTokens"
  | "headers"
  | "agentIdentity"
  | "personalAccessToken"
  | "bedrockApiKey"
  | "bedrockAccessKeys";
export type PlanType =
  | "free"
  | "go"
  | "plus"
  | "pro"
  | "prolite"
  | "promax"
  | "team"
  | "self_serve_business_prolite"
  | "self_serve_business_usage_based"
  | "business"
  | "ent26"
  | "enterprise_cbp_automation"
  | "enterprise_cbp_usage_based"
  | "enterprise"
  | "edu"
  | "edu_plus"
  | "edu_pro"
  | "sci"
  | "sci_plus"
  | "unknown";
export type AccountGatewayOAuthChangedNotificationMethod = "account/gatewayOAuth/changed";
export type GatewayOAuthStatus = "notReady" | "started" | "succeeded" | "failed";
export type AccountRateLimitsUpdatedNotificationMethod = "account/rateLimits/updated";
export type RateLimitReachedType =
  | "rate_limit_reached"
  | "workspace_owner_credits_depleted"
  | "workspace_member_credits_depleted"
  | "workspace_owner_usage_limit_reached"
  | "workspace_member_usage_limit_reached";
export type AppListUpdatedNotificationMethod = "app/list/updated";
export type RemoteControlStatusChangedNotificationMethod = "remoteControl/status/changed";
export type RemoteControlConnectionStatus = "disabled" | "connecting" | "connected" | "errored";
export type ExternalAgentConfigImportProgressNotificationMethod = "externalAgentConfig/import/progress";
export type ExternalAgentConfigMigrationItemType =
  | "AGENTS_MD"
  | "CONFIG"
  | "SKILLS"
  | "PLUGINS"
  | "MCP_SERVER_CONFIG"
  | "SUBAGENTS"
  | "HOOKS"
  | "COMMANDS"
  | "MEMORY"
  | "SESSIONS";
export type ExternalAgentConfigImportCompletedNotificationMethod = "externalAgentConfig/import/completed";
export type FsChangedNotificationMethod = "fs/changed";
export type ItemReasoningSummaryTextDeltaNotificationMethod = "item/reasoning/summaryTextDelta";
export type ItemReasoningSummaryPartAddedNotificationMethod = "item/reasoning/summaryPartAdded";
export type ItemReasoningTextDeltaNotificationMethod = "item/reasoning/textDelta";
export type ThreadCompactedNotificationMethod = "thread/compacted";
export type ModelReroutedNotificationMethod = "model/rerouted";
export type ModelRerouteReason = "highRiskCyberActivity";
export type ModelVerificationNotificationMethod = "model/verification";
export type ModelVerification = "trustedAccessForCyber";
export type ModelProviderAuthRecoveryStartedNotificationMethod = "modelProvider/authRecoveryStarted";
export type ModelProviderAuthRecoveryCompletedNotificationMethod = "modelProvider/authRecoveryCompleted";
export type TurnModerationMetadataNotificationMethod = "turn/moderationMetadata";
export type ModelSafetyBufferingUpdatedNotificationMethod = "model/safetyBuffering/updated";
export type WarningNotificationMethod = "warning";
export type GuardianWarningNotificationMethod = "guardianWarning";
export type DeprecationNoticeNotificationMethod = "deprecationNotice";
export type ConfigWarningNotificationMethod = "configWarning";
export type FuzzyFileSearchSessionUpdatedNotificationMethod = "fuzzyFileSearch/sessionUpdated";
export type FuzzyFileSearchMatchType = "file" | "directory";
export type FuzzyFileSearchSessionCompletedNotificationMethod = "fuzzyFileSearch/sessionCompleted";
export type ThreadRealtimeStartedNotificationMethod = "thread/realtime/started";
export type RealtimeConversationVersion = "v1" | "v2" | "v3";
export type ThreadRealtimeItemAddedNotificationMethod = "thread/realtime/itemAdded";
export type ThreadRealtimeItemStartedNotificationMethod = "thread/realtime/item/started";
/**
 * EXPERIMENTAL - a thread-scoped realtime item in the canonical timeline.
 */
export type ThreadRealtimeItem = {
  id: string;
  realtimeSessionId: string;
} & ThreadRealtimeItem1;
export type ThreadRealtimeItem1 =
  | RealtimeSessionStartedThreadRealtimeItem
  | TranscriptSegmentThreadRealtimeItem
  | BemItemPromotedThreadRealtimeItem
  | RealtimeSessionClosedThreadRealtimeItem;
export type RealtimeSessionStartedThreadRealtimeItemType = "realtimeSessionStarted";
export type ThreadRealtimeTranscriptRole = "user" | "assistant";
export type TranscriptSegmentThreadRealtimeItemType = "transcriptSegment";
/**
 * EXPERIMENTAL - how an existing agent item appears in a realtime conversation.
 */
export type ThreadRealtimeBemItemPresentation =
  | WholeItemThreadRealtimeBemItemPresentation
  | InlineMarkdownThreadRealtimeBemItemPresentation
  | InlineVisualizationThreadRealtimeBemItemPresentation;
export type WholeItemThreadRealtimeBemItemPresentationType = "wholeItem";
export type InlineMarkdownThreadRealtimeBemItemPresentationType = "inlineMarkdown";
export type InlineVisualizationThreadRealtimeBemItemPresentationType = "inlineVisualization";
export type BemItemPromotedThreadRealtimeItemType = "bemItemPromoted";
export type ThreadRealtimeSessionOutcome = "ended" | "failed";
export type RealtimeSessionClosedThreadRealtimeItemType = "realtimeSessionClosed";
export type ThreadRealtimeItemTranscriptDeltaNotificationMethod = "thread/realtime/item/transcript/delta";
export type ThreadRealtimeItemCompletedNotificationMethod = "thread/realtime/item/completed";
export type ThreadRealtimeTranscriptDeltaNotificationMethod = "thread/realtime/transcript/delta";
export type ThreadRealtimeTranscriptDoneNotificationMethod = "thread/realtime/transcript/done";
export type ThreadRealtimeOutputAudioDeltaNotificationMethod = "thread/realtime/outputAudio/delta";
export type ThreadRealtimeSdpNotificationMethod = "thread/realtime/sdp";
export type ThreadRealtimeErrorNotificationMethod = "thread/realtime/error";
export type ThreadRealtimeClosedNotificationMethod = "thread/realtime/closed";
export type WindowsWorldWritableWarningNotificationMethod = "windows/worldWritableWarning";
export type WindowsSandboxSetupCompletedNotificationMethod = "windowsSandbox/setupCompleted";
export type WindowsSandboxSetupMode = "elevated" | "unelevated";
export type AccountLoginCompletedNotificationMethod = "account/login/completed";
export type DesktopOnboardingEntrypoint = "life_sciences";

/**
 * NEW NOTIFICATIONS
 */
export interface ErrorNotification {
  method: ErrorNotificationMethod;
  params: ErrorNotification1;
}
export interface ErrorNotification1 {
  error: TurnError;
  threadId: string;
  turnId: string;
  willRetry: boolean;
}
export interface TurnError {
  additionalDetails?: string | null;
  codexErrorInfo?: CodexErrorInfo | null;
  message: string;
  /**
   * Optional public explanation and continuation instruction for a misalignment block.
   */
  misalignment?: MisalignmentErrorDetails | null;
}
export interface HttpConnectionFailedCodexErrorInfo {
  httpConnectionFailed: {
    httpStatusCode?: number | null;
  };
}
/**
 * Failed to connect to the response SSE stream.
 */
export interface ResponseStreamConnectionFailedCodexErrorInfo {
  responseStreamConnectionFailed: {
    httpStatusCode?: number | null;
  };
}
/**
 * The response SSE stream disconnected in the middle of a turn before completion.
 */
export interface ResponseStreamDisconnectedCodexErrorInfo {
  responseStreamDisconnected: {
    httpStatusCode?: number | null;
  };
}
/**
 * Reached the retry limit for responses.
 */
export interface ResponseTooManyFailedAttemptsCodexErrorInfo {
  responseTooManyFailedAttempts: {
    httpStatusCode?: number | null;
  };
}
/**
 * Returned when `turn/start` or `turn/steer` is submitted while the current active turn cannot accept same-turn steering, for example `/review` or manual `/compact`.
 */
export interface ActiveTurnNotSteerableCodexErrorInfo {
  activeTurnNotSteerable: {
    turnKind: NonSteerableTurnKind;
  };
}
export interface MisalignmentErrorDetails {
  /**
   * A substantive localized explanation is required before offering continuation.
   */
  detailedExplanation?: string | null;
  /**
   * Open-ended classification; clients must accept categories added by Responses.
   */
  errorType?: string | null;
  /**
   * Opaque server-issued block target. Presence alone does not enable target-based continuation.
   */
  reviewTarget?: string | null;
  /**
   * Instruction to submit as the next turn's user input if continuation is confirmed.
   */
  steer?: MisalignmentSteer | null;
}
export interface MisalignmentSteer {
  message: string;
}
export interface ThreadStartedNotification {
  method: ThreadStartedNotificationMethod;
  params: ThreadStartedNotification1;
}
export interface ThreadStartedNotification1 {
  thread: Thread;
}
export interface Thread {
  /**
   * Optional random unique nickname assigned to an AgentControl-spawned sub-agent.
   */
  agentNickname?: string | null;
  /**
   * Optional role (agent_role) assigned to an AgentControl-spawned sub-agent.
   */
  agentRole?: string | null;
  /**
   * Version of the CLI that created the thread.
   */
  cliVersion: string;
  /**
   * Unix timestamp (in seconds) when the thread was created.
   */
  createdAt: number;
  /**
   * Working directory captured for the thread.
   */
  cwd: AbsolutePathBuf;
  /**
   * Whether the thread is ephemeral and should not be materialized on disk.
   */
  ephemeral: boolean;
  /**
   * Source thread id when this thread was created by forking another thread.
   */
  forkedFromId?: string | null;
  /**
   * Optional Git metadata captured when the thread was created.
   */
  gitInfo?: GitInfo | null;
  /**
   * Persisted thread history contract selected when this thread was created.
   */
  historyMode?: ThreadHistoryMode & string;
  /**
   * Identifier for this thread. Codex-generated thread IDs are UUIDv7.
   */
  id: string;
  /**
   * Current configured model when loaded, otherwise the latest persisted model. Null when unavailable. This is not per-turn execution telemetry.
   */
  model?: string | null;
  /**
   * Model provider used for this thread (for example, 'openai').
   */
  modelProvider: string;
  /**
   * Optional user-facing thread title.
   */
  name?: string | null;
  /**
   * Originator recorded when the thread was created, independent of its current client or executor. Null when the recorded originator is unavailable.
   */
  originator?: string | null;
  /**
   * The ID of the parent thread. This will only be set if this thread is a subagent.
   */
  parentThreadId?: string | null;
  /**
   * [UNSTABLE] Path to the thread on disk.
   */
  path?: string | null;
  /**
   * Usually the first user message in the thread, if available.
   */
  preview: string;
  /**
   * Canonical project assignment owned by app-server, if any.
   */
  projectId: string | null;
  /**
   * Current configured reasoning effort when loaded, otherwise the latest persisted effort. Null when unset or unavailable. This is not per-turn execution telemetry.
   */
  reasoningEffort?: ReasoningEffort | null;
  /**
   * Unix timestamp (in seconds) used for thread recency ordering.
   */
  recencyAt?: number | null;
  /**
   * The independently persisted section selected for this thread, if any.
   */
  section?: ThreadSection | null;
  /**
   * Unix timestamp in seconds when the thread entered its current section.
   */
  sectionEnteredAt?: number | null;
  /**
   * Session id shared by threads that belong to the same session tree.
   */
  sessionId: string;
  /**
   * Origin of the thread (CLI, VSCode, codex exec, codex app-server, etc.).
   */
  source: SessionSource;
  /**
   * Current runtime status for the thread.
   */
  status: ThreadStatus;
  /**
   * Optional analytics source classification for this thread.
   */
  threadSource?: ThreadSource | null;
  /**
   * Only populated on `thread/resume`, `thread/fork`, and `thread/read` (when `includeTurns` is true) responses. For all other responses and notifications returning a Thread, the turns field will be an empty list.
   */
  turns: Turn[];
  /**
   * Unix timestamp (in seconds) when the thread was last updated.
   */
  updatedAt: number;
}
export interface GitInfo {
  branch?: string | null;
  originUrl?: string | null;
  sha?: string | null;
}
/**
 * An independently persisted, user-visible thread section.
 */
export interface ThreadSection {
  /**
   * Optional appearance synchronized across clients.
   */
  appearance?: ThreadSectionAppearance | null;
  /**
   * Opaque UUIDv7 identity that remains stable when the section is renamed.
   */
  id: string;
  /**
   * The current user-visible section name.
   */
  name: string;
}
/**
 * Extensible visual presentation for a custom thread section.
 */
export interface ThreadSectionAppearance {
  color?: string | null;
  icon?: string | null;
}
export interface CustomSessionSource {
  custom: string;
}
export interface SubAgentSessionSource {
  subAgent: SubAgentSource;
}
export interface ThreadSpawnSubAgentSource {
  thread_spawn: {
    agent_nickname?: string | null;
    agent_path?: AgentPath | null;
    agent_role?: string | null;
    depth: number;
    parent_thread_id: ThreadId;
  };
}
export interface OtherSubAgentSource {
  other: string;
}
export interface NotLoadedThreadStatus {
  type: NotLoadedThreadStatusType;
}
export interface IdleThreadStatus {
  type: IdleThreadStatusType;
}
export interface SystemErrorThreadStatus {
  type: SystemErrorThreadStatusType;
}
export interface ActiveThreadStatus {
  activeFlags: ThreadActiveFlag[];
  type: ActiveThreadStatusType;
}
export interface Turn {
  /**
   * Unix timestamp (in seconds) when the turn completed.
   */
  completedAt?: number | null;
  /**
   * Duration between turn start and completion in milliseconds, if known.
   */
  durationMs?: number | null;
  /**
   * Error associated with a failed or interrupted turn.
   */
  error?: TurnError | null;
  /**
   * Identifier for this turn. Codex-generated turn IDs are UUIDv7.
   */
  id: string;
  /**
   * Thread items currently included in this turn payload.
   */
  items: ThreadItem[];
  /**
   * Describes how much of `items` has been loaded for this turn.
   */
  itemsView?: TurnItemsView & string;
  /**
   * ID of the first turn in the chain of work that led to this turn. Pass this as `rootTurnId` when starting work on behalf of this turn. May be null in older history or a `review/start` response.
   */
  rootTurnId?: string | null;
  /**
   * Unix timestamp (in seconds) when the turn started.
   */
  startedAt?: number | null;
  status: TurnStatus;
}
export interface UserMessageThreadItem {
  clientId?: string | null;
  content: UserInput[];
  id: string;
  type: UserMessageThreadItemType;
}
export interface TextUserInput {
  text: string;
  /**
   * UI-defined spans within `text` used to render or persist special elements.
   */
  text_elements?: TextElement[];
  type: TextUserInputType;
}
export interface TextElement {
  /**
   * Byte range in the parent `text` buffer that this element occupies.
   */
  byteRange: ByteRange;
  /**
   * Optional human-readable placeholder for the element, displayed in the UI.
   */
  placeholder?: string | null;
}
export interface ByteRange {
  end: number;
  start: number;
}
export interface UrlUserInput {
  url: string;
}
export interface FileIdUserInput {
  fileId: string;
}
export interface LocalImageUserInput {
  detail?: ImageDetail | null;
  path: string;
  type: LocalImageUserInputType;
}
export interface UrlUserInput1 {
  url: string;
}
export interface FileIdUserInput1 {
  fileId: string;
}
export interface LocalAudioUserInput {
  path: string;
  type: LocalAudioUserInputType;
}
export interface SkillUserInput {
  name: string;
  path: string;
  type: SkillUserInputType;
}
export interface MentionUserInput {
  name: string;
  path: string;
  type: MentionUserInputType;
}
export interface HookPromptThreadItem {
  fragments: HookPromptFragment[];
  id: string;
  type: HookPromptThreadItemType;
}
export interface HookPromptFragment {
  hookRunId: string;
  text: string;
}
export interface AgentMessageThreadItem {
  delivery?: AgentMessageDelivery | null;
  id: string;
  memoryCitation?: MemoryCitation | null;
  phase?: MessagePhase | null;
  questions?: AsyncUserInputQuestion[] | null;
  text: string;
  type: AgentMessageThreadItemType;
}
export interface MemoryCitation {
  entries: MemoryCitationEntry[];
  threadIds: string[];
}
export interface MemoryCitationEntry {
  lineEnd: number;
  lineStart: number;
  note: string;
  path: string;
}
export interface AsyncUserInputQuestion {
  options?: string[] | null;
  title: string;
}
export interface FunctionCallOutputThreadItem {
  id: string;
  name: string;
  namespace?: string | null;
  output: FunctionCallOutputBody;
  type: FunctionCallOutputThreadItemType;
}
export interface InputTextFunctionCallOutputContentItem {
  text: string;
  type: InputTextFunctionCallOutputContentItemType;
}
export interface ImageUrlFunctionCallOutputContentItem {
  image_url: string;
}
export interface FileIdFunctionCallOutputContentItem {
  file_id: string;
}
export interface InputAudioFunctionCallOutputContentItem {
  audio_url: string;
  type: InputAudioFunctionCallOutputContentItemType;
}
export interface EncryptedContentFunctionCallOutputContentItem {
  encrypted_content: string;
  type: EncryptedContentFunctionCallOutputContentItemType;
}
/**
 * EXPERIMENTAL - proposed plan item content. The completed plan item is authoritative and may not match the concatenation of `PlanDelta` text.
 */
export interface PlanThreadItem {
  id: string;
  text: string;
  type: PlanThreadItemType;
}
export interface ReasoningThreadItem {
  content?: string[];
  id: string;
  summary?: string[];
  type: ReasoningThreadItemType;
}
export interface CommandExecutionThreadItem {
  /**
   * The command's output, aggregated from stdout and stderr.
   */
  aggregatedOutput?: string | null;
  /**
   * The command to be executed.
   */
  command: string;
  /**
   * A best-effort parsing of the command to understand the action(s) it will perform. This returns a list of CommandAction objects because a single shell command may be composed of many commands piped together.
   */
  commandActions: CommandAction[];
  /**
   * The command's working directory.
   */
  cwd: LegacyAppPathString;
  /**
   * The duration of the command execution in milliseconds.
   */
  durationMs?: number | null;
  /**
   * The command's exit code.
   */
  exitCode?: number | null;
  id: string;
  /**
   * Trusted first-party plugin id when this command resolves to one plugin script.
   */
  pluginId?: string | null;
  /**
   * Identifier for the underlying PTY process (when available).
   */
  processId?: string | null;
  /**
   * Safe plugin-relative path when this command resolves to one plugin script.
   */
  scriptPath?: string | null;
  source?: CommandExecutionSource & string;
  status: CommandExecutionStatus;
  type: CommandExecutionThreadItemType;
}
export interface ReadCommandAction {
  command: string;
  name: string;
  path: LegacyAppPathString;
  type: ReadCommandActionType;
}
export interface ListFilesCommandAction {
  command: string;
  path?: string | null;
  type: ListFilesCommandActionType;
}
export interface SearchCommandAction {
  command: string;
  path?: string | null;
  query?: string | null;
  type: SearchCommandActionType;
}
export interface UnknownCommandAction {
  command: string;
  type: UnknownCommandActionType;
}
export interface FileChangeThreadItem {
  changes: FileUpdateChange[];
  id: string;
  status: PatchApplyStatus;
  type: FileChangeThreadItemType;
}
export interface FileUpdateChange {
  diff: string;
  kind: PatchChangeKind;
  path: string;
}
export interface AddPatchChangeKind {
  type: AddPatchChangeKindType;
}
export interface DeletePatchChangeKind {
  type: DeletePatchChangeKindType;
}
export interface UpdatePatchChangeKind {
  move_path?: string | null;
  type: UpdatePatchChangeKindType;
}
export interface McpToolCallThreadItem {
  appContext?: McpToolCallAppContext | null;
  arguments: unknown;
  /**
   * The duration of the MCP tool call in milliseconds.
   */
  durationMs?: number | null;
  error?: McpToolCallError | null;
  id: string;
  /**
   * Legacy compatibility field; prefer `mcpAppUi.resourceUri` when available.
   */
  mcpAppResourceUri?: string | null;
  /**
   * Presentation captured from the invoked descriptor; absent in older history.
   */
  mcpAppUi?: McpAppUi | null;
  pluginId?: string | null;
  readOnlyHint?: boolean | null;
  result?: McpToolCallResult | null;
  server: string;
  status: McpToolCallStatus;
  tool: string;
  type: McpToolCallThreadItemType;
}
export interface McpToolCallAppContext {
  actionName?: string | null;
  appName?: string | null;
  connectorId: string;
  linkId?: string | null;
  resourceUri?: string | null;
}
export interface McpToolCallError {
  message: string;
}
/**
 * UI resource and display preference for model invocations, captured from the tool descriptor.
 */
export interface McpAppUi {
  preferredModelDisplayMode: McpAppDisplayMode;
  resourceUri: string;
}
export interface McpToolCallResult {
  _meta?: unknown;
  content: unknown[];
  structuredContent?: unknown;
}
export interface DynamicToolCallThreadItem {
  arguments: unknown;
  contentItems?: DynamicToolCallOutputContentItem[] | null;
  /**
   * The duration of the dynamic tool call in milliseconds.
   */
  durationMs?: number | null;
  id: string;
  namespace?: string | null;
  status: DynamicToolCallStatus;
  success?: boolean | null;
  tool: string;
  type: DynamicToolCallThreadItemType;
}
export interface InputTextDynamicToolCallOutputContentItem {
  text: string;
  type: InputTextDynamicToolCallOutputContentItemType;
}
export interface InputImageDynamicToolCallOutputContentItem {
  imageUrl: string;
  type: InputImageDynamicToolCallOutputContentItemType;
}
export interface InputAudioDynamicToolCallOutputContentItem {
  audioUrl: string;
  type: InputAudioDynamicToolCallOutputContentItemType;
}
export interface CollabAgentToolCallThreadItem {
  /**
   * Last known status of the target agents, when available.
   */
  agentsStates: {
    [k: string]: CollabAgentState;
  };
  /**
   * Unique identifier for this collab tool call.
   */
  id: string;
  /**
   * Model requested for the spawned agent, when applicable.
   */
  model?: string | null;
  /**
   * Prompt text sent as part of the collab tool call, when available.
   */
  prompt?: string | null;
  /**
   * Reasoning effort requested for the spawned agent, when applicable.
   */
  reasoningEffort?: ReasoningEffort | null;
  /**
   * Thread ID of the receiving agent, when applicable. In case of spawn operation, this corresponds to the newly spawned agent.
   */
  receiverThreadIds: string[];
  /**
   * Thread ID of the agent issuing the collab request.
   */
  senderThreadId: string;
  /**
   * Current status of the collab tool call.
   */
  status: CollabAgentToolCallStatus;
  /**
   * Name of the collab tool that was invoked.
   */
  tool: CollabAgentTool;
  type: CollabAgentToolCallThreadItemType;
}
export interface CollabAgentState {
  message?: string | null;
  status: CollabAgentStatus;
}
export interface SubAgentActivityThreadItem {
  agentPath: string;
  agentThreadId: string;
  id: string;
  kind: SubAgentActivityKind;
  /**
   * Resolved model at sub-agent creation; absent from older records and other activities.
   */
  model?: string | null;
  /**
   * Resolved reasoning effort at sub-agent creation, when known.
   */
  reasoningEffort?: ReasoningEffort | null;
  type: SubAgentActivityThreadItemType;
}
export interface WebSearchThreadItem {
  action?: WebSearchAction | null;
  id: string;
  query: string;
  /**
   * Structured search results returned out-of-band by standalone web search.
   *
   * These stay as opaque JSON at the extension/app-server boundary so new result fields and result types can pass through without a Codex release.
   */
  results?: unknown[] | null;
  type: WebSearchThreadItemType;
}
export interface SearchWebSearchAction {
  queries?: string[] | null;
  query?: string | null;
  type: SearchWebSearchActionType;
}
export interface OpenPageWebSearchAction {
  type: OpenPageWebSearchActionType;
  url?: string | null;
}
export interface FindInPageWebSearchAction {
  pattern?: string | null;
  type: FindInPageWebSearchActionType;
  url?: string | null;
}
export interface OtherWebSearchAction {
  type: OtherWebSearchActionType;
}
export interface ImageViewThreadItem {
  id: string;
  path: LegacyAppPathString;
  type: ImageViewThreadItemType;
}
/**
 * Display item emitted by the interruptible `clock.sleep` tool.
 */
export interface SleepThreadItem {
  durationMs: number;
  id: string;
  type: SleepThreadItemType;
}
export interface FileIdThreadItem {
  fileId: string;
}
export interface ResultThreadItem {
  result: string;
}
export interface UsageLimitExceededImageGenerationFailure {
  limitId: string;
  resetsAt?: number | null;
  type: UsageLimitExceededImageGenerationFailureType;
}
/**
 * A local image file successfully read for this exact image-generation request.
 */
export interface ImageGenerationInputImage {
  path: AbsolutePathBuf;
  /**
   * Lowercase SHA-256 of the file bytes read before image normalization.
   */
  sha256: string;
}
export interface EnteredReviewModeThreadItem {
  id: string;
  review: string;
  type: EnteredReviewModeThreadItemType;
}
export interface ExitedReviewModeThreadItem {
  id: string;
  review: string;
  type: ExitedReviewModeThreadItemType;
}
export interface ContextCompactionThreadItem {
  id: string;
  type: ContextCompactionThreadItemType;
}
export interface ThreadStatusChangedNotification {
  method: ThreadStatusChangedNotificationMethod;
  params: ThreadStatusChangedNotification1;
}
export interface ThreadStatusChangedNotification1 {
  status: ThreadStatus;
  threadId: string;
}
export interface ThreadReadStateChangedNotification {
  method: ThreadReadStateChangedNotificationMethod;
  params: ThreadReadStateChangedNotification1;
}
export interface ThreadReadStateChangedNotification1 {
  readState: ThreadReadState;
  threadId: string;
}
/**
 * The first unread position in a durable local thread. A null position means read. The opaque revision guards edits against activity or marks the caller has not seen.
 */
export interface ThreadReadState {
  firstUnread?: ThreadUnreadPosition | null;
  revision: string;
}
/**
 * Explicitly marked unread, including when the thread has no turns.
 */
export interface ThreadStartThreadUnreadPosition {
  type: ThreadStartThreadUnreadPositionType;
}
/**
 * The earliest completed result needing attention.
 */
export interface TurnThreadUnreadPosition {
  turnId: string;
  type: TurnThreadUnreadPositionType;
}
export interface ThreadArchivedNotification {
  method: ThreadArchivedNotificationMethod;
  params: ThreadArchivedNotification1;
}
export interface ThreadArchivedNotification1 {
  threadId: string;
}
export interface ThreadDeletedNotification {
  method: ThreadDeletedNotificationMethod;
  params: ThreadDeletedNotification1;
}
export interface ThreadDeletedNotification1 {
  threadId: string;
}
export interface ThreadUnarchivedNotification {
  method: ThreadUnarchivedNotificationMethod;
  params: ThreadUnarchivedNotification1;
}
export interface ThreadUnarchivedNotification1 {
  threadId: string;
}
export interface ThreadClosedNotification {
  method: ThreadClosedNotificationMethod;
  params: ThreadClosedNotification1;
}
export interface ThreadClosedNotification1 {
  threadId: string;
}
export interface ThreadRevertedNotification {
  method: ThreadRevertedNotificationMethod;
  params: ThreadRevertedNotification1;
}
export interface ThreadRevertedNotification1 {
  threadId: string;
}
export interface SkillsChangedNotification {
  method: SkillsChangedNotificationMethod;
  params: SkillsChangedNotification1;
}
/**
 * Notification emitted when watched local skill files change.
 *
 * Treat this as an invalidation signal and re-run `skills/list` with the client's current parameters when refreshed skill metadata is needed.
 */
export interface SkillsChangedNotification1 {}
export interface ThreadNameUpdatedNotification {
  method: ThreadNameUpdatedNotificationMethod;
  params: ThreadNameUpdatedNotification1;
}
export interface ThreadNameUpdatedNotification1 {
  threadId: string;
  threadName?: string | null;
}
export interface ThreadSectionChangedNotification {
  method: ThreadSectionChangedNotificationMethod;
  params: ThreadSectionChangedNotification1;
}
/**
 * Broadcast after a successful move into, within, or out of a section.
 */
export interface ThreadSectionChangedNotification1 {
  /**
   * Destination section, or `null` when the thread was removed from its section.
   */
  sectionId: string | null;
  threadId: string;
}
export interface ThreadAttachmentUpdatedNotification {
  method: ThreadAttachmentUpdatedNotificationMethod;
  params: ThreadAttachmentUpdatedNotification1;
}
/**
 * Notification published after a thread attachment is created or deleted.
 */
export interface ThreadAttachmentUpdatedNotification1 {
  attachmentId: string;
  attachmentType: string;
  identityKey: string;
  operation: ThreadAttachmentOperation;
  threadId: string;
}
export interface ThreadGoalUpdatedNotification {
  method: ThreadGoalUpdatedNotificationMethod;
  params: ThreadGoalUpdatedNotification1;
}
export interface ThreadGoalUpdatedNotification1 {
  goal: ThreadGoal;
  threadId: string;
  turnId?: string | null;
}
export interface ThreadGoal {
  createdAt: number;
  objective: string;
  status: ThreadGoalStatus;
  threadId: string;
  timeUsedSeconds: number;
  tokenBudget?: number | null;
  tokensUsed: number;
  updatedAt: number;
}
export interface ThreadPredictionUpdatedNotification {
  method: ThreadPredictionUpdatedNotificationMethod;
  params: ThreadPredictionUpdatedNotification1;
}
export interface ThreadPredictionUpdatedNotification1 {
  result: ThreadPredictionResult;
  sourceTurnId: string;
  threadId: string;
}
export interface CompletedThreadPredictionResult {
  text?: string | null;
  type: CompletedThreadPredictionResultType;
}
export interface FailedThreadPredictionResult {
  type: FailedThreadPredictionResultType;
}
export interface ThreadGoalClearedNotification {
  method: ThreadGoalClearedNotificationMethod;
  params: ThreadGoalClearedNotification1;
}
export interface ThreadGoalClearedNotification1 {
  threadId: string;
}
export interface ThreadQueueChangedNotification {
  method: ThreadQueueChangedNotificationMethod;
  params: ThreadQueueChangedNotification1;
}
export interface ThreadQueueChangedNotification1 {
  threadId: string;
}
export interface ProjectChangedNotification {
  method: ProjectChangedNotificationMethod;
  params: ProjectChangedNotification1;
}
export interface ProjectChangedNotification1 {
  changeType: ProjectChangeType;
  projectId: string;
}
export interface ThreadProjectUpdatedNotification {
  method: ThreadProjectUpdatedNotificationMethod;
  params: ThreadProjectUpdatedNotification1;
}
export interface ThreadProjectUpdatedNotification1 {
  projectId: string | null;
  threadId: string;
}
export interface ThreadEnvironmentConnectedNotification {
  method: ThreadEnvironmentConnectedNotificationMethod;
  params: EnvironmentConnectionNotification;
}
export interface EnvironmentConnectionNotification {
  environmentId: string;
  threadId: string;
}
export interface ThreadEnvironmentDisconnectedNotification {
  method: ThreadEnvironmentDisconnectedNotificationMethod;
  params: EnvironmentConnectionNotification;
}
export interface ThreadSettingsUpdatedNotification {
  method: ThreadSettingsUpdatedNotificationMethod;
  params: ThreadSettingsUpdatedNotification1;
}
export interface ThreadSettingsUpdatedNotification1 {
  threadId: string;
  threadSettings: ThreadSettings;
}
export interface ThreadSettings {
  activePermissionProfile?: ActivePermissionProfile | null;
  approvalPolicy: AskForApproval;
  approvalsReviewer: ApprovalsReviewer;
  collaborationMode: CollaborationMode;
  cwd: AbsolutePathBuf;
  /**
   * Saved list of disabled plugin IDs. Does not yet filter plugin capabilities.
   */
  disabledPluginIds?: string[];
  effort?: ReasoningEffort | null;
  model: string;
  modelProvider: string;
  /**
   * @deprecated Reports the saved setting; `friendly` and `pragmatic` no longer select a style.
   */
  personality?: Personality | null;
  sandboxPolicy: SandboxPolicy;
  serviceTier?: string | null;
  summary?: ReasoningSummary | null;
}
export interface ActivePermissionProfile {
  /**
   * Parent profile identifier from the selected permissions profile's `extends` setting, when present.
   */
  extends?: string | null;
  /**
   * Identifier from `default_permissions` or the implicit built-in default, such as `:workspace` or a user-defined `[permissions.<id>]` profile.
   */
  id: string;
}
export interface GranularAskForApproval {
  granular: {
    mcp_elicitations: boolean;
    request_permissions?: boolean;
    rules: boolean;
    sandbox_approval: boolean;
    skill_approval?: boolean;
  };
}
/**
 * Collaboration mode for a Codex session.
 */
export interface CollaborationMode {
  mode: ModeKind;
  settings: Settings;
}
/**
 * Settings for a collaboration mode.
 */
export interface Settings {
  developer_instructions?: string | null;
  model: string;
  reasoning_effort?: ReasoningEffort | null;
}
export interface DangerFullAccessSandboxPolicy {
  type: DangerFullAccessSandboxPolicyType;
}
export interface ReadOnlySandboxPolicy {
  networkAccess?: boolean;
  type: ReadOnlySandboxPolicyType;
}
export interface ExternalSandboxSandboxPolicy {
  networkAccess?: NetworkAccess & string;
  type: ExternalSandboxSandboxPolicyType;
}
export interface WorkspaceWriteSandboxPolicy {
  excludeSlashTmp?: boolean;
  excludeTmpdirEnvVar?: boolean;
  networkAccess?: boolean;
  type: WorkspaceWriteSandboxPolicyType;
  writableRoots?: AbsolutePathBuf[];
}
export interface ThreadTokenUsageUpdatedNotification {
  method: ThreadTokenUsageUpdatedNotificationMethod;
  params: ThreadTokenUsageUpdatedNotification1;
}
export interface ThreadTokenUsageUpdatedNotification1 {
  threadId: string;
  tokenUsage: ThreadTokenUsage;
  turnId: string;
}
export interface ThreadTokenUsage {
  last: TokenUsageBreakdown;
  modelContextWindow?: number | null;
  total: TokenUsageBreakdown;
}
export interface TokenUsageBreakdown {
  cacheWriteInputTokens?: number;
  cachedInputTokens: number;
  inputTokens: number;
  outputTokens: number;
  reasoningOutputTokens: number;
  totalTokens: number;
}
export interface TurnStartedNotification {
  method: TurnStartedNotificationMethod;
  params: TurnStartedNotification1;
}
export interface TurnStartedNotification1 {
  threadId: string;
  turn: Turn;
}
export interface HookStartedNotification {
  method: HookStartedNotificationMethod;
  params: HookStartedNotification1;
}
export interface HookStartedNotification1 {
  run: HookRunSummary;
  threadId: string;
  turnId?: string | null;
}
export interface HookRunSummary {
  completedAt?: number | null;
  displayOrder: number;
  durationMs?: number | null;
  entries: HookOutputEntry[];
  eventName: HookEventName;
  executionMode: HookExecutionMode;
  handlerType: HookHandlerType;
  id: string;
  scope: HookScope;
  source?: HookSource & string;
  sourcePath: LegacyAppPathString;
  startedAt: number;
  status: HookRunStatus;
  statusMessage?: string | null;
}
export interface HookOutputEntry {
  kind: HookOutputEntryKind;
  text: string;
}
export interface TurnCompletedNotification {
  method: TurnCompletedNotificationMethod;
  params: TurnCompletedNotification1;
}
export interface TurnCompletedNotification1 {
  threadId: string;
  turn: Turn;
}
export interface HookCompletedNotification {
  method: HookCompletedNotificationMethod;
  params: HookCompletedNotification1;
}
export interface HookCompletedNotification1 {
  run: HookRunSummary;
  threadId: string;
  turnId?: string | null;
}
export interface TurnDiffUpdatedNotification {
  method: TurnDiffUpdatedNotificationMethod;
  params: TurnDiffUpdatedNotification1;
}
/**
 * Notification that the turn-level unified diff has changed. Contains the latest aggregated diff across all file changes in the turn.
 */
export interface TurnDiffUpdatedNotification1 {
  diff: string;
  threadId: string;
  turnId: string;
}
export interface TurnPlanUpdatedNotification {
  method: TurnPlanUpdatedNotificationMethod;
  params: TurnPlanUpdatedNotification1;
}
export interface TurnPlanUpdatedNotification1 {
  explanation?: string | null;
  plan: TurnPlanStep[];
  threadId: string;
  turnId: string;
}
export interface TurnPlanStep {
  status: TurnPlanStepStatus;
  step: string;
}
export interface ItemStartedNotification {
  method: ItemStartedNotificationMethod;
  params: ItemStartedNotification1;
}
export interface ItemStartedNotification1 {
  item: ThreadItem;
  /**
   * Unix timestamp (in milliseconds) when this item lifecycle started.
   */
  startedAtMs: number;
  threadId: string;
  turnId: string;
}
export interface ItemAutoApprovalReviewStartedNotification {
  method: ItemAutoApprovalReviewStartedNotificationMethod;
  params: ItemGuardianApprovalReviewStartedNotification;
}
/**
 * [UNSTABLE] Temporary notification payload for approval auto-review. This shape is expected to change soon.
 */
export interface ItemGuardianApprovalReviewStartedNotification {
  action: GuardianApprovalReviewAction;
  review: GuardianApprovalReview;
  /**
   * Stable identifier for this review.
   */
  reviewId: string;
  /**
   * Unix timestamp (in milliseconds) when this review started.
   */
  startedAtMs: number;
  /**
   * Identifier for the reviewed item or tool call when one exists.
   *
   * In most cases, one review maps to one target item. The exceptions are - execve reviews, where a single command may contain multiple execve calls to review (only possible when using the shell_zsh_fork feature) - stdin reviews, which refer to the existing parent command item and have a separate approval ID in the action payload - network policy reviews, where there is no target item
   *
   * A network call is triggered by a CommandExecution item, so having a target_item_id set to the CommandExecution item would be misleading because the review is about the network call, not the command execution. Therefore, target_item_id is set to None for network policy reviews.
   */
  targetItemId?: string | null;
  threadId: string;
  turnId: string;
}
export interface CommandGuardianApprovalReviewAction {
  command: string;
  cwd: LegacyAppPathString;
  source: GuardianCommandSource;
  type: CommandGuardianApprovalReviewActionType;
}
export interface ExecveGuardianApprovalReviewAction {
  argv: string[];
  cwd: AbsolutePathBuf;
  program: string;
  source: GuardianCommandSource;
  type: ExecveGuardianApprovalReviewActionType;
}
/**
 * A child approval for input to an existing command execution item.
 */
export interface WriteStdinGuardianApprovalReviewAction {
  approvalId: string;
  cwd: LegacyAppPathString;
  processId: string;
  stdin: string;
  type: WriteStdinGuardianApprovalReviewActionType;
}
export interface ApplyPatchGuardianApprovalReviewAction {
  cwd: LegacyAppPathString;
  files: LegacyAppPathString[];
  type: ApplyPatchGuardianApprovalReviewActionType;
}
export interface NetworkAccessGuardianApprovalReviewAction {
  host: string;
  port: number;
  protocol: NetworkApprovalProtocol;
  target: string;
  type: NetworkAccessGuardianApprovalReviewActionType;
}
export interface McpToolCallGuardianApprovalReviewAction {
  connectorId?: string | null;
  connectorName?: string | null;
  server: string;
  toolName: string;
  toolTitle?: string | null;
  type: McpToolCallGuardianApprovalReviewActionType;
}
export interface RequestPermissionsGuardianApprovalReviewAction {
  permissions: RequestPermissionProfile;
  reason?: string | null;
  type: RequestPermissionsGuardianApprovalReviewActionType;
}
export interface RequestPermissionProfile {
  fileSystem?: AdditionalFileSystemPermissions | null;
  network?: AdditionalNetworkPermissions | null;
}
export interface AdditionalFileSystemPermissions {
  entries?: FileSystemSandboxEntry[] | null;
  globScanMaxDepth?: number | null;
  /**
   * This will be removed in favor of `entries`.
   */
  read?: LegacyAppPathString[] | null;
  /**
   * This will be removed in favor of `entries`.
   */
  write?: LegacyAppPathString[] | null;
}
export interface FileSystemSandboxEntry {
  access: FileSystemAccessMode;
  path: FileSystemPath;
}
export interface PathFileSystemPath {
  path: LegacyAppPathString;
  type: PathFileSystemPathType;
}
export interface GlobPatternFileSystemPath {
  pattern: string;
  type: GlobPatternFileSystemPathType;
}
export interface SpecialFileSystemPath {
  type: SpecialFileSystemPathType;
  value: FileSystemSpecialPath;
}
export interface RootFileSystemSpecialPath {
  kind: "root";
}
export interface MinimalFileSystemSpecialPath {
  kind: "minimal";
}
export interface KindFileSystemSpecialPath {
  kind: "project_roots";
  subpath?: LegacyAppPathString | null;
}
export interface TmpdirFileSystemSpecialPath {
  kind: "tmpdir";
}
export interface SlashTmpFileSystemSpecialPath {
  kind: "slash_tmp";
}
export interface AdditionalNetworkPermissions {
  enabled?: boolean | null;
}
/**
 * [UNSTABLE] Temporary approval auto-review payload used by `item/autoApprovalReview/*` notifications. This shape is expected to change soon.
 */
export interface GuardianApprovalReview {
  rationale?: string | null;
  riskLevel?: GuardianRiskLevel | null;
  status: GuardianApprovalReviewStatus;
  userAuthorization?: GuardianUserAuthorization | null;
}
export interface ItemAutoApprovalReviewCompletedNotification {
  method: ItemAutoApprovalReviewCompletedNotificationMethod;
  params: ItemGuardianApprovalReviewCompletedNotification;
}
/**
 * [UNSTABLE] Temporary notification payload for approval auto-review. This shape is expected to change soon.
 */
export interface ItemGuardianApprovalReviewCompletedNotification {
  action: GuardianApprovalReviewAction;
  /**
   * Unix timestamp (in milliseconds) when this review completed.
   */
  completedAtMs: number;
  decisionSource: AutoReviewDecisionSource;
  review: GuardianApprovalReview;
  /**
   * Stable identifier for this review.
   */
  reviewId: string;
  /**
   * Unix timestamp (in milliseconds) when this review started.
   */
  startedAtMs: number;
  /**
   * Identifier for the reviewed item or tool call when one exists.
   *
   * In most cases, one review maps to one target item. The exceptions are - execve reviews, where a single command may contain multiple execve calls to review (only possible when using the shell_zsh_fork feature) - stdin reviews, which refer to the existing parent command item and have a separate approval ID in the action payload - network policy reviews, where there is no target item
   *
   * A network call is triggered by a CommandExecution item, so having a target_item_id set to the CommandExecution item would be misleading because the review is about the network call, not the command execution. Therefore, target_item_id is set to None for network policy reviews.
   */
  targetItemId?: string | null;
  threadId: string;
  turnId: string;
}
export interface AutoApprovalReviewStrictReviewRequiredNotification {
  method: AutoApprovalReviewStrictReviewRequiredNotificationMethod;
  params: StrictReviewRequiredNotification;
}
export interface StrictReviewRequiredNotification {
  /**
   * Unix timestamp (in milliseconds) when this review started.
   */
  startedAtMs: number;
  threadId: string;
  turnId: string;
}
export interface ItemCompletedNotification {
  method: ItemCompletedNotificationMethod;
  params: ItemCompletedNotification1;
}
export interface ItemCompletedNotification1 {
  /**
   * Unix timestamp (in milliseconds) when this item lifecycle completed.
   */
  completedAtMs: number;
  item: ThreadItem;
  threadId: string;
  turnId: string;
}
export interface ItemAgentMessageDeltaNotification {
  method: ItemAgentMessageDeltaNotificationMethod;
  params: AgentMessageDeltaNotification;
}
export interface AgentMessageDeltaNotification {
  delta: string;
  itemId: string;
  threadId: string;
  turnId: string;
}
/**
 * EXPERIMENTAL - proposed plan streaming deltas for plan items.
 */
export interface ItemPlanDeltaNotification {
  method: ItemPlanDeltaNotificationMethod;
  params: PlanDeltaNotification;
}
/**
 * EXPERIMENTAL - proposed plan streaming deltas for plan items. Clients should not assume concatenated deltas match the completed plan item content.
 */
export interface PlanDeltaNotification {
  delta: string;
  itemId: string;
  threadId: string;
  turnId: string;
}
/**
 * Stream base64-encoded stdout/stderr chunks for a running `command/exec` session.
 */
export interface CommandExecOutputDeltaNotification {
  method: CommandExecOutputDeltaNotificationMethod;
  params: CommandExecOutputDeltaNotification1;
}
/**
 * Base64-encoded output chunk emitted for a streaming `command/exec` request.
 *
 * These notifications are connection-scoped. If the originating connection closes, the server terminates the process.
 */
export interface CommandExecOutputDeltaNotification1 {
  /**
   * `true` on the final streamed chunk for a stream when `outputBytesCap` truncated later output on that stream.
   */
  capReached: boolean;
  /**
   * Base64-encoded output bytes.
   */
  deltaBase64: string;
  /**
   * Client-supplied, connection-scoped `processId` from the original `command/exec` request.
   */
  processId: string;
  /**
   * Output stream for this chunk.
   */
  stream: CommandExecOutputStream;
}
/**
 * Stream base64-encoded stdout/stderr chunks for a running `process/spawn` session.
 */
export interface ProcessOutputDeltaNotification {
  method: ProcessOutputDeltaNotificationMethod;
  params: ProcessOutputDeltaNotification1;
}
/**
 * Base64-encoded output chunk emitted for a streaming `process/spawn` request.
 */
export interface ProcessOutputDeltaNotification1 {
  /**
   * True on the final streamed chunk for this stream when output was truncated by `outputBytesCap`.
   */
  capReached: boolean;
  /**
   * Base64-encoded output bytes.
   */
  deltaBase64: string;
  /**
   * Client-supplied, connection-scoped `processHandle` from `process/spawn`.
   */
  processHandle: string;
  /**
   * Output stream this chunk belongs to.
   */
  stream: ProcessOutputStream;
}
/**
 * Final exit notification for a `process/spawn` session.
 */
export interface ProcessExitedNotification {
  method: ProcessExitedNotificationMethod;
  params: ProcessExitedNotification1;
}
/**
 * Final process exit notification for `process/spawn`.
 */
export interface ProcessExitedNotification1 {
  /**
   * Process exit code.
   */
  exitCode: number;
  /**
   * Whether output collection hit its post-exit deadline before seeing EOF or reaching the requested byte cap on either stream. Older servers omit this field.
   */
  outputDrainTimedOut?: boolean | null;
  /**
   * Client-supplied, connection-scoped `processHandle` from `process/spawn`.
   */
  processHandle: string;
  /**
   * Buffered stderr capture.
   *
   * Empty when stderr was streamed via `process/outputDelta`.
   */
  stderr: string;
  /**
   * Whether stderr reached `outputBytesCap`.
   *
   * In streaming mode, stderr is empty and cap state is also reported on the final stderr `process/outputDelta` notification.
   */
  stderrCapReached: boolean;
  /**
   * Buffered stdout capture.
   *
   * Empty when stdout was streamed via `process/outputDelta`.
   */
  stdout: string;
  /**
   * Whether stdout reached `outputBytesCap`.
   *
   * In streaming mode, stdout is empty and cap state is also reported on the final stdout `process/outputDelta` notification.
   */
  stdoutCapReached: boolean;
}
export interface ItemCommandExecutionOutputDeltaNotification {
  method: ItemCommandExecutionOutputDeltaNotificationMethod;
  params: CommandExecutionOutputDeltaNotification;
}
export interface CommandExecutionOutputDeltaNotification {
  delta: string;
  itemId: string;
  threadId: string;
  turnId: string;
}
export interface ItemCommandExecutionTerminalInteractionNotification {
  method: ItemCommandExecutionTerminalInteractionNotificationMethod;
  params: TerminalInteractionNotification;
}
export interface TerminalInteractionNotification {
  itemId: string;
  processId: string;
  stdin: string;
  threadId: string;
  turnId: string;
}
/**
 * Deprecated legacy apply_patch output stream notification.
 */
export interface ItemFileChangeOutputDeltaNotification {
  method: ItemFileChangeOutputDeltaNotificationMethod;
  params: FileChangeOutputDeltaNotification;
}
/**
 * Deprecated legacy notification for `apply_patch` textual output.
 *
 * The server no longer emits this notification.
 */
export interface FileChangeOutputDeltaNotification {
  delta: string;
  itemId: string;
  threadId: string;
  turnId: string;
}
export interface ItemFileChangePatchUpdatedNotification {
  method: ItemFileChangePatchUpdatedNotificationMethod;
  params: FileChangePatchUpdatedNotification;
}
export interface FileChangePatchUpdatedNotification {
  changes: FileUpdateChange[];
  itemId: string;
  threadId: string;
  turnId: string;
}
export interface ServerRequestResolvedNotification {
  method: ServerRequestResolvedNotificationMethod;
  params: ServerRequestResolvedNotification1;
}
export interface ServerRequestResolvedNotification1 {
  requestId: RequestId;
  threadId: string;
}
export interface ItemMcpToolCallProgressNotification {
  method: ItemMcpToolCallProgressNotificationMethod;
  params: McpToolCallProgressNotification;
}
export interface McpToolCallProgressNotification {
  itemId: string;
  message: string;
  threadId: string;
  turnId: string;
}
export interface McpServerOauthLoginCompletedNotification {
  method: McpServerOauthLoginCompletedNotificationMethod;
  params: McpServerOauthLoginCompletedNotification1;
}
export interface McpServerOauthLoginCompletedNotification1 {
  error?: string | null;
  /**
   * Identifies the explicit login attempt. Older servers omit this field.
   */
  loginId?: string | null;
  name: string;
  success: boolean;
  threadId?: string | null;
}
export interface McpServerStartupStatusUpdatedNotification {
  method: McpServerStartupStatusUpdatedNotificationMethod;
  params: McpServerStatusUpdatedNotification;
}
export interface McpServerStatusUpdatedNotification {
  error?: string | null;
  failureReason?: McpServerStartupFailureReason | null;
  name: string;
  status: McpServerStartupState;
  threadId?: string | null;
}
export interface McpServerEventStreamNotificationNotification {
  method: McpServerEventStreamNotificationNotificationMethod;
  params: McpServerEventStreamNotification;
}
export interface McpServerEventStreamNotification {
  notification: McpServerEventNotification;
  subscriptionId: string;
}
export interface McpServerEventNotification {
  method: string;
  params: unknown;
}
export interface AccountUpdatedNotification {
  method: AccountUpdatedNotificationMethod;
  params: AccountUpdatedNotification1;
}
export interface AccountUpdatedNotification1 {
  authMode?: AuthMode | null;
  planType?: PlanType | null;
}
export interface AccountGatewayOAuthChangedNotification {
  method: AccountGatewayOAuthChangedNotificationMethod;
  params: GatewayOAuthChangedNotification;
}
export interface GatewayOAuthChangedNotification {
  /**
   * Authorization handoff, sent only to the connection that started login.
   */
  authUrl?: string | null;
  error?: string | null;
  providerId: string;
  status: GatewayOAuthStatus;
}
export interface AccountRateLimitsUpdatedNotification {
  method: AccountRateLimitsUpdatedNotificationMethod;
  params: AccountRateLimitsUpdatedNotification1;
}
/**
 * Sparse rolling rate-limit update.
 *
 * Clients should merge available values into the most recent `account/rateLimits/read` response or refetch that snapshot. Nullable account metadata may be unavailable in a rolling update and does not clear a previously observed value.
 */
export interface AccountRateLimitsUpdatedNotification1 {
  rateLimits: RateLimitSnapshot;
}
export interface RateLimitSnapshot {
  credits?: CreditsSnapshot | null;
  individualLimit?: SpendControlLimitSnapshot | null;
  limitId?: string | null;
  limitName?: string | null;
  /**
   * Normal model whose display name and reasoning options describe this quota alias.
   */
  normalModelSlug?: string | null;
  planType?: PlanType | null;
  primary?: RateLimitWindow | null;
  rateLimitReachedType?: RateLimitReachedType | null;
  secondary?: RateLimitWindow | null;
  /**
   * Backend-reported spend-control state. `None` is unavailable, not a sparse-update recovery.
   */
  spendControlReached?: boolean | null;
}
export interface CreditsSnapshot {
  balance?: string | null;
  hasCredits: boolean;
  unlimited: boolean;
}
export interface SpendControlLimitSnapshot {
  limit: string;
  remainingPercent: number;
  resetsAt: number;
  used: string;
}
export interface RateLimitWindow {
  resetsAt?: number | null;
  usedPercent: number;
  windowDurationMins?: number | null;
}
export interface AppListUpdatedNotification {
  method: AppListUpdatedNotificationMethod;
  params: AppListUpdatedNotification1;
}
/**
 * EXPERIMENTAL - notification emitted when the app list changes.
 */
export interface AppListUpdatedNotification1 {
  data: AppInfo[];
}
/**
 * EXPERIMENTAL - app metadata returned by app-list APIs.
 */
export interface AppInfo {
  appMetadata?: AppMetadata | null;
  branding?: AppBranding | null;
  description?: string | null;
  distributionChannel?: string | null;
  iconAssets?: {
    [k: string]: string;
  } | null;
  iconDarkAssets?: {
    [k: string]: string;
  } | null;
  id: string;
  installUrl?: string | null;
  isAccessible?: boolean;
  /**
   * Whether this app is enabled in config.toml. Example: ```toml [apps.bad_app] enabled = false ```
   */
  isEnabled?: boolean;
  labels?: {
    [k: string]: string;
  } | null;
  logoUrl?: string | null;
  logoUrlDark?: string | null;
  name: string;
  pluginDisplayNames?: string[];
}
export interface AppMetadata {
  categories?: string[] | null;
  developer?: string | null;
  firstPartyRequiresInstall?: boolean | null;
  review?: AppReview | null;
  screenshots?: AppScreenshot[] | null;
  seoDescription?: string | null;
  showInComposerWhenUnlinked?: boolean | null;
  subCategories?: string[] | null;
  version?: string | null;
  versionId?: string | null;
  versionNotes?: string | null;
}
export interface AppReview {
  status: string;
}
export interface AppScreenshot {
  fileId?: string | null;
  url?: string | null;
  userPrompt: string;
}
/**
 * EXPERIMENTAL - app metadata returned by app-list APIs.
 */
export interface AppBranding {
  category?: string | null;
  developer?: string | null;
  isDiscoverableApp: boolean;
  privacyPolicy?: string | null;
  termsOfService?: string | null;
  website?: string | null;
}
export interface RemoteControlStatusChangedNotification {
  method: RemoteControlStatusChangedNotificationMethod;
  params: RemoteControlStatusChangedNotification1;
}
/**
 * Current remote-control connection status and remote identity exposed to clients.
 */
export interface RemoteControlStatusChangedNotification1 {
  environmentId?: string | null;
  installationId: string;
  serverName: string;
  status: RemoteControlConnectionStatus;
}
export interface ExternalAgentConfigImportProgressNotification {
  method: ExternalAgentConfigImportProgressNotificationMethod;
  params: ExternalAgentConfigImportProgressNotification1;
}
export interface ExternalAgentConfigImportProgressNotification1 {
  importId: string;
  itemTypeResults: ExternalAgentConfigImportTypeResult[];
}
export interface ExternalAgentConfigImportTypeResult {
  failures: ExternalAgentConfigImportItemTypeFailure[];
  itemType: ExternalAgentConfigMigrationItemType;
  successes: ExternalAgentConfigImportItemTypeSuccess[];
}
export interface ExternalAgentConfigImportItemTypeFailure {
  cwd?: string | null;
  errorType?: string | null;
  failureStage: string;
  itemType: ExternalAgentConfigMigrationItemType;
  message: string;
  source?: string | null;
  subErrorType?: string | null;
}
export interface ExternalAgentConfigImportItemTypeSuccess {
  cwd?: string | null;
  itemType: ExternalAgentConfigMigrationItemType;
  source?: string | null;
  target?: string | null;
  /**
   * Original title for an imported session; null for other item types.
   */
  title?: string | null;
}
export interface ExternalAgentConfigImportCompletedNotification {
  method: ExternalAgentConfigImportCompletedNotificationMethod;
  params: ExternalAgentConfigImportCompletedNotification1;
}
export interface ExternalAgentConfigImportCompletedNotification1 {
  importId: string;
  itemTypeResults: ExternalAgentConfigImportTypeResult[];
}
export interface FsChangedNotification {
  method: FsChangedNotificationMethod;
  params: FsChangedNotification1;
}
/**
 * Filesystem watch notification emitted for `fs/watch` subscribers.
 */
export interface FsChangedNotification1 {
  /**
   * File or directory paths associated with this event.
   */
  changedPaths: AbsolutePathBuf[];
  /**
   * Watch identifier previously provided to `fs/watch`.
   */
  watchId: string;
}
export interface ItemReasoningSummaryTextDeltaNotification {
  method: ItemReasoningSummaryTextDeltaNotificationMethod;
  params: ReasoningSummaryTextDeltaNotification;
}
export interface ReasoningSummaryTextDeltaNotification {
  delta: string;
  itemId: string;
  summaryIndex: number;
  threadId: string;
  turnId: string;
}
export interface ItemReasoningSummaryPartAddedNotification {
  method: ItemReasoningSummaryPartAddedNotificationMethod;
  params: ReasoningSummaryPartAddedNotification;
}
export interface ReasoningSummaryPartAddedNotification {
  itemId: string;
  summaryIndex: number;
  threadId: string;
  turnId: string;
}
export interface ItemReasoningTextDeltaNotification {
  method: ItemReasoningTextDeltaNotificationMethod;
  params: ReasoningTextDeltaNotification;
}
export interface ReasoningTextDeltaNotification {
  contentIndex: number;
  delta: string;
  itemId: string;
  threadId: string;
  turnId: string;
}
/**
 * Deprecated: Use `ContextCompaction` item type instead.
 */
export interface ThreadCompactedNotification {
  method: ThreadCompactedNotificationMethod;
  params: ContextCompactedNotification;
}
/**
 * Deprecated: Use `ContextCompaction` item type instead.
 */
export interface ContextCompactedNotification {
  threadId: string;
  turnId: string;
}
export interface ModelReroutedNotification {
  method: ModelReroutedNotificationMethod;
  params: ModelReroutedNotification1;
}
export interface ModelReroutedNotification1 {
  fromModel: string;
  reason: ModelRerouteReason;
  threadId: string;
  toModel: string;
  turnId: string;
}
export interface ModelVerificationNotification {
  method: ModelVerificationNotificationMethod;
  params: ModelVerificationNotification1;
}
export interface ModelVerificationNotification1 {
  threadId: string;
  turnId: string;
  verifications: ModelVerification[];
}
export interface ModelProviderAuthRecoveryStartedNotification {
  method: ModelProviderAuthRecoveryStartedNotificationMethod;
  params: AuthRecoveryNotification;
}
export interface AuthRecoveryNotification {
  message: string;
  provider: string;
  threadId: string;
  turnId: string;
}
export interface ModelProviderAuthRecoveryCompletedNotification {
  method: ModelProviderAuthRecoveryCompletedNotificationMethod;
  params: AuthRecoveryNotification;
}
export interface TurnModerationMetadataNotification {
  method: TurnModerationMetadataNotificationMethod;
  params: TurnModerationMetadataNotification1;
}
export interface TurnModerationMetadataNotification1 {
  metadata: unknown;
  threadId: string;
  turnId: string;
}
export interface ModelSafetyBufferingUpdatedNotification {
  method: ModelSafetyBufferingUpdatedNotificationMethod;
  params: ModelSafetyBufferingUpdatedNotification1;
}
export interface ModelSafetyBufferingUpdatedNotification1 {
  fasterModel?: string | null;
  model: string;
  reasons: string[];
  showBufferingUi: boolean;
  threadId: string;
  turnId: string;
  useCases: string[];
}
export interface WarningNotification {
  method: WarningNotificationMethod;
  params: WarningNotification1;
}
export interface WarningNotification1 {
  /**
   * Concise warning message for the user.
   */
  message: string;
  /**
   * Optional thread target when the warning applies to a specific thread.
   */
  threadId?: string | null;
}
export interface GuardianWarningNotification {
  method: GuardianWarningNotificationMethod;
  params: GuardianWarningNotification1;
}
export interface GuardianWarningNotification1 {
  /**
   * Concise guardian warning message for the user.
   */
  message: string;
  /**
   * Thread target for the guardian warning.
   */
  threadId: string;
}
export interface DeprecationNoticeNotification {
  method: DeprecationNoticeNotificationMethod;
  params: DeprecationNoticeNotification1;
}
export interface DeprecationNoticeNotification1 {
  /**
   * Optional extra guidance, such as migration steps or rationale.
   */
  details?: string | null;
  /**
   * Concise summary of what is deprecated.
   */
  summary: string;
}
export interface ConfigWarningNotification {
  method: ConfigWarningNotificationMethod;
  params: ConfigWarningNotification1;
}
export interface ConfigWarningNotification1 {
  /**
   * Optional extra guidance or error details.
   */
  details?: string | null;
  /**
   * Optional path to the config file that triggered the warning.
   */
  path?: string | null;
  /**
   * Optional range for the error location inside the config file.
   */
  range?: TextRange | null;
  /**
   * Concise summary of the warning.
   */
  summary: string;
}
export interface TextRange {
  end: TextPosition;
  start: TextPosition;
}
export interface TextPosition {
  /**
   * 1-based column number (in Unicode scalar values).
   */
  column: number;
  /**
   * 1-based line number.
   */
  line: number;
}
export interface FuzzyFileSearchSessionUpdatedNotification {
  method: FuzzyFileSearchSessionUpdatedNotificationMethod;
  params: FuzzyFileSearchSessionUpdatedNotification1;
}
export interface FuzzyFileSearchSessionUpdatedNotification1 {
  files: FuzzyFileSearchResult[];
  query: string;
  sessionId: string;
}
/**
 * Superset of [`codex_file_search::FileMatch`]
 */
export interface FuzzyFileSearchResult {
  file_name: string;
  indices?: number[] | null;
  match_type: FuzzyFileSearchMatchType;
  path: string;
  root: string;
  score: number;
}
export interface FuzzyFileSearchSessionCompletedNotification {
  method: FuzzyFileSearchSessionCompletedNotificationMethod;
  params: FuzzyFileSearchSessionCompletedNotification1;
}
export interface FuzzyFileSearchSessionCompletedNotification1 {
  sessionId: string;
}
export interface ThreadRealtimeStartedNotification {
  method: ThreadRealtimeStartedNotificationMethod;
  params: ThreadRealtimeStartedNotification1;
}
/**
 * EXPERIMENTAL - emitted when thread realtime startup is accepted.
 */
export interface ThreadRealtimeStartedNotification1 {
  realtimeSessionId?: string | null;
  threadId: string;
  version: RealtimeConversationVersion;
}
export interface ThreadRealtimeItemAddedNotification {
  method: ThreadRealtimeItemAddedNotificationMethod;
  params: ThreadRealtimeItemAddedNotification1;
}
/**
 * EXPERIMENTAL - raw non-audio thread realtime item emitted by the backend.
 */
export interface ThreadRealtimeItemAddedNotification1 {
  item: unknown;
  threadId: string;
}
export interface ThreadRealtimeItemStartedNotification {
  method: ThreadRealtimeItemStartedNotificationMethod;
  params: ThreadRealtimeItemStartedNotification1;
}
/**
 * EXPERIMENTAL - a realtime timeline item started before its content streams.
 */
export interface ThreadRealtimeItemStartedNotification1 {
  item: ThreadRealtimeItem;
  threadId: string;
}
export interface RealtimeSessionStartedThreadRealtimeItem {
  type: RealtimeSessionStartedThreadRealtimeItemType;
}
export interface TranscriptSegmentThreadRealtimeItem {
  role: ThreadRealtimeTranscriptRole;
  text: string;
  type: TranscriptSegmentThreadRealtimeItemType;
}
export interface BemItemPromotedThreadRealtimeItem {
  item_id: string;
  presentation: ThreadRealtimeBemItemPresentation;
  turn_id: string;
  type: BemItemPromotedThreadRealtimeItemType;
}
export interface WholeItemThreadRealtimeBemItemPresentation {
  type: WholeItemThreadRealtimeBemItemPresentationType;
}
export interface InlineMarkdownThreadRealtimeBemItemPresentation {
  type: InlineMarkdownThreadRealtimeBemItemPresentationType;
}
export interface InlineVisualizationThreadRealtimeBemItemPresentation {
  index: number;
  type: InlineVisualizationThreadRealtimeBemItemPresentationType;
}
export interface RealtimeSessionClosedThreadRealtimeItem {
  outcome: ThreadRealtimeSessionOutcome;
  type: RealtimeSessionClosedThreadRealtimeItemType;
}
export interface ThreadRealtimeItemTranscriptDeltaNotification {
  method: ThreadRealtimeItemTranscriptDeltaNotificationMethod;
  params: ThreadRealtimeItemTranscriptDeltaNotification1;
}
/**
 * EXPERIMENTAL - text appended to an active realtime transcript item.
 */
export interface ThreadRealtimeItemTranscriptDeltaNotification1 {
  delta: string;
  itemId: string;
  threadId: string;
}
export interface ThreadRealtimeItemCompletedNotification {
  method: ThreadRealtimeItemCompletedNotificationMethod;
  params: ThreadRealtimeItemCompletedNotification1;
}
/**
 * EXPERIMENTAL - a realtime timeline item published after canonical commit.
 */
export interface ThreadRealtimeItemCompletedNotification1 {
  item: ThreadRealtimeItem;
  threadId: string;
}
export interface ThreadRealtimeTranscriptDeltaNotification {
  method: ThreadRealtimeTranscriptDeltaNotificationMethod;
  params: ThreadRealtimeTranscriptDeltaNotification1;
}
/**
 * EXPERIMENTAL - flat transcript delta emitted whenever realtime transcript text changes.
 */
export interface ThreadRealtimeTranscriptDeltaNotification1 {
  /**
   * Live transcript delta from the realtime event.
   */
  delta: string;
  role: string;
  threadId: string;
}
export interface ThreadRealtimeTranscriptDoneNotification {
  method: ThreadRealtimeTranscriptDoneNotificationMethod;
  params: ThreadRealtimeTranscriptDoneNotification1;
}
/**
 * EXPERIMENTAL - final transcript text emitted when realtime completes a transcript part.
 */
export interface ThreadRealtimeTranscriptDoneNotification1 {
  role: string;
  /**
   * Final complete text for the transcript part.
   */
  text: string;
  threadId: string;
}
export interface ThreadRealtimeOutputAudioDeltaNotification {
  method: ThreadRealtimeOutputAudioDeltaNotificationMethod;
  params: ThreadRealtimeOutputAudioDeltaNotification1;
}
/**
 * EXPERIMENTAL - streamed output audio emitted by thread realtime.
 */
export interface ThreadRealtimeOutputAudioDeltaNotification1 {
  audio: ThreadRealtimeAudioChunk;
  threadId: string;
}
/**
 * EXPERIMENTAL - thread realtime audio chunk.
 */
export interface ThreadRealtimeAudioChunk {
  data: string;
  itemId?: string | null;
  numChannels: number;
  sampleRate: number;
  samplesPerChannel?: number | null;
}
export interface ThreadRealtimeSdpNotification {
  method: ThreadRealtimeSdpNotificationMethod;
  params: ThreadRealtimeSdpNotification1;
}
/**
 * EXPERIMENTAL - emitted with the remote SDP for a WebRTC realtime session.
 */
export interface ThreadRealtimeSdpNotification1 {
  sdp: string;
  threadId: string;
}
export interface ThreadRealtimeErrorNotification {
  method: ThreadRealtimeErrorNotificationMethod;
  params: ThreadRealtimeErrorNotification1;
}
/**
 * EXPERIMENTAL - emitted when thread realtime encounters an error.
 */
export interface ThreadRealtimeErrorNotification1 {
  message: string;
  threadId: string;
}
export interface ThreadRealtimeClosedNotification {
  method: ThreadRealtimeClosedNotificationMethod;
  params: ThreadRealtimeClosedNotification1;
}
/**
 * EXPERIMENTAL - emitted when thread realtime transport closes.
 */
export interface ThreadRealtimeClosedNotification1 {
  reason?: string | null;
  threadId: string;
}
/**
 * Notifies the user of world-writable directories on Windows, which cannot be protected by the sandbox.
 */
export interface WindowsWorldWritableWarningNotification {
  method: WindowsWorldWritableWarningNotificationMethod;
  params: WindowsWorldWritableWarningNotification1;
}
export interface WindowsWorldWritableWarningNotification1 {
  extraCount: number;
  failedScan: boolean;
  samplePaths: string[];
}
export interface WindowsSandboxSetupCompletedNotification {
  method: WindowsSandboxSetupCompletedNotificationMethod;
  params: WindowsSandboxSetupCompletedNotification1;
}
export interface WindowsSandboxSetupCompletedNotification1 {
  error?: string | null;
  mode: WindowsSandboxSetupMode;
  success: boolean;
}
export interface AccountLoginCompletedNotification {
  method: AccountLoginCompletedNotificationMethod;
  params: AccountLoginCompletedNotification1;
}
export interface AccountLoginCompletedNotification1 {
  error?: string | null;
  loginId?: string | null;
  onboardingEntrypoint?: DesktopOnboardingEntrypoint | null;
  success: boolean;
}
