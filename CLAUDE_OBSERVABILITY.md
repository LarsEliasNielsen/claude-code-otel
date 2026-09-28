# Monitoring

> How to enable and configure OpenTelemetry for Claude Code, and what it emits.

Claude Code supports OpenTelemetry (OTel) metrics, events and (beta) traces for monitoring and observability.

Metrics are time series exported via the OpenTelemetry metrics protocol. Events are exported via the OpenTelemetry logs protocol. You are responsible for configuring the metrics and logs backends and for choosing an aggregation granularity that fits your monitoring needs.

This reference follows the official [Claude Code monitoring documentation](https://code.claude.com/docs/en/monitoring-usage). Attribute names and event shapes were verified against live data from Claude Code 2.1.281 flowing through this stack. Where the live data differs from the official docs, this file describes the live data and says so.

<Note>
  OpenTelemetry support is in beta and details are subject to change.
</Note>

## Quick Start

```bash
# 1. Enable telemetry
export CLAUDE_CODE_ENABLE_TELEMETRY=1

# 2. Choose exporters (configure only what you need)
export OTEL_METRICS_EXPORTER=otlp       # Options: otlp, prometheus, console, none
export OTEL_LOGS_EXPORTER=otlp          # Options: otlp, console, none

# 3. Configure the OTLP endpoint
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# 4. Set authentication (if required)
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer your-token"

# 5. For debugging: shorter export intervals
export OTEL_METRIC_EXPORT_INTERVAL=10000  # 10 seconds (default: 60000ms)
export OTEL_LOGS_EXPORT_INTERVAL=5000     # 5 seconds (default: 5000ms)

# 6. Richer skill, MCP and tool data (see "Content logging gates")
export OTEL_LOG_TOOL_DETAILS=1

# 7. Run Claude Code
claude
```

<Note>
  The default export intervals are 60 seconds for metrics and 5 seconds for logs. Shorter intervals help during setup; reset them for production use.
</Note>

## Administrator Configuration

Administrators can set OpenTelemetry configuration for all users through the managed settings file. Environment variables defined there have high precedence and users cannot override them. See [settings precedence](https://code.claude.com/docs/en/settings#settings-precedence).

The managed settings file is located at:

* macOS: `/Library/Application Support/ClaudeCode/managed-settings.json`
* Linux and WSL: `/etc/claude-code/managed-settings.json`
* Windows: `C:\Program Files\ClaudeCode\managed-settings.json`

```json
{
  "env": {
    "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
    "OTEL_METRICS_EXPORTER": "otlp",
    "OTEL_LOGS_EXPORTER": "otlp",
    "OTEL_EXPORTER_OTLP_PROTOCOL": "grpc",
    "OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector.company.com:4317",
    "OTEL_EXPORTER_OTLP_HEADERS": "Authorization=Bearer company-token"
  }
}
```

Managed settings can be distributed via MDM or other device management tools.

## Configuration Details

### Core Configuration Variables

| Environment Variable                                | Description                                                   | Example Values                       |
| --------------------------------------------------- | ------------------------------------------------------------- | ------------------------------------ |
| `CLAUDE_CODE_ENABLE_TELEMETRY`                      | Enables telemetry collection (required)                       | `1`                                  |
| `OTEL_METRICS_EXPORTER`                             | Metrics exporter type(s), comma-separated                     | `console`, `otlp`, `prometheus`, `none` |
| `OTEL_LOGS_EXPORTER`                                | Logs/events exporter type(s), comma-separated                 | `console`, `otlp`, `none`            |
| `OTEL_EXPORTER_OTLP_PROTOCOL`                       | Protocol for the OTLP exporter (all signals)                  | `grpc`, `http/json`, `http/protobuf` |
| `OTEL_EXPORTER_OTLP_ENDPOINT`                       | OTLP collector endpoint (all signals)                         | `http://localhost:4317`              |
| `OTEL_EXPORTER_OTLP_METRICS_PROTOCOL`               | Protocol for metrics (overrides general)                      | `grpc`, `http/json`, `http/protobuf` |
| `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT`               | OTLP metrics endpoint (overrides general)                     | `http://localhost:4318/v1/metrics`   |
| `OTEL_EXPORTER_OTLP_LOGS_PROTOCOL`                  | Protocol for logs (overrides general)                         | `grpc`, `http/json`, `http/protobuf` |
| `OTEL_EXPORTER_OTLP_LOGS_ENDPOINT`                  | OTLP logs endpoint (overrides general)                        | `http://localhost:4318/v1/logs`      |
| `OTEL_EXPORTER_OTLP_HEADERS`                        | Authentication headers for OTLP                               | `Authorization=Bearer token`         |
| `OTEL_EXPORTER_OTLP_METRICS_HEADERS`                | Metrics headers, merged with the generic headers              | `Authorization=Bearer token`         |
| `OTEL_EXPORTER_OTLP_LOGS_HEADERS`                   | Logs headers, merged with the generic headers                 | `Authorization=Bearer token`         |
| `OTEL_METRIC_EXPORT_INTERVAL`                       | Metrics export interval in ms (default: 60000)                | `5000`, `60000`                      |
| `OTEL_LOGS_EXPORT_INTERVAL`                         | Logs export interval in ms (default: 5000)                    | `1000`, `10000`                      |
| `OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE` | Metrics temporality (default: `delta`)                        | `delta`, `cumulative`                |
| `OTEL_RESOURCE_ATTRIBUTES`                          | Custom attributes, comma-separated `key=value`, no spaces     | `department=eng,team.id=platform`    |
| `CLAUDE_CODE_OTEL_CONTENT_MAX_LENGTH`               | Max length of content-bearing attributes (default: 61440)     | `20000`                              |
| `CLAUDE_CODE_OTEL_HEADERS_HELPER_DEBOUNCE_MS`       | Refresh interval for dynamic headers (default: 29 minutes)    | `1740000`                            |

mTLS: for `grpc` use `OTEL_EXPORTER_OTLP_CLIENT_KEY`, `OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE` and `OTEL_EXPORTER_OTLP_CERTIFICATE` (per-signal `_METRICS_`, `_LOGS_` and `_TRACES_` variants exist). For `http/*` use `CLAUDE_CODE_CLIENT_CERT`, `CLAUDE_CODE_CLIENT_KEY`, `CLAUDE_CODE_CLIENT_KEY_PASSPHRASE` and `NODE_EXTRA_CA_CERTS`.

### Content Logging Gates

These control how much detail events carry. All are off by default.

| Environment Variable            | Effect                                                                                                                                                                |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `OTEL_LOG_USER_PROMPTS`         | Include prompt text on `user_prompt` events (otherwise `<REDACTED>`)                                                                                                  |
| `OTEL_LOG_ASSISTANT_RESPONSES`  | Include response text on `assistant_response` events. Falls back to `OTEL_LOG_USER_PROMPTS` when unset; set `0` to keep responses redacted while prompts are logged |
| `OTEL_LOG_TOOL_DETAILS`         | Include `tool_parameters`, `tool_input`, bash commands, full error messages, and unredacted skill, MCP server/tool, custom command and workflow names                 |
| `OTEL_LOG_TOOL_CONTENT`         | Include tool output in the `tool.output` span event (requires tracing)                                                                                                |
| `OTEL_LOG_MANAGED_SETTINGS`     | Add redacted managed settings and their SHA-256 digest to `managed_settings_resolved` events                                                                          |
| `OTEL_LOG_RAW_API_BODIES`       | Emit full Messages API request/response JSON as `api_request_body` / `api_response_body` events. `1` inlines (truncated), `file:<dir>` writes untruncated files. Implies all other content gates |

`OTEL_LOG_TOOL_DETAILS=1` exports full bash commands and tool inputs. Treat the logs backend as sensitive when it is on.

### Metrics Cardinality Control

| Environment Variable                       | Description                                                     | Default |
| ------------------------------------------ | --------------------------------------------------------------- | ------- |
| `OTEL_METRICS_INCLUDE_SESSION_ID`          | Include `session.id`                                            | `true`  |
| `OTEL_METRICS_INCLUDE_VERSION`             | Include `app.version`                                           | `false` |
| `OTEL_METRICS_INCLUDE_ACCOUNT_UUID`        | Include `user.account_uuid` and `user.account_id`               | `true`  |
| `OTEL_METRICS_INCLUDE_ENTRYPOINT`          | Include `app.entrypoint` (`cli`, `sdk-ts`, `claude-vscode`, ...)  | `false` |
| `OTEL_METRICS_INCLUDE_RESOURCE_ATTRIBUTES` | Copy `OTEL_RESOURCE_ATTRIBUTES` keys onto metric data points    | `true`  |
| `OTEL_METRICS_INCLUDE_REPOSITORY`          | Include `vcs.*` repository identity (v2.1.269+)                 | `false` |

Lower cardinality means cheaper storage and faster queries at the cost of granularity.

### Tracing (Beta)

| Environment Variable                   | Description                                                                                  |
| -------------------------------------- | -------------------------------------------------------------------------------------------- |
| `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA`  | `1` enables span tracing (required for traces)                                               |
| `OTEL_TRACES_EXPORTER`                 | `console`, `otlp`, `none`                                                                    |
| `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`   | Traces endpoint override (protocol and headers variants exist)                               |
| `OTEL_TRACES_EXPORT_INTERVAL`          | Span batch export interval in ms (default: 5000)                                             |
| `ENABLE_BETA_TRACING_DETAILED`         | Detailed tracing including `claude_code.hook` spans. Shell, user or managed settings only    |
| `BETA_TRACING_ENDPOINT`                | Endpoint for detailed beta tracing; replaces the logs and traces exporters                   |

This stack has no traces backend. Add Tempo (or use `docker-compose-lgtm.yml`) to collect spans.

## Standard Attributes

Every metric and event carries these where available:

| Attribute                  | Description                                                           | Controlled by                              |
| -------------------------- | --------------------------------------------------------------------- | ------------------------------------------ |
| `session.id`               | Session identifier                                                    | `OTEL_METRICS_INCLUDE_SESSION_ID`          |
| `app.version`              | Claude Code version                                                   | `OTEL_METRICS_INCLUDE_VERSION`             |
| `app.entrypoint`           | Launch method: `cli`, `sdk-cli`, `sdk-ts`, `sdk-py`, `claude-vscode`  | `OTEL_METRICS_INCLUDE_ENTRYPOINT`          |
| `organization.id`          | Organization UUID (when authenticated)                                | Always                                     |
| `user.account_uuid`        | Account UUID (when authenticated)                                     | `OTEL_METRICS_INCLUDE_ACCOUNT_UUID`        |
| `user.account_id`          | Account ID in tagged format (when authenticated)                      | `OTEL_METRICS_INCLUDE_ACCOUNT_UUID`        |
| `user.id`                  | Anonymous installation ID persisted in `~/.claude.json`               | Always                                     |
| `user.email`               | User email (when authenticated)                                       | Always                                     |
| `terminal.type`            | Terminal, e.g. `iTerm.app`, `vscode`, `windows-terminal`, `tmux`      | Always when detected                       |
| `vcs.repository.url.full`, `vcs.owner.name`, `vcs.repository.name`, `vcs.provider.name` | Repository identity from the `origin` remote | `OTEL_METRICS_INCLUDE_REPOSITORY` |

Service information: service name `claude-code`, meter name `com.anthropic.claude_code`, events scope `com.anthropic.claude_code.events`.

### Event Correlation Attributes

| Attribute            | Description                                                                                                  |
| -------------------- | ------------------------------------------------------------------------------------------------------------ |
| `prompt.id`          | UUID linking every event (API requests, tool decisions, tool results, skill activations) caused by one user prompt |
| `event.sequence`     | 0-based per-process counter. Order events by `event.timestamp`, then `event.sequence`                        |
| `message.uuid`       | Transcript message UUID on `user_prompt`, `assistant_response` and `api_response_body`                       |
| `client_request_id`  | Client-generated UUID sent as `x-client-request-id` on `api_request` and `api_error`                         |
| `tool_use_id`        | Links `tool_decision` to `tool_result`, and matches the `tool_use_id` passed to hooks                        |
| `workflow.run_id`, `workflow.name` | Present on events from agents running inside Workflow tool runs                                |

## Metrics

| Metric Name                           | Description                                     | Unit   |
| ------------------------------------- | ----------------------------------------------- | ------ |
| `claude_code.session.count`           | CLI sessions started                            | count  |
| `claude_code.lines_of_code.count`     | Lines of code modified                          | count  |
| `claude_code.pull_request.count`      | Pull requests created                           | count  |
| `claude_code.commit.count`            | Git commits created                             | count  |
| `claude_code.cost.usage`              | Cost of API requests                            | USD    |
| `claude_code.token.usage`             | Tokens used                                     | tokens |
| `claude_code.code_edit_tool.decision` | Code editing tool permission decisions          | count  |
| `claude_code.active_time.total`       | Active time                                     | s      |

### Metric Attributes

In addition to the standard attributes:

| Metric                                | Additional attributes |
| ------------------------------------- | --------------------- |
| `session.count`                       | `start_type`: `fresh`, `resume`, `continue`, `agents_view` |
| `lines_of_code.count`                 | `type`: `added`, `removed`; `model` |
| `pull_request.count`, `commit.count`  | none |
| `cost.usage`                          | `model`, `query_source`, `speed`, `effort`, plus the attribution attributes below |
| `token.usage`                         | `type`: `input`, `output`, `cacheRead`, `cacheCreation`; `model`, `query_source`, `speed`, `effort`, plus the attribution attributes below |
| `code_edit_tool.decision`             | `tool_name`: `Edit`, `Write`, `NotebookEdit`; `decision`: `accept`, `reject`; `source`: `config`, `hook`, `user_permanent`, `user_temporary`, `user_abort`, `user_reject`; `language` (e.g. `TypeScript`, `Python`, `unknown`) |
| `active_time.total`                   | `type`: `user` (keyboard interaction) or `cli` (tool execution and model responses) |

`query_source` is `main`, `subagent` or `auxiliary` (title generation, summaries, WebFetch post-processing). `speed` is `fast` in fast mode. `effort` is `low`, `medium`, `high`, `xhigh` or `max` on models that support it.

### Attribution Attributes (cost and token metrics)

These answer "what was the model doing when this was spent". Each one is absent when it does not apply.

| Attribute          | Present when                                              | Redaction                                                                               |
| ------------------ | --------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `skill.name`       | A skill is active                                         | Built-in, bundled, user-defined and official-marketplace names verbatim; third-party plugin skills become `third-party` |
| `agent.name`       | The request was issued by a named subagent                | Built-in and official-marketplace names verbatim; user-defined become `custom`          |
| `plugin.name`      | The request came from a plugin                            | Official-marketplace names verbatim; others become `third-party`                        |
| `marketplace.name` | The plugin is from the official marketplace               | n/a                                                                                     |
| `mcp_server.name`  | The request consumed an MCP tool result (v2.1.222+)       | Built-in, claude.ai-proxied and official-registry names verbatim; user-configured become `custom` |
| `mcp_tool.name`    | Same as `mcp_server.name`                                 | Same as `mcp_server.name`                                                               |

## Events

Events are exported via the logs protocol when `OTEL_LOGS_EXPORTER` is set. The log body is the event name (e.g. `claude_code.tool_result`); everything else is in attributes.

### User Prompt (`claude_code.user_prompt`)

Emitted when the user submits a prompt or a slash command.

* `prompt_length`: length of the prompt
* `prompt`: prompt text, `<REDACTED>` unless `OTEL_LOG_USER_PROMPTS=1`
* `command_name`: slash command name. Built-in and bundled names verbatim; custom, plugin and MCP commands report `custom` or `mcp` unless `OTEL_LOG_TOOL_DETAILS=1`
* `command_source`: `builtin`, `custom` or `mcp` (plugin commands report `custom`)
* `message.uuid`: absent on command dispatches

### Assistant Response (`claude_code.assistant_response`)

* `model`, `query_source` (e.g. `repl_main_thread`, `compact`, `web_fetch_apply`, a subagent name)
* `response_length`
* `response`: `<REDACTED>` unless `OTEL_LOG_ASSISTANT_RESPONSES=1` (truncated at `CLAUDE_CODE_OTEL_CONTENT_MAX_LENGTH`)
* `request_id`, `message.uuid`

### API Request (`claude_code.api_request`)

* `model`, `query_source`, `effort`, `speed`
* `cost_usd`, `cost_usd_micros`
* `duration_ms`: total request duration
* `ttft_ms`: time to first token
* `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_creation_tokens`
* `request_id`, `client_request_id`
* `skill_name`, `mcp_server_name`, `mcp_tool_name`: same attribution and redaction as on the cost metric

### API Error (`claude_code.api_error`)

* `model`, `error`, `status_code`, `duration_ms`, `attempt`, `client_request_id`

### Tool Decision (`claude_code.tool_decision`)

Emitted when a tool's permission decision is made, before it runs.

* `tool_name`: tool name. MCP tools report `mcp_tool` (see below)
* `tool_source`: `builtin` or `mcp`
* `tool_use_id`
* `decision`: `accept` or `reject`
* `source`: where the decision came from
  * `config`: an allow rule or permission mode approved it
  * `hook`: a PreToolUse hook decided
  * `user_permanent`: the user approved and chose "always allow"
  * `user_temporary`: the user approved this call only
  * `user_reject`: the user rejected the call
  * `user_abort`: the user aborted while the prompt was open
* `tool_parameters`: JSON, with `OTEL_LOG_TOOL_DETAILS=1` (keys described under Tool Result)

The official docs name the decision attribute `decision_source`. Claude Code 2.1.281 emits it as `source` on this event; `tool_result` uses `decision_source`.

### Tool Result (`claude_code.tool_result`)

Emitted after a tool finishes. Rejected calls never produce one.

* `tool_name`, `tool_use_id`
* `success`: `"true"` or `"false"`
* `duration_ms`
* `error_type`: error category, e.g. `Error:ENOENT`, `ShellError`
* `error`: full message, with `OTEL_LOG_TOOL_DETAILS=1`
* `decision_type`: always `accept`
* `decision_source`: `config`, `hook`, `user_permanent` or `user_temporary`
* `tool_input_size_bytes`, `tool_result_size_bytes`
* `mcp_server_scope`: on MCP tools, e.g. `user`, `project`, `claudeai`
* `tool_input`: raw tool input JSON, with `OTEL_LOG_TOOL_DETAILS=1`
* `tool_parameters`: JSON summary, with `OTEL_LOG_TOOL_DETAILS=1`

`tool_parameters` keys depend on the tool:

| Tool     | `tool_parameters` example |
| -------- | ------------------------- |
| `Bash`   | `{"bash_command":"git","full_command":"git status","description":"..."}` |
| `Skill`  | `{"skill_name":"keybindings-help"}` |
| MCP tool | `{"mcp_server_name":"context7","mcp_tool_name":"resolve-library-id"}` |

MCP tool calls report `tool_name="mcp_tool"`. The server and tool names are only available inside `tool_parameters`, so per-server MCP analysis of tool events requires `OTEL_LOG_TOOL_DETAILS=1`.

### Skill Activated (`claude_code.skill_activated`)

Emitted when a skill loads. Observed in Claude Code 2.1.281.

* `skill_name`
* `skill_source`: where the skill comes from, e.g. `bundled`, `user`, `project`, `plugin`
* `invocation_trigger`: how it was invoked, e.g. `nested-skill`

Skill calls also appear as `tool_decision` / `tool_result` events with `tool_name="Skill"`.

### MCP Server Connection (`claude_code.mcp_server_connection`)

Emitted when Claude Code connects to an MCP server. Observed in Claude Code 2.1.281.

* `server_name`, `server_scope` (`user`, `project`, `claudeai`, ...)
* `transport_type`: `stdio`, `http`, `sse`, `claudeai-proxy`, ...
* `status`: `connected` or a failure status
* `duration_ms`: connection time
* `is_plugin`: whether a plugin provides the server

### Plugin Loaded (`claude_code.plugin_loaded`)

Emitted per plugin at startup. Observed in Claude Code 2.1.281.

* `plugin_name`, `plugin_version`, `plugin_id_hash`, `marketplace_name`, `plugin_scope`, `enabled_via`
* `has_hooks`, `has_mcp`, `host_owned_mcp`, `safe_mode`
* `skill_path_count`, `command_path_count`, `agent_path_count`

### Permission Mode Changed (`claude_code.permission_mode_changed`)

Emitted when the permission mode changes. Observed in Claude Code 2.1.281.

* `from_mode`, `to_mode`: e.g. `default`, `acceptEdits`, `plan`, `auto`
* `trigger`: what caused the change

### Managed Settings Resolved (`claude_code.managed_settings_resolved`)

Emitted at startup when managed settings are evaluated.

* `managed_settings_trigger`, `managed_settings_sources`, `managed_settings_source_behavior`
* `managed_settings_helper_state`, `managed_settings_helper_applied`
* `managed_settings`, `managed_settings_digest`: with `OTEL_LOG_MANAGED_SETTINGS=1`

### API Request / Response Bodies (`claude_code.api_request_body`, `claude_code.api_response_body`)

Only with `OTEL_LOG_RAW_API_BODIES`. Carry the full Messages API JSON (inline and truncated, or as a `body_ref` to a file on disk).

### Hook Spans (`claude_code.hook`)

Only with detailed beta tracing. Attributes: `hook_event` (e.g. `PreToolUse`), `hook_name` (e.g. `PreToolUse:Write`), `num_hooks`, `duration_ms`, `num_success`, `num_blocking`, `num_non_blocking_error`, `num_cancelled`, and `hook_definitions` with `OTEL_LOG_TOOL_DETAILS=1`.

## How the Data Lands in This Stack

### Prometheus

The collector's Prometheus exporter converts names: dots become underscores and unit and `_total` suffixes are added.

| OTel metric                           | Prometheus series                              |
| ------------------------------------- | ---------------------------------------------- |
| `claude_code.session.count`           | `claude_code_session_count_total`              |
| `claude_code.lines_of_code.count`     | `claude_code_lines_of_code_count_total`        |
| `claude_code.pull_request.count`      | `claude_code_pull_request_count_total`         |
| `claude_code.commit.count`            | `claude_code_commit_count_total`               |
| `claude_code.cost.usage`              | `claude_code_cost_usage_USD_total`             |
| `claude_code.token.usage`             | `claude_code_token_usage_tokens_total`         |
| `claude_code.code_edit_tool.decision` | `claude_code_code_edit_tool_decision_total`    |
| `claude_code.active_time.total`       | `claude_code_active_time_seconds_total`        |

Labels follow the same rule: `skill.name` becomes `skill_name`, `mcp_server.name` becomes `mcp_server_name`. A series only appears after its first data point, so `claude_code_code_edit_tool_decision_total` does not exist until someone edits a file.

`increase()` ignores the first sample of a new series. Every combination of `session_id`, `skill_name` and `mcp_server_name` is its own series, so rare skill and MCP series often report 0. The dashboard therefore computes skill and MCP cost and tokens from `api_request` events in Loki (`| unwrap cost_usd`), which counts every request exactly.

### Loki

Loki's OTLP endpoint stores event attributes as structured metadata with dots replaced by underscores (`event.name` becomes `event_name`). The only stream label is `service_name`. Filter on attributes directly, without a parser:

```logql
sum by (tool_name) (count_over_time({service_name="claude-code"} | event_name="tool_result" | success="false" [1h]))
```

The log line is the plain event name, not JSON. `| json` fails with `JSONParserErr` on it, and `| json | __error__=""` drops every line. Parse the JSON inside an attribute by making it the line first:

```logql
{service_name="claude-code"} | event_name="tool_result" | tool_name="mcp_tool"
  | line_format "{{.tool_parameters}}" | json mcp_server="mcp_server_name", mcp_tool="mcp_tool_name"
```

`unwrap` works on structured metadata: `| unwrap duration_ms`.

## Analysis Recipes

### Skills

| Question                                   | Source |
| ------------------------------------------ | ------ |
| Which skills are used, and how often?      | `skill_activated` count by `skill_name` |
| Where do skills come from?                 | `skill_activated` by `skill_source` and `invocation_trigger` |
| What does each skill cost?                 | `claude_code_cost_usage_USD_total` by `skill_name` |
| Share of spend under skills                | cost with `skill_name!=""` divided by total cost |

### MCP

| Question                                   | Source |
| ------------------------------------------ | ------ |
| Which servers and tools are called?        | `tool_result` with `tool_name="mcp_tool"`, parsed `tool_parameters` |
| Are MCP tools reliable and fast?           | same, `success` and `unwrap duration_ms` |
| Which tools flood the context?             | same, `unwrap tool_result_size_bytes` |
| Do servers connect, and how quickly?       | `mcp_server_connection` by `server_name`, `status`, `duration_ms` |
| What do MCP results cost downstream?       | cost/token metrics by `mcp_server_name`, `mcp_tool_name` |

### Permissions

| Question                                   | Source |
| ------------------------------------------ | ------ |
| How often are users prompted?              | `tool_decision` with `source=~"user_.*"` |
| How much do allow rules and hooks cover?   | `tool_decision` with `source=~"config\|hook"` over total |
| What gets rejected?                        | `tool_decision` with `decision="reject"` by `tool_name` |
| Which tools need allow rules?              | `tool_decision` by `tool_name` and `source`; high `user_temporary` counts are candidates |
| Are edits accepted, by language?           | `claude_code_code_edit_tool_decision_total` by `decision`, `language` |
| How do users move between modes?           | `permission_mode_changed` by `from_mode`, `to_mode`, `trigger` |
| Did an approved call then fail?            | join `tool_decision` and `tool_result` on `tool_use_id` |

### Security

| Question                                   | Source |
| ------------------------------------------ | ------ |
| Which programs does Claude run, how often? | `tool_result` for `Bash` and `PowerShell`, `program` extracted as below |
| Which run without a prompt?                | same, by `program` and `decision_source` |
| Which commands fail?                       | same, `success="false"` |
| What reaches the network?                  | same, `program=~"curl\|wget\|ssh\|Invoke-WebRequest\|..."`, plus `WebFetch` and `WebSearch` calls |

All of these need `OTEL_LOG_TOOL_DETAILS=1`. `tool_input` shortens long strings to `…[N chars]`, so the full command comes from `tool_parameters.full_command` for Bash. PowerShell has no `tool_parameters` and falls back to `tool_input.command`. `bash_command` is not usable as the program: it is Bash-only and holds the raw first token (`SP="..."`, `MSYS_NO_PATHCONV=1`, `cd`). The dashboard derives `command` and `program` like this:

```logql
{service_name="claude-code"} | event_name="tool_result" | tool_name=~"Bash|PowerShell"
  | line_format "{{.tool_parameters}}" | json full="full_command" | drop __error__, __error_details__
  | line_format "{{.tool_input}}" | json input="command" | drop __error__, __error_details__
  | label_format command="{{if .full}}{{.full}}{{else}}{{.input}}{{end}}" | drop full, input
  | line_format "{{.command}}"
  | regexp `^\s*(?:(?:[A-Za-z_][A-Za-z0-9_]*=(?:"[^"]*"|'[^']*'|\S*)|cd\s+(?:"[^"]*"|'[^']*'|\S+)|sudo)\s*(?:&&|;)?\s*)*(?P<program>[^\s;|&()…]+)`
```

The regexp skips leading `VAR=value` assignments, `cd dir &&` and `sudo`. Write it as a backtick string: inside double quotes LogQL rejects `\s` as an invalid escape. It only sees the first program, so `a && b` and pipes count as `a`. Add a risk category with one more filter on the result, e.g. `| program=~"(?i)rm|Remove-Item|chmod"` for file destruction or `| command=~"(?i).*(npm|pip|pnpm) (install|add).*"` for package installs.

### Sigma Detections

`security/sigma/sigma_hook.py` is a report-only PreToolUse hook. It matches every Bash and PowerShell command against SigmaHQ command-line rules and sends the result to the collector over OTLP/HTTP (`localhost:4318`, override with `SIGMA_HOOK_OTLP_ENDPOINT`). The events land in Loki under `service_name="claude-code-sigma"`, separate from Claude Code's own events, and power the **Claude Code Security** dashboard.

| Event | When | Attributes |
| ----- | ---- | ---------- |
| `sigma_scan` | every scanned command | `tool_use_id`, `session_id`, `prompt_id`, `tool_name`, `command`, `cwd`, `permission_mode`, `segment_count`, `match_count`, `max_level`, `duration_ms`, `rules_version` |
| `sigma_match` | once per matched rule | the same IDs plus `rule_id`, `rule_title`, `rule_level`, `rule_status`, `rule_author`, `rule_category`, `rule_reference`, `rule_falsepositives`, `mitre_techniques`, `mitre_tactics`, `matched_segment` |
| `sigma_hook_error` | the hook failed | `error`, `tool_use_id`, `session_id` |

`tool_use_id` is the same ID Claude Code puts on `tool_decision` and `tool_result`, so a match can be joined with what happened to the command:

```logql
{service_name="claude-code-sigma"} | event_name="sigma_match" | rule_level=~"high|critical"
```

```logql
sum by (rule_title) (count_over_time({service_name="claude-code-sigma"} | event_name="sigma_match" [24h]))
```

How a command is matched:

* The command is split on `&&`, `||`, `;`, `|` and newlines, respecting quotes. Heredoc bodies are skipped because they are data.
* Each segment becomes a pseudo process per product (linux, macos, windows). `Image` is built from the first word (`/usr/bin/curl`, `C:\Windows\System32\curl.exe`), `OriginalFileName` is `<program>.exe` on Windows, and `CommandLine` is the segment.
* One extra row carries the whole command line, so rules that look at the pipe itself (`base64 -d | bash`) still match. For the PowerShell tool that row is `powershell.exe`, and `ps_script` rules run against the whole script.
* Fields the hook cannot know (`ParentImage`, `User`, `Hashes`, ...) stay NULL. Rules that require them never match. Exclusions based on them never apply, which only matters for processes Claude did not start.
* The `/dev/tcp` reverse shell rule is a syslog keyword rule and not included. The netcat, python, perl, php and ruby reverse shell rules are.

`rules.json` is compiled by `make sigma-rules` from a pinned SigmaHQ release (`sigma_core+`: stable and test rules at medium, high and critical). See `security/sigma/NOTICE.md` for the license (DRL 1.1).

### Cost and Performance

* Cost and tokens by `model`, `query_source` (main vs subagent vs auxiliary) and `effort`
* Cache efficiency: `cacheRead / (input + cacheRead)` from `claude_code_token_usage_tokens_total`
* Latency: `duration_ms` and `ttft_ms` on `api_request`
* Errors: `api_error` by `status_code` and `attempt`
* Trace one prompt end to end: filter all events by `prompt_id`, order by `event_sequence`

<Note>
  Cost metrics are approximations. For official billing data, refer to your API provider (Claude Console, AWS Bedrock, or Google Cloud Vertex).
</Note>

## Backend Considerations

* Time series databases (Prometheus): rates and aggregated metrics
* Log aggregation (Loki, Elasticsearch): event analysis and search
* Columnar stores (ClickHouse): complex joins and unique-user (DAU/WAU/MAU) queries
* Full observability platforms (Honeycomb, Datadog): correlation between metrics, events and traces

## Security and Privacy

* Telemetry is opt-in and requires explicit configuration
* API keys and file contents are never included in metrics or events
* Prompt and response text is redacted by default; only lengths are recorded
* `OTEL_LOG_TOOL_DETAILS=1` exports bash commands, tool inputs and unredacted names of user-defined skills, MCP servers and commands
* `user.email` and account identifiers are included when authenticated
