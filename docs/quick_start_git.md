# 🚀 Como Criar o Repositório Git do GDR

## ⚡ Método Rápido (Recomendado)

### **1. Baixar e Executar Script Automático**
```bash
# Salvar o script de criação automática
# (copiar conteúdo de create_gdr_repository.sh)

chmod +x create_gdr_repository.sh
./create_gdr_repository.sh
```

### **2. Copiar Arquivos do GDR**
```bash
# Após o script criar a estrutura, copiar seus arquivos:
cd gdr-framework  # ou nome que você escolheu

# Código principal
cp /caminho/dos/seus/arquivos/gdr_mvp.py src/
cp /caminho/dos/seus/arquivos/run_gdr.py src/
cp /caminho/dos/seus/arquivos/google_places_collector.py src/
cp /caminho/dos/seus/arquivos/complete_pipeline_demo.py src/
cp /caminho/dos/seus/arquivos/recovery_demo.py src/

# Dados
cp /caminho/dos/seus/arquivos/leads.xlsx data/input/

# Configuração (suas APIs reais)
cp /caminho/dos/seus/arquivos/.env .

# Documentação
cp /caminho/dos/seus/arquivos/PRD.md docs/
cp /caminho/dos/seus/arquivos/README_MVP.md docs/
cp /caminho/dos/seus/arquivos/metadata_esperado_etapa1.txt docs/
```

### **3. Fazer Commit dos Arquivos**
```bash
git add .
git commit -m "feat: Adiciona código fonte completo do GDR

- Framework principal (gdr_mvp.py)
- Scripts de execução e demos
- 1000 leads reais para teste
- Documentação técnica completa
- Configuração de APIs"
```

### **4. Criar Repositório no GitHub**
1. Vá para https://github.com/new
2. Nome: `gdr-framework`
3. Descrição: `🤖 GDR Framework - Generative Development Representative`
4. ❌ **NÃO** inicializar com README
5. Clique "Create repository"

### **5. Conectar e Fazer Push**
```bash
git remote add origin https://github.com/SEU_USUARIO/gdr-framework.git
git branch -M main
git push -u origin main
```

---

## 🔧 Método Manual (Passo a Passo)

### **1. Criar Estrutura de Diretórios**
```bash
mkdir gdr-framework
cd gdr-framework

# Criar estrutura
mkdir -p {src,tests,docs,data/{input,samples},examples/{basic,advanced}}
mkdir -p {scripts/setup,.github/workflows}
```

### **2. Inicializar Git**
```bash
git init
```

### **3. Criar .gitignore**
```bash
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
.Python
venv/
.env

# GDR Specific
outputs/
logs/
gdr_state/
*.log

# OS
.DS_Store
Thumbs.db
EOF
```

### **4. Criar requirements.txt**
```bash
cat > requirements.txt << 'EOF'
pandas>=1.5.0
numpy>=1.24.0
openpyxl>=3.1.0
aiohttp>=3.8.0
python-dotenv>=1.0.0
beautifulsoup4>=4.11.0
openai>=1.0.0
anthropic>=0.7.0
google-generativeai>=0.3.0
scikit-learn>=1.3.0
pytest>=7.4.0
EOF
```

### **5. Criar README.md**
```bash
cat > README.md << 'EOF'
# 🚀 GDR Framework

Framework de IA para automação de SDR/BDR.

## Quick Start
```bash
git clone https://github.com/SEU_USUARIO/gdr-framework.git
cd gdr-framework
pip install -r requirements.txt
python src/run_gdr.py -m 10
```
EOF
```

### **6. Copiar Arquivos do GDR**
```bash
# Mesma estrutura do método rápido
cp seus_arquivos/* nas_pastas_apropriadas/
```

### **7. Commit e Push**
```bash
git add .
git commit -m "🚀 Initial commit: GDR Framework"
git remote add origin https://github.com/SEU_USUARIO/gdr-framework.git
git push -u origin main
```

---

## 📁 Estrutura Final Esperada

```
gdr-framework/
├── src/
│   ├── gdr_mvp.py                 # ✅ Código principal
│   ├── run_gdr.py                 # ✅ Script de execução
│   ├── google_places_collector.py # ✅ Coletor Google Places
│   ├── complete_pipeline_demo.py  # ✅ Demo completa
│   └── recovery_demo.py           # ✅ Demo de recovery
├── data/
│   └── input/
│       └── leads.xlsx             # ✅ 1000 leads reais
├── docs/
│   ├── PRD.md                     # ✅ Documentação técnica
│   ├── README_MVP.md              # ✅ Guia do MVP
│   └── metadata_esperado_etapa1.txt # ✅ Especificação
├── .env                           # ✅ Suas APIs (não commitado)
├── .env.example                   # ✅ Exemplo público
├── requirements.txt               # ✅ Dependências
├── README.md                      # ✅ Documentação principal
└── .gitignore                     # ✅ Arquivos ignorados
```

---

## ✅ Checklist Final

### **Antes do Push:**
- [ ] Todos os arquivos .py estão em `src/`
- [ ] Arquivo `leads.xlsx` está em `data/input/`
- [ ] Arquivo `.env` configurado com suas APIs
- [ ] Arquivo `.env` está no `.gitignore` (segurança)
- [ ] README.md está completo e informativo

### **Após o Push:**
- [ ] Repositório aparece no GitHub
- [ ] README.md é exibido na página principal
- [ ] Não há arquivos sensíveis commitados
- [ ] CI/CD está funcionando (se configurado)

### **Teste de Funcionalidade:**
```bash
# Clonar em diretório temporário para testar
git clone https://github.com/SEU_USUARIO/gdr-framework.git /tmp/test-gdr
cd /tmp/test-gdr

# Configurar
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# (editar .env com APIs)

# Testar
python src/run_gdr.py --validate-only
python src/run_gdr.py -m 5
```

---

## 🔐 Segurança das APIs

### **NUNCA commitar:**
```bash
# Verificar que .env não vai para o Git
git status
# .env NÃO deve aparecer na lista

# Se aparecer, adicionar ao .gitignore:
echo ".env" >> .gitignore
git add .gitignore
git commit -m "fix: Adiciona .env ao gitignore"
```

### **Arquivo .env.example (público):**
```bash
OPENAI_API_KEY=your_openai_api_key
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
# ...exemplos vazios
```

### **Arquivo .env (privado):**
```bash
OPENAI_API_KEY=sk-proj-7q9sR5YBmpLwCC4dWKotlL6buonxbdOS36W_...
GOOGLE_MAPS_API_KEY=AIzaSyBMkdOiWIPVy0jPP4YeW3FLZBD4IsoIJ54
# ...suas chaves reais
```

---

## 🎉 Pronto!

Após seguir qualquer um dos métodos, você terá:

✅ **Repositório profissional** no GitHub  
✅ **Código organizado** e documentado  
✅ **APIs protegidas** adequadamente  
✅ **Estrutura escalável** para colaboração  
✅ **Pronto para demonstração** e produção  

**🌟 Compartilhe o link do seu repositório!**

**URL**: `https://github.com/SEU_USUARIO/gdr-framework`