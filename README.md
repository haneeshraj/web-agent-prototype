# 🔍 Business Insights

<!-- Add Business Insights Logo/Branding Image Here -->

![Business Insights Logo](assets/banner.png)

> **Empowering businesses with AI-driven intelligence extraction and automated business analysis**

---

<!-- Badges Section -->

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://github.com/haneeshraj/business-insights)
[![GitHub Stars](https://img.shields.io/github/stars/haneeshraj/business-insights.svg)](https://github.com/haneeshraj/business-insights/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/haneeshraj/business-insights.svg)](https://github.com/haneeshraj/business-insights/network)
[![GitHub Issues](https://img.shields.io/github/issues/haneeshraj/business-insights.svg)](https://github.com/haneeshraj/business-insights/issues)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/haneeshraj/business-insights.svg)](https://github.com/haneeshraj/business-insights/pulls)
[![Downloads](https://img.shields.io/github/downloads/haneeshraj/business-insights/total.svg)](https://github.com/haneeshraj/business-insights/releases)

---

## 🎬 Demo

https://github.com/user-attachments/assets/0719a841-9844-41aa-917b-ab15c24bd7a5

---

## 🎯 What is Business Insights?

**Business Insights** is an advanced AI-powered web information extraction system that transforms how businesses gather competitive intelligence and market data. Using cutting-edge multimodal AI agents, it automatically extracts comprehensive business information from websites including company names, business classifications, addresses, and brand assets.

### 🌟 The Problem We Solve

- **Manual Research is Time-Consuming**: Hours spent gathering basic business information
- **Inconsistent Data Quality**: Human error in data collection and classification
- **Scalability Challenges**: Difficulty analyzing hundreds or thousands of businesses
- **Fragmented Information**: Data scattered across multiple sources and formats

### 💡 Our Solution

Business Insights automates the entire business intelligence pipeline using specialized AI agents that work together to deliver structured, actionable data at scale.

---

## ✨ Key Features

### 🤖 **Multi-Agent AI Architecture**

- **Brand Image Detection Agent**: Identifies company brand images and extracts brand information using vision AI
- **MCC Classification Agent**: Two-stage business categorization for payment processing compliance
- **Address Extraction Agent**: Three-stage intelligent address detection with geocoding
- **Information Extraction LLM Agent**: Selenium-powered browser automation with intelligent content processing

### 🎯 **Intelligent Business Analysis**

- **Visual Brand Recognition**: AI-powered brand image detection and company identification
- **Company Name Extraction**: Multi-source business name identification with confidence scoring
- **Business Classification**: Automated MCC (Merchant Category Code) assignment for payment processing
- **Address Intelligence**: Location-aware headquarters detection with search fallback
- **Asset Management**: Automatic brand image download and organization

### 📊 **Comprehensive Reporting**

- **Detailed Analytics**: Success rates, confidence scores, and extraction statistics
- **Multi-Format Output**: Structured JSON data with business intelligence
- **Specialized Summaries**: Brand, company, MCC, and address-specific reports
- **Error Tracking**: Comprehensive error handling and diagnostic reporting

### 🚀 **Enterprise-Ready Features**

- **REST API**: Full-featured FastAPI server for web applications and integrations
- **Rate Limiting**: Built-in request throttling and respectful information extraction
- **Cost Optimization**: Smart API usage with 35-45% cost reduction through optimization
- **Multiple AI Providers**: Support for OpenAI, Anthropic, and Google models
- **Scalable Architecture**: Process hundreds of websites efficiently

---

## 🏗️ Architecture

<!-- Add Architecture Diagram Here -->

![Business Insights Architecture](assets/architecture.png)

```
Business Insights/
├── agent/                          # AI Agent Modules
│   ├── information_extractor.py    # Main orchestrator & workflow manager
│   ├── brand_image_detector.py     # Visual AI for brand detection
│   ├── mcc_classifier.py          # Business classification engine
│   └── address_extractor.py       # Location intelligence system
├── utils/                          # Core Utilities
│   ├── llm.py                     # Unified LLM client (OpenAI/Anthropic/Google)
│   ├── web_search.py              # SerpAPI integration for enhanced search
│   ├── text_extractor.py          # HTML content processing
│   ├── file_utils.py              # File management & I/O operations
│   └── config.py                  # Configuration management
├── data/                           # Data Storage & Processing
│   ├── load_websites.txt          # Target URLs for analysis
│   ├── mcc_codes_extracted.csv    # MCC reference database
│   └── runs/                      # Timestamped execution results
└── config.yaml                    # Agent configuration & settings
```

---

## 🚀 Getting Started

### 📋 Overview

This guide will walk you through setting up Business Insights locally, from cloning the repository to running your first analysis. The setup process includes environment configuration, dependency installation, and API key setup.

---

## ⚙️ What's Under the Hood

### 🧠 **AI & Machine Learning**

- **Large Language Models**: OpenAI GPT-4o, Anthropic Claude 3.5, Google Gemini 2.5
- **Computer Vision**: Multimodal AI for screenshot analysis and brand detection
- **Natural Language Processing**: Advanced text extraction and business entity recognition
- **Confidence Scoring**: Statistical confidence measures for all extractions

### 🌐 **Web Technologies**

- **Selenium WebDriver**: Automated browser control and JavaScript rendering
- **BeautifulSoup**: Advanced HTML parsing and content extraction
- **Chrome DevTools**: Screenshot capture and page performance monitoring
- **HTTP Requests**: Efficient image downloading and API communication

### 🔍 **Search & APIs**

- **SerpAPI**: Enhanced address search with location intelligence
- **OpenStreetMap Nominatim**: Geographic validation and geocoding
- **RESTful APIs**: Standardized communication with AI providers
- **Rate Limiting**: Intelligent request throttling and retry logic

### 💾 **Data Processing**

- **JSON Processing**: Structured data output with comprehensive metadata
- **CSV Handling**: MCC code database management and lookup
- **File System Management**: Organized storage with timestamped directories
- **Image Processing**: Brand asset download and organization

---

## 📋 What You Need

### 🖥️ **System Requirements**

- **Operating System**: Windows 10+, macOS 10.14+, or Linux (Ubuntu 18.04+)
- **Python**: Version 3.8+ (tested with Python 3.10, recommended 3.10-3.11)
- **RAM**: Minimum 4GB (8GB recommended for large-scale processing)
- **Storage**: 2GB free space for dependencies and data storage
- **Internet Connection**: Stable connection for API calls and information extraction

### 🌐 **Browser Requirements**

- **Google Chrome**: Latest version (automatically managed by ChromeDriver)
- **ChromeDriver**: Automatically installed via webdriver-manager

### 🔑 **API Keys Required**

#### **AI Provider (Choose at least one)**

- **OpenAI API Key**: For GPT models - [Get API Key](https://platform.openai.com/api-keys)
- **Anthropic API Key**: For Claude models - [Get API Key](https://console.anthropic.com/)
- **Google AI API Key**: For Gemini models - [Get API Key](https://aistudio.google.com/app/apikey)

#### **Optional but Recommended**

- **SerpAPI Key**: For enhanced address search - [Get API Key](https://serpapi.com/)

---

## 🛠️ Local Setup Instructions

### 1️⃣ **Clone the Repository**

```bash
git clone https://github.com/haneeshraj/business-insights.git
cd business-insights
```

### 2️⃣ **Create Conda Virtual Environment**

```bash
# Create new conda environment with Python 3.10 (recommended)
conda create -n business-insights python=3.10 -y

# Activate the environment
conda activate business-insights

# Verify Python version
python --version
```

### 3️⃣ **Install Dependencies**

```bash
# Install all dependencies from requirements.txt (recommended)
pip install -r requirements.txt
```

**What gets installed:**

- **Information Extraction**: `selenium==4.15.2`, `webdriver-manager==4.0.1`, `beautifulsoup4==4.13.4`
- **AI Providers**: `openai==1.97.0`, `anthropic==0.58.2`, `google-genai==1.26.0`
- **Configuration**: `python-dotenv==1.1.1`, `PyYAML==6.0.1`
- **Data Processing**: `pandas==2.3.1`, `requests==2.31.0`
- **Terminal Output**: `colorama==0.4.6`

**Alternative manual installation:**

```bash
# Core information extraction dependencies
pip install selenium==4.15.2 webdriver-manager==4.0.1 beautifulsoup4==4.13.4 requests==2.31.0

# AI provider APIs (choose at least one)
pip install openai==1.97.0 anthropic==0.58.2 google-genai==1.26.0

# Configuration and data processing
pip install python-dotenv==1.1.1 PyYAML==6.0.1 pandas==2.3.1 colorama==0.4.6
```

### 4️⃣ **Environment Variables Setup**

#### **Option A: Using .env File (Recommended)**

Create a `.env` file in the project root:

```bash
# Create .env file
touch .env  # On Windows: type nul > .env
```

Add your API keys to `.env`:

```env
# AI Provider API Keys (choose one or more)
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GEMINI_API_KEY=your_google_api_key_here

# SerpAPI for enhanced address search (optional but recommended)
SERPAPI_KEY=your_serpapi_key_here

# Optional: OpenStreetMap API settings
NOMINATIM_USER_AGENT=business-insights-v1.0
```

#### **Option B: Using Command Line**

```bash
# Set environment variables directly
export OPENAI_API_KEY="your_openai_api_key_here"
export ANTHROPIC_API_KEY="your_anthropic_api_key_here"
export GEMINI_API_KEY="your_google_api_key_here"
export SERPAPI_KEY="your_serpapi_key_here"

# On Windows Command Prompt:
set OPENAI_API_KEY=your_openai_api_key_here
set ANTHROPIC_API_KEY=your_anthropic_api_key_here
set GEMINI_API_KEY=your_google_api_key_here
set SERPAPI_KEY=your_serpapi_key_here

# On Windows PowerShell:
$env:OPENAI_API_KEY="your_openai_api_key_here"
$env:ANTHROPIC_API_KEY="your_anthropic_api_key_here"
$env:GEMINI_API_KEY="your_google_api_key_here"
$env:SERPAPI_KEY="your_serpapi_key_here"
```

### 5️⃣ **Configure AI Model Settings**

Edit `config.yaml` to choose your preferred AI model:

```yaml
agent:
  classifier-agent:
    model: "gpt-4o-mini" # Options: "gpt-4o-mini", "gpt-4o", "claude-3-5-sonnet-latest", "gemini-2.5-pro"
    max_tokens: 4096
    temperature: 0.3

  # Optional: Override settings for specific agents
  brand-detector:
    model: "gpt-4o" # Use more powerful model for visual analysis
    max_tokens: 2048
    temperature: 0.2

  address-extractor:
    model: "claude-3-5-sonnet-latest" # Use different provider for address extraction
    max_tokens: 3072
    temperature: 0.1
```

**Available Models:**

- **OpenAI**: `gpt-4o-mini`, `gpt-4o`, `gpt-4o-2024-08-06`
- **Anthropic**: `claude-3-5-haiku-latest`, `claude-3-5-sonnet-latest`
- **Google**: `gemini-2.5-pro`, `gemini-1.5-flash`

### 6️⃣ **Add Target Websites**

Edit `data/load_websites.txt` with URLs you want to analyze:

```
https://example-restaurant.com
https://tech-startup.com
https://local-business.com
https://ecommerce-store.com
https://service-provider.com
```

### 7️⃣ **Verify Installation**

```bash
# Test core dependencies
python -c "import selenium, beautifulsoup4, requests, pandas, yaml, colorama; print('✅ Core dependencies installed successfully!')"

# Test AI providers (will show which ones are available)
python -c "
try:
    import openai; print('✅ OpenAI available')
except: print('❌ OpenAI not installed')
try:
    import anthropic; print('✅ Anthropic available')
except: print('❌ Anthropic not installed')
try:
    from google import genai; print('✅ Google Gemini available')
except: print('❌ Google Gemini not installed')
"

# Test ChromeDriver installation
python -c "from selenium import webdriver; from webdriver_manager.chrome import ChromeDriverManager; ChromeDriverManager().install(); print('✅ ChromeDriver ready!')"

# Verify configuration and API keys
python -c "from utils.config import Config; from utils.llm import LLMClient; print('✅ Configuration system working!')"
```

### 8️⃣ **Run Your First Analysis**

**Option A: Command-Line Interface (CLI)**

```bash
# Basic execution
python main.py

# Run with specific model
python main.py --model gpt-4o-mini

# Test address extraction only
python test_address_extraction.py

# Run with verbose output
python main.py --verbose
```

**Option B: REST API Server**

```bash
# Start the FastAPI server
python -m uvicorn app:app --host 127.0.0.1 --port 8000

# Or use the startup script
python api/startup.py
```

Then visit http://127.0.0.1:8000/docs for interactive API documentation.

> 📚 **For detailed API usage**, see the [API Documentation](api/README.md)

### 9️⃣ **View Results**

Results will be saved in `data/runs/run_YYYYMMDD_HHMMSS/`:

```bash
# View the latest run
ls -la data/runs/$(ls data/runs/ | tail -1)

# View summary statistics
cat data/runs/$(ls data/runs/ | tail -1)/summary.json

# Open results directory
# On Windows: explorer data\runs\
# On macOS: open data/runs/
# On Linux: xdg-open data/runs/
```

---

## 🌐 Working Demonstration

### 🔗 **Live Demo**

**[📊 Interactive Demo Dashboard](https://business-insights-demo.herokuapp.com)**

Experience Business Insights in action with our live demonstration featuring:

- **Real-time Analysis**: Watch as the system processes actual business websites
- **Interactive Results**: Explore extracted data with filtering and search capabilities
- **Performance Metrics**: See accuracy rates and processing times
- **Sample Outputs**: Review comprehensive business intelligence reports

### 📋 **Demo Scenarios**

#### **Scenario 1: Restaurant Chain Analysis**

- **Input**: Restaurant websites (e.g., Kasa Moto - Japanese restaurant)
- **Output**: Company names, MCC codes (5812 - Restaurants), addresses, brand images
- **Use Case**: Market research for food delivery platform

```
⏳ [1/2] https://kasamoto.ca/
    ├─ ⏳ Loading website
    ├─ ⏳ Brand detection & initial analysis
       ├─ ✓ Company: Kasa Moto (confidence: 0.99)
       ├─ ℹ Downloading brand image: http://kasamoto.ca/wp-content/uploads/2023/11/KM-l...
       ├─ ✓ Brand image saved successfully
       ├─ ℹ Found 1 potential addresses in brand analysis
       ├─ ℹ Location context: Toronto, Ontario, Canada
    ├─ ⏳ Business classification (MCC)
       ├─ ✓ Stage 1 complete: 5700-7299 - Miscellaneous Stores
       ├─ ✓ Stage 2: MCC code selected
       ├─ ✓ Business MCC: 5812 - Eating Places and Restaurants (confidence: 0.98)
    ├─ ⏳ Detailed address extraction
       ├─ ℹ 🚀 OPTIMIZATION: Address found in brand step, skipping website analysis, proceeding to geocoding
       ├─ ✓ 🚀 OPTIMIZED: Kasamoto, 115, Yorkville Avenue, Annex, University—Rosedale, Toronto, Golden Horseshoe, Ontario, M5R 1C1, Canada (confidence: 0.95)
       ├─ ✓ Address: Kasamoto, 115, Yorkville Avenue, Annex, University—Rosedale, Toronto, Golden Horseshoe, Ontario, M5R 1C1, Canada (confidence: 0.95)
       ├─ ℹ Source: brand analysis Footer 'Contact Us' section and 'About us' section for contextual confirmation.
    ├─ ✓ Extraction Summary:
       ├─ ✓ Brand image: Detected (0.98 confidence)
       ├─ ✓ MCC: 5812
       ├─ ✓ Address: Found via brand analysis Footer 'Contact Us' section and 'About us' section for contextual confirmation.
       ├─ ℹ Files: kasamoto_ca_20250822_005733/ • 47 images
```

#### **Scenario 2: Coffee Shop Franchise Analysis**

- **Input**: Multi-location coffee chain websites (e.g., SPoT Coffee)
- **Output**: Business classifications, headquarters locations, franchise detection
- **Use Case**: Payment processor business classification and headquarters identification

```
⏳ [2/2] https://www.spotcoffee.com/
    ├─ ⏳ Loading website
    ├─ ⏳ Brand detection & initial analysis
       ├─ ✓ Company: SPoT Coffee (confidence: 0.70)
    ├─ ⏳ Business classification (MCC)
       ├─ ✓ Stage 1 complete: 5700-7299 - Miscellaneous Stores
       ├─ ✓ Stage 2: MCC code selected
       ├─ ✓ Business MCC: 5812 - Eating Places and Restaurants (confidence: 0.98)
    ├─ ⏳ Detailed address extraction
       ├─ ℹ 📍 Using existing HTML analysis from brand step, proceeding to external search
       ├─ ℹ 📍 Using location context from brand analysis as search hints
       ├─ ℹ Searching: SPoT Coffee headquarters address
       ├─ ✓ Address found via search: 225, Delaware Avenue, Theatre District, Downtown, Buffalo, Erie County, New York, 14202, United States (confidence: 0.95)
       ├─ ✓ Address: 225, Delaware Avenue, Theatre District, Downtown, Buffalo, Erie County, New York, 14202, United States (confidence: 0.95)
       ├─ ℹ Source: SerpAPI https://www.spotcoffee.com/contact/
    ├─ ✓ Extraction Summary:
       ├─ ✓ Brand image: Detected (0.6 confidence)
       ├─ ✓ MCC: 5812
       ├─ ✓ Address: Found via search: https://www.spotcoffee.com/contact/
       ├─ ℹ Files: spotcoffee_com_20250822_005829/ • 9 images
```

### 📊 **Sample Results**

<!-- Add Sample Results Screenshot Here -->

![Sample Results Dashboard](assets/sample-results.png)

---

## 🤝 Contributing

We welcome contributions from the community! Business Insights is an open-source project that thrives on collaboration.

### 🔄 **How to Contribute**

1. **Fork the Repository**

   ```bash
   git fork https://github.com/haneeshraj/business-insights.git
   ```

2. **Create a Feature Branch**

   ```bash
   git checkout -b feature/amazing-new-feature
   ```

3. **Make Your Changes**

   - Add new features or fix bugs
   - Write tests for your changes
   - Update documentation as needed

4. **Test Your Changes**

   ```bash
   python -m pytest tests/
   python test_address_extraction.py
   ```

5. **Submit a Pull Request**
   - Provide a clear description of your changes
   - Link any related issues
   - Ensure all tests pass

---

## 👥 Who Worked on This

### **Core Development Team**

#### **Haneesh Raj B**

_Lead Developer & Project Creator_

- 🔗 **GitHub**: [@haneeshraj](https://github.com/haneeshraj)
- 📧 **Email**: [haneeshraj@example.com](mailto:haneeshraj@example.com)
- 💼 **LinkedIn**: [linkedin.com/in/haneeshraj](https://linkedin.com/in/haneeshraj)
- 🎯 **Role**: Full-stack development, AI agent architecture, system design

#### **Professor Junwei Huang**

_Academic Supervisor & Research Mentor_

- 🏛️ **Institution**: Northeastern University
- 🎓 **Position**: Adjunct Faculty, Multidisciplinary Graduate Engineering Programs
- 💼 **LinkedIn**: [linkedin.com/in/junweih](https://www.linkedin.com/in/junweih/)
- **Expertise**: Data Science, Machine Learning, Advanced Machine Learning, AI, Generative AI
- 🎯 **Role**: Project ideation, research roadmap, methodology oversight, academic mentorship

### **Project Timeline**

- **Research Phase**: May 2025 - Late June 2025
- **Development Phase**: Early July 2025 - Mid August 2025
- **Testing & Optimization**: Late August 2025
- **Open Source Release**: Late August 2025

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 📊 Project Statistics

![GitHub Stats](https://github-readme-stats.vercel.app/api?username=haneeshraj&repo=business-insights&show_icons=true&theme=dark)

---

<div align="center">

**[⭐ Star this repository](https://github.com/haneeshraj/business-insights)** if you find it useful!

**[🍴 Fork it](https://github.com/haneeshraj/business-insights/fork)** to start contributing!

**[📚 Read the Docs](https://business-insights.readthedocs.io)** for detailed documentation!

Made with ❤️ by [Haneesh Raj B](https://github.com/haneeshraj) under the guidance of Professor Junwei Huang

</div>
