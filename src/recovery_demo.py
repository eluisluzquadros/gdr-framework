#!/usr/bin/env python3
"""
GDR Recovery Demo
Demonstra sistema de persistência e recuperação à falhas
"""

import asyncio
import time
import signal
import sys
from pathlib import Path
from datetime import datetime

from gdr_mvp import GDRFramework, logger

class RecoveryDemo:
    """Demo do sistema de recovery"""
    
    def __init__(self):
        self.gdr = GDRFramework()
        self.interrupted = False
        
        # Setup signal handler para CTRL+C
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handler para interrupção do usuário"""
        logger.info("🛑 Interrupção detectada! Salvando estado...")
        self.interrupted = True
    
    async def demo_recovery_system(self, input_file: str = "leads.xlsx", max_leads: int = 30):
        """Demonstra sistema de recovery completo"""
        
        print("🚀 GDR RECOVERY SYSTEM DEMO")
        print("=" * 50)
        print("Este demo mostra como o sistema:")
        print("✅ Salva checkpoints automáticos")
        print("✅ Recupera processamento após falhas")
        print("✅ Mantém consistência de dados")
        print("✅ Evita reprocessamento desnecessário")
        print("=" * 50)
        
        # Carregar leads
        logger.info(f"📁 Carregando leads de {input_file}")
        all_leads = self.gdr.load_leads_from_excel(input_file)
        
        if not all_leads:
            logger.error("❌ Nenhum lead encontrado")
            return
        
        test_leads = all_leads[:max_leads]
        logger.info(f"📊 Processando {len(test_leads)} leads para demo")
        
        # Demonstrar diferentes cenários
        await self._demo_normal_processing(test_leads)
        await self._demo_interrupted_processing(test_leads)
        await self._demo_recovery_from_checkpoint(test_leads)
    
    async def _demo_normal_processing(self, leads):
        """Demo: Processamento normal"""
        print("\n🟢 CENÁRIO 1: Processamento Normal")
        print("-" * 30)
        
        try:
            start_time = time.time()
            
            results, token_usages = await self.gdr.process_leads_batch_with_recovery(
                leads[:10],  # Apenas 10 para ser rápido
                max_concurrent=3,
                checkpoint_interval=5
            )
            
            end_time = time.time()
            
            successful = len([r for r in results if r.get('processing_status') == 'success'])
            total_cost = sum(usage.cost_usd for usage in token_usages)
            
            print(f"✅ Processamento concluído em {end_time - start_time:.1f}s")
            print(f"📊 {successful}/{len(results)} leads processados com sucesso")
            print(f"💰 Custo: ${total_cost:.6f}")
            print(f"💾 Checkpoints salvos automaticamente")
            
        except Exception as e:
            print(f"❌ Erro: {e}")
    
    async def _demo_interrupted_processing(self, leads):
        """Demo: Processamento interrompido"""
        print("\n🟡 CENÁRIO 2: Simulação de Interrupção")
        print("-" * 30)
        print("Pressione CTRL+C durante o processamento para simular falha...")
        
        try:
            # Usar mais leads para ter tempo de interromper
            start_time = time.time()
            
            # Processar com intervalos maiores para dar tempo de interromper
            results, token_usages = await self.gdr.process_leads_batch_with_recovery(
                leads[:20],
                max_concurrent=1,  # Mais lento para dar tempo de interromper
                checkpoint_interval=3
            )
            
            end_time = time.time()
            print(f"✅ Processamento concluído sem interrupção em {end_time - start_time:.1f}s")
            
        except KeyboardInterrupt:
            print(f"🛑 Processamento interrompido pelo usuário")
            print(f"💾 Estado salvo em checkpoints para recuperação")
        except Exception as e:
            print(f"❌ Erro simulado: {e}")
            print(f"💾 Estado preservado para recovery")
    
    async def _demo_recovery_from_checkpoint(self, leads):
        """Demo: Recuperação a partir de checkpoint"""
        print("\n🔄 CENÁRIO 3: Recuperação de Checkpoint")
        print("-" * 30)
        
        # Verificar se existem checkpoints
        checkpoint_dir = Path("./gdr_state/checkpoints")
        
        if not checkpoint_dir.exists():
            print("ℹ️ Nenhum checkpoint encontrado para recovery")
            return
        
        checkpoint_files = list(checkpoint_dir.glob("checkpoint_*.pkl"))
        
        if not checkpoint_files:
            print("ℹ️ Nenhum checkpoint disponível")
            return
        
        print(f"📁 Encontrados {len(checkpoint_files)} checkpoints")
        
        # Listar checkpoints disponíveis
        for i, checkpoint_file in enumerate(checkpoint_files):
            mtime = datetime.fromtimestamp(checkpoint_file.stat().st_mtime)
            print(f"   {i+1}. {checkpoint_file.name} (modificado: {mtime.strftime('%H:%M:%S')})")
        
        print("\n🔄 Tentando recuperar do checkpoint mais recente...")
        
        try:
            # Simular recovery - executar novamente o mesmo batch
            results, token_usages = await self.gdr.process_leads_batch_with_recovery(
                leads[:20],  # Mesmo range que foi interrompido
                max_concurrent=3,
                checkpoint_interval=5
            )
            
            successful = len([r for r in results if r.get('processing_status') == 'success'])
            print(f"✅ Recovery concluído: {successful}/{len(results)} leads")
            print(f"💾 Dados recuperados e processamento continuado")
            
        except Exception as e:
            print(f"❌ Erro durante recovery: {e}")
    
    def show_state_directory(self):
        """Mostra estrutura do diretório de estado"""
        print("\n📂 ESTRUTURA DO SISTEMA DE PERSISTÊNCIA")
        print("-" * 30)
        
        state_dir = Path("./gdr_state")
        
        if not state_dir.exists():
            print("ℹ️ Diretório de estado não existe ainda")
            return
        
        for subdir in ['checkpoints', 'partial_results', 'locks']:
            subdir_path = state_dir / subdir
            if subdir_path.exists():
                files = list(subdir_path.glob("*"))
                print(f"📁 {subdir}/")
                if files:
                    for file in files[:5]:  # Mostrar apenas primeiros 5
                        size_kb = file.stat().st_size / 1024
                        mtime = datetime.fromtimestamp(file.stat().st_mtime)
                        print(f"   └─ {file.name} ({size_kb:.1f}KB, {mtime.strftime('%H:%M:%S')})")
                    if len(files) > 5:
                        print(f"   └─ ... e mais {len(files) - 5} arquivos")
                else:
                    print("   └─ (vazio)")
            else:
                print(f"📁 {subdir}/ (não existe)")
        
        print("\n💡 COMO FUNCIONA:")
        print("✅ checkpoints/     - Estado do processamento (a cada N leads)")
        print("✅ partial_results/ - Resultados individuais por lead")
        print("✅ locks/          - Previne processamento duplicado")
    
    def cleanup_demo_files(self):
        """Limpa arquivos de demo"""
        print("\n🧹 LIMPEZA DE ARQUIVOS DE DEMO")
        print("-" * 30)
        
        state_dir = Path("./gdr_state")
        
        if not state_dir.exists():
            print("ℹ️ Nenhum arquivo para limpar")
            return
        
        files_removed = 0
        for subdir in state_dir.rglob("*"):
            if subdir.is_file():
                subdir.unlink()
                files_removed += 1
        
        # Remover diretórios vazios
        try:
            state_dir.rmdir()
        except:
            pass
        
        print(f"✅ {files_removed} arquivos removidos")

async def main():
    """Função principal do demo"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description='GDR Recovery System Demo')
    parser.add_argument('--input', '-i', default='leads.xlsx', help='Arquivo de entrada')
    parser.add_argument('--max-leads', '-m', type=int, default=20, help='Máximo de leads')
    parser.add_argument('--show-state', action='store_true', help='Mostrar estado atual')
    parser.add_argument('--cleanup', action='store_true', help='Limpar arquivos de demo')
    
    args = parser.parse_args()
    
    demo = RecoveryDemo()
    
    if args.show_state:
        demo.show_state_directory()
        return
    
    if args.cleanup:
        demo.cleanup_demo_files()
        return
    
    try:
        await demo.demo_recovery_system(args.input, args.max_leads)
        
        print("\n" + "=" * 50)
        print("🎉 DEMO DE RECOVERY CONCLUÍDO!")
        print("=" * 50)
        print("📚 O que você aprendeu:")
        print("✅ Checkpoints automáticos preservam progresso")
        print("✅ Interrupções não causam perda de dados")
        print("✅ Recovery é transparente e automático")
        print("✅ Sistema evita reprocessamento desnecessário")
        print("✅ Paralelização é mantida com segurança")
        print("\n💡 Para ver arquivos de estado:")
        print("python recovery_demo.py --show-state")
        print("\n🧹 Para limpar arquivos de demo:")
        print("python recovery_demo.py --cleanup")
        
    except KeyboardInterrupt:
        print("\n🛑 Demo interrompido - estado preservado!")
    except Exception as e:
        print(f"\n❌ Erro no demo: {e}")

if __name__ == "__main__":
    asyncio.run(main())
