#!/bin/bash

# GDR Framework - Complete Setup and Execution Script
# This script sets up the environment and demonstrates the complete GDR pipeline

set -e

echo "🚀 GDR Framework - Complete Setup"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if Python 3.8+ is available
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
        REQUIRED_VERSION="3.8"
        
        if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
            print_status "Python $PYTHON_VERSION encontrado"
            PYTHON_CMD="python3"
        else
            print_error "Python 3.8+ é necessário. Versão encontrada: $PYTHON_VERSION"
            exit 1
        fi
    else
        print_error "Python3 não encontrado. Por favor, instale Python 3.8+"
        exit 1
    fi
}

# Setup virtual environment
setup_venv() {
    print_info "Configurando ambiente virtual..."
    
    if [ ! -d "venv" ]; then
        $PYTHON_CMD -m venv venv
        print_status "Ambiente virtual criado"
    else
        print_info "Ambiente virtual já existe"
    fi
    
    # Activate virtual environment
    source venv/bin/activate || source venv/Scripts/activate 2>/dev/null || {
        print_error "Erro ao ativar ambiente virtual"
        exit 1
    }
    
    print_status "Ambiente virtual ativado"
}

# Install dependencies
install_dependencies() {
    print_info "Instalando dependências..."
    
    pip install --upgrade pip
    pip install -r requirements.txt
    
    print_status "Dependências instaladas"
}

# Check environment variables
check_env() {
    print_info "Verificando variáveis de ambiente..."
    
    if [ ! -f ".env" ]; then
        print_error "Arquivo .env não encontrado"
        print_info "Por favor, crie o arquivo .env com suas chaves de API"
        exit 1
    fi
    
    # Source .env file
    source .env
    
    # Check required variables
    REQUIRED_VARS=("OPENAI_API_KEY" "GOOGLE_CSE_API_KEY" "GOOGLE_CSE_ID")
    MISSING_VARS=()
    
    for var in "${REQUIRED_VARS[@]}"; do
        if [ -z "${!var}" ]; then
            MISSING_VARS+=("$var")
        fi
    done
    
    if [ ${#MISSING_VARS[@]} -ne 0 ]; then
        print_error "Variáveis de ambiente faltando: ${MISSING_VARS[*]}"
        print_info "Configure o arquivo .env com suas chaves de API"
        exit 1
    fi
    
    print_status "Variáveis de ambiente configuradas"
}

# Create necessary directories
setup_directories() {
    print_info "Criando diretórios..."
    
    mkdir -p outputs
    mkdir -p logs
    mkdir -p temp
    
    print_status "Diretórios criados"
}

# Show available demos
show_demos() {
    echo ""
    echo "🎯 DEMOS DISPONÍVEIS"
    echo "===================="
    echo ""
    echo "1. DEMO BÁSICO - Processar planilha existente:"
    echo "   python run_gdr.py -i leads.xlsx -m 10"
    echo ""
    echo "2. DEMO GOOGLE PLACES - Coletar leads do zero:"
    echo "   python google_places_collector.py"
    echo ""
    echo "3. PIPELINE COMPLETO - Coleta + Processamento:"
    echo "   python complete_pipeline_demo.py -s celulares_acessorios -m 15"
    echo ""
    echo "4. VALIDAÇÃO - Apenas testar configuração:"
    echo "   python run_gdr.py --validate-only"
    echo ""
}

# Run interactive demo selection
run_interactive_demo() {
    echo ""
    echo "🤖 EXECUÇÃO INTERATIVA"
    echo "======================"
    echo ""
    echo "Escolha uma opção:"
    echo "1) Validar configuração apenas"
    echo "2) Processar planilha existente (10 leads)"
    echo "3) Pipeline completo: Coleta + Processamento"
    echo "4) Coletar leads do Google Places apenas"
    echo "5) Sair"
    echo ""
    
    read -p "Digite sua escolha (1-5): " choice
    
    case $choice in
        1)
            print_info "Executando validação..."
            $PYTHON_CMD run_gdr.py --validate-only
            ;;
        2)
            print_info "Processando planilha existente..."
            if [ -f "leads.xlsx" ]; then
                $PYTHON_CMD run_gdr.py -i leads.xlsx -m 10
            else
                print_error "Arquivo leads.xlsx não encontrado"
                print_info "Execute a opção 4 primeiro para coletar leads"
            fi
            ;;
        3)
            print_info "Executando pipeline completo..."
            $PYTHON_CMD complete_pipeline_demo.py -s celulares_acessorios -m 15
            ;;
        4)
            print_info "Coletando leads do Google Places..."
            $PYTHON_CMD google_places_collector.py
            ;;
        5)
            print_info "Saindo..."
            exit 0
            ;;
        *)
            print_error "Opção inválida"
            run_interactive_demo
            ;;
    esac
}

# Main execution
main() {
    echo ""
    print_info "Iniciando setup do GDR Framework..."
    echo ""
    
    # Setup steps
    check_python
    setup_venv
    install_dependencies
    check_env
    setup_directories
    
    echo ""
    print_status "Setup concluído com sucesso!"
    
    # Show available options
    show_demos
    
    # Ask if user wants to run interactive demo
    echo ""
    read -p "Deseja executar uma demo agora? (y/N): " run_demo
    
    if [[ $run_demo =~ ^[Yy]$ ]]; then
        run_interactive_demo
    else
        echo ""
        print_info "Setup concluído. Use os comandos acima para executar as demos."
        echo ""
        print_info "Para ativar o ambiente virtual manualmente:"
        echo "source venv/bin/activate  # Linux/Mac"
        echo "venv\\Scripts\\activate     # Windows"
        echo ""
    fi
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "GDR Framework Setup Script"
        echo ""
        echo "Uso:"
        echo "  ./setup_and_run.sh          # Setup interativo"
        echo "  ./setup_and_run.sh --demo1  # Validação apenas"
        echo "  ./setup_and_run.sh --demo2  # Processar planilha"
        echo "  ./setup_and_run.sh --demo3  # Pipeline completo"
        echo "  ./setup_and_run.sh --demo4  # Coletar Google Places"
        echo ""
        exit 0
        ;;
    --demo1)
        check_python
        setup_venv
        source venv/bin/activate 2>/dev/null || source venv/Scripts/activate
        $PYTHON_CMD run_gdr.py --validate-only
        ;;
    --demo2)
        check_python
        setup_venv
        source venv/bin/activate 2>/dev/null || source venv/Scripts/activate
        $PYTHON_CMD run_gdr.py -i leads.xlsx -m 10
        ;;
    --demo3)
        check_python
        setup_venv
        source venv/bin/activate 2>/dev/null || source venv/Scripts/activate
        $PYTHON_CMD complete_pipeline_demo.py -s celulares_acessorios -m 15
        ;;
    --demo4)
        check_python
        setup_venv
        source venv/bin/activate 2>/dev/null || source venv/Scripts/activate
        $PYTHON_CMD google_places_collector.py
        ;;
    *)
        main
        ;;
esac
