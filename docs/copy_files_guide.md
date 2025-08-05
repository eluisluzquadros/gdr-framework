# 📁 Guia de Organização dos Arquivos GDR

## 🎯 Como Organizar os Arquivos no Git

### **Passo 1: Executar o Setup do Git**
```bash
# Baixar e executar o script de setup
chmod +x git_setup_complete.sh
./git_setup_complete.sh
```

### **Passo 2: Copiar Arquivos do GDR para as Pastas Corretas**

#### **📂 Código Principal → `src/`**
```bash
# Copiar arquivos principais do GDR
cp gdr_mvp.py src/
cp run_gdr.py src/
cp google_places_collector.py src/
cp complete_pipeline_demo.py src/
cp recovery_demo.py src/
```

#### **📋 Configuração → Raiz do projeto**
```bash
# Arquivos de configuração
cp requirements.txt .
cp setup_and_run.sh .

# Copiar .env com APIs (substituir o .env.example)
cp .env .env.example  # Backup das suas APIs
cp .env .  # Arquivo de trabalho
```

#### **📊 Dados → `data/`**
```bash
# Copiar dados de exemplo
cp leads.xlsx data/input/
cp *.xlsx data/samples/  # Outros exemplos se houver
```

#### **📚 Documentação → `docs/`**
```bash
# Copiar documentação técnica
cp PRD.md docs/
cp README_MVP.md docs/
cp MELHORIAS_IMPLEMENTADAS.md docs/
cp metadata_esperado_etapa1.txt docs/
cp metadata_esperado_etapa2.txt docs/
```

#### **🧪 Exemplos → `examples/`**
```bash
# Criar exemplos práticos
mkdir -p examples/basic examples/advanced

# Exemplo básico
cat > examples/basic/simple_processing.py << 'EOF'
#!/usr/bin/env python3
"""
Exemplo básico de processamento com GDR
"""
import sys
sys.path.append('../../src')

import asyncio
from gdr_mvp import GDRFramework

async def main():
    gdr = GDRFramework()
    
    # Carregar leads
    leads = gdr.load_leads_from_excel('../../data/input/leads.xlsx')
    
    # Processar apenas 5 para exemplo
    results, token_usages = await gdr.process_leads_batch(leads[:5])
    
    print(f"Processados: {len(results)} leads")
    print(f"Custo: ${sum(usage.cost_usd for usage in token_usages):.6f}")

if __name__ == "__main__":
    asyncio.run(main())
EOF

# Exemplo avançado
cat > examples/advanced/custom_configuration.py << 'EOF'
#!/usr/bin/env python3
"""
Exemplo avançado com configuração customizada
"""
import sys
sys.path.append('../../src')

import asyncio
from gdr_mvp import GDRFramework

async def main():
    # Configuração customizada
    gdr = GDRFramework()
    
    # Configurar paralelismo e checkpoints
    leads = gdr.load_leads_from_excel('../../data/input/leads.xlsx')
    
    results, token_usages = await gdr.process_leads_batch_with_recovery(
        leads[:20],
        max_concurrent=5,      # Mais paralelismo
        checkpoint_interval=5  # Checkpoints frequentes
    )
    
    # Análise avançada
    successful = [r for r in results if r.get('processing_status') == 'success']
    print(f"Taxa de sucesso: {len(successful)/len(results)*100:.1f}%")

if __name__ == "__main__":
    asyncio.run(main())
EOF
```

---

## 🔧 **Estrutura Final do Repositório**

```
gdr-framework/
├── src/                           # 🐍 Código Python
│   ├── gdr_mvp.py                # Framework principal
│   ├── run_gdr.py                # Script de execução
│   ├── google_places_collector.py # Coletor Google Places
│   ├── complete_pipeline_demo.py  # Demo pipeline completo
│   └── recovery_demo.py          # Demo de recovery
│
├── data/                         # 📊 Dados
│   ├── input/
│   │   └── leads.xlsx           # 1000 leads reais
│   └── samples/
│       └── exemplo_saida.xlsx   # Exemplo de resultado
│
├── docs/                        # 📚 Documentação
│   ├── PRD.md                   # Product Requirements
│   ├── README_MVP.md            # Documentação do MVP
│   ├── MELHORIAS_IMPLEMENTADAS.md # Changelog
│   ├── metadata_esperado_etapa1.txt
│   └── API_REFERENCE.md         # Referência da API
│
├── examples/                    # 📖 Exemplos
│   ├── basic/
│   │   └── simple_processing.py
│   └── advanced/
│       └── custom_configuration.py
│
├── tests/                       # 🧪 Testes
│   ├── __init__.py
│   ├── conftest.py
│   └── test_basic.py
│
├── scripts/                     # 🔧 Scripts
│   └── setup/
│       └── project_setup.py
│
├── .github/                     # ⚙️ CI/CD
│   └── workflows/
│       └── ci.yml
│
├── README.md                    # 📖 Documentação principal
├── requirements.txt             # 📦 Dependências
├── .env                        # 🔑 API Keys (não commitado)
├── .env.example                # 🔑 Exemplo de configuração
├── .gitignore                  # 🚫 Arquivos ignorados
├── LICENSE                     # 📄 Licença MIT
└── setup_and_run.sh           # 🚀 Setup automático
```

---

## 🚀 **Como Fazer o Push para GitHub**

### **1. Criar Repositório no GitHub**
1. Vá para [GitHub.com](https://github.com)
2. Clique em "New repository"
3. Nome: `gdr-framework`
4. Descrição: `🤖 GDR Framework - Generative Development Representative`
5. ✅ Público ou Privado (sua escolha)
6. ❌ **NÃO** inicializar com README
7. Clique "Create repository"

### **2. Conectar Local com GitHub**
```bash
# Adicionar remote origin
git remote add origin https://github.com/SEU_USUARIO/gdr-framework.git

# Verificar se foi adicionado
git remote -v

# Fazer primeiro push
git branch -M main
git push -u origin main
```

### **3. Verificar se Subiu Corretamente**
- Acesse: `https://github.com/SEU_USUARIO/gdr-framework`
- Deve mostrar todos os arquivos organizados
- README.md será exibido automaticamente
- CI/CD será executado automaticamente

---

## 🔒 **Proteger API Keys**

### **Arquivo .env (NÃO commitado):**
```bash
# Suas APIs reais (não vão para o Git)
OPENAI_API_KEY=sk-proj-7q9sR5YBmpLwCC4dWKotlL6buonxbdOS36W_...
GOOGLE_MAPS_API_KEY=AIzaSyBMkdOiWIPVy0jPP4YeW3FLZBD4IsoIJ54
# ... outras chaves
```

### **Arquivo .env.example (Commitado):**
```bash
# Exemplo público (vai para o Git)
OPENAI_API_KEY=your_openai_api_key
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
# ... exemplos
```

### **Garantir Segurança:**
```bash
# Verificar que .env está no .gitignore
grep ".env" .gitignore

# Nunca commitá-lo
git status  # .env não deve aparecer
```

---

## 🎯 **Comandos de Teste Após Setup**

### **1. Testar Estrutura:**
```bash
# Verificar arquivos
ls -la src/
ls -la data/input/
ls -la docs/

# Testar imports
cd src && python -c "from gdr_mvp import GDRFramework; print('✅ Import OK')"
```

### **2. Testar Funcionalidade:**
```bash
# Validar configuração
python src/run_gdr.py --validate-only

# Demo rápida
python src/run_gdr.py -m 5

# Exemplo básico
python examples/basic/simple_processing.py
```

### **3. Testar CI/CD:**
```bash
# Fazer pequena mudança e push
echo "# Test" >> README.md
git add .
git commit -m "test: CI/CD trigger"
git push

# Verificar Actions no GitHub
# https://github.com/SEU_USUARIO/gdr-framework/actions
```

---

## 📈 **Melhorias Futuras do Repositório**

### **1. Badges no README:**
```markdown
![Build Status](https://github.com/SEU_USUARIO/gdr-framework/workflows/CI/badge.svg)
![Coverage](https://codecov.io/gh/SEU_USUARIO/gdr-framework/branch/main/graph/badge.svg)
![Python](https://img.shields.io/badge/python-v3.8+-blue.svg)
```

### **2. GitHub Templates:**
```bash
# Issue template
mkdir -p .github/ISSUE_TEMPLATE

# Pull request template  
touch .github/pull_request_template.md
```

### **3. GitHub Pages (Documentação):**
```bash
# Configurar docs/ como GitHub Pages
# Settings → Pages → Source: docs/
```

---

## 🎉 **Resultado Final**

Após seguir este guia, você terá:

✅ **Repositório profissional** no GitHub  
✅ **Estrutura organizada** por tipo de arquivo  
✅ **CI/CD automático** com testes  
✅ **Documentação completa** e acessível  
✅ **API Keys protegidas** adequadamente  
✅ **Exemplos funcionais** para novos usuários  
✅ **Sistema de releases** configurado  

**🚀 Pronto para compartilhar e colaborar!**