# AEIOU 🤖

AEIOU is a collaborative coding partner for Neovim that helps with code analysis, task management, and development workflow.

**Background**: AEIOU is built on a groundbreaking **layered collaborative architecture** that treats coding as a true partnership between human and AI. Unlike traditional AI assistants that respond linearly to prompts, AEIOU uses an **always-on impulse system** where tiny "watcher" models continuously monitor your codebase, clustering signals into actionable insights that drive intelligent initiative.

The system operates in three layers:
- **L0 Watchers**: Tiny models analyzing code for duplication, complexity, test gaps, and patterns
- **L1 Interpreters**: Small models clustering signals into structured TaskSpecs with priorities
- **L2 Synthesizer**: Large model governing conversation, planning, and orchestration

This creates **non-linear collaboration** - working in parallel when you're focused, surfacing insights via Intent Cards when appropriate, and engaging in discussion only when needed. The system maintains **energy budgets** that adapt to your activity, **quorum rules** requiring multiple signals before action, and **ephemeral branches** for safe experimentation.

AEIOU learns your **personal style profile** from your codebase, builds a **project graph** of files→symbols→dependencies→owners, and offers **curiosity-driven alternatives** through a dedicated budget for "wild but plausible" ideas. It's not just another AI assistant - it's a sophisticated collaborative partner designed for the nuanced, iterative nature of software development.

## ✨ Features

- **Natural Language Processing** 📝 - Convert plain English descriptions into structured code specifications
- **Real-time Code Analysis** 🔍 - Monitor code quality, detect duplication, and assess complexity
- **Task Orchestration** 🎯 - Break down complex tasks and manage parallel execution
- **Intelligent Code Generation** ⚡ - Generate code from specifications with AI assistance
- **Version Control Integration** 🔀 - Seamless branch management and diff analysis
- **Permission System** 🔐 - Granular control over tool access and operations
- **Memory & Learning** 🧠 - Persistent knowledge base with historical pattern recognition
- **Health Monitoring** 📊 - System performance tracking and automated maintenance

## 📋 Requirements

- **Python**: 3.10 or higher
- **Neovim**: 0.8 or higher
- **Git**: For version control operations
- **OpenAI API Key**: For AI-powered features (optional)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/theapemachine/aeiou.git
cd aeiou
```

### 2. Set Up Development Environment

Run the automated setup script:

```bash
./scripts/setup_dev.sh
```

This will:
- Create a Python virtual environment
- Install all required dependencies
- Set up the database
- Configure Neovim plugin for development

### 3. Configure API Key

Edit the environment file and add your OpenAI API key:

```bash
# Edit sidecar/.env
OPENAI_API_KEY=your_api_key_here
```

### 4. Start the Sidecar Service

```bash
make run
```

The service will start on `http://127.0.0.1:8000`

### 5. Test in Neovim

Open Neovim and try the basic commands:

```vim
:AeiouTranscode
```

Type a description like "Add a user authentication function" and press Enter.

## 📖 Usage

### Basic Workflow

1. **Describe** your coding task in plain English
2. **Generate** a structured specification
3. **Review** and refine the specification
4. **Execute** the task with AI assistance
5. **Monitor** progress and make adjustments

### Key Commands

- `:AeiouTranscode` - Convert natural language to code specifications
- `:AeiouGenerateFromPrompt` - Generate code from a prompt
- `:AeiouShowTaskSpec` - Display current task specification
- `:AeiouFocusMode [pair|background|solo_batches]` - Set interaction mode
- `:AeiouKillSwitch` - Emergency stop for all operations

### Focus Modes

- **Pair Mode** 👥 - Step-by-step guidance with frequent interaction
- **Background Mode** 🔄 - Quiet operation with automatic task execution
- **Solo Batches Mode** 📦 - Batch processing for multiple tasks

## 🏗️ Project Structure

```
aeiou/
├── lua/                    # Neovim plugin (at root for GitHub installation)
│   └── aeiou/              # Plugin Lua modules
├── doc/                    # Neovim documentation
├── sidecar/                # Python backend service
│   ├── app/                # Main application code
│   ├── tests/              # Test suite
│   └── requirements.txt    # Python dependencies
├── nvim/                   # Original Neovim plugin location (for development)
│   ├── lua/aeiou/          # Plugin Lua modules
│   └── doc/                # Documentation
├── scripts/                # Development scripts
├── docs/                   # Additional documentation
├── Makefile               # Build automation
└── README.md              # This file
```

## 🛠️ Development

### Available Make Targets

```bash
make help           # Show all available targets
make run            # Start development server
make test           # Run test suite
make lint           # Check code style
make format         # Auto-format code
make clean          # Clean build artifacts
```

### Installing from GitHub

Add this to your lazy.nvim config:

```lua
{
  "TheApeMachine/aeiou",
  config = function()
    require('aeiou').setup({
      sidecar_url = "http://127.0.0.1:8000",
      auto_start = true
    })
  end,
}
```

### Development Setup

For local development, use the local path:

```lua
{
  dir = "~/path/to/aeiou",  -- Path to your local aeiou directory
  config = function()
    require('aeiou').setup({
      sidecar_url = "http://127.0.0.1:8000",
      auto_start = true
    })
  end,
}
```

### Manual Setup

If you prefer manual setup:

```bash
# Python environment
cd sidecar
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# Database
python -c "from app.memory_store import MemoryStore; MemoryStore()"

# Neovim plugin (symlink method)
mkdir -p ~/.local/share/nvim/site/pack/aeiou/start
ln -s $(pwd)/nvim ~/.local/share/nvim/site/pack/aeiou/start/

# Or copy the files
cp -r nvim/lua/aeiou ~/.local/share/nvim/site/pack/aeiou/start/
```

## 🔧 Configuration

### Environment Variables

Create `sidecar/.env`:

```bash
OPENAI_API_KEY=your_key_here
DATABASE_URL=sqlite:///aeiou_memory.db
HOST=127.0.0.1
PORT=8000
DEBUG=True
```

### Neovim Configuration

Add to your `init.lua`:

```lua
require('aeiou').setup({
  sidecar_url = "http://127.0.0.1:8000",
  auto_start = true
})
```

## 🧪 Testing

Run the test suite:

```bash
make test
```

Run with coverage:

```bash
make test-coverage
```

## 📚 Documentation

- **User Guide**: See `nvim/README.md`
- **API Reference**: See `nvim/doc/aeiou.txt`
- **Contributing**: See `CONTRIBUTING.md`

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

## 🙋 Support

- **Issues**: [GitHub Issues](https://github.com/theapemachine/aeiou/issues)
- **Discussions**: [GitHub Discussions](https://github.com/theapemachine/aeiou/discussions)

---

**AEIOU** - Making coding more collaborative, one task at a time.