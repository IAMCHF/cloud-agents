/**
 * 本文件由 scripts/codex-schema.mjs 自动生成，请勿手改。
 * 来源：codex-cli 0.167.0 `app-server generate-json-schema`。
 * 重新生成：`pnpm codex:schema`；漂移校验：`pnpm codex:schema:check`。
 */

/**
 * Request from the client to the server.
 */
export type ClientRequest =
  | InitializeRequest
  | ThreadStartRequest
  | ThreadResumeRequest
  | ThreadForkRequest
  | ThreadArchiveRequest
  | ThreadDeleteRequest
  | ThreadUnsubscribeRequest
  | ThreadNameSetRequest
  | ThreadGoalSetRequest
  | ThreadGoalGetRequest
  | ThreadGoalClearRequest
  | ThreadMetadataUpdateRequest
  | ThreadAttachmentAddRequest
  | ThreadAttachmentListRequest
  | ThreadAttachmentOwnerListRequest
  | ThreadAttachmentRemoveRequest
  | ThreadSectionMoveRequest
  | ThreadUnarchiveRequest
  | ThreadCompactStartRequest
  | ThreadShellCommandRequest
  | ThreadApproveGuardianDeniedActionRequest
  | ThreadRevertRequest
  | ThreadListRequest
  | ThreadSectionListRequest
  | ThreadSectionCreateRequest
  | ThreadSectionUpdateRequest
  | ThreadSectionDeleteRequest
  | ThreadLoadedListRequest
  | ThreadReadRequest
  | ThreadTurnsListRequest
  | ThreadItemsListRequest
  | ThreadInjectItemsRequest
  | SkillsListRequest
  | SkillsExtraRootsSetRequest
  | HooksListRequest
  | MarketplaceAddRequest
  | MarketplaceRemoveRequest
  | MarketplaceUpgradeRequest
  | PluginListRequest
  | PluginInstalledRequest
  | PluginReconcileRequest
  | PluginReadRequest
  | PluginSkillReadRequest
  | PluginShareSaveRequest
  | PluginShareUpdateTargetsRequest
  | PluginShareListRequest
  | PluginShareCheckoutRequest
  | PluginShareDeleteRequest
  | AppReadRequest
  | AppListRequest
  | AppInstalledRequest
  | FsReadFileRequest
  | FsWriteFileRequest
  | FsCreateDirectoryRequest
  | FsGetMetadataRequest
  | FsReadDirectoryRequest
  | FsRemoveRequest
  | FsCopyRequest
  | FsWatchRequest
  | FsUnwatchRequest
  | SkillsConfigWriteRequest
  | PluginInstallRequest
  | PluginUninstallRequest
  | TurnStartRequest
  | TurnSteerRequest
  | TurnInterruptRequest
  | ReviewStartRequest
  | ModelListRequest
  | AccountGatewayOAuthReadRequest
  | AccountGatewayOAuthLoginRequest
  | AccountGatewayOAuthCancelRequest
  | ModelProviderCapabilitiesReadRequest
  | ExperimentalFeatureListRequest
  | PermissionProfileListRequest
  | ExperimentalFeatureEnablementSetRequest
  | McpServerOauthLoginRequest
  | ConfigMcpServerReloadRequest
  | McpServerStatusListRequest
  | McpServerResourceReadRequest
  | McpServerToolCallRequest
  | WindowsSandboxSetupStartRequest
  | WindowsSandboxReadinessRequest
  | AccountLoginStartRequest
  | AccountLoginCancelRequest
  | AccountLogoutRequest
  | AccountRateLimitsReadRequest
  | AccountRateLimitResetCreditConsumeRequest
  | AccountUsageReadRequest
  | AccountWorkspaceMessagesReadRequest
  | AccountSendAddCreditsNudgeEmailRequest
  | FeedbackUploadRequest
  | FeedbackSaveRequest
  | CommandExecRequest
  | CommandExecWriteRequest
  | CommandExecTerminateRequest
  | CommandExecResizeRequest
  | ConfigReadRequest
  | ExternalAgentConfigDetectRequest
  | ExternalAgentConfigImportRequest
  | ExternalAgentConfigImportRecordHistoryRequest
  | ExternalAgentConfigImportReadHistoriesRequest
  | ConfigValueWriteRequest
  | ConfigBatchWriteRequest
  | ConfigRequirementsReadRequest
  | AccountReadRequest
  | FuzzyFileSearchRequest;
export type RequestId = string | number;
export type InitializeRequestMethod = "initialize";
export type ThreadStartRequestMethod = "thread/start";
export type AskForApproval = ("untrusted" | "on-request" | "never") | GranularAskForApproval;
/**
 * Configures who approval requests are routed to for review. Examples include sandbox escapes, blocked network access, MCP approval prompts, and ARC escalations. Defaults to `user`. `auto_review` uses a carefully prompted subagent to gather relevant context and apply a risk-based decision framework before approving or denying the request. The legacy value `guardian_subagent` is accepted for compatibility.
 */
export type ApprovalsReviewer = "user" | "auto_review" | "guardian_subagent";
/**
 * Deprecated: `friendly` and `pragmatic` no longer select a style.
 */
export type Personality = "none" | "friendly" | "pragmatic";
export type SandboxMode = "read-only" | "workspace-write" | "danger-full-access";
export type ThreadStartSource = "startup" | "clear";
export type ThreadSource = string;
export type ThreadResumeRequestMethod = "thread/resume";
export type ThreadForkRequestMethod = "thread/fork";
export type ThreadArchiveRequestMethod = "thread/archive";
export type ThreadDeleteRequestMethod = "thread/delete";
export type ThreadUnsubscribeRequestMethod = "thread/unsubscribe";
export type ThreadNameSetRequestMethod = "thread/name/set";
export type ThreadGoalSetRequestMethod = "thread/goal/set";
/**
 * Distinguishes explicit user actions from automatic goal lifecycle mutations.
 */
export type ThreadGoalMutationOrigin = "user" | "automatic";
export type ThreadGoalStatus = "active" | "paused" | "blocked" | "usageLimited" | "budgetLimited" | "complete";
export type ThreadGoalGetRequestMethod = "thread/goal/get";
export type ThreadGoalClearRequestMethod = "thread/goal/clear";
export type ThreadMetadataUpdateRequestMethod = "thread/metadata/update";
export type ThreadAttachmentAddRequestMethod = "thread/attachment/add";
export type ThreadAttachmentListRequestMethod = "thread/attachment/list";
export type ThreadAttachmentOwnerListRequestMethod = "thread/attachmentOwner/list";
export type ThreadAttachmentRemoveRequestMethod = "thread/attachment/remove";
export type ThreadSectionMoveRequestMethod = "thread/section/move";
export type ThreadUnarchiveRequestMethod = "thread/unarchive";
export type ThreadCompactStartRequestMethod = "thread/compact/start";
export type ThreadShellCommandRequestMethod = "thread/shellCommand";
export type ThreadApproveGuardianDeniedActionRequestMethod = "thread/approveGuardianDeniedAction";
export type ThreadRevertRequestMethod = "thread/revert";
export type ThreadListRequestMethod = "thread/list";
export type ThreadListCwdFilter = string | string[];
export type SortDirection = "asc" | "desc";
export type ThreadSortKey = "created_at" | "updated_at" | "recency_at" | "section_position";
export type ThreadSourceKind =
  | "cli"
  | "vscode"
  | "exec"
  | "appServer"
  | "subAgent"
  | "subAgentReview"
  | "subAgentCompact"
  | "subAgentThreadSpawn"
  | "subAgentOther"
  | "unknown";
export type ThreadSectionListRequestMethod = "threadSection/list";
export type ThreadSectionCreateRequestMethod = "threadSection/create";
export type ThreadSectionUpdateRequestMethod = "threadSection/update";
export type ThreadSectionDeleteRequestMethod = "threadSection/delete";
export type ThreadLoadedListRequestMethod = "thread/loaded/list";
export type ThreadReadRequestMethod = "thread/read";
export type ThreadTurnsListRequestMethod = "thread/turns/list";
export type TurnItemsView = "notLoaded" | "summary" | "full";
export type ThreadItemsListRequestMethod = "thread/items/list";
/**
 * Starting position for an item-history page.
 */
export type ThreadItemsListCursor = string | ThreadItemsListAnchor;
/**
 * An exclusive item position within the requested visible turn.
 */
export type ThreadItemsListAnchor = ItemThreadItemsListAnchor;
export type ItemThreadItemsListAnchorType = "item";
export type ThreadInjectItemsRequestMethod = "thread/inject_items";
export type SkillsListRequestMethod = "skills/list";
export type SkillsExtraRootsSetRequestMethod = "skills/extraRoots/set";
/**
 * A path that is guaranteed to be absolute and normalized (though it is not guaranteed to be canonicalized or exist on the filesystem).
 *
 * IMPORTANT: When deserializing an `AbsolutePathBuf`, a base path must be set using [AbsolutePathBufGuard::new]. If no base path is set, the deserialization will fail unless the path being deserialized is already absolute.
 */
export type AbsolutePathBuf = string;
export type HooksListRequestMethod = "hooks/list";
export type MarketplaceAddRequestMethod = "marketplace/add";
export type MarketplaceRemoveRequestMethod = "marketplace/remove";
export type MarketplaceUpgradeRequestMethod = "marketplace/upgrade";
export type PluginListRequestMethod = "plugin/list";
export type PluginListMarketplaceKind =
  "local" | "vertical" | "workspace-directory" | "shared-with-me" | "created-by-me-remote";
export type PluginInstalledRequestMethod = "plugin/installed";
export type PluginReconcileRequestMethod = "plugin/reconcile";
export type PluginReadRequestMethod = "plugin/read";
export type PluginSkillReadRequestMethod = "plugin/skill/read";
export type PluginShareSaveRequestMethod = "plugin/share/save";
export type PluginShareDiscoverability = "LISTED" | "UNLISTED" | "PRIVATE";
export type PluginSharePrincipalType = "user" | "group" | "workspace";
export type PluginShareTargetRole = "reader" | "editor";
export type PluginShareUpdateTargetsRequestMethod = "plugin/share/updateTargets";
export type PluginShareUpdateDiscoverability = "UNLISTED" | "PRIVATE" | "LISTED";
export type PluginShareListRequestMethod = "plugin/share/list";
export type PluginShareCheckoutRequestMethod = "plugin/share/checkout";
export type PluginShareDeleteRequestMethod = "plugin/share/delete";
export type AppReadRequestMethod = "app/read";
export type AppListRequestMethod = "app/list";
export type AppInstalledRequestMethod = "app/installed";
export type FsReadFileRequestMethod = "fs/readFile";
export type FsWriteFileRequestMethod = "fs/writeFile";
export type FsCreateDirectoryRequestMethod = "fs/createDirectory";
export type FsGetMetadataRequestMethod = "fs/getMetadata";
export type FsReadDirectoryRequestMethod = "fs/readDirectory";
export type FsRemoveRequestMethod = "fs/remove";
export type FsCopyRequestMethod = "fs/copy";
export type FsWatchRequestMethod = "fs/watch";
export type FsUnwatchRequestMethod = "fs/unwatch";
export type SkillsConfigWriteRequestMethod = "skills/config/write";
export type PluginInstallRequestMethod = "plugin/install";
export type PluginUninstallRequestMethod = "plugin/uninstall";
export type TurnStartRequestMethod = "turn/start";
/**
 * A non-empty reasoning effort value advertised by the model.
 */
export type ReasoningEffort = string;
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
export type TurnSteerRequestMethod = "turn/steer";
export type TurnInterruptRequestMethod = "turn/interrupt";
export type ReviewStartRequestMethod = "review/start";
export type ReviewDelivery = "inline";
export type ReviewTarget =
  UncommittedChangesReviewTarget | BaseBranchReviewTarget | CommitReviewTarget | CustomReviewTarget;
export type UncommittedChangesReviewTargetType = "uncommittedChanges";
export type BaseBranchReviewTargetType = "baseBranch";
export type CommitReviewTargetType = "commit";
export type CustomReviewTargetType = "custom";
export type ModelListRequestMethod = "model/list";
export type AccountGatewayOAuthReadRequestMethod = "account/gatewayOAuth/read";
export type AccountGatewayOAuthLoginRequestMethod = "account/gatewayOAuth/login";
export type AccountGatewayOAuthCancelRequestMethod = "account/gatewayOAuth/cancel";
export type ModelProviderCapabilitiesReadRequestMethod = "modelProvider/capabilities/read";
export type ExperimentalFeatureListRequestMethod = "experimentalFeature/list";
export type PermissionProfileListRequestMethod = "permissionProfile/list";
export type ExperimentalFeatureEnablementSetRequestMethod = "experimentalFeature/enablement/set";
export type McpServerOauthLoginRequestMethod = "mcpServer/oauth/login";
export type McpServerOauthClientRegistration = "auto" | "cimd" | "dcr";
export type ConfigMcpServerReloadRequestMethod = "config/mcpServer/reload";
export type McpServerStatusListRequestMethod = "mcpServerStatus/list";
export type McpServerStatusDetail = "full" | "toolsAndAuthOnly";
export type McpServerResourceReadRequestMethod = "mcpServer/resource/read";
export type McpServerToolCallRequestMethod = "mcpServer/tool/call";
export type WindowsSandboxSetupStartRequestMethod = "windowsSandbox/setupStart";
export type WindowsSandboxSetupMode = "elevated" | "unelevated";
export type WindowsSandboxReadinessRequestMethod = "windowsSandbox/readiness";
export type AccountLoginStartRequestMethod = "account/login/start";
export type LoginAccountParams =
  | ApiKeyLoginAccountParams
  | ChatgptLoginAccountParams
  | ChatgptDeviceCodeLoginAccountParams
  | ChatgptAuthTokensLoginAccountParams
  | AmazonBedrockLoginAccountParams
  | AmazonBedrockAccessKeysLoginAccountParams;
export type ApiKeyLoginAccountParamsType = "apiKey";
export type LoginAppBrand = "codex" | "chatgpt";
export type ChatgptLoginAccountParamsType = "chatgpt";
export type ChatgptDeviceCodeLoginAccountParamsType = "chatgptDeviceCode";
export type ChatgptAuthTokensLoginAccountParamsType = "chatgptAuthTokens";
export type AmazonBedrockLoginAccountParamsType = "amazonBedrock";
export type AmazonBedrockAccessKeysLoginAccountParamsType = "amazonBedrockAccessKeys";
export type AccountLoginCancelRequestMethod = "account/login/cancel";
export type AccountLogoutRequestMethod = "account/logout";
export type AccountRateLimitsReadRequestMethod = "account/rateLimits/read";
export type AccountRateLimitResetCreditConsumeRequestMethod = "account/rateLimitResetCredit/consume";
export type AccountUsageReadRequestMethod = "account/usage/read";
export type AccountWorkspaceMessagesReadRequestMethod = "account/workspaceMessages/read";
export type AccountSendAddCreditsNudgeEmailRequestMethod = "account/sendAddCreditsNudgeEmail";
export type AddCreditsNudgeCreditType = "credits" | "usage_limit";
export type FeedbackUploadRequestMethod = "feedback/upload";
export type FeedbackSaveRequestMethod = "feedback/save";
export type LegacyAppPathString = string;
export type CommandExecRequestMethod = "command/exec";
export type CommandExecWriteRequestMethod = "command/exec/write";
export type CommandExecTerminateRequestMethod = "command/exec/terminate";
export type CommandExecResizeRequestMethod = "command/exec/resize";
export type ConfigReadRequestMethod = "config/read";
export type ExternalAgentConfigDetectRequestMethod = "externalAgentConfig/detect";
export type ExternalAgentConfigImportRequestMethod = "externalAgentConfig/import";
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
export type ExternalAgentConfigImportRecordHistoryRequestMethod = "externalAgentConfig/import/recordHistory";
export type ExternalAgentConfigImportReadHistoriesRequestMethod = "externalAgentConfig/import/readHistories";
export type ConfigValueWriteRequestMethod = "config/value/write";
export type MergeStrategy = "replace" | "upsert";
export type ConfigBatchWriteRequestMethod = "config/batchWrite";
export type ConfigRequirementsReadRequestMethod = "configRequirements/read";
export type AccountReadRequestMethod = "account/read";
export type FuzzyFileSearchRequestMethod = "fuzzyFileSearch";

export interface InitializeRequest {
  id: RequestId;
  method: InitializeRequestMethod;
  params: InitializeParams;
}
export interface InitializeParams {
  capabilities?: InitializeCapabilities | null;
  clientInfo: ClientInfo;
}
/**
 * Client-declared capabilities negotiated during initialize.
 */
export interface InitializeCapabilities {
  /**
   * Opt into receiving experimental API methods and fields.
   */
  experimentalApi?: boolean;
  /**
   * Use explicit gateway OAuth login instead of automatic browser authorization. Applies to this app-server's gateway runtime; later connections cannot undo it.
   */
  explicitGatewayOauth?: boolean;
  /**
   * MCP extension settings declared by the app-server client.
   */
  extensions?: {
    [k: string]: unknown;
  } | null;
  /**
   * Legacy opt-in for the `openai/form` MCP extension.
   *
   * New clients should declare `openai/form` in [`Self::extensions`].
   */
  mcpServerOpenaiFormElicitation?: boolean;
  /**
   * Exact notification method names that should be suppressed for this connection (for example `thread/started`).
   */
  optOutNotificationMethods?: string[] | null;
  /**
   * Opt into `attestation/generate` requests for upstream `x-oai-attestation`.
   */
  requestAttestation?: boolean;
  /**
   * Present `humanCommand` approvals to a person and return only a one-time decision. Requires `experimentalApi`. Pending requests can be replayed to compatible clients.
   */
  requiredHumanApproval?: boolean;
}
export interface ClientInfo {
  name: string;
  title?: string | null;
  version: string;
}
/**
 * NEW APIs
 */
export interface ThreadStartRequest {
  id: RequestId;
  method: ThreadStartRequestMethod;
  params: ThreadStartParams;
}
export interface ThreadStartParams {
  approvalPolicy?: AskForApproval | null;
  /**
   * Override where approval requests are routed for review on this thread and subsequent turns.
   */
  approvalsReviewer?: ApprovalsReviewer | null;
  baseInstructions?: string | null;
  config?: {
    [k: string]: unknown;
  } | null;
  cwd?: string | null;
  developerInstructions?: string | null;
  ephemeral?: boolean | null;
  model?: string | null;
  modelProvider?: string | null;
  /**
   * @deprecated `friendly` and `pragmatic` no longer select a style.
   */
  personality?: Personality | null;
  sandbox?: SandboxMode | null;
  serviceName?: string | null;
  serviceTier?: string | null;
  sessionStartSource?: ThreadStartSource | null;
  /**
   * Optional client-supplied analytics source classification for this thread.
   */
  threadSource?: ThreadSource | null;
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
export interface ThreadResumeRequest {
  id: RequestId;
  method: ThreadResumeRequestMethod;
  params: ThreadResumeParams;
}
/**
 * There are three ways to resume a thread: 1. By thread_id: load the thread from disk by thread_id and resume it. 2. By history: instantiate the thread from memory and resume it. 3. By path: load the thread from disk by path and resume it.
 *
 * For non-running threads, the precedence is: history > non-empty path > thread_id. If using history or a non-empty path for a non-running thread, the thread_id param will be ignored.
 *
 * If thread_id identifies a running thread, app-server rejoins that thread and treats a non-empty path as a consistency check against the active rollout path. Empty string path values are treated as absent.
 *
 * Prefer using thread_id whenever possible.
 */
export interface ThreadResumeParams {
  approvalPolicy?: AskForApproval | null;
  /**
   * Override where approval requests are routed for review on this thread and subsequent turns.
   */
  approvalsReviewer?: ApprovalsReviewer | null;
  baseInstructions?: string | null;
  config?: {
    [k: string]: unknown;
  } | null;
  cwd?: string | null;
  developerInstructions?: string | null;
  /**
   * When true, return only thread metadata and live-resume state without populating `thread.turns`. This is useful when the client plans to call `thread/turns/list` immediately after resuming. Full-history hydration is deprecated for paginated threads; use this with `thread/turns/list` and `thread/items/list` instead.
   */
  excludeTurns?: boolean;
  /**
   * Configuration overrides for the resumed thread, if any.
   */
  model?: string | null;
  modelProvider?: string | null;
  /**
   * @deprecated `friendly` and `pragmatic` no longer select a style. Changing this does not rewrite the thread's existing instructions.
   */
  personality?: Personality | null;
  sandbox?: SandboxMode | null;
  serviceTier?: string | null;
  threadId: string;
}
export interface ThreadForkRequest {
  id: RequestId;
  method: ThreadForkRequestMethod;
  params: ThreadForkParams;
}
/**
 * There are two ways to fork a thread: 1. By thread_id: load the thread from disk by thread_id and fork it into a new thread. 2. By path: load the thread from disk by path and fork it into a new thread.
 *
 * If using a non-empty path, the thread_id param will be ignored. Empty string path values are treated as absent.
 *
 * Prefer using thread_id whenever possible.
 */
export interface ThreadForkParams {
  approvalPolicy?: AskForApproval | null;
  /**
   * Override where approval requests are routed for review on this thread and subsequent turns.
   */
  approvalsReviewer?: ApprovalsReviewer | null;
  baseInstructions?: string | null;
  config?: {
    [k: string]: unknown;
  } | null;
  cwd?: string | null;
  developerInstructions?: string | null;
  ephemeral?: boolean;
  /**
   * When true, return only thread metadata and live fork state without populating `thread.turns`. This is useful when the client plans to call `thread/turns/list` immediately after forking. Full-history hydration is deprecated for paginated threads; use this with `thread/turns/list` and `thread/items/list` instead.
   */
  excludeTurns?: boolean;
  /**
   * Optional last turn id to fork through, inclusive.
   *
   * When specified, turns after `last_turn_id` are omitted from the fork. The referenced turn cannot be in progress.
   */
  lastTurnId?: string | null;
  /**
   * Configuration overrides for the forked thread, if any.
   */
  model?: string | null;
  modelProvider?: string | null;
  sandbox?: SandboxMode | null;
  serviceTier?: string | null;
  threadId: string;
  /**
   * Optional client-supplied analytics source classification for this forked thread.
   */
  threadSource?: ThreadSource | null;
}
export interface ThreadArchiveRequest {
  id: RequestId;
  method: ThreadArchiveRequestMethod;
  params: ThreadArchiveParams;
}
export interface ThreadArchiveParams {
  threadId: string;
}
export interface ThreadDeleteRequest {
  id: RequestId;
  method: ThreadDeleteRequestMethod;
  params: ThreadDeleteParams;
}
export interface ThreadDeleteParams {
  threadId: string;
}
export interface ThreadUnsubscribeRequest {
  id: RequestId;
  method: ThreadUnsubscribeRequestMethod;
  params: ThreadUnsubscribeParams;
}
export interface ThreadUnsubscribeParams {
  threadId: string;
}
export interface ThreadNameSetRequest {
  id: RequestId;
  method: ThreadNameSetRequestMethod;
  params: ThreadSetNameParams;
}
export interface ThreadSetNameParams {
  name: string;
  threadId: string;
}
export interface ThreadGoalSetRequest {
  id: RequestId;
  method: ThreadGoalSetRequestMethod;
  params: ThreadGoalSetParams;
}
export interface ThreadGoalSetParams {
  objective?: string | null;
  /**
   * Missing provenance does not supply user authorization.
   */
  origin?: ThreadGoalMutationOrigin | null;
  status?: ThreadGoalStatus | null;
  threadId: string;
  tokenBudget?: number | null;
}
export interface ThreadGoalGetRequest {
  id: RequestId;
  method: ThreadGoalGetRequestMethod;
  params: ThreadGoalGetParams;
}
export interface ThreadGoalGetParams {
  threadId: string;
}
export interface ThreadGoalClearRequest {
  id: RequestId;
  method: ThreadGoalClearRequestMethod;
  params: ThreadGoalClearParams;
}
export interface ThreadGoalClearParams {
  /**
   * Missing provenance does not supply user authorization.
   */
  origin?: ThreadGoalMutationOrigin | null;
  threadId: string;
}
export interface ThreadMetadataUpdateRequest {
  id: RequestId;
  method: ThreadMetadataUpdateRequestMethod;
  params: ThreadMetadataUpdateParams;
}
export interface ThreadMetadataUpdateParams {
  /**
   * Patch the stored Git metadata for this thread. Omit a field to leave it unchanged, set it to `null` to clear it, or provide a string to replace the stored value.
   */
  gitInfo?: ThreadMetadataGitInfoUpdateParams | null;
  threadId: string;
}
export interface ThreadMetadataGitInfoUpdateParams {
  /**
   * Omit to leave the stored branch unchanged, set to `null` to clear it, or provide a non-empty string to replace it.
   */
  branch?: string | null;
  /**
   * Omit to leave the stored origin URL unchanged, set to `null` to clear it, or provide a non-empty string to replace it.
   */
  originUrl?: string | null;
  /**
   * Omit to leave the stored commit unchanged, set to `null` to clear it, or provide a non-empty string to replace it.
   */
  sha?: string | null;
}
export interface ThreadAttachmentAddRequest {
  id: RequestId;
  method: ThreadAttachmentAddRequestMethod;
  params: ThreadAttachmentAddParams;
}
/**
 * Parameters for creating or locating an attachment on its owning thread.
 */
export interface ThreadAttachmentAddParams {
  attachmentType: string;
  identityKey: string;
  payload: unknown;
  threadId: string;
}
export interface ThreadAttachmentListRequest {
  id: RequestId;
  method: ThreadAttachmentListRequestMethod;
  params: ThreadAttachmentListParams;
}
/**
 * Parameters for listing attachments from one thread.
 */
export interface ThreadAttachmentListParams {
  cursor?: string | null;
  limit?: number | null;
  threadId: string;
}
export interface ThreadAttachmentOwnerListRequest {
  id: RequestId;
  method: ThreadAttachmentOwnerListRequestMethod;
  params: ThreadAttachmentOwnerListParams;
}
/**
 * Parameters for reverse lookup by attachment identity within this server's store.
 */
export interface ThreadAttachmentOwnerListParams {
  /**
   * Omitted or null returns all matches; false returns non-archived threads only.
   */
  archived?: boolean | null;
  attachmentType: string;
  cursor?: string | null;
  identityKey: string;
  limit?: number | null;
}
export interface ThreadAttachmentRemoveRequest {
  id: RequestId;
  method: ThreadAttachmentRemoveRequestMethod;
  params: ThreadAttachmentRemoveParams;
}
/**
 * Parameters for deleting an attachment by its stable thread-local identity.
 */
export interface ThreadAttachmentRemoveParams {
  attachmentType: string;
  identityKey: string;
  threadId: string;
}
export interface ThreadSectionMoveRequest {
  id: RequestId;
  method: ThreadSectionMoveRequestMethod;
  params: ThreadSectionMoveParams;
}
/**
 * Parameters for moving a thread within a server-owned section ordering.
 */
export interface ThreadSectionMoveParams {
  /**
   * Existing thread to insert before; omission or null appends to the section.
   */
  beforeThreadId?: string | null;
  /**
   * Destination section, or `null` to remove the thread from its section.
   */
  sectionId: string | null;
  /**
   * Thread to move into, within, or out of a section.
   */
  threadId: string;
}
export interface ThreadUnarchiveRequest {
  id: RequestId;
  method: ThreadUnarchiveRequestMethod;
  params: ThreadUnarchiveParams;
}
export interface ThreadUnarchiveParams {
  threadId: string;
}
export interface ThreadCompactStartRequest {
  id: RequestId;
  method: ThreadCompactStartRequestMethod;
  params: ThreadCompactStartParams;
}
export interface ThreadCompactStartParams {
  threadId: string;
}
export interface ThreadShellCommandRequest {
  id: RequestId;
  method: ThreadShellCommandRequestMethod;
  params: ThreadShellCommandParams;
}
export interface ThreadShellCommandParams {
  /**
   * Shell command string evaluated by the thread's configured shell. Unlike `command/exec`, this intentionally preserves shell syntax such as pipes, redirects, and quoting. This runs unsandboxed with full access rather than inheriting the thread sandbox policy.
   */
  command: string;
  threadId: string;
  /**
   * Maximum execution time in milliseconds. Defaults to one hour when omitted or null. Must be non-negative; zero requests an immediate timeout, not unlimited execution. Does not affect the immediate RPC acknowledgement.
   */
  timeoutMs?: number | null;
}
export interface ThreadApproveGuardianDeniedActionRequest {
  id: RequestId;
  method: ThreadApproveGuardianDeniedActionRequestMethod;
  params: ThreadApproveGuardianDeniedActionParams;
}
export interface ThreadApproveGuardianDeniedActionParams {
  /**
   * Serialized `codex_protocol::protocol::GuardianAssessmentEvent`.
   */
  event: {
    [k: string]: unknown;
  };
  threadId: string;
}
export interface ThreadRevertRequest {
  id: RequestId;
  method: ThreadRevertRequestMethod;
  params: ThreadRevertParams;
}
/**
 * Replace a paginated thread's durable history with the prefix before one turn.
 *
 * This only changes persisted conversation history. It does not revert local file changes.
 */
export interface ThreadRevertParams {
  /**
   * Turn excluded from the replacement history, together with every later turn.
   */
  beforeTurnId: string;
  threadId: string;
}
export interface ThreadListRequest {
  id: RequestId;
  method: ThreadListRequestMethod;
  params: ThreadListParams;
}
export interface ThreadListParams {
  /**
   * Optional archived filter; when set to true, only archived threads are returned. If false or null, only non-archived threads are returned.
   */
  archived?: boolean | null;
  /**
   * Opaque pagination cursor returned by a previous call.
   */
  cursor?: string | null;
  /**
   * Optional cwd filter or filters; when set, only threads whose session cwd exactly matches one of these paths are returned.
   */
  cwd?: ThreadListCwdFilter | null;
  /**
   * Thread IDs to exclude before applying the result limit. Up to 100 entries; invalid IDs or a larger list are rejected, never truncated. Send the same exclusions on each page. Omitted, null, or empty means no exclusions.
   */
  excludedThreadIds?: string[] | null;
  /**
   * Optional page size; defaults to a reasonable server-side value.
   */
  limit?: number | null;
  /**
   * Optional provider filter; when set, only sessions recorded under these providers are returned. When present but empty, includes all providers.
   */
  modelProviders?: string[] | null;
  /**
   * Optional originator allowlist, matching any supplied value exactly. Supported by hosted backends only; the local app-server rejects a nonempty list. Omitted or empty lists leave originators unrestricted.
   */
  originators?: string[] | null;
  /**
   * Optional substring filter for the extracted thread title.
   */
  searchTerm?: string | null;
  /**
   * Omit to include every section, set to `null` for unsectioned threads, or provide a section ID to return only threads in that section.
   */
  sectionId?: string | null;
  /**
   * Optional sort direction; defaults to descending (newest first).
   */
  sortDirection?: SortDirection | null;
  /**
   * Optional sort key; defaults to created_at.
   */
  sortKey?: ThreadSortKey | null;
  /**
   * Optional source filter; when set, only sessions from these source kinds are returned. When omitted or empty, defaults to interactive sources.
   */
  sourceKinds?: ThreadSourceKind[] | null;
  /**
   * If true, return from the state DB without scanning JSONL rollouts to repair thread metadata. Omitted or false preserves scan-and-repair behavior.
   */
  useStateDbOnly?: boolean;
}
export interface ThreadSectionListRequest {
  id: RequestId;
  method: ThreadSectionListRequestMethod;
  params: ThreadSectionListParams;
}
/**
 * Parameters for listing independently persisted thread sections.
 */
export interface ThreadSectionListParams {
  /**
   * Opaque pagination cursor returned by a previous call.
   */
  cursor?: string | null;
  /**
   * Maximum number of sections to return.
   */
  limit?: number | null;
}
export interface ThreadSectionCreateRequest {
  id: RequestId;
  method: ThreadSectionCreateRequestMethod;
  params: ThreadSectionCreateParams;
}
/**
 * Parameters for creating an independently persisted thread section.
 */
export interface ThreadSectionCreateParams {
  appearance?: ThreadSectionAppearance | null;
  /**
   * The user-visible name of the section.
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
export interface ThreadSectionUpdateRequest {
  id: RequestId;
  method: ThreadSectionUpdateRequestMethod;
  params: ThreadSectionUpdateParams;
}
/**
 * Parameters for updating an independently persisted thread section.
 */
export interface ThreadSectionUpdateParams {
  /**
   * Omit to preserve appearance, use `null` to clear it, or provide a replacement.
   */
  appearance?: ThreadSectionAppearance | null;
  /**
   * The updated user-visible name of the section.
   */
  name: string;
  /**
   * The stable, server-generated identity of the section to update.
   */
  sectionId: string;
}
export interface ThreadSectionDeleteRequest {
  id: RequestId;
  method: ThreadSectionDeleteRequestMethod;
  params: ThreadSectionDeleteParams;
}
/**
 * Parameters for deleting an independently persisted thread section.
 */
export interface ThreadSectionDeleteParams {
  /**
   * The stable, server-generated identity of the section to delete.
   */
  sectionId: string;
}
export interface ThreadLoadedListRequest {
  id: RequestId;
  method: ThreadLoadedListRequestMethod;
  params: ThreadLoadedListParams;
}
export interface ThreadLoadedListParams {
  /**
   * Opaque pagination cursor returned by a previous call.
   */
  cursor?: string | null;
  /**
   * Optional page size; defaults to no limit.
   */
  limit?: number | null;
}
export interface ThreadReadRequest {
  id: RequestId;
  method: ThreadReadRequestMethod;
  params: ThreadReadParams;
}
export interface ThreadReadParams {
  /**
   * When true, include turns and their items from rollout history. Full-history hydration is deprecated for paginated threads; prefer a metadata-only read and page with `thread/turns/list` and `thread/items/list`.
   */
  includeTurns?: boolean;
  threadId: string;
}
export interface ThreadTurnsListRequest {
  id: RequestId;
  method: ThreadTurnsListRequestMethod;
  params: ThreadTurnsListParams;
}
export interface ThreadTurnsListParams {
  /**
   * Opaque cursor to pass to the next call to continue after the last turn.
   */
  cursor?: string | null;
  /**
   * How much item detail to include for each returned turn; defaults to summary.
   */
  itemsView?: TurnItemsView | null;
  /**
   * Optional turn page size.
   */
  limit?: number | null;
  /**
   * Optional turn pagination direction; defaults to descending.
   */
  sortDirection?: SortDirection | null;
  threadId: string;
}
export interface ThreadItemsListRequest {
  id: RequestId;
  method: ThreadItemsListRequestMethod;
  params: ThreadItemsListParams;
}
export interface ThreadItemsListParams {
  /**
   * Opaque continuation cursor or an exclusive item anchor in the requested visible turn. An item anchor requires a non-empty `turnId`; ascending (the default) returns items after it, and descending returns items before it. Continue with the returned string cursor.
   */
  cursor?: ThreadItemsListCursor | null;
  /**
   * Optional item page size.
   */
  limit?: number | null;
  /**
   * Optional item pagination direction; defaults to ascending.
   */
  sortDirection?: SortDirection | null;
  threadId: string;
  /**
   * Optional turn id to filter by. When omitted, returns items across the thread.
   */
  turnId?: string | null;
}
export interface ItemThreadItemsListAnchor {
  itemId: string;
  type: ItemThreadItemsListAnchorType;
}
/**
 * Append raw Responses API items to the thread history without starting a user turn.
 */
export interface ThreadInjectItemsRequest {
  id: RequestId;
  method: ThreadInjectItemsRequestMethod;
  params: ThreadInjectItemsParams;
}
export interface ThreadInjectItemsParams {
  /**
   * Raw Responses API items to append to the thread's model-visible history.
   */
  items: unknown[];
  threadId: string;
}
export interface SkillsListRequest {
  id: RequestId;
  method: SkillsListRequestMethod;
  params: SkillsListParams;
}
export interface SkillsListParams {
  /**
   * When empty, defaults to the current session working directory.
   */
  cwds?: string[];
  /**
   * When true, bypass the skills cache and re-scan skills from disk.
   */
  forceReload?: boolean;
}
export interface SkillsExtraRootsSetRequest {
  id: RequestId;
  method: SkillsExtraRootsSetRequestMethod;
  params: SkillsExtraRootsSetParams;
}
export interface SkillsExtraRootsSetParams {
  extraRoots: AbsolutePathBuf[];
}
export interface HooksListRequest {
  id: RequestId;
  method: HooksListRequestMethod;
  params: HooksListParams;
}
export interface HooksListParams {
  /**
   * Working directories to inspect when no thread is specified. An empty list uses the session cwd.
   */
  cwds?: string[];
  /**
   * List a loaded thread's hooks, including its selected environments. Omit `cwds` in this mode.
   */
  threadId?: string | null;
}
export interface MarketplaceAddRequest {
  id: RequestId;
  method: MarketplaceAddRequestMethod;
  params: MarketplaceAddParams;
}
export interface MarketplaceAddParams {
  refName?: string | null;
  source: string;
  sparsePaths?: string[] | null;
}
export interface MarketplaceRemoveRequest {
  id: RequestId;
  method: MarketplaceRemoveRequestMethod;
  params: MarketplaceRemoveParams;
}
export interface MarketplaceRemoveParams {
  marketplaceName: string;
}
export interface MarketplaceUpgradeRequest {
  id: RequestId;
  method: MarketplaceUpgradeRequestMethod;
  params: MarketplaceUpgradeParams;
}
export interface MarketplaceUpgradeParams {
  marketplaceName?: string | null;
}
export interface PluginListRequest {
  id: RequestId;
  method: PluginListRequestMethod;
  params: PluginListParams;
}
export interface PluginListParams {
  /**
   * Optional working directories used to discover repo marketplaces. When omitted, only home-scoped marketplaces and the official curated marketplace are considered.
   */
  cwds?: AbsolutePathBuf[] | null;
  /**
   * Whether the client requests a fresh remote plugin catalog fetch.
   */
  forceRefetch?: boolean;
  /**
   * Optional marketplace kind filter. When omitted, only local marketplaces are queried, plus the default remote catalog when enabled by feature flag.
   */
  marketplaceKinds?: PluginListMarketplaceKind[] | null;
}
export interface PluginInstalledRequest {
  id: RequestId;
  method: PluginInstalledRequestMethod;
  params: PluginInstalledParams;
}
export interface PluginInstalledParams {
  /**
   * Optional working directories used to discover repo marketplaces.
   */
  cwds?: AbsolutePathBuf[] | null;
  /**
   * Additional uninstalled plugin names that should be returned when present locally. This is used by mention surfaces that intentionally expose install entrypoints.
   */
  installSuggestionPluginNames?: string[] | null;
}
export interface PluginReconcileRequest {
  id: RequestId;
  method: PluginReconcileRequestMethod;
  params: PluginReconcileParams;
}
export interface PluginReconcileParams {
  /**
   * Optional client-provided reason recorded with the reconciliation attempt.
   */
  reason?: string | null;
}
export interface PluginReadRequest {
  id: RequestId;
  method: PluginReadRequestMethod;
  params: PluginReadParams;
}
export interface PluginReadParams {
  marketplacePath?: AbsolutePathBuf | null;
  pluginName: string;
  remoteMarketplaceName?: string | null;
}
export interface PluginSkillReadRequest {
  id: RequestId;
  method: PluginSkillReadRequestMethod;
  params: PluginSkillReadParams;
}
export interface PluginSkillReadParams {
  remoteMarketplaceName: string;
  remotePluginId: string;
  skillName: string;
}
export interface PluginShareSaveRequest {
  id: RequestId;
  method: PluginShareSaveRequestMethod;
  params: PluginShareSaveParams;
}
export interface PluginShareSaveParams {
  discoverability?: PluginShareDiscoverability | null;
  pluginPath: AbsolutePathBuf;
  remotePluginId?: string | null;
  shareTargets?: PluginShareTarget[] | null;
}
export interface PluginShareTarget {
  principalId: string;
  principalType: PluginSharePrincipalType;
  role: PluginShareTargetRole;
}
export interface PluginShareUpdateTargetsRequest {
  id: RequestId;
  method: PluginShareUpdateTargetsRequestMethod;
  params: PluginShareUpdateTargetsParams;
}
export interface PluginShareUpdateTargetsParams {
  discoverability: PluginShareUpdateDiscoverability;
  remotePluginId: string;
  shareTargets: PluginShareTarget[];
}
export interface PluginShareListRequest {
  id: RequestId;
  method: PluginShareListRequestMethod;
  params: PluginShareListParams;
}
export interface PluginShareListParams {}
export interface PluginShareCheckoutRequest {
  id: RequestId;
  method: PluginShareCheckoutRequestMethod;
  params: PluginShareCheckoutParams;
}
export interface PluginShareCheckoutParams {
  remotePluginId: string;
}
export interface PluginShareDeleteRequest {
  id: RequestId;
  method: PluginShareDeleteRequestMethod;
  params: PluginShareDeleteParams;
}
export interface PluginShareDeleteParams {
  remotePluginId: string;
}
export interface AppReadRequest {
  id: RequestId;
  method: AppReadRequestMethod;
  params: AppsReadParams;
}
/**
 * EXPERIMENTAL - read metadata for specific apps/connectors.
 */
export interface AppsReadParams {
  /**
   * App ids to read. The server accepts at most 100 ids and deduplicates repeated ids while preserving their first-request order.
   */
  appIds: string[];
  /**
   * When true, include display-only public tool summaries in the returned metadata.
   */
  includeTools?: boolean;
  /**
   * Optional loaded thread id used to evaluate effective app configuration.
   */
  threadId?: string | null;
}
export interface AppListRequest {
  id: RequestId;
  method: AppListRequestMethod;
  params: AppsListParams;
}
/**
 * EXPERIMENTAL - list available apps/connectors.
 */
export interface AppsListParams {
  /**
   * Opaque pagination cursor returned by a previous call.
   */
  cursor?: string | null;
  /**
   * When true, bypass app caches and fetch the latest data from sources.
   */
  forceRefetch?: boolean;
  /**
   * Optional page size; defaults to a reasonable server-side value.
   */
  limit?: number | null;
  /**
   * Optional thread id used to evaluate app feature gating from that thread's config.
   */
  threadId?: string | null;
}
export interface AppInstalledRequest {
  id: RequestId;
  method: AppInstalledRequestMethod;
  params: AppsInstalledParams;
}
/**
 * Read the committed installed connector runtime snapshot.
 */
export interface AppsInstalledParams {
  /**
   * When true and Apps are permitted, refresh and publish the hosted connector runtime tool snapshot first.
   */
  forceRefresh?: boolean;
  /**
   * Optional loaded thread id used to evaluate effective app configuration.
   */
  threadId?: string | null;
}
export interface FsReadFileRequest {
  id: RequestId;
  method: FsReadFileRequestMethod;
  params: FsReadFileParams;
}
/**
 * Read a file from the host filesystem.
 */
export interface FsReadFileParams {
  /**
   * Absolute path to read.
   */
  path: AbsolutePathBuf;
}
export interface FsWriteFileRequest {
  id: RequestId;
  method: FsWriteFileRequestMethod;
  params: FsWriteFileParams;
}
/**
 * Write a file on the host filesystem.
 */
export interface FsWriteFileParams {
  /**
   * File contents encoded as base64.
   */
  dataBase64: string;
  /**
   * Absolute path to write.
   */
  path: AbsolutePathBuf;
}
export interface FsCreateDirectoryRequest {
  id: RequestId;
  method: FsCreateDirectoryRequestMethod;
  params: FsCreateDirectoryParams;
}
/**
 * Create a directory on the host filesystem.
 */
export interface FsCreateDirectoryParams {
  /**
   * Absolute directory path to create.
   */
  path: AbsolutePathBuf;
  /**
   * Whether parent directories should also be created. Defaults to `true`.
   */
  recursive?: boolean | null;
}
export interface FsGetMetadataRequest {
  id: RequestId;
  method: FsGetMetadataRequestMethod;
  params: FsGetMetadataParams;
}
/**
 * Request metadata for an absolute path.
 */
export interface FsGetMetadataParams {
  /**
   * Absolute path to inspect.
   */
  path: AbsolutePathBuf;
}
export interface FsReadDirectoryRequest {
  id: RequestId;
  method: FsReadDirectoryRequestMethod;
  params: FsReadDirectoryParams;
}
/**
 * List direct child names for a directory.
 */
export interface FsReadDirectoryParams {
  /**
   * Absolute directory path to read.
   */
  path: AbsolutePathBuf;
}
export interface FsRemoveRequest {
  id: RequestId;
  method: FsRemoveRequestMethod;
  params: FsRemoveParams;
}
/**
 * Remove a file or directory tree from the host filesystem.
 */
export interface FsRemoveParams {
  /**
   * Whether missing paths should be ignored. Defaults to `true`.
   */
  force?: boolean | null;
  /**
   * Absolute path to remove.
   */
  path: AbsolutePathBuf;
  /**
   * Whether directory removal should recurse. Defaults to `true`.
   */
  recursive?: boolean | null;
}
export interface FsCopyRequest {
  id: RequestId;
  method: FsCopyRequestMethod;
  params: FsCopyParams;
}
/**
 * Copy a file or directory tree on the host filesystem.
 */
export interface FsCopyParams {
  /**
   * Absolute destination path.
   */
  destinationPath: AbsolutePathBuf;
  /**
   * Required for directory copies; ignored for file copies.
   */
  recursive?: boolean;
  /**
   * Absolute source path.
   */
  sourcePath: AbsolutePathBuf;
}
export interface FsWatchRequest {
  id: RequestId;
  method: FsWatchRequestMethod;
  params: FsWatchParams;
}
/**
 * Start filesystem watch notifications for an absolute path.
 */
export interface FsWatchParams {
  /**
   * Absolute file or directory path to watch.
   */
  path: AbsolutePathBuf;
  /**
   * Connection-scoped watch identifier used for `fs/unwatch` and `fs/changed`.
   */
  watchId: string;
}
export interface FsUnwatchRequest {
  id: RequestId;
  method: FsUnwatchRequestMethod;
  params: FsUnwatchParams;
}
/**
 * Stop filesystem watch notifications for a prior `fs/watch`.
 */
export interface FsUnwatchParams {
  /**
   * Watch identifier previously provided to `fs/watch`.
   */
  watchId: string;
}
export interface SkillsConfigWriteRequest {
  id: RequestId;
  method: SkillsConfigWriteRequestMethod;
  params: SkillsConfigWriteParams;
}
export interface SkillsConfigWriteParams {
  enabled: boolean;
  /**
   * Name-based selector.
   */
  name?: string | null;
  /**
   * Path-based selector.
   */
  path?: AbsolutePathBuf | null;
}
export interface PluginInstallRequest {
  id: RequestId;
  method: PluginInstallRequestMethod;
  params: PluginInstallParams;
}
export interface PluginInstallParams {
  /**
   * Client-generated identifier used to correlate one installation attempt.
   */
  installAttemptId?: string | null;
  marketplacePath?: AbsolutePathBuf | null;
  pluginName: string;
  remoteMarketplaceName?: string | null;
}
export interface PluginUninstallRequest {
  id: RequestId;
  method: PluginUninstallRequestMethod;
  params: PluginUninstallParams;
}
export interface PluginUninstallParams {
  pluginId: string;
}
export interface TurnStartRequest {
  id: RequestId;
  method: TurnStartRequestMethod;
  params: TurnStartParams;
}
export interface TurnStartParams {
  /**
   * Override the approval policy for this turn and subsequent turns.
   */
  approvalPolicy?: AskForApproval | null;
  /**
   * Override where approval requests are routed for review on this turn and subsequent turns.
   */
  approvalsReviewer?: ApprovalsReviewer | null;
  clientUserMessageId?: string | null;
  /**
   * Override the working directory for this turn and subsequent turns.
   */
  cwd?: string | null;
  /**
   * Replace this thread's disabled plugin IDs. Omitted/null preserves the list; [] clears it.
   */
  disabledPluginIds?: string[] | null;
  /**
   * Override the reasoning effort for this turn and subsequent turns.
   */
  effort?: ReasoningEffort | null;
  input: UserInput[];
  /**
   * Override the model for this turn and subsequent turns.
   */
  model?: string | null;
  /**
   * Optional JSON Schema used to constrain the final assistant message for this turn.
   */
  outputSchema?: {
    [k: string]: unknown;
  };
  /**
   * ID of the turn that caused this new turn to start.
   *
   * Set this when starting work on behalf of another turn, such as delegated work in a different thread. Leave unset for work started directly by the user. Ignored when this request adds input to an active turn.
   */
  parentTurnId?: string | null;
  /**
   * @deprecated `friendly` and `pragmatic` no longer select a style. Changing this does not rewrite the thread's existing instructions.
   */
  personality?: Personality | null;
  /**
   * ID of the first turn in the chain of work that led to this new turn.
   *
   * When setting `parentTurnId`, set this to the parent turn's `rootTurnId` when known. This keeps descendant work attributed to the original turn. If omitted, the new turn becomes its own root. Ignored when this request adds input to an active turn.
   */
  rootTurnId?: string | null;
  /**
   * Override the sandbox policy for this turn and subsequent turns.
   */
  sandboxPolicy?: SandboxPolicy | null;
  /**
   * Override the service tier for this turn and subsequent turns.
   */
  serviceTier?: string | null;
  /**
   * Override the service tier only when this request starts a new turn. Use "default" for standard speed. Omitted or null inherits the thread's tier. Does not change the thread's tier or a turn being steered.
   */
  serviceTierForTurn?: string | null;
  /**
   * Override the reasoning summary for this turn and subsequent turns.
   */
  summary?: ReasoningSummary | null;
  threadId: string;
  toolOutput?: TurnToolOutput | null;
  /**
   * Optional source classification for the caller that starts this turn. Ignored when this request steers an already-active turn.
   */
  turnTrigger?: string | null;
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
export interface TurnToolOutput {
  name: string;
  namespace?: string | null;
  output: FunctionCallOutputBody;
  /**
   * Requests retention of this output in the thread's model history.
   */
  retain?: boolean;
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
export interface TurnSteerRequest {
  id: RequestId;
  method: TurnSteerRequestMethod;
  params: TurnSteerParams;
}
export interface TurnSteerParams {
  clientUserMessageId?: string | null;
  /**
   * Required active turn id precondition. The request fails when it does not match the currently active turn.
   */
  expectedTurnId: string;
  input: UserInput[];
  threadId: string;
}
export interface TurnInterruptRequest {
  id: RequestId;
  method: TurnInterruptRequestMethod;
  params: TurnInterruptParams;
}
export interface TurnInterruptParams {
  threadId: string;
  turnId: string;
}
export interface ReviewStartRequest {
  id: RequestId;
  method: ReviewStartRequestMethod;
  params: ReviewStartParams;
}
export interface ReviewStartParams {
  /**
   * Reviews run inline on the supplied thread. Omit this field or pass `inline`. To review on a separate thread, start a thread first and use its id.
   */
  delivery?: ReviewDelivery | null;
  target: ReviewTarget;
  threadId: string;
}
/**
 * Review the working tree: staged, unstaged, and untracked files.
 */
export interface UncommittedChangesReviewTarget {
  type: UncommittedChangesReviewTargetType;
}
/**
 * Review changes between the current branch and the given base branch.
 */
export interface BaseBranchReviewTarget {
  branch: string;
  type: BaseBranchReviewTargetType;
}
/**
 * Review the changes introduced by a specific commit.
 */
export interface CommitReviewTarget {
  sha: string;
  /**
   * Optional human-readable label (e.g., commit subject) for UIs.
   */
  title?: string | null;
  type: CommitReviewTargetType;
}
/**
 * Arbitrary instructions, equivalent to the old free-form prompt.
 */
export interface CustomReviewTarget {
  instructions: string;
  type: CustomReviewTargetType;
}
export interface ModelListRequest {
  id: RequestId;
  method: ModelListRequestMethod;
  params: ModelListParams;
}
export interface ModelListParams {
  /**
   * Opaque pagination cursor returned by a previous call.
   */
  cursor?: string | null;
  /**
   * When true, include models that are hidden from the default picker list.
   */
  includeHidden?: boolean | null;
  /**
   * Optional page size; defaults to a reasonable server-side value.
   */
  limit?: number | null;
}
export interface AccountGatewayOAuthReadRequest {
  id: RequestId;
  method: AccountGatewayOAuthReadRequestMethod;
  params?: null;
}
export interface AccountGatewayOAuthLoginRequest {
  id: RequestId;
  method: AccountGatewayOAuthLoginRequestMethod;
  params?: null;
}
export interface AccountGatewayOAuthCancelRequest {
  id: RequestId;
  method: AccountGatewayOAuthCancelRequestMethod;
  params?: null;
}
export interface ModelProviderCapabilitiesReadRequest {
  id: RequestId;
  method: ModelProviderCapabilitiesReadRequestMethod;
  params: ModelProviderCapabilitiesReadParams;
}
export interface ModelProviderCapabilitiesReadParams {}
export interface ExperimentalFeatureListRequest {
  id: RequestId;
  method: ExperimentalFeatureListRequestMethod;
  params: ExperimentalFeatureListParams;
}
export interface ExperimentalFeatureListParams {
  /**
   * Opaque pagination cursor returned by a previous call.
   */
  cursor?: string | null;
  /**
   * Optional page size; defaults to a reasonable server-side value.
   */
  limit?: number | null;
  /**
   * Optional loaded thread id. Pass this when showing feature state for an existing thread so enablement is computed from that thread's refreshed config, including project-local config for the thread's cwd.
   */
  threadId?: string | null;
}
export interface PermissionProfileListRequest {
  id: RequestId;
  method: PermissionProfileListRequestMethod;
  params: PermissionProfileListParams;
}
export interface PermissionProfileListParams {
  /**
   * Opaque pagination cursor returned by a previous call.
   */
  cursor?: string | null;
  /**
   * Optional working directory to resolve project config layers.
   */
  cwd?: string | null;
  /**
   * Optional page size; defaults to the full result set.
   */
  limit?: number | null;
}
export interface ExperimentalFeatureEnablementSetRequest {
  id: RequestId;
  method: ExperimentalFeatureEnablementSetRequestMethod;
  params: ExperimentalFeatureEnablementSetParams;
}
export interface ExperimentalFeatureEnablementSetParams {
  /**
   * Process-wide runtime feature enablement keyed by canonical feature name.
   *
   * Only named features are updated. Omitted features are left unchanged. Send an empty map for a no-op.
   */
  enablement: {
    [k: string]: boolean;
  };
}
export interface McpServerOauthLoginRequest {
  id: RequestId;
  method: McpServerOauthLoginRequestMethod;
  params: McpServerOauthLoginParams;
}
export interface McpServerOauthLoginParams {
  /**
   * Registration strategy for this login only; omission selects automatic discovery.
   */
  clientRegistration?: McpServerOauthClientRegistration | null;
  name: string;
  scopes?: string[] | null;
  threadId?: string | null;
  timeoutSecs?: number | null;
}
export interface ConfigMcpServerReloadRequest {
  id: RequestId;
  method: ConfigMcpServerReloadRequestMethod;
  params?: null;
}
export interface McpServerStatusListRequest {
  id: RequestId;
  method: McpServerStatusListRequestMethod;
  params: ListMcpServerStatusParams;
}
export interface ListMcpServerStatusParams {
  /**
   * Opaque pagination cursor returned by a previous call.
   */
  cursor?: string | null;
  /**
   * Controls how much MCP inventory data to fetch for each server. Defaults to `Full` when omitted.
   */
  detail?: McpServerStatusDetail | null;
  /**
   * Optional page size; defaults to a server-defined value.
   */
  limit?: number | null;
  /**
   * Limit discovery to one server. With a thread ID, reuse that thread's MCP connection.
   */
  serverName?: string | null;
  threadId?: string | null;
}
export interface McpServerResourceReadRequest {
  id: RequestId;
  method: McpServerResourceReadRequestMethod;
  params: McpResourceReadParams;
}
export interface McpResourceReadParams {
  connectorId?: string | null;
  /**
   * Originating MCP tool call used to select the resource's app.
   */
  originCallId?: string | null;
  server: string;
  /**
   * Explicit hosted app/account. Omit to retain legacy resource discovery.
   */
  target?: McpResourceReadTarget | null;
  threadId?: string | null;
  uri: string;
}
export interface McpResourceReadTarget {
  connectorId: string;
  /**
   * Null explicitly requests no-auth access, subject to the app's resource policy.
   */
  linkId: string | null;
}
export interface McpServerToolCallRequest {
  id: RequestId;
  method: McpServerToolCallRequestMethod;
  params: McpServerToolCallParams;
}
export interface McpServerToolCallParams {
  _meta?: unknown;
  arguments?: unknown;
  server: string;
  threadId: string;
  tool: string;
}
export interface WindowsSandboxSetupStartRequest {
  id: RequestId;
  method: WindowsSandboxSetupStartRequestMethod;
  params: WindowsSandboxSetupStartParams;
}
export interface WindowsSandboxSetupStartParams {
  cwd?: AbsolutePathBuf | null;
  mode: WindowsSandboxSetupMode;
}
export interface WindowsSandboxReadinessRequest {
  id: RequestId;
  method: WindowsSandboxReadinessRequestMethod;
  params?: null;
}
export interface AccountLoginStartRequest {
  id: RequestId;
  method: AccountLoginStartRequestMethod;
  params: LoginAccountParams;
}
export interface ApiKeyLoginAccountParams {
  apiKey: string;
  type: ApiKeyLoginAccountParamsType;
}
export interface ChatgptLoginAccountParams {
  appBrand?: LoginAppBrand | null;
  codexStreamlinedLogin?: boolean;
  type: ChatgptLoginAccountParamsType;
  useHostedLoginSuccessPage?: boolean;
}
export interface ChatgptDeviceCodeLoginAccountParams {
  type: ChatgptDeviceCodeLoginAccountParamsType;
}
/**
 * [UNSTABLE] FOR OPENAI INTERNAL USE ONLY - DO NOT USE. The access token must contain the same scopes that Codex-managed ChatGPT auth tokens have.
 */
export interface ChatgptAuthTokensLoginAccountParams {
  /**
   * Access token (JWT) supplied by the client. This token is used for backend API requests and email extraction.
   */
  accessToken: string;
  /**
   * Workspace/account identifier supplied by the client.
   */
  chatgptAccountId: string;
  /**
   * Optional plan type supplied by the client.
   *
   * When `null`, Codex attempts to derive the plan type from access-token claims. If unavailable, the plan defaults to `unknown`.
   */
  chatgptPlanType?: string | null;
  type: ChatgptAuthTokensLoginAccountParamsType;
}
/**
 * [UNSTABLE] Managed Amazon Bedrock login is experimental.
 */
export interface AmazonBedrockLoginAccountParams {
  apiKey: string;
  region: string;
  type: AmazonBedrockLoginAccountParamsType;
}
/**
 * [UNSTABLE] Managed Amazon Bedrock AWS access key login is experimental.
 */
export interface AmazonBedrockAccessKeysLoginAccountParams {
  accessKeyId: string;
  region: string;
  secretAccessKey: string;
  sessionToken?: string | null;
  type: AmazonBedrockAccessKeysLoginAccountParamsType;
}
export interface AccountLoginCancelRequest {
  id: RequestId;
  method: AccountLoginCancelRequestMethod;
  params: CancelLoginAccountParams;
}
export interface CancelLoginAccountParams {
  loginId: string;
}
export interface AccountLogoutRequest {
  id: RequestId;
  method: AccountLogoutRequestMethod;
  params?: null;
}
export interface AccountRateLimitsReadRequest {
  id: RequestId;
  method: AccountRateLimitsReadRequestMethod;
  params?: GetAccountRateLimitsParams | null;
}
/**
 * Usage-read capabilities of the requesting client, never inferred from its experiment arm.
 */
export interface GetAccountRateLimitsParams {
  /**
   * Skip the separate reset-credit detail lookup for background usage polls. The usage response still includes the available count; omitted/false preserves detailed reads.
   */
  excludeResetCreditDetails?: boolean;
  /**
   * The client supports automatic Luna Reserve fallback. For eligible ChatGPT CLI users, allow the backend to record experiment exposure after ordinary usage is blocked.
   */
  supportsLunaReserve?: boolean;
}
export interface AccountRateLimitResetCreditConsumeRequest {
  id: RequestId;
  method: AccountRateLimitResetCreditConsumeRequestMethod;
  params: ConsumeAccountRateLimitResetCreditParams;
}
export interface ConsumeAccountRateLimitResetCreditParams {
  /**
   * Opaque reset-credit identifier to redeem. When omitted, the backend selects the next available credit.
   */
  creditId?: string | null;
  /**
   * Identifies one logical reset attempt. A UUID is recommended; reuse the same value when retrying that attempt.
   */
  idempotencyKey: string;
}
export interface AccountUsageReadRequest {
  id: RequestId;
  method: AccountUsageReadRequestMethod;
  params?: GetAccountTokenUsageParams | null;
}
export interface GetAccountTokenUsageParams {
  /**
   * When present, read estimated usage for this thread instead of account-wide token activity.
   */
  threadId?: string | null;
}
export interface AccountWorkspaceMessagesReadRequest {
  id: RequestId;
  method: AccountWorkspaceMessagesReadRequestMethod;
  params?: null;
}
export interface AccountSendAddCreditsNudgeEmailRequest {
  id: RequestId;
  method: AccountSendAddCreditsNudgeEmailRequestMethod;
  params: SendAddCreditsNudgeEmailParams;
}
export interface SendAddCreditsNudgeEmailParams {
  creditType: AddCreditsNudgeCreditType;
}
export interface FeedbackUploadRequest {
  id: RequestId;
  method: FeedbackUploadRequestMethod;
  params: FeedbackUploadParams;
}
export interface FeedbackUploadParams {
  classification: string;
  extraLogFiles?: string[] | null;
  includeLogs?: boolean;
  reason?: string | null;
  tags?: {
    [k: string]: string;
  } | null;
  threadId?: string | null;
}
export interface FeedbackSaveRequest {
  id: RequestId;
  method: FeedbackSaveRequestMethod;
  params: FeedbackSaveParams;
}
export interface FeedbackSaveParams {
  classification: string;
  extraLogFiles?: string[] | null;
  includeLogs?: boolean;
  reason?: string | null;
  /**
   * Absolute, previously unused ZIP path on the app-server host. The caller owns this file, including after a disconnected RPC.
   */
  savePath: LegacyAppPathString;
  tags?: {
    [k: string]: string;
  } | null;
  threadId?: string | null;
}
/**
 * Execute a standalone command (argv vector) under the server's sandbox.
 */
export interface CommandExecRequest {
  id: RequestId;
  method: CommandExecRequestMethod;
  params: CommandExecParams;
}
/**
 * Run a standalone command (argv vector) in the server sandbox without creating a thread or turn.
 *
 * The final `command/exec` response is deferred until the process exits and is sent only after all `command/exec/outputDelta` notifications for that connection have been emitted.
 */
export interface CommandExecParams {
  /**
   * Command argv vector. Empty arrays are rejected.
   */
  command: string[];
  /**
   * Optional working directory. Defaults to the server cwd.
   */
  cwd?: string | null;
  /**
   * Disable stdout/stderr capture truncation for this request.
   *
   * Cannot be combined with `outputBytesCap`.
   */
  disableOutputCap?: boolean;
  /**
   * Disable the timeout entirely for this request.
   *
   * Cannot be combined with `timeoutMs`.
   */
  disableTimeout?: boolean;
  /**
   * Optional environment overrides merged into the server-computed environment.
   *
   * Matching names override inherited values. Set a key to `null` to unset an inherited variable.
   */
  env?: {
    [k: string]: string | null;
  } | null;
  /**
   * Optional per-stream stdout/stderr capture cap in bytes.
   *
   * When omitted, the server default applies. Cannot be combined with `disableOutputCap`.
   */
  outputBytesCap?: number | null;
  /**
   * Optional client-supplied, connection-scoped process id.
   *
   * Required for `tty`, `streamStdin`, `streamStdoutStderr`, and follow-up `command/exec/write`, `command/exec/resize`, and `command/exec/terminate` calls. When omitted, buffered execution gets an internal id that is not exposed to the client.
   */
  processId?: string | null;
  /**
   * Optional sandbox policy for this command.
   *
   * Uses the same shape as thread/turn execution sandbox configuration and defaults to the user's configured policy when omitted. Cannot be combined with `permissionProfile`.
   */
  sandboxPolicy?: SandboxPolicy | null;
  /**
   * Optional initial PTY size in character cells. Only valid when `tty` is true.
   */
  size?: CommandExecTerminalSize | null;
  /**
   * Allow follow-up `command/exec/write` requests to write stdin bytes.
   *
   * Requires a client-supplied `processId`.
   */
  streamStdin?: boolean;
  /**
   * Stream stdout/stderr via `command/exec/outputDelta` notifications.
   *
   * Streamed bytes are not duplicated into the final response and require a client-supplied `processId`.
   */
  streamStdoutStderr?: boolean;
  /**
   * Optional timeout in milliseconds.
   *
   * When omitted, the server default applies. Cannot be combined with `disableTimeout`.
   */
  timeoutMs?: number | null;
  /**
   * Enable PTY mode.
   *
   * This implies `streamStdin` and `streamStdoutStderr`.
   */
  tty?: boolean;
}
/**
 * PTY size in character cells for `command/exec` PTY sessions.
 */
export interface CommandExecTerminalSize {
  /**
   * Terminal width in character cells.
   */
  cols: number;
  /**
   * Terminal height in character cells.
   */
  rows: number;
}
/**
 * Write stdin bytes to a running `command/exec` session or close stdin.
 */
export interface CommandExecWriteRequest {
  id: RequestId;
  method: CommandExecWriteRequestMethod;
  params: CommandExecWriteParams;
}
/**
 * Write stdin bytes to a running `command/exec` session, close stdin, or both.
 */
export interface CommandExecWriteParams {
  /**
   * Close stdin after writing `deltaBase64`, if present.
   */
  closeStdin?: boolean;
  /**
   * Optional base64-encoded stdin bytes to write.
   */
  deltaBase64?: string | null;
  /**
   * Client-supplied, connection-scoped `processId` from the original `command/exec` request.
   */
  processId: string;
}
/**
 * Terminate a running `command/exec` session by client-supplied `processId`.
 */
export interface CommandExecTerminateRequest {
  id: RequestId;
  method: CommandExecTerminateRequestMethod;
  params: CommandExecTerminateParams;
}
/**
 * Terminate a running `command/exec` session.
 */
export interface CommandExecTerminateParams {
  /**
   * Client-supplied, connection-scoped `processId` from the original `command/exec` request.
   */
  processId: string;
}
/**
 * Resize a running PTY-backed `command/exec` session by client-supplied `processId`.
 */
export interface CommandExecResizeRequest {
  id: RequestId;
  method: CommandExecResizeRequestMethod;
  params: CommandExecResizeParams;
}
/**
 * Resize a running PTY-backed `command/exec` session.
 */
export interface CommandExecResizeParams {
  /**
   * Client-supplied, connection-scoped `processId` from the original `command/exec` request.
   */
  processId: string;
  /**
   * New PTY size in character cells.
   */
  size: CommandExecTerminalSize;
}
export interface ConfigReadRequest {
  id: RequestId;
  method: ConfigReadRequestMethod;
  params: ConfigReadParams;
}
export interface ConfigReadParams {
  /**
   * Optional working directory to resolve project config layers. If specified, return the effective config as seen from that directory (i.e., including any project layers between `cwd` and the project/repo root).
   */
  cwd?: string | null;
  includeLayers?: boolean;
}
export interface ExternalAgentConfigDetectRequest {
  id: RequestId;
  method: ExternalAgentConfigDetectRequestMethod;
  params: ExternalAgentConfigDetectParams;
}
export interface ExternalAgentConfigDetectParams {
  /**
   * Zero or more working directories to include for repo-scoped detection.
   */
  cwds?: string[] | null;
  /**
   * If true, include detection under the user's home directory.
   */
  includeHome?: boolean;
  /**
   * Maximum age in days for detected sessions. Missing values use the default limit.
   */
  maxSessionAgeDays?: number | null;
  /**
   * Maximum number of sessions to detect. Missing values use the default limit.
   */
  maxSessions?: number | null;
  /**
   * Optional migration-source selector. Missing or unrecognized values use the default source.
   */
  migrationSource?: string | null;
  /**
   * Deprecated field retained for compatibility. This field is ignored; use `migrationSource` to select the migration source.
   */
  source?: string | null;
}
export interface ExternalAgentConfigImportRequest {
  id: RequestId;
  method: ExternalAgentConfigImportRequestMethod;
  params: ExternalAgentConfigImportParams;
}
export interface ExternalAgentConfigImportParams {
  migrationItems: ExternalAgentConfigMigrationItem[];
  /**
   * Migration-source selector used to produce the migration items. Pass the same value to detection and import; missing or unrecognized values use the default source.
   */
  migrationSource?: string | null;
  /**
   * Opaque provider identifier supplied by the caller for analytics attribution and import history display. This does not select the migration source.
   */
  providerId?: string | null;
  /**
   * Optional identifier for the product that initiated the import.
   */
  source?: string | null;
}
export interface ExternalAgentConfigMigrationItem {
  /**
   * Null or empty means home-scoped migration; non-empty means repo-scoped migration.
   */
  cwd?: string | null;
  description: string;
  details?: MigrationDetails | null;
  itemType: ExternalAgentConfigMigrationItemType;
}
export interface MigrationDetails {
  commands?: CommandMigration[];
  hooks?: HookMigration[];
  mcpServers?: McpServerMigration[];
  memory?: string[];
  plugins?: PluginsMigration[];
  sessions?: SessionMigration[];
  skills?: SkillMigration[];
  subagents?: SubagentMigration[];
}
export interface CommandMigration {
  name: string;
}
export interface HookMigration {
  name: string;
}
export interface McpServerMigration {
  name: string;
}
export interface PluginsMigration {
  marketplaceName: string;
  pluginNames: string[];
}
export interface SessionMigration {
  cwd: string;
  path: string;
  title?: string | null;
}
export interface SkillMigration {
  name: string;
}
export interface SubagentMigration {
  name: string;
}
export interface ExternalAgentConfigImportRecordHistoryRequest {
  id: RequestId;
  method: ExternalAgentConfigImportRecordHistoryRequestMethod;
  params: ExternalAgentConfigImportHistoryRecordParams;
}
export interface ExternalAgentConfigImportHistoryRecordParams {
  /**
   * Completed results grouped by imported item type.
   */
  itemTypeResults: ExternalAgentConfigImportHistoryRecordTypeResultParams[];
  /**
   * Opaque provider identifier for the externally completed import.
   */
  providerId: string;
}
export interface ExternalAgentConfigImportHistoryRecordTypeResultParams {
  failures: ExternalAgentConfigImportItemTypeFailure[];
  itemType: ExternalAgentConfigMigrationItemType;
  successes: ExternalAgentConfigImportHistoryRecordSuccessParams[];
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
export interface ExternalAgentConfigImportHistoryRecordSuccessParams {
  cwd?: string | null;
  itemType: ExternalAgentConfigMigrationItemType;
  source?: string | null;
  target?: string | null;
  /**
   * Original title for an imported session, when available.
   */
  title?: string | null;
}
export interface ExternalAgentConfigImportReadHistoriesRequest {
  id: RequestId;
  method: ExternalAgentConfigImportReadHistoriesRequestMethod;
  params?: null;
}
export interface ConfigValueWriteRequest {
  id: RequestId;
  method: ConfigValueWriteRequestMethod;
  params: ConfigValueWriteParams;
}
export interface ConfigValueWriteParams {
  expectedVersion?: string | null;
  /**
   * Path to the config file to write; defaults to the user's `config.toml` when omitted.
   */
  filePath?: string | null;
  keyPath: string;
  mergeStrategy: MergeStrategy;
  value: unknown;
}
export interface ConfigBatchWriteRequest {
  id: RequestId;
  method: ConfigBatchWriteRequestMethod;
  params: ConfigBatchWriteParams;
}
export interface ConfigBatchWriteParams {
  edits: ConfigEdit[];
  expectedVersion?: string | null;
  /**
   * Path to the config file to write; defaults to the user's `config.toml` when omitted.
   */
  filePath?: string | null;
  /**
   * When true, hot-reload updated runtime settings into loaded threads after writing. Session-static model, reasoning-effort, Plan-mode reasoning-effort, and service-tier defaults are not reloaded. The deprecated personality setting is also not reloaded.
   */
  reloadUserConfig?: boolean;
}
export interface ConfigEdit {
  keyPath: string;
  mergeStrategy: MergeStrategy;
  value: unknown;
}
export interface ConfigRequirementsReadRequest {
  id: RequestId;
  method: ConfigRequirementsReadRequestMethod;
  params?: null;
}
export interface AccountReadRequest {
  id: RequestId;
  method: AccountReadRequestMethod;
  params: GetAccountParams;
}
export interface GetAccountParams {
  /**
   * When `true`, requests a proactive token refresh before returning.
   *
   * In managed auth mode this triggers the normal refresh-token flow. In external auth mode this flag is ignored. Clients should refresh tokens themselves and call `account/login/start` with `chatgptAuthTokens`.
   */
  refreshToken?: boolean;
}
export interface FuzzyFileSearchRequest {
  id: RequestId;
  method: FuzzyFileSearchRequestMethod;
  params: FuzzyFileSearchParams;
}
export interface FuzzyFileSearchParams {
  cancellationToken?: string | null;
  query: string;
  roots: string[];
}
