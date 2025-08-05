# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GDR (Generative Development Representative) is an AI framework that automates SDR/BDR functions through multi-source lead collection, enrichment, and intelligent qualification using multi-LLM consensus. The framework processes lead data from Google Places, websites, social media, and search engines, then uses statistical analysis (Kappa scores) to validate data quality across multiple LLMs (OpenAI, Claude, Gemini, DeepSeek, ZhipuAI).

## Common Development Commands

### Running the Framework
```bash
# Quick test with 10 leads
python src/run_gdr.py -m 10

# Process specific input file
python src/run_gdr.py --input data/input/leads.xlsx --max-leads 50

# Run complete pipeline demo (collection + processing)
python src/complete_pipeline_demo.py

# Collect new leads from Google Places
python src/google_places_collector.py
```

### Testing and Development
```bash
# Run tests (when implemented)
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_collectors.py -v

# Run tests with coverage
python -m pytest --cov=src tests/

# Format code
black src/

# Lint code
flake8 src/

# Type checking
mypy src/
```

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Create and activate virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Setup environment variables
cp .env.example .env  # Then edit .env with your API keys
```

## Architecture Overview

### Core Components

1. **Main Framework** (`src/gdr_mvp.py`)
   - `GDRFramework`: Orchestrates the entire lead processing pipeline
   - `ProcessingState`: Manages checkpoint/recovery for batch processing
   - `PersistenceManager`: Handles state persistence and recovery
   - Implements concurrent processing with configurable batch sizes

2. **Data Collection Layer**
   - `GooglePlacesCollector`: Scrapes business data from Google Places API
   - `WebsiteScraper`: Extracts contact information from websites using BeautifulSoup
   - `GoogleSearchScraper`: Finds additional contact info via Google Custom Search API
   - Social media scrapers (Apify integration) for Instagram, Facebook, Linktree

3. **LLM Consensus System**
   - Multi-provider support: OpenAI, Claude, Gemini, DeepSeek, ZhipuAI
   - Implements consensus mechanism with statistical validation
   - Kappa score calculation for inter-rater reliability
   - Automatic retry and fallback mechanisms

4. **Data Models**
   - `LeadInput`: Input lead data structure
   - `LeadEnrichment`: Enriched lead information
   - `ConsensusResult`: Multi-LLM consensus output
   - `TokenUsage`: Cost tracking for API usage

### Key Design Patterns

- **Async/Await Pattern**: All scrapers and API calls use asyncio for concurrent processing
- **Checkpoint/Recovery**: Batch processing with automatic state persistence
- **Factory Pattern**: Dynamic scraper instantiation based on configuration
- **Strategy Pattern**: Different consensus strategies for LLM outputs
- **Circuit Breaker**: Rate limiting and error handling for external APIs

## Critical Implementation Details

### API Rate Limiting
The framework implements sophisticated rate limiting:
- Google Places: 10 QPS with exponential backoff
- OpenAI: Respects token limits with automatic chunking
- Custom rate limiters for each scraper with configurable delays

### Data Validation
Multi-layer validation approach:
1. Input validation: CNPJ format, required fields
2. Scraper validation: Contact info patterns (email, phone)
3. LLM validation: Cross-validation between multiple providers
4. Statistical validation: Kappa scores for consensus quality

### Error Handling
- Graceful degradation when scrapers fail
- Automatic retries with exponential backoff
- Detailed error logging with context
- Recovery from partial failures

### Cost Management
- Real-time token usage tracking
- Cost estimation before processing
- Per-lead and batch-level cost reporting
- Configurable limits to prevent runaway costs

## Environment Variables

Required API keys in `.env`:
```
# Google APIs
GOOGLE_MAPS_API_KEY=your_key
GOOGLE_CSE_API_KEY=your_key
GOOGLE_CSE_ID=your_id

# LLM APIs (at least one required)
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
GEMINI_API_KEY=your_key
DEEPSEEK_API_KEY=your_key
ZHIPUAI_API_KEY=your_key

# Optional scrapers
APIFY_API_KEY=your_key
```

## Data Flow

1. **Input**: Excel file with company data (CNPJ, name, address)
2. **Collection**: Parallel scraping from multiple sources
3. **Enrichment**: Data consolidation and validation
4. **Consensus**: Multi-LLM analysis with statistical validation
5. **Output**: Excel report with enriched data, Kappa scores, and cost analysis

## Performance Considerations

- Concurrent processing: Default 3-5 concurrent leads
- Memory usage: ~100MB base + 50MB per 100 leads
- Processing speed: ~2-5 seconds per lead (depends on scrapers)
- Cost: ~$0.001-0.005 per lead (varies by LLM usage)

## Debugging Tips

- Enable debug logging: `logging.basicConfig(level=logging.DEBUG)`
- Check `gdr_processing.log` for detailed execution traces
- Use checkpoint files in `gdr_state/checkpoints/` for recovery
- Monitor token usage in real-time through console output

## Future Development Areas

The codebase is structured to support:
- Additional scraper integrations
- New LLM providers
- Computer vision for Street View analysis
- Real-time processing API
- Web dashboard interface
- Advanced geographic analysis features