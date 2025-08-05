#!/bin/bash

# GDR Framework - One-Click Repository Creator
# Este script cria automaticamente o repositório Git completo do GDR

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
NC='\033[0m'

print_header() {
    echo -e "${PURPLE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                 GDR FRAMEWORK REPOSITORY SETUP              ║"
    echo "║              One-Click Git Repository Creator                ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    echo -e "${BLUE}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Verificar dependências
check_dependencies() {
    print_step "Verificando dependências..."
    
    # Git
    if ! command -v git &> /dev/null; then
        print_error "Git não está instalado"
        exit 1
    fi
    
    # Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 não está instalado"
        exit 1
    fi
    
    print_success "Dependências OK"
}

# Configurar informações do projeto
setup_project_info() {
    print_step "Configurando informações do projeto..."
    
    # Nome do projeto
    read -p "Nome do repositório [gdr-framework]: " REPO_NAME
    REPO_NAME=${REPO_NAME:-gdr-framework}
    
    # Nome do usuário GitHub
    read -p "Seu usuário do GitHub: " GITHUB_USER
    if [ -z "$GITHUB_USER" ]; then
        print_error "Usuário do GitHub é obrigatório"
        exit 1
    fi
    
    # Configuração Git local
    if [ -z "$(git config --global user.name)" ]; then
        read -p "Seu nome completo: " GIT_NAME
        git config --global user.name "$GIT_NAME"
    fi
    
    if [ -z "$(git config --global user.email)" ]; then
        read -p "Seu email: " GIT_EMAIL
        git config --global user.email "$GIT_EMAIL"
    fi
    
    export REPO_NAME
    export GITHUB_USER
    
    print_success "Informações configuradas"
}

# Criar diretório do projeto
create_project_directory() {
    print_step "Criando diretório do projeto..."
    
    if [ -d "$REPO_NAME" ]; then
        print_warning "Diretório $REPO_NAME já existe"
        read -p "Remover e recriar? (y/N): " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            rm -rf "$REPO_NAME"
        else
            print_error "Operação cancelada"
            exit 1
        fi
    fi
    
    mkdir -p "$REPO_NAME"
    cd "$REPO_NAME"
    
    print_success "Diretório criado: $REPO_NAME"
}

# Executar setup do Git
run_git_setup() {
    print_step "Executando setup do Git..."
    
    # Baixar o script de setup (simulado - em produção você baixaria de um URL)
    # Por enquanto, vamos recriar o conteúdo essencial aqui
    
    # Inicializar Git
    git init
    
    # Criar estrutura de diretórios
    mkdir -p {src,tests,docs,data/{input,samples},examples/{basic,advanced},scripts/setup,.github/workflows}
    
    # Criar .gitignore
    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
env/
ENV/
.venv/

# Environment variables
.env

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# GDR Specific
outputs/
logs/
temp/
gdr_state/
*.log

# Data files (uncomment if you don't want to track)
# data/input/*.xlsx
# data/input/*.csv
EOF
    
    print_success "Setup do Git concluído"
}

# Criar arquivos de configuração
create_config_files() {
    print_step "Criando arquivos de configuração..."
    
    # requirements.txt
    cat > requirements.txt << 'EOF'
# GDR Framework Dependencies

# Core Data Processing
pandas>=1.5.0
numpy>=1.24.0
openpyxl>=3.1.0
xlsxwriter>=3.0.0

# HTTP & Async
aiohttp>=3.8.0
requests>=2.28.0

# Environment & Config
python-dotenv>=1.0.0

# Text Processing & Web Scraping
beautifulsoup4>=4.11.0
lxml>=4.9.0

# LLM APIs
openai>=1.0.0
anthropic>=0.7.0
google-generativeai>=0.3.0

# Statistics & ML
scikit-learn>=1.3.0
scipy>=1.10.0

# Development & Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
black>=23.0.0
flake8>=6.0.0
mypy>=1.5.0
EOF
    
    # .env.example
    cat > .env.example << 'EOF'
# GDR Framework - Environment Variables Example
# Copy this file to .env and fill in your API keys

# Google APIs
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
GOOGLE_CSE_API_KEY=your_google_custom_search_api_key
GOOGLE_CSE_ID=your_custom_search_engine_id

# LLM APIs
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
GEMINI_API_KEY=your_google_gemini_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
ZHIPUAI_API_KEY=your_zhipuai_api_key

# Scraping APIs
APIFY_API_KEY=your_apify_api_key
APIFY_API_KEY_LINKTREE=your_apify_linktree_api_key

# Processing Configuration
MAX_CONCURRENT_REQUESTS=3
REQUEST_TIMEOUT=30
RETRY_ATTEMPTS=3

# Output Configuration
OUTPUT_DIR=./outputs
LOG_LEVEL=INFO
EOF
    
    print_success "Arquivos de configuração criados"
}

# Criar README principal
create_readme() {
    print_step "Criando README.md..."
    
    cat > README.md << EOF
# 🚀 GDR Framework - Generative Development Representative

![Python](https://img.shields.io/badge/python-v3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-Production--Ready-brightgreen.svg)

## 🎯 Visão Geral

O **GDR (Generative Development Representative)** é um framework de IA que automatiza completamente a função de SDR/BDR, processando leads desde a coleta até a qualificação final com relatórios executivos e controle de custos.

### ✨ Principais Características

- 🤖 **Multi-LLM Consensus**: OpenAI, Claude, Gemini, DeepSeek, ZhipuAI
- 🕷️ **Multi-Source Data Collection**: Google Places, Websites, Social Media
- 📊 **Statistical Analysis**: Kappa scores para validação de concordância
- 💾 **Fault Recovery**: Sistema de persistência e recuperação automática
- 💰 **Cost Control**: Tracking detalhado de tokens e custos por LLM
- 📈 **Professional Reports**: Excel com análises executivas

## 🚀 Quick Start

\`\`\`bash
# 1. Clone o repositório
git clone https://github.com/${GITHUB_USER}/${REPO_NAME}.git
cd ${REPO_NAME}

# 2. Setup do ambiente
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# 3. Configurar APIs
cp .env.example .env
# Editar .env com suas chaves de API

# 4. Executar demo
python src/run_gdr.py -m 10
\`\`\`

## 📊 Performance

### Resultados Típicos:
- ⚡ **30 segundos/lead** em média
- 💰 **~\$0.002/lead** custo total
- 🎯 **95%+ taxa de sucesso**
- 📧 **75%+ cobertura de emails**
- 📞 **90%+ cobertura de telefones**

### Escalabilidade:
\`\`\`
   10 leads = ~\$0.02 USD  (30 segundos)
  100 leads = ~\$0.20 USD  (5 minutos)
1.000 leads = ~\$2.00 USD  (50 minutos)
\`\`\`

## 📁 Estrutura do Projeto

\`\`\`
${REPO_NAME}/
├── src/                    # Código fonte principal
├── data/                   # Dados de entrada e amostras
├── docs/                   # Documentação técnica
├── examples/               # Exemplos de uso
├── tests/                  # Testes automatizados
├── requirements.txt        # Dependências Python
└── .env.example           # Exemplo de configuração
\`\`\`

## 🛠️ Casos de Uso

### 1. **Enriquecimento de Base Existente**
\`\`\`bash
python src/run_gdr.py -i sua_base.xlsx -m 100
\`\`\`

### 2. **Prospecção do Zero**
\`\`\`bash
python src/google_places_collector.py
python src/run_gdr.py -i leads_coletados.xlsx
\`\`\`

### 3. **Pipeline Completo**
\`\`\`bash
python src/complete_pipeline_demo.py -s setor -m 50
\`\`\`

## 🔧 Configuração

Copie \`.env.example\` para \`.env\` e configure suas API keys:

\`\`\`bash
OPENAI_API_KEY=sua_chave_openai
GOOGLE_MAPS_API_KEY=sua_chave_google
GOOGLE_CSE_API_KEY=sua_chave_cse
GOOGLE_CSE_ID=seu_id_cse
\`\`\`

## 📚 Documentação

- 📋 [PRD Completo](docs/PRD.md)
- 🏗️ [Arquitetura](docs/ARCHITECTURE.md)
- 🔧 [API Reference](docs/API_REFERENCE.md)
- 📖 [Exemplos](examples/README.md)

## 🧪 Testes

\`\`\`bash
# Executar testes
python -m pytest tests/

# Com coverage
python -m pytest --cov=src tests/
\`\`\`

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch (\`git checkout -b feature/nova-funcionalidade\`)
3. Commit suas mudanças (\`git commit -am 'Adiciona nova funcionalidade'\`)
4. Push para a branch (\`git push origin feature/nova-funcionalidade\`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para detalhes.

---

**🚀 Built for Sales Teams | Made with ❤️**
EOF
    
    print_success "README.md criado"
}

# Criar LICENSE
create_license() {
    cat > LICENSE << 'EOF'
MIT License

Copyright (c) 2025 GDR Framework

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOF
}

# Criar documentação básica
create_basic_docs() {
    print_step "Criando documentação básica..."
    
    # docs/README.md
    cat > docs/README.md << 'EOF'
# 📚 Documentação GDR Framework

## 📋 Índice

### 🏗️ Arquitetura
- [PRD - Product Requirements](PRD.md)
- [Arquitetura do Sistema](ARCHITECTURE.md)

### 🚀 Implementação
- [Guia de Instalação](INSTALLATION.md)
- [Configuração de APIs](API_SETUP.md)

### 📖 Uso
- [Guia de Uso](USAGE.md)
- [Exemplos Práticos](../examples/README.md)
- [Troubleshooting](TROUBLESHOOTING.md)

### 🔧 Desenvolvimento
- [API Reference](API_REFERENCE.md)
- [Contribuição](CONTRIBUTING.md)
EOF
    
    # examples/README.md
    cat > examples/README.md << 'EOF'
# 📖 Exemplos GDR Framework

## 🎯 Básicos

### Processamento Simples
\`\`\`bash
python ../src/run_gdr.py -m 10
\`\`\`

### Validação de Configuração
\`\`\`bash
python ../src/run_gdr.py --validate-only
\`\`\`

## 🔬 Avançados

### Configuração Customizada
\`\`\`python
# Ver examples/advanced/custom_configuration.py
\`\`\`

### Pipeline Completo
\`\`\`bash
python ../src/complete_pipeline_demo.py
\`\`\`
EOF
    
    # Criar exemplo básico
    cat > examples/basic/simple_example.py << 'EOF'
#!/usr/bin/env python3
"""
Exemplo básico de uso do GDR Framework
"""

import sys
import asyncio
from pathlib import Path

# Adicionar src ao path
sys.path.append(str(Path(__file__).parent.parent.parent / 'src'))

from gdr_mvp import GDRFramework

async def main():
    """Exemplo simples de processamento"""
    print("🚀 GDR Framework - Exemplo Básico")
    print("=" * 40)
    
    # Inicializar framework
    gdr = GDRFramework()
    
    # Verificar se arquivo de dados existe
    data_file = Path(__file__).parent.parent.parent / 'data' / 'input' / 'leads.xlsx'
    
    if not data_file.exists():
        print("❌ Arquivo de dados não encontrado")
        print(f"   Esperado: {data_file}")
        return
    
    # Carregar leads
    leads = gdr.load_leads_from_excel(str(data_file))
    print(f"📊 Carregados {len(leads)} leads")
    
    # Processar apenas 3 para exemplo rápido
    print("🔄 Processando 3 leads de exemplo...")
    results, token_usages = await gdr.process_leads_batch(leads[:3])
    
    # Mostrar resultados
    successful = [r for r in results if r.get('processing_status') == 'success']
    total_cost = sum(usage.cost_usd for usage in token_usages)
    
    print("✅ Processamento concluído!")
    print(f"   └─ Sucessos: {len(successful)}/{len(results)}")
    print(f"   └─ Custo: ${total_cost:.6f}")
    
    # Mostrar amostra de resultado
    if successful:
        sample = successful[0]
        print("📋 Amostra de resultado:")
        print(f"   └─ Nome: {sample.get('original_nome')}")
        print(f"   └─ Email: {sample.get('gdr_concenso_email', 'N/A')}")
        print(f"   └─ Telefone: {sample.get('gdr_concenso_telefone', 'N/A')}")

if __name__ == "__main__":
    asyncio.run(main())
EOF
    
    print_success "Documentação básica criada"
}

# Criar commit inicial
create_initial_commit() {
    print_step "Criando commit inicial..."
    
    # Adicionar todos os arquivos
    git add .
    
    # Commit inicial
    git commit -m "🚀 Initial commit: GDR Framework

✨ Framework de IA para automação de SDR/BDR

Features:
- Multi-LLM consensus (OpenAI, Claude, Gemini, DeepSeek, ZhipuAI)
- Multi-source data collection (Google Places, websites, social media)  
- Statistical analysis com Kappa scores
- Sistema de persistência e recovery automático
- Relatórios profissionais em Excel
- Controle detalhado de custos por token

Performance:
- 95%+ taxa de sucesso
- ~\$0.002/lead custo médio
- 30s/lead tempo médio de processamento
- Recovery automático em falhas

Pronto para produção! 🚀"

    print_success "Commit inicial criado"
}

# Instruções finais
show_final_instructions() {
    print_step "Instruções finais"
    
    echo ""
    echo "🎉 REPOSITÓRIO CRIADO COM SUCESSO!"
    echo "=================================="
    echo ""
    echo "📁 Localização: $(pwd)"
    echo "🌟 GitHub URL: https://github.com/${GITHUB_USER}/${REPO_NAME}"
    echo ""
    echo "🔧 PRÓXIMOS PASSOS:"
    echo ""
    echo "1. 📂 ADICIONAR ARQUIVOS DO GDR:"
    echo "   cp /caminho/dos/seus/arquivos/gdr_mvp.py src/"
    echo "   cp /caminho/dos/seus/arquivos/run_gdr.py src/"
    echo "   cp /caminho/dos/seus/arquivos/leads.xlsx data/input/"
    echo "   cp /caminho/dos/seus/arquivos/.env ."
    echo ""
    echo "2. 🔐 CONFIGURAR APIS:"
    echo "   # Editar .env com suas chaves reais"
    echo "   nano .env"
    echo ""
    echo "3. 🚀 CRIAR REPOSITÓRIO NO GITHUB:"
    echo "   # Vá para https://github.com/new"
    echo "   # Nome: ${REPO_NAME}"
    echo "   # Descrição: 🤖 GDR Framework - Generative Development Representative"
    echo "   # ❌ NÃO inicializar com README"
    echo ""
    echo "4. 📡 CONECTAR E FAZER PUSH:"
    echo "   git remote add origin https://github.com/${GITHUB_USER}/${REPO_NAME}.git"
    echo "   git branch -M main"
    echo "   git push -u origin main"
    echo ""
    echo "5. ✅ TESTAR FUNCIONALIDADE:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    echo "   python src/run_gdr.py --validate-only"
    echo ""
    echo "6. 🎮 EXECUTAR DEMO:"
    echo "   python src/run_gdr.py -m 5"
    echo ""
    echo "📚 Documentação completa em: docs/README.md"
    echo "📖 Exemplos práticos em: examples/"
    echo ""
    echo -e "${GREEN}🚀 Seu repositório GDR está pronto para o mundo!${NC}"
}

# Função principal
main() {
    print_header
    
    echo "Este script criará um repositório Git completo para o GDR Framework."
    echo "Você precisará ter seus arquivos Python prontos para copiar depois."
    echo ""
    read -p "Continuar? (y/N): " confirm
    
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        echo "Operação cancelada."
        exit 0
    fi
    
    # Executar todas as etapas
    check_dependencies
    setup_project_info
    create_project_directory
    run_git_setup
    create_config_files
    create_readme
    create_license
    create_basic_docs
    create_initial_commit
    show_final_instructions
}

# Executar se chamado diretamente
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
