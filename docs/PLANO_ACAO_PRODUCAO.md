# Plano de Ação - GDR Framework em Produção
**Data**: 07 de Agosto de 2025 (Atualizado)  
**Objetivo**: Processar 10,000 leads com máxima eficiência
**Status**: Melhorias na Consolidação Implementadas (v2.1)

## 🎯 Objetivo Principal

Configurar e executar o GDR Framework para processar 10,000 leads de forma eficiente, confiável e econômica, mantendo a qualidade dos dados e minimizando custos.

## 📋 Fase 1: Preparação (1-2 dias)

### 1.1 Otimização de Configuração
- [ ] Aumentar concorrência de 3 para 10 leads simultâneos
- [ ] Configurar timeouts otimizados por scraper
- [ ] Ajustar rate limiting para evitar throttling
- [ ] Implementar retry logic mais agressivo
- [✅] **CONCLUÍDO**: Melhorar consolidação de telefones (agrega todos encontrados)
- [✅] **CONCLUÍDO**: Separar extração de WhatsApp de telefones gerais
- [✅] **CONCLUÍDO**: Corrigir processamento de URLs Instagram com UTM
- [✅] **CONCLUÍDO**: Prevenir criação de URLs falsas

### 1.2 Infraestrutura
- [ ] Provisionar servidor dedicado (mínimo 8GB RAM, 4 cores)
- [ ] Configurar monitoramento de recursos (CPU, RAM, Network)
- [ ] Setup de logs centralizados
- [ ] Configurar backups automáticos

### 1.3 Validação de APIs
- [ ] Verificar limites de rate das APIs
- [ ] Confirmar custos estimados com providers
- [ ] Obter API keys de produção
- [ ] Configurar billing alerts

## 📊 Fase 2: Teste de Carga (1 dia)

### 2.1 Teste com 100 Leads
```bash
python src/run_gdr.py --max-leads 100 --concurrent 10 --yes
```
- [ ] Validar performance com concorrência aumentada
- [ ] Monitorar uso de memória e CPU
- [ ] Verificar taxa de erros
- [ ] Calcular custo real

### 2.2 Teste com 500 Leads
```bash
python src/run_gdr.py --max-leads 500 --concurrent 15 --yes
```
- [ ] Validar estabilidade em execução prolongada
- [ ] Testar sistema de checkpoint/recovery
- [ ] Identificar gargalos
- [ ] Ajustar configurações

## 🚀 Fase 3: Execução em Produção (3-5 dias)

### 3.1 Estratégia de Execução

**Opção A: Processamento Completo**
- Processar todos 10,000 leads com todos os scrapers
- Tempo estimado: 28-40 horas
- Custo estimado: $58-70 USD

**Opção B: Processamento em Fases**
1. **Fase 1**: Dados básicos (Google + Website)
   - Tempo: 10-15 horas
   - Custo: ~$25 USD
   
2. **Fase 2**: Redes sociais para leads de alta prioridade
   - Tempo: 15-20 horas
   - Custo: ~$35 USD

### 3.2 Comandos de Execução

**Processamento em Lotes de 1000**
```bash
# Lote 1
python src/run_gdr.py --input data/leads_1000_batch1.xlsx --concurrent 10 --yes

# Lote 2 
python src/run_gdr.py --input data/leads_1000_batch2.xlsx --concurrent 10 --yes

# ... até Lote 10
```

**Processamento Contínuo com Checkpoints**
```bash
# Execução principal com recovery automático
python src/run_gdr.py --max-leads 10000 --concurrent 10 --checkpoint-interval 100 --yes
```

### 3.3 Monitoramento Durante Execução

**Script de Monitoramento** (executar em terminal separado)
```bash
# Monitor de progresso
watch -n 60 'tail -n 50 gdr_processing.log | grep "Processado"'

# Monitor de erros
tail -f gdr_processing.log | grep -E "ERROR|WARNING"

# Monitor de recursos
htop
```

## 📈 Fase 4: Otimizações em Tempo Real

### 4.1 Ajustes Dinâmicos
- [ ] Se taxa de erro > 5%, reduzir concorrência
- [ ] Se memória > 80%, fazer restart controlado
- [ ] Se API rate limit, ajustar delays
- [ ] Se custo > esperado, desabilitar scrapers menos importantes

### 4.2 Comandos de Emergência

**Pausar Processamento**
```bash
# Salva estado atual e para
Ctrl+C (checkpoint automático será salvo)
```

**Retomar Processamento**
```bash
# Retoma do último checkpoint
python src/run_gdr.py --resume --concurrent 10 --yes
```

**Modo Econômico** (sem redes sociais)
```bash
python src/run_gdr.py --fast-mode --concurrent 20 --yes
```

## 📊 Fase 5: Pós-Processamento (1 dia)

### 5.1 Validação de Dados
- [ ] Verificar completude dos dados
- [ ] Identificar leads sem enriquecimento
- [ ] Calcular estatísticas finais
- [ ] Gerar relatório executivo

### 5.2 Reprocessamento Seletivo
```python
# Script para reprocessar falhas
import pandas as pd
df = pd.read_excel('outputs/gdr_results_final.xlsx')
failed = df[df['processing_status'] != 'success']
failed.to_excel('leads_reprocess.xlsx')
```

### 5.3 Entrega Final
- [ ] Consolidar todos os resultados
- [ ] Gerar relatório final em Excel
- [ ] Backup de todos os dados
- [ ] Documentar lições aprendidas

## 💡 Scripts Úteis

## ✅ Melhorias Recentes Implementadas

### Consolidação de Dados Aprimorada
1. **Agregação de Telefones**: 
   - Antes: Retornava apenas o primeiro telefone encontrado
   - Agora: Agrega TODOS os telefones de todas as fontes em lista separada por vírgulas
   - Benefício: Maior valor para o cliente com múltiplos pontos de contato

2. **Separação WhatsApp**:
   - Campo dedicado `gdr_consolidated_whatsapp` para números WhatsApp
   - Extração de links wa.me e identificação de números móveis
   - Benefício: Facilita campanhas de WhatsApp marketing

3. **Validação de URLs**:
   - Instagram não cria mais URLs falsas baseadas em supossições
   - Processamento correto de URLs com parâmetros UTM
   - Benefício: Dados mais confiáveis e precisos

### Monitor de Custo em Tempo Real
```python
# cost_monitor.py
import pandas as pd
import glob

files = glob.glob('outputs/gdr_results_*.xlsx')
total_cost = 0
total_leads = 0

for file in files:
    df = pd.read_excel(file, sheet_name='Estatísticas')
    total_cost += df['total_cost_usd'].iloc[0]
    total_leads += df['total_leads_processed'].iloc[0]

print(f"Leads Processados: {total_leads}")
print(f"Custo Total: ${total_cost:.2f}")
print(f"Custo Médio: ${total_cost/total_leads:.4f}")
print(f"Projeção 10k leads: ${(total_cost/total_leads)*10000:.2f}")
```

### Consolidador de Resultados
```python
# consolidate_results.py
import pandas as pd
import glob

all_files = glob.glob('outputs/gdr_results_*.xlsx')
all_data = []

for file in all_files:
    df = pd.read_excel(file, sheet_name='Dados Completos')
    all_data.append(df)

final_df = pd.concat(all_data, ignore_index=True)
final_df.to_excel('outputs/GDR_10000_LEADS_FINAL.xlsx', index=False)
print(f"Total consolidado: {len(final_df)} leads")
```

## 🚨 Plano de Contingência

### Se o processamento falhar:
1. Sistema salvará checkpoint automaticamente
2. Verificar logs para identificar causa
3. Ajustar configuração se necessário
4. Retomar com comando `--resume`

### Se custos excederem orçamento:
1. Pausar imediatamente (Ctrl+C)
2. Ativar `--fast-mode` (sem redes sociais)
3. Processar apenas leads prioritários
4. Considerar processamento em fases

### Se APIs apresentarem limites:
1. Reduzir concorrência
2. Aumentar delays entre requisições
3. Distribuir processamento em múltiplos dias
4. Considerar múltiplas API keys

## 📝 Checklist Final Pré-Execução

- [ ] Backup do banco de dados atual
- [ ] Verificar espaço em disco (mínimo 10GB livres)
- [ ] Confirmar API keys válidas
- [ ] Testar conexão com todas as APIs
- [ ] Configurar monitoramento
- [ ] Preparar scripts de emergência
- [ ] Definir horário de início (preferencialmente noturno)
- [ ] Notificar equipe sobre processamento

## 🎯 Métricas de Sucesso

- ✅ Taxa de sucesso > 95%
- ✅ Custo total < $70 USD
- ✅ Tempo total < 48 horas
- ✅ Dados de contato para > 80% dos leads
- ✅ Zero perda de dados
- ✅ Sistema estável durante toda execução
- ✅ **NOVO**: Telefones consolidados com agregação completa
- ✅ **NOVO**: URLs Instagram validadas (sem dados falsos)
- 🔄 **EM PROGRESSO**: Taxa de detecção WhatsApp em melhoria

---

**Próximo Passo**: Iniciar Fase 1 - Preparação da infraestrutura e otimização de configurações.