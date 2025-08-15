# 🕷️ Web Agent Prototype - AI-Powered Business Intelligence Scraper

> **⚠️ PROTOTYPE PROJECT**: This is a proof-of-concept prototype for AI-powered web scraping and business intelligence extraction. The complete project repository will be released soon.

## 🎯 Overview

The Web Agent Prototype is an advanced AI-powered web scraping system that extracts comprehensive business intelligence from websites using multiple specialized AI agents. It combines traditional web scraping with modern multimodal AI capabilities to automatically identify businesses, classify their types, extract addresses, and download brand assets.

## ✨ Key Features

### 🤖 **Multi-Agent AI Architecture**

- **Logo Detection Agent**: Identifies company logos and extracts merchant names using vision-capable LLMs
- **MCC Classification Agent**: Two-stage business classification for payment processing (Merchant Category Codes)
- **Address Extraction Agent**: Three-stage address extraction with location-aware search capabilities
- **Web Scraping Engine**: Selenium-based automated browser with intelligent content extraction

### 🎯 **Intelligent Business Analysis**

- **Visual Logo Recognition**: AI-powered logo detection from screenshots
- **Merchant Name Extraction**: Multi-source business name identification
- **Business Classification**: Automated MCC code assignment with confidence scoring
- **Address Intelligence**: Location-aware headquarters detection with search fallback
- **Asset Management**: Automatic logo download and organization

### 📊 **Comprehensive Reporting**

- **Detailed Analytics**: Success rates, confidence scores, and extraction statistics
- **Multi-Format Output**: JSON data files with structured business intelligence
- **Specialized Summaries**: Logo, merchant, MCC, and address-specific reports
- **Error Tracking**: Comprehensive error handling and reporting

## 🏗️ Architecture

```
Web Agent Prototype/
├── agent/                     # AI Agent Modules
│   ├── scraper.py            # Main orchestrator
│   ├── logo_detector.py      # Logo detection & merchant extraction
│   ├── mcc_classifier.py     # Business classification (MCC codes)
│   └── address_extractor.py  # Address extraction & location intelligence
├── utils/                     # Utility Modules
│   ├── llm.py               # Unified LLM client (OpenAI, Anthropic, Google)
│   ├── web_search.py        # SerpAPI integration
│   ├── text_extractor.py    # HTML content processing
│   ├── file_utils.py        # File management utilities
│   └── config.py            # Configuration management
├── data/                     # Data Storage
│   ├── load_websites.txt    # Target URLs
│   ├── mcc_codes_extracted.csv # MCC reference data
│   └── runs/                # Timestamped execution results
└── config.yaml             # Agent configuration
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Chrome browser installed
- API keys for AI services

### Installation

1. **Clone the repository** (when released):

```bash
git clone <repository-url>
cd web-agent-prototype
```

2. **Create virtual environment**:

```bash
python -m venv web-agent
source web-agent/bin/activate  # On Windows: web-agent\Scripts\activate
```

3. **Install dependencies**:

```bash
pip install selenium webdriver-manager beautifulsoup4 requests
pip install openai anthropic google-generativeai  # AI providers
pip install pyyaml python-dotenv pandas
```

4. **Set up environment variables**:
   Create a `.env` file in the project root:

```env
# AI Provider API Keys (choose one or more)
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GEMINI_API_KEY=your_google_api_key_here

# SerpAPI for address search (optional but recommended)
SERPAPI_KEY=your_serpapi_key_here
```

5. **Configure the system**:
   Edit `config.yaml` to choose your preferred AI model:

```yaml
agent:
  classifier-agent:
    model: "gpt-4o-mini" # or "gemini-2.5-pro", "claude-3-5-sonnet-latest"
    max_tokens: 2048
    temperature: 0.3
```

6. **Add target websites**:
   Edit `data/load_websites.txt` with URLs to analyze:

```
https://example-restaurant.com
https://another-business.com
```

### Running the System

**Basic execution**:

```bash
python main.py
```

**Test address extraction**:

```bash
python test_address_extraction.py
```

## 📋 How It Works

### 1. **Website Scraping**

- Loads websites using Selenium WebDriver
- Takes screenshots after 5-second load time
- Extracts and cleans HTML content
- Catalogs all images on the page

### 2. **AI Analysis Pipeline**

#### **Logo Detection & Merchant Extraction**

- Analyzes screenshots using vision-capable LLMs
- Identifies company logos from visual elements
- Extracts business names from multiple sources (logos, titles, headers)
- Downloads identified logos locally

#### **MCC Classification (2-Stage)**

- **Stage 1**: Categorizes business into broad MCC categories
- **Stage 2**: Assigns specific MCC codes within categories
- Uses business-specific validation rules
- Provides confidence scoring and reasoning

#### **Address Extraction (3-Stage)**

- **Stage 0**: Extracts location context from website content
- **Stage 1**: Analyzes website HTML for business addresses
- **Stage 2**: Uses SerpAPI search with location-aware queries if needed
- Prioritizes original headquarters over expansion locations

### 3. **Data Organization**

Results are saved in timestamped directories:

```
data/runs/run_YYYYMMDD_HHMMSS/
├── domain1_timestamp/
│   ├── screenshot_domain1_timestamp.png
│   ├── page.html
│   ├── images.json
│   ├── logo_detection.json
│   ├── mcc_classification.json
│   └── address_extraction.json
├── download_images/
│   └── logo_files.png
├── summary.json
├── logo_summary.json
├── merchant_summary.json
├── mcc_summary.json
└── address_summary.json
```

## 🔧 Configuration

### AI Model Selection

The system supports multiple AI providers:

**OpenAI Models**:

- `gpt-4o-mini` (recommended for cost-effectiveness)
- `gpt-4o` (higher accuracy)
- `gpt-5-mini` (latest model)

**Anthropic Models**:

- `claude-3-5-haiku-latest`
- `claude-3-5-sonnet-latest`

**Google Models**:

- `gemini-2.5-pro`

### Address Search Configuration

For enhanced address extraction, configure SerpAPI:

1. Get API key from [SerpAPI](https://serpapi.com/)
2. Add `SERPAPI_KEY` to your `.env` file
3. System will automatically use search-based fallback

## 📊 Output Examples

### Business Intelligence Extracted

```json
{
  "merchant_name": "Acme Pizza Restaurant",
  "merchant_confidence": 0.95,
  "final_mcc_code": "5812",
  "mcc_confidence": 0.87,
  "business_type": "Eating Places and Restaurants",
  "final_address": "123 Main Street, New York, NY 10001",
  "address_confidence": 0.9,
  "address_source": "website_contact_page",
  "logo_detected": true,
  "downloaded_logo_path": "download_images/acme_20250814_123456.png"
}
```

### Summary Statistics

```json
{
  "total_websites": 50,
  "successful_scrapes": 48,
  "logos_detected": 42,
  "merchants_identified": 45,
  "mcc_classifications_successful": 47,
  "addresses_found": 38,
  "average_confidence_scores": {
    "merchant": 0.87,
    "mcc": 0.82,
    "address": 0.79
  }
}
```

## 🎯 Use Cases

### **Payment Processing**

- Automated MCC code assignment for merchant onboarding
- Business verification and classification
- Risk assessment based on business type

### **Business Intelligence**

- Competitive analysis and market research
- Brand monitoring and logo tracking
- Business directory creation

### **Due Diligence**

- Automated business verification
- Address validation for KYC processes
- Business type confirmation

## ⚠️ Important Notes

### **Rate Limiting**

- Built-in delays between requests (10 seconds)
- Retry logic for API rate limits
- Respectful scraping practices

### **Cost Considerations**

- LLM API costs vary by model and usage
- SerpAPI charges per search query
- Monitor usage and set appropriate limits

### **Legal Compliance**

- Respect website terms of service
- Consider robots.txt directives
- Implement appropriate delays
- Use for legitimate business purposes only

## 🐛 Troubleshooting

### Common Issues

**WebDriver Problems**:

```bash
# Clear WebDriver cache
rm -rf ~/.wdm/  # Linux/Mac
rmdir /s %USERPROFILE%\.wdm  # Windows
```

**API Key Issues**:

- Verify API keys in `.env` file
- Check API quotas and billing
- Ensure correct model names in config

**Address Extraction Issues**:

- Verify SERPAPI_KEY is set
- Check SerpAPI quota
- Review location context extraction

### Debug Mode

Add logging for detailed debugging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🔮 Future Enhancements

- Support for additional AI providers
- Enhanced multi-language support
- Real-time processing capabilities
- API endpoint for integration
- Advanced filtering and search capabilities

## 📝 License

This prototype is for demonstration and research purposes. Full license terms will be provided with the complete project release.

## 🤝 Contributing

This is a prototype project. Contribution guidelines and the full repository will be available soon.

## 📧 Contact

For questions about this prototype or the upcoming full release, please contact the development team.

---

**⚠️ Disclaimer**: This is a prototype project for demonstration purposes. The complete, production-ready version will be released in a separate repository with additional features, documentation, and support.
