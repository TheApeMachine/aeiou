# AEIOU Neovim Plugin

A comprehensive collaborative coding partner that transforms natural language prompts into structured code specifications and provides intelligent code assistance.

## Features

- **Natural Language Processing**: Convert plain English prompts into canonical code specifications
- **Intelligent Code Analysis**: Real-time analysis of code quality, duplication, and complexity
- **Task Orchestration**: Automated task breakdown and parallel execution
- **Focus Modes**: Adaptable interaction styles (Pair, Background, Solo Batches)
- **Permission Management**: Granular control over tool access and operations
- **Version Control Integration**: Seamless branch management and diff narration
- **Memory & Learning**: Persistent knowledge base with RAG-powered insights

## Installation

### Using lazy.nvim

```lua
{
  "theapemachine/aeiou",
  dir = "~/path/to/aeiou/nvim",
  config = function()
    require('aeiou').setup({
      sidecar_url = "http://127.0.0.1:8000",
      auto_start = true
    })
  end,
}
```

### Manual Installation

1. Clone the repository
2. Copy `nvim/lua/aeiou/` to your Neovim runtime path
3. Add to your init.lua:

```lua
require('aeiou').setup({
  sidecar_url = "http://127.0.0.1:8000",
  auto_start = true
})
```

## Configuration

```lua
require('aeiou').setup({
  sidecar_url = "http://127.0.0.1:8000",  -- Sidecar service URL
  auto_start = true,                      -- Auto-start sidecar on setup
})
```

## Commands

### Core Commands

- `:AeiouTranscode` - Open transcoder window for natural language to spec conversion
- `:AeiouGenerateFromPrompt` - Generate code from a prompt
- `:AeiouGenerateOpsFromPrompt` - Generate and apply edit operations
- `:AeiouShowTaskSpec` - Display current TaskSpec
- `:AeiouShowIntentCard` - Show next intent card

### Mode Management

- `:AeiouFocusMode [pair|background|solo_batches]` - Set focus mode
- `:AeiouListModes` - List available focus modes

### Task Management

- `:AeiouIntentStats` - Show intent card statistics
- `:AeiouSubtasks` - Display active subtasks

### Safety & Permissions

- `:AeiouKillSwitch` - Activate emergency kill switch
- `:AeiouResetSafety` - Reset safety counters

### Development

- `:AeiouDigest` - Force generate activity digest
- `:AeiouDigestInterval [seconds]` - Set digest interval

## Focus Modes

### Pair Mode
- Narrated small steps with user guidance
- High interaction frequency
- Step-by-step confirmation

### Background Mode
- Quiet operation with minimal interruptions
- Automatic task execution
- Low interaction frequency

### Solo Batches Mode
- Autonomous execution of multiple tasks
- Batch processing
- No interruptions

## Usage Examples

### Basic Code Generation

1. Open a file in Neovim
2. Run `:AeiouTranscode`
3. Type: "Add a REST API endpoint for user management"
4. Press Enter to generate specification
5. Use `:AeiouGenerateFromPrompt` to create code

### Task Orchestration

1. Write a complex task description
2. AEIOU automatically analyzes and creates intent cards
3. Review and approve tasks with `:AeiouShowIntentCard`
4. Tasks are broken down into subtasks and executed

### Code Analysis

- Real-time analysis runs automatically
- View current analysis with `:AeiouShowTaskSpec`
- Get activity digests with `:AeiouDigest`

## Architecture

AEIOU consists of two main components:

1. **Neovim Plugin** (`nvim/`): User interface and editor integration
2. **Python Sidecar** (`sidecar/`): AI processing and analysis engine

The sidecar provides REST APIs for:
- Natural language processing
- Code analysis and generation
- Task orchestration
- Memory and learning
- Permission management

## Requirements

- Neovim 0.8+
- Python 3.10+
- Git (for VCS operations)
- OpenAI API key (for AI features)

## Troubleshooting

### Sidecar Connection Issues

```bash
# Check if sidecar is running
curl http://127.0.0.1:8000/health

# Start sidecar manually
cd sidecar && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Permission Issues

```vim
:AeiouResetSafety
:AeiouKillSwitch  " Emergency stop
```

### Mode Issues

```vim
:AeiouFocusMode background  " Switch to background mode
:AeiouListModes            " See available modes
```

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for development guidelines.

## License

See [LICENSE](../LICENSE) for licensing information.
