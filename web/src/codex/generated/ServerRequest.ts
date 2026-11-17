/**
 * 本文件由 scripts/codex-schema.mjs 自动生成，请勿手改。
 * 来源：codex-cli 0.167.0 `app-server generate-json-schema`。
 * 重新生成：`pnpm codex:schema`；漂移校验：`pnpm codex:schema:check`。
 */

/**
 * Request initiated from the server and sent to the client.
 */
export type ServerRequest =
  | ItemCommandExecutionRequestApprovalRequest
  | ItemFileChangeRequestApprovalRequest
  | ItemToolRequestUserInputRequest
  | McpServerElicitationRequestRequest
  | ItemPermissionsRequestApprovalRequest
  | ItemToolCallRequest
  | AccountChatgptAuthTokensRefreshRequest
  | AttestationGenerateRequest
  | ApplyPatchApprovalRequest
  | ExecCommandApprovalRequest;
export type RequestId = string | number;
export type ItemCommandExecutionRequestApprovalRequestMethod = "item/commandExecution/requestApproval";
export type CommandAction = ReadCommandAction | ListFilesCommandAction | SearchCommandAction | UnknownCommandAction;
export type LegacyAppPathString = string;
export type ReadCommandActionType = "read";
export type ListFilesCommandActionType = "listFiles";
export type SearchCommandActionType = "search";
export type UnknownCommandActionType = "unknown";
/**
 * Distinguishes a command approval from input sent to an existing terminal.
 */
export type CommandExecutionApprovalKind = ("command" | "writeStdin") | "humanCommand";
export type NetworkApprovalProtocol = "http" | "https" | "socks5Tcp" | "socks5Udp";
export type NetworkPolicyRuleAction = "allow" | "deny";
export type ItemFileChangeRequestApprovalRequestMethod = "item/fileChange/requestApproval";
export type ItemToolRequestUserInputRequestMethod = "item/tool/requestUserInput";
export type McpServerElicitationRequestRequestMethod = "mcpServer/elicitation/request";
export type McpServerElicitationRequestParams = {
  serverName: string;
  threadId: string;
  /**
   * Active Codex turn when this elicitation was observed, if app-server could correlate one.
   *
   * This is nullable because MCP models elicitation as a standalone server-to-client request identified by the MCP server request id. It may be triggered during a turn, but turn context is app-server correlation rather than part of the protocol identity of the elicitation itself.
   */
  turnId?: string | null;
} & McpServerElicitationRequestParams1;
export type McpServerElicitationRequestParams1 =
  | {
      _meta?: unknown;
      message: string;
      mode: "form";
      requestedSchema: McpElicitationSchema;
    }
  | {
      _meta?: unknown;
      message: string;
      mode: "openai/form";
      requestedSchema: unknown;
    }
  | {
      _meta?: unknown;
      message: string;
      mode: "openaiForm";
      requestedSchema: unknown;
    }
  | {
      _meta?: unknown;
      elicitationId: string;
      message: string;
      mode: "url";
      url: string;
    };
export type McpElicitationPrimitiveSchema =
  McpElicitationEnumSchema | McpElicitationStringSchema | McpElicitationNumberSchema | McpElicitationBooleanSchema;
export type McpElicitationEnumSchema =
  McpElicitationSingleSelectEnumSchema | McpElicitationMultiSelectEnumSchema | McpElicitationLegacyTitledEnumSchema;
export type McpElicitationSingleSelectEnumSchema =
  McpElicitationUntitledSingleSelectEnumSchema | McpElicitationTitledSingleSelectEnumSchema;
export type McpElicitationStringType = "string";
export type McpElicitationMultiSelectEnumSchema =
  McpElicitationUntitledMultiSelectEnumSchema | McpElicitationTitledMultiSelectEnumSchema;
export type McpElicitationArrayType = "array";
export type McpElicitationStringFormat = "email" | "uri" | "date" | "date-time";
export type McpElicitationNumberType = "number" | "integer";
export type McpElicitationBooleanType = "boolean";
export type McpElicitationObjectType = "object";
export type ItemPermissionsRequestApprovalRequestMethod = "item/permissions/requestApproval";
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
export type ItemToolCallRequestMethod = "item/tool/call";
export type AccountChatgptAuthTokensRefreshRequestMethod = "account/chatgptAuthTokens/refresh";
export type ChatgptAuthTokensRefreshReason = "unauthorized";
export type AttestationGenerateRequestMethod = "attestation/generate";
export type ApplyPatchApprovalRequestMethod = "applyPatchApproval";
export type ThreadId = string;
export type FileChange = AddFileChange | DeleteFileChange | UpdateFileChange;
export type AddFileChangeType = "add";
export type DeleteFileChangeType = "delete";
export type UpdateFileChangeType = "update";
export type ExecCommandApprovalRequestMethod = "execCommandApproval";
export type ParsedCommand = ReadParsedCommand | ListFilesParsedCommand | SearchParsedCommand | UnknownParsedCommand;
export type ReadParsedCommandType = "read";
export type ListFilesParsedCommandType = "list_files";
export type SearchParsedCommandType = "search";
export type UnknownParsedCommandType = "unknown";

/**
 * NEW APIs Sent when approval is requested for a specific command execution. This request is used for Turns started via turn/start.
 */
export interface ItemCommandExecutionRequestApprovalRequest {
  id: RequestId;
  method: ItemCommandExecutionRequestApprovalRequestMethod;
  params: CommandExecutionRequestApprovalParams;
}
export interface CommandExecutionRequestApprovalParams {
  /**
   * Unique identifier for this specific approval callback.
   *
   * For regular shell/unified_exec approvals, this is null.
   *
   * For zsh-exec-bridge subcommand approvals, multiple callbacks can belong to one parent `itemId`, so `approvalId` is a distinct opaque callback id (a UUID) used to disambiguate routing. Stdin approvals also use a distinct callback id; inspect `kind` to distinguish them.
   */
  approvalId?: string | null;
  /**
   * The command to be executed.
   */
  command?: string | null;
  /**
   * Best-effort parsed command actions for friendly display.
   */
  commandActions?: CommandAction[] | null;
  /**
   * The command's working directory.
   */
  cwd?: LegacyAppPathString | null;
  /**
   * Environment in which the command will run.
   */
  environmentId?: string | null;
  itemId: string;
  /**
   * Kind of action under review. Defaults to `command` for older servers.
   */
  kind?: CommandExecutionApprovalKind & string;
  /**
   * Optional context for a managed-network approval prompt.
   */
  networkApprovalContext?: NetworkApprovalContext | null;
  /**
   * Optional proposed execpolicy amendment to allow similar commands without prompting.
   */
  proposedExecpolicyAmendment?: string[] | null;
  /**
   * Optional proposed network policy amendments (allow/deny host) for future requests.
   */
  proposedNetworkPolicyAmendments?: NetworkPolicyAmendment[] | null;
  /**
   * Optional explanatory reason (e.g. request for network access).
   */
  reason?: string | null;
  /**
   * Unix timestamp (in milliseconds) when this approval request started.
   */
  startedAtMs: number;
  threadId: string;
  turnId: string;
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
export interface NetworkApprovalContext {
  host: string;
  protocol: NetworkApprovalProtocol;
}
export interface NetworkPolicyAmendment {
  action: NetworkPolicyRuleAction;
  host: string;
}
/**
 * Sent when approval is requested for a specific file change. This request is used for Turns started via turn/start.
 */
export interface ItemFileChangeRequestApprovalRequest {
  id: RequestId;
  method: ItemFileChangeRequestApprovalRequestMethod;
  params: FileChangeRequestApprovalParams;
}
export interface FileChangeRequestApprovalParams {
  /**
   * [UNSTABLE] When set, the agent is asking the user to allow writes under this root for the remainder of the session (unclear if this is honored today).
   */
  grantRoot?: string | null;
  itemId: string;
  /**
   * Optional explanatory reason (e.g. request for extra write access).
   */
  reason?: string | null;
  /**
   * Unix timestamp (in milliseconds) when this approval request started.
   */
  startedAtMs: number;
  threadId: string;
  turnId: string;
}
/**
 * EXPERIMENTAL - Request input from the user for a tool call.
 */
export interface ItemToolRequestUserInputRequest {
  id: RequestId;
  method: ItemToolRequestUserInputRequestMethod;
  params: ToolRequestUserInputParams;
}
/**
 * EXPERIMENTAL. Params sent with a request_user_input event.
 */
export interface ToolRequestUserInputParams {
  /**
   * @deprecated Use `isBlocking` to decide whether the request should block.
   */
  autoResolutionMs?: number | null;
  isBlocking: boolean;
  itemId: string;
  questions: ToolRequestUserInputQuestion[];
  threadId: string;
  turnId: string;
}
/**
 * EXPERIMENTAL. Represents one request_user_input question and its required options.
 */
export interface ToolRequestUserInputQuestion {
  header: string;
  id: string;
  isOther?: boolean;
  isSecret?: boolean;
  options?: ToolRequestUserInputOption[] | null;
  question: string;
}
/**
 * EXPERIMENTAL. Defines a single selectable option for request_user_input.
 */
export interface ToolRequestUserInputOption {
  description: string;
  label: string;
}
/**
 * Request input for an MCP server elicitation.
 */
export interface McpServerElicitationRequestRequest {
  id: RequestId;
  method: McpServerElicitationRequestRequestMethod;
  params: McpServerElicitationRequestParams;
}
/**
 * Typed form schema for MCP `elicitation/create` requests.
 *
 * This matches the `requestedSchema` shape from the MCP 2025-11-25 `ElicitRequestFormParams` schema.
 */
export interface McpElicitationSchema {
  $schema?: string | null;
  properties: {
    [k: string]: McpElicitationPrimitiveSchema;
  };
  required?: string[] | null;
  type: McpElicitationObjectType;
}
export interface McpElicitationUntitledSingleSelectEnumSchema {
  default?: string | null;
  description?: string | null;
  enum: string[];
  title?: string | null;
  type: McpElicitationStringType;
}
export interface McpElicitationTitledSingleSelectEnumSchema {
  default?: string | null;
  description?: string | null;
  oneOf: McpElicitationConstOption[];
  title?: string | null;
  type: McpElicitationStringType;
}
export interface McpElicitationConstOption {
  const: string;
  title: string;
}
export interface McpElicitationUntitledMultiSelectEnumSchema {
  default?: string[] | null;
  description?: string | null;
  items: McpElicitationUntitledEnumItems;
  maxItems?: number | null;
  minItems?: number | null;
  title?: string | null;
  type: McpElicitationArrayType;
}
export interface McpElicitationUntitledEnumItems {
  enum: string[];
  type: McpElicitationStringType;
}
export interface McpElicitationTitledMultiSelectEnumSchema {
  default?: string[] | null;
  description?: string | null;
  items: McpElicitationTitledEnumItems;
  maxItems?: number | null;
  minItems?: number | null;
  title?: string | null;
  type: McpElicitationArrayType;
}
export interface McpElicitationTitledEnumItems {
  anyOf: McpElicitationConstOption[];
}
export interface McpElicitationLegacyTitledEnumSchema {
  default?: string | null;
  description?: string | null;
  enum: string[];
  enumNames?: string[] | null;
  title?: string | null;
  type: McpElicitationStringType;
}
export interface McpElicitationStringSchema {
  default?: string | null;
  description?: string | null;
  format?: McpElicitationStringFormat | null;
  maxLength?: number | null;
  minLength?: number | null;
  title?: string | null;
  type: McpElicitationStringType;
}
export interface McpElicitationNumberSchema {
  default?: number | null;
  description?: string | null;
  maximum?: number | null;
  minimum?: number | null;
  title?: string | null;
  type: McpElicitationNumberType;
}
export interface McpElicitationBooleanSchema {
  default?: boolean | null;
  description?: string | null;
  title?: string | null;
  type: McpElicitationBooleanType;
}
/**
 * Request approval for additional permissions from the user.
 */
export interface ItemPermissionsRequestApprovalRequest {
  id: RequestId;
  method: ItemPermissionsRequestApprovalRequestMethod;
  params: PermissionsRequestApprovalParams;
}
export interface PermissionsRequestApprovalParams {
  cwd: LegacyAppPathString;
  environmentId?: string | null;
  itemId: string;
  permissions: RequestPermissionProfile;
  reason?: string | null;
  /**
   * Unix timestamp (in milliseconds) when this approval request started.
   */
  startedAtMs: number;
  threadId: string;
  turnId: string;
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
 * Execute a dynamic tool call on the client.
 */
export interface ItemToolCallRequest {
  id: RequestId;
  method: ItemToolCallRequestMethod;
  params: DynamicToolCallParams;
}
export interface DynamicToolCallParams {
  arguments: unknown;
  callId: string;
  namespace?: string | null;
  threadId: string;
  tool: string;
  turnId: string;
}
export interface AccountChatgptAuthTokensRefreshRequest {
  id: RequestId;
  method: AccountChatgptAuthTokensRefreshRequestMethod;
  params: ChatgptAuthTokensRefreshParams;
}
export interface ChatgptAuthTokensRefreshParams {
  /**
   * Workspace/account identifier that Codex was previously using.
   *
   * Clients that manage multiple accounts/workspaces can use this as a hint to refresh the token for the correct workspace.
   *
   * This may be `null` when the prior auth state did not include a workspace identifier (`chatgpt_account_id`).
   */
  previousAccountId?: string | null;
  reason: ChatgptAuthTokensRefreshReason;
}
/**
 * Generate a fresh upstream attestation result on demand.
 */
export interface AttestationGenerateRequest {
  id: RequestId;
  method: AttestationGenerateRequestMethod;
  params: AttestationGenerateParams;
}
export interface AttestationGenerateParams {}
/**
 * DEPRECATED APIs below Request to approve a patch. This request is used for Turns started via the legacy APIs (i.e. SendUserTurn, SendUserMessage).
 */
export interface ApplyPatchApprovalRequest {
  id: RequestId;
  method: ApplyPatchApprovalRequestMethod;
  params: ApplyPatchApprovalParams;
}
export interface ApplyPatchApprovalParams {
  /**
   * Use to correlate this with [codex_protocol::protocol::PatchApplyBeginEvent] and [codex_protocol::protocol::PatchApplyEndEvent].
   */
  callId: string;
  conversationId: ThreadId;
  fileChanges: {
    [k: string]: FileChange;
  };
  /**
   * When set, the agent is asking the user to allow writes under this root for the remainder of the session (unclear if this is honored today).
   */
  grantRoot?: string | null;
  /**
   * Optional explanatory reason (e.g. request for extra write access).
   */
  reason?: string | null;
}
export interface AddFileChange {
  content: string;
  type: AddFileChangeType;
}
export interface DeleteFileChange {
  content: string;
  type: DeleteFileChangeType;
}
export interface UpdateFileChange {
  move_path?: string | null;
  type: UpdateFileChangeType;
  unified_diff: string;
}
/**
 * Request to exec a command. This request is used for Turns started via the legacy APIs (i.e. SendUserTurn, SendUserMessage).
 */
export interface ExecCommandApprovalRequest {
  id: RequestId;
  method: ExecCommandApprovalRequestMethod;
  params: ExecCommandApprovalParams;
}
export interface ExecCommandApprovalParams {
  /**
   * Identifier for this specific approval callback.
   */
  approvalId?: string | null;
  /**
   * Use to correlate this with [codex_protocol::protocol::ExecCommandBeginEvent] and [codex_protocol::protocol::ExecCommandEndEvent].
   */
  callId: string;
  command: string[];
  conversationId: ThreadId;
  cwd: string;
  parsedCmd: ParsedCommand[];
  reason?: string | null;
}
export interface ReadParsedCommand {
  cmd: string;
  name: string;
  /**
   * (Best effort) Path to the file being read by the command. When possible, this is an absolute path, though when relative, it should be resolved against the `cwd`` that will be used to run the command to derive the absolute path.
   */
  path: string;
  type: ReadParsedCommandType;
}
export interface ListFilesParsedCommand {
  cmd: string;
  path?: string | null;
  type: ListFilesParsedCommandType;
}
export interface SearchParsedCommand {
  cmd: string;
  path?: string | null;
  query?: string | null;
  type: SearchParsedCommandType;
}
export interface UnknownParsedCommand {
  cmd: string;
  type: UnknownParsedCommandType;
}
