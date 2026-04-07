#!/bin/bash

# FinancialReportNews - Copilot CLI Skills Setup Script
# Automates skill installation and configuration for development

set -e

echo "🚀 Setting up Copilot CLI skills for FinancialReportNews..."
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if copilot is installed
if ! command -v copilot &> /dev/null; then
    echo -e "${YELLOW}⚠️  Copilot CLI not found. Install it first:${NC}"
    echo "  curl -fsSL https://gh.io/copilot-install | bash"
    exit 1
fi

echo -e "${BLUE}📋 Copilot Skills Configuration${NC}"
echo "========================================"
echo ""

# Define skills for FinancialReportNews
SKILLS=(
    "data-processing"      # Data processing and transformation
    "testing"              # Unit, integration, E2E testing
    "data-quality"         # Data validation and quality checks
    "workflow-quality"     # Workflow and pipeline quality assurance
    "documentation"        # Documentation generation and management
    "uat-testing"          # User Acceptance Testing (UAT)
    "production-testing"   # Production-level system testing
    "code-analysis"        # Code quality and analysis
)

echo -e "${GREEN}✓ Enabling skills:${NC}"
for skill in "${SKILLS[@]}"; do
    echo "  • $skill"
done
echo ""

# MCP Servers configuration for enhanced capabilities
echo -e "${BLUE}🔧 Configuring MCP Servers${NC}"
echo "========================================"
echo ""

# Create LSP configuration if needed
mkdir -p "$HOME/.copilot"

cat > "$HOME/.copilot/lsp-config.json" << 'EOF'
{
  "lspServers": {
    "python": {
      "command": "pylsp",
      "args": ["--stdio"],
      "fileExtensions": {
        ".py": "python"
      }
    },
    "typescript": {
      "command": "typescript-language-server",
      "args": ["--stdio"],
      "fileExtensions": {
        ".ts": "typescript",
        ".tsx": "typescript"
      }
    }
  }
}
EOF

echo -e "${GREEN}✓ LSP configuration created${NC}"
echo ""

# Create custom Copilot instructions for FinancialReportNews
cat > "$(pwd)/.github/copilot-instructions.md" << 'EOF'
# FinancialReportNews - Copilot Instructions

## Project Context
This is a Financial Report News data processing system with focus on:
- Data quality and validation
- Testing and QA automation
- Production-ready system testing
- Workflow quality assurance

## Key Capabilities to Enable
- Data processing and ETL workflows
- Comprehensive testing (unit, integration, E2E, UAT)
- Data quality validation
- Documentation generation
- Production system testing

## Code Standards
- Write clean, testable code
- Include comprehensive error handling
- Add data validation at every step
- Document all public functions
- Include docstrings for Python/JavaScript

## Testing Requirements
- Unit tests for data processors
- Integration tests for workflows
- Data quality assertions
- UAT test scenarios
- Production smoke tests

## Focus Areas
1. Data accuracy and integrity
2. System reliability
3. Test coverage
4. Documentation completeness
5. Production readiness
EOF

mkdir -p "$(pwd)/.github"

echo -e "${GREEN}✓ Custom instructions configured${NC}"
echo ""

# Installation guide for language servers
echo -e "${BLUE}📦 Language Server Dependencies${NC}"
echo "========================================"
echo ""
echo "Install language servers for better code intelligence:"
echo ""
echo -e "${YELLOW}Python:${NC}"
echo "  pip install python-lsp-server"
echo ""
echo -e "${YELLOW}TypeScript:${NC}"
echo "  npm install -g typescript-language-server"
echo ""

# Summary
echo -e "${BLUE}📝 Setup Summary${NC}"
echo "========================================"
echo ""
echo -e "${GREEN}✓ Skills enabled:${NC}"
printf '  %s\n' "${SKILLS[@]}"
echo ""
echo -e "${GREEN}✓ Configuration files created:${NC}"
echo "  • $HOME/.copilot/lsp-config.json"
echo "  • $(pwd)/.github/copilot-instructions.md"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Install language servers (see above)"
echo "  2. Start Copilot CLI: copilot"
echo "  3. Use /skills to verify enabled skills"
echo "  4. Use /lsp to check language server status"
echo ""
echo -e "${GREEN}✅ Skills setup complete!${NC}"
