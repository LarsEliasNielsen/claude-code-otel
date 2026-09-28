# Claude Code Observability Stack

[![GitHub](https://img.shields.io/badge/GitHub-ColeMurray%2Fclaude--code--otel-blue?logo=github)](https://github.com/ColeMurray/claude-code-otel)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](docker-compose.yml)

A comprehensive observability solution for monitoring Claude Code usage, performance, and costs. This setup implements the recommendations from the [Claude Code Observability Documentation](CLAUDE_OBSERVABILITY.md) to provide deep insights into AI-assisted development workflows.

## 📸 Dashboard Screenshots

### 💰 Cost & Usage Analysis
Track spending across different Claude models with detailed breakdowns of costs, API requests, and token usage patterns.

<img src="docs/images/cost-usage-analytics.png" alt="Cost & Usage Analysis Dashboard" width="800">

*Features: Model cost comparison, API request tracking, token usage breakdown by type*

### 📊 User Activity & Productivity 
Monitor development productivity with comprehensive session analytics, tool usage patterns, and code change metrics.

<img src="docs/images/user-activity.png" alt="User Activity & Productivity Dashboard" width="800">

*Features: Session tracking, tool performance metrics, code productivity insights*

## 🎯 Features

### 📊 **Comprehensive Monitoring**
- **Cost Analysis**: Track usage costs by model, user, and time periods
- **User Analytics**: Daily/Weekly/Monthly Active Users (DAU/WAU/MAU)
- **Tool Usage**: Monitor which Claude Code tools are used most frequently
- **Performance Metrics**: API latency, success rates, and bottleneck identification
- **Productivity Insights**: Lines of code changes, commits, and pull requests

### 📊 **Enhanced Analytics**
- **API Request Tracking**: Monitor actual request counts by model version
- **Token Efficiency**: Track cost-per-token across different models
- **Session Analytics**: Comprehensive session and productivity tracking
- **Real-time Monitoring**: Live dashboards with 30-second refresh rates

### 📈 **Rich Dashboards**
- **Executive Overview**: High-level KPIs and trends
- **Cost Management**: Detailed cost breakdowns and projections
- **Tool Performance**: Success rates and execution times
- **User Activity**: Productivity and engagement metrics
- **Error Analysis**: Comprehensive error tracking and investigation

## 🏗️ Architecture

```
Claude Code → OpenTelemetry Collector → Prometheus (metrics) + Loki (events/logs)
                                     ↓
                              Grafana (visualization & analysis)
```

### Components

| Service | Purpose | Port | UI |
|---------|---------|------|----| 
| **OpenTelemetry Collector** | Metrics/logs ingestion | 4317 (gRPC), 4318 (HTTP) | - |
| **Prometheus** | Metrics storage & querying | 9090 | http://localhost:9090 |
| **Loki** | Log aggregation & storage | 3100 | - |
| **Grafana** | Dashboards & visualization | 3000 | http://localhost:3000 |

## 🚀 Quick Start

### 1. Start the Stack
```bash
# Start all services
make up

# Check status
make status
```

### 2. Configure Claude Code

Add the following to Claude Code settings `~/.claude/settings.json`. Replace `/path/to/claude-code-otel` with the path to this checkout (`make setup-claude` prints the hook snippet with your path filled in):

```json
{
  "env": {
    "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
    "OTEL_METRICS_EXPORTER": "otlp",
    "OTEL_LOGS_EXPORTER": "otlp",
    "OTEL_EXPORTER_OTLP_PROTOCOL": "grpc",
    "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317",
    "OTEL_METRIC_EXPORT_INTERVAL": 10000,
    "OTEL_LOGS_EXPORT_INTERVAL": 5000,
    "OTEL_LOG_TOOL_DETAILS": 1,
    "OTEL_METRICS_INCLUDE_VERSION": true,
    "OTEL_METRICS_INCLUDE_REPOSITORY": true,
    "OTEL_RESOURCE_ATTRIBUTES": "team.id=platform"
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|PowerShell",
        "hooks": [
          {
            "type": "command",
            "async": true,
            "timeout": 30,
            "command": "python /path/to/claude-code-otel/security/sigma/sigma_hook.py"
          }
        ]
      }
    ]
  }
}
```

- **`env`** turns on Claude Code's own telemetry, which feeds the **Claude Code** dashboard. Use the variable names exactly as shown. A name copied from a shell, such as `$env:OTEL_METRICS_INCLUDE_VERSION` or `export OTEL_...`, is set as a different variable and silently does nothing.
- **`hooks`** registers the [Sigma command detection](#-sigma-command-detection) hook, which feeds the **Claude Code Security** dashboard. Claude Code's telemetry does not include these events, so without the hook that dashboard stays empty. The hook needs Python 3.9+. Use the Python launcher on your `PATH`: on Windows that is usually `python`, not `python3` (`make setup-claude PYTHON=python`). The hook runs in the background, so a wrong launcher fails silently.

If your settings file already has an `env` or `hooks` block, merge these entries into it. In particular, add the object above to an existing `PreToolUse` array instead of replacing the array.

Run Claude Code:

```bash
claude
```

> `OTEL_LOG_TOOL_DETAILS=1` exports bash commands and tool inputs to Loki, and the Sigma hook sends every Bash and PowerShell command to it. Treat the logs backend as sensitive. Settings take effect for Claude Code sessions started after they are saved.

### 3. Access Dashboards
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

> 🖼️ **Visual Guide**: Check out the [Dashboard Screenshots](#-dashboard-screenshots) to see what your dashboards will look like!

## 📊 Available Metrics

Based on the [Claude Code Observability Documentation](CLAUDE_OBSERVABILITY.md), this stack monitors:

### Core Metrics
- `claude_code.session.count` - CLI sessions started
- `claude_code.lines_of_code.count` - Lines of code modified (added/removed)
- `claude_code.pull_request.count` - Pull requests created
- `claude_code.commit.count` - Git commits created
- `claude_code.cost.usage` - Cost of sessions by model
- `claude_code.token.usage` - Token usage (input/output/cache/creation)
- `claude_code.code_edit_tool.decision` - Tool permission decisions

### Event Data
- `claude_code.user_prompt` - User prompt submissions
- `claude_code.tool_result` - Tool execution results and timings
- `claude_code.api_request` - API requests with duration and tokens
- `claude_code.api_error` - API errors with status codes
- `claude_code.tool_decision` - Tool permission decisions

## 🔍 Usage Analysis

### Real-time Dashboard Analysis

Access comprehensive analytics through the Grafana dashboard at http://localhost:3000:

- **Cost Analysis**: Real-time cost tracking with model breakdowns
- **Request Monitoring**: API request counts and patterns by model
- **Token Efficiency**: Track token usage and cost-per-token metrics
- **Tool Performance**: Success rates and execution time analysis
- **Session Analytics**: User activity and productivity insights

### Key Metrics Available
- Total and per-model costs with trending
- API request counts independent of cost variations
- Token usage breakdown (input/output/cache/creation)
- Tool usage patterns and success rates
- Session activity and code productivity metrics

## 📊 Key Dashboard Features

> 💡 **See [Dashboard Screenshots](#-dashboard-screenshots) above for visual examples**

### 💰 Cost & Usage Analysis
- **Cost by Model**: Track spending across different Claude models
- **API Request Tracking**: Monitor actual request counts by model version  
- **Token Usage Breakdown**: Detailed analysis by token type (input/output/cache)

### 🔧 Tool Performance
- **Usage Patterns**: Most frequently used Claude Code tools
- **Success Rates**: Tool execution success percentages
- **Performance Metrics**: Average execution times and bottleneck identification

### ⚡ Real-time Monitoring
- **Live Metrics**: 30-second refresh rate for current activity
- **Session Tracking**: Active sessions and productivity metrics
- **Error Analysis**: API errors and troubleshooting information

## 📋 Dashboard Sections

The Grafana dashboard is organized into sections reflecting the observability documentation recommendations:

### 📊 Overview
- Active sessions, cost, token usage, lines of code changed

### 💰 Cost & Usage Analysis  
- Cost trends by model, token usage breakdown
- **NEW**: API request count tracking by model version
- Implements cost monitoring recommendations

### 🔧 Tool Usage & Performance
- Tool frequency and success rates
- Performance bottleneck identification

### 🧩 Skills
- Skill activations, cost and tokens per skill, source and invocation trigger

### 🔌 MCP Servers & Tools
- Calls, success rate, p95 latency and result size per server/tool
- Server connection status and cost of requests that consumed MCP results

### 🛡️ Permissions
- Tool decisions by source (allow rule, hook, user prompt, rejection) and by tool
- Code edit decisions, permission mode changes, rejection log

> Skill and MCP names on tool events require `OTEL_LOG_TOOL_DETAILS=1`.

### ⚡ Performance & Errors
- API latency by model, error rate tracking
- Performance monitoring as recommended

### 📝 User Activity & Productivity
- Code changes, commits, pull requests
- Productivity measurement insights

### 🔍 Event Logs
- Real-time tool execution events and API errors
- Structured log analysis for troubleshooting

## 🚨 Sigma Command Detection

A PreToolUse hook checks every Bash and PowerShell command Claude Code runs against about 1,300 [SigmaHQ](https://github.com/SigmaHQ/sigma) command-line rules (reverse shells, download cradles, encoded PowerShell, certutil abuse, and so on). Matches show up in the **Claude Code Security** dashboard with rule level, MITRE ATT&CK techniques, and whether the command succeeded and how it was approved.

The hook only reports. It runs in the background, adds no delay and never blocks a command. It needs Python 3.9+ and nothing else.

1. Register the hook in `~/.claude/settings.json` with the `hooks` block from [Configure Claude Code](#2-configure-claude-code).

2. Start a new Claude Code session and let it run a Bash or PowerShell command. Check that the events arrived: `curl -s http://localhost:3100/loki/api/v1/label/service_name/values` should list `claude-code-sigma`.

3. Open http://localhost:3000/d/claude-code-security. Hide noisy rules with the **Exclude rules** filter. Only commands run after the hook was registered appear. On a quiet day, **Commands Scanned** counts up while the match panels stay at zero.

Try a command without running it: `python security/sigma/sigma_hook.py --scan "echo aGk= | base64 -d | bash"`.

`make sigma-rules` rebuilds `security/sigma/rules.json` from the pinned SigmaHQ release (it installs pySigma into `security/sigma/.venv`). `make test-sigma` runs the tests. The commands are sent to your local collector only. Event reference: [CLAUDE_OBSERVABILITY.md](CLAUDE_OBSERVABILITY.md#sigma-detections).

## 🔧 Advanced Configuration

### Environment Variables

Key configuration options (see [CLAUDE_OBSERVABILITY.md](CLAUDE_OBSERVABILITY.md) for complete reference):

```bash
# Core telemetry
CLAUDE_CODE_ENABLE_TELEMETRY=1

# Exporter configuration
OTEL_METRICS_EXPORTER=otlp,prometheus    # Multiple exporters
OTEL_LOGS_EXPORTER=otlp

# Protocol and endpoints
OTEL_EXPORTER_OTLP_PROTOCOL=grpc
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer token"

# Export intervals
OTEL_METRIC_EXPORT_INTERVAL=60000        # 1 minute (production)
OTEL_LOGS_EXPORT_INTERVAL=5000           # 5 seconds

# Privacy controls
OTEL_LOG_USER_PROMPTS=1                   # Enable prompt content logging

# Cardinality control
OTEL_METRICS_INCLUDE_SESSION_ID=true
OTEL_METRICS_INCLUDE_VERSION=false
OTEL_METRICS_INCLUDE_ACCOUNT_UUID=true
```

### Collector Configuration

The OpenTelemetry collector is configured with:
- **Processors**: Resource enrichment and event filtering
- **Multiple Pipelines**: Separate routing for metrics and different event types
- **Metric Relabeling**: Cardinality control for better performance

### Backend Considerations

Following the documentation recommendations:

- **Metrics Backend**: Prometheus (time series) + optional columnar stores
- **Events Backend**: Loki (log aggregation) with JSON parsing
- **Cardinality Management**: Configurable attribute inclusion
- **Retention**: Configure based on your analysis needs

## 🛠️ Management Commands

```bash
# Stack management
make up                    # Start all services
make down                  # Stop all services  
make restart              # Restart services
make clean                # Clean up containers and volumes

# Monitoring
make logs                 # View all logs
make logs-collector       # View collector logs only
make status              # Show service status

# Validation
make validate-config     # Validate all configs
make setup-claude       # Show Claude Code setup instructions
```

## 🎯 Use Cases

### For Engineering Teams
- **Cost Management**: Track AI assistance costs by team/project
- **Productivity Measurement**: Quantify development velocity improvements
- **Tool Adoption**: Understand which Claude Code features drive value
- **Performance Optimization**: Identify and resolve usage bottlenecks

### For Platform Teams
- **Capacity Planning**: Predict infrastructure needs based on usage growth
- **SLA Monitoring**: Track API performance and availability
- **Security**: Monitor unusual usage patterns
- **Resource Optimization**: Optimize token usage and reduce costs

### For Management
- **ROI Analysis**: Measure productivity gains from AI assistance
- **Usage Insights**: Understand adoption patterns across teams
- **Cost Control**: Monitor and optimize AI assistance spending
- **Strategic Planning**: Data-driven decisions on AI tool investments

## 🔒 Security & Privacy

- **User Privacy**: Prompt content logging is disabled by default
- **Data Isolation**: All data stays within your infrastructure
- **Access Control**: Configure Grafana authentication as needed
- **Audit Trail**: Complete logging of all tool usage and decisions

## 📚 Resources

- [Claude Code Observability Documentation](CLAUDE_OBSERVABILITY.md) - Complete reference
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/) - OTel specification
- [Prometheus Documentation](https://prometheus.io/docs/) - Metrics and alerting
- [Grafana Documentation](https://grafana.com/docs/) - Dashboards and visualization
- [Loki Documentation](https://grafana.com/docs/loki/) - Log aggregation

## 🤝 Contributing

This observability stack implements the patterns and recommendations from the official Claude Code documentation. To contribute:

1. Follow the metric naming conventions in the documentation
2. Update dashboards to reflect new data sources and metrics
3. Test configurations before submitting changes
4. Ensure all sensitive information is excluded from commits
5. Update documentation for any new features or configuration changes

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built following the [Claude Code Observability Documentation](CLAUDE_OBSERVABILITY.md)
- Uses OpenTelemetry standards for metrics and events
- Implements industry best practices for observability stack architecture 
