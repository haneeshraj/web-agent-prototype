# Business Insights API

A powerful REST API for AI-powered business intelligence extraction from websites. Extract company information, business classifications, addresses, and brand images from any website URL.

## 🚀 Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file with your API keys:

```env
# At least one AI provider is required
OPENAI_API_KEY=your_openai_key_here
GOOGLE_API_KEY=your_google_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here

# Optional: For enhanced address search
SERPAPI_API_KEY=your_serpapi_key_here
```

### 3. Start the API Server

```bash
# Using the startup script (recommended)
python api/startup.py

# Or directly with uvicorn
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

### 4. Test the API

Visit the interactive documentation at: http://127.0.0.1:8000/docs

Or test with cURL or your frontend application.

## 📖 API Endpoints

### Base URL: `http://127.0.0.1:8000`

### `GET /`

Basic API information and available endpoints.

### `GET /health`

Check API health status and WebDriver readiness.

**Response:**

```json
{
  "status": "healthy",
  "webdriver_ready": true,
  "timestamp": "2024-08-22T10:30:45.123456"
}
```

### `POST /analyze`

Analyze a website and extract business intelligence.

**Request Body:**

```json
{
  "url": "https://www.spotcoffee.com",
  "include_screenshot": true
}
```

**Clean Response Structure:**

```json
{
  "success": true,
  "url": "https://www.spotcoffee.com",
  "processing_time_seconds": 45.2,
  "timestamp": "2025-08-22T17:30:45Z",
  "data": {
    "original_url": "https://www.spotcoffee.com/wp-content/uploads/spot-coffee-logo.png",

    "company_name": "SPoT Coffee",
    "company_name_confidence": 0.95,
    "company_name_reasoning": "Page title, header logo, footer copyright",

    "mcc_code": 5812,
    "mcc_name": "Eating Places and Restaurants",
    "mcc_confidence": 0.95,
    "mcc_reasoning": "Restaurant business model with food service",

    "brand_image_found": true,
    "brand_image_confidence": 0.95,
    "brand_image_reasoning": "Main logo in header with company name",

    "address": "225, Delaware Avenue, Buffalo, NY",
    "address_latitude": null,
    "address_longitude": null,
    "address_confidence": 0.95,
    "address_reasoning": "search_spotcoffee.com",

    "total_tokens_used": 21220,
    "processing_time_seconds": 45.2,
    "status": "success",
    "success": true
  },
  "error": null
}
```

### `GET /config`

Get current API configuration and model information.

## 🔧 Configuration

Edit `config.yaml` to customize:

```yaml
agent:
  classifier-agent:
    model: "gemini-2.0-flash"
    max_tokens: 8192
    temperature: 0.3

processing:
  website_delay_seconds: 50
  rate_limit_delay_seconds: 10

api:
  host: "127.0.0.1"
  port: 8000
  cors_origins: ["*"]
```

## � Integration Examples

### Next.js/React (TypeScript)

```typescript
// api/business-insights.ts
interface AnalysisRequest {
  url: string;
  include_screenshot?: boolean;
}

interface AnalysisResponse {
  success: boolean;
  url: string;
  processing_time_seconds: number;
  timestamp: string;
  data: {
    original_url: string;
    company_name: string;
    company_name_confidence: number;
    company_name_reasoning: string;
    mcc_code: number;
    mcc_name: string;
    mcc_confidence: number;
    mcc_reasoning: string;
    brand_image_found: boolean;
    brand_image_confidence: number;
    brand_image_reasoning: string;
    address: string;
    address_latitude: number | null;
    address_longitude: number | null;
    address_confidence: number;
    address_reasoning: string;
    total_tokens_used: number;
    processing_time_seconds: number;
    status: string;
    success: boolean;
  };
  error: string | null;
}

export async function analyzeWebsite(
  url: string,
  includeScreenshot: boolean = true
): Promise<AnalysisResponse> {
  const response = await fetch("http://127.0.0.1:8000/analyze", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      url,
      include_screenshot: includeScreenshot,
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function checkHealth() {
  const response = await fetch("http://127.0.0.1:8000/health");
  return response.json();
}
```

### React Component Example

```tsx
// components/WebsiteAnalyzer.tsx
import { useState } from "react";
import {
  analyzeWebsite,
  type AnalysisResponse,
} from "../api/business-insights";

export default function WebsiteAnalyzer() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResponse | null>(null);

  const handleAnalyze = async () => {
    if (!url) return;

    setLoading(true);
    try {
      const analysis = await analyzeWebsite(url);
      setResult(analysis);
    } catch (error) {
      console.error("Analysis failed:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6">
      <div className="mb-4">
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Enter website URL"
          className="w-full p-2 border rounded"
        />
        <button
          onClick={handleAnalyze}
          disabled={loading}
          className="mt-2 px-4 py-2 bg-blue-500 text-white rounded"
        >
          {loading ? "Analyzing..." : "Analyze Website"}
        </button>
      </div>

      {result && result.success && (
        <div className="bg-gray-100 p-4 rounded">
          <h3 className="font-bold">{result.data.company_name}</h3>
          <p>
            MCC: {result.data.mcc_code} - {result.data.mcc_name}
          </p>
          <p>Address: {result.data.address}</p>
          <p>Confidence: {result.data.company_name_confidence}</p>
          <p>Tokens Used: {result.data.total_tokens_used}</p>
        </div>
      )}
    </div>
  );
}
```

### JavaScript/Vanilla JS

```javascript
async function analyzeWebsite(url, includeScreenshot = true) {
  const response = await fetch("http://127.0.0.1:8000/analyze", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      url: url,
      include_screenshot: includeScreenshot,
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

// Usage
analyzeWebsite("https://www.example.com")
  .then((result) => {
    if (result.success) {
      console.log("Company:", result.data.company_name);
      console.log("MCC Code:", result.data.mcc_code);
      console.log("Address:", result.data.address);
    }
  })
  .catch((error) => console.error("Analysis failed:", error));
```

## 🌐 cURL Examples

### Health Check

```bash
curl -X GET "http://127.0.0.1:8000/health"
```

### Analyze Website

```bash
curl -X POST "http://127.0.0.1:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.spotcoffee.com",
    "include_screenshot": true
  }'
```

## 📊 What Gets Extracted

The API extracts focused business intelligence:

### ✅ **Essential Data Only:**

1. **Original URL** - Brand image source URL from website
2. **Company Information** - Name, confidence, reasoning
3. **MCC Classification** - Code, name, confidence, reasoning
4. **Brand Image Analysis** - Detection, confidence, reasoning
5. **Address Data** - Address, coordinates (when available), confidence, reasoning
6. **Performance Metrics** - Tokens used, processing time, status, success

### 🚫 **Removed Clutter:**

- No unnecessary file paths
- No verbose metadata
- No duplicate information
- Clean, focused response structure

## 🔒 Security Considerations

### For Production Use:

1. **CORS Configuration**: Update `cors_origins` in `config.yaml`
2. **API Authentication**: Add authentication middleware
3. **Rate Limiting**: Implement request rate limiting
4. **Input Validation**: Validate and sanitize URLs
5. **Environment Variables**: Secure API key storage

## 🛠️ Troubleshooting

### WebDriver Issues

- Ensure Google Chrome is installed
- Try clearing WebDriver cache: Delete `~/.wdm` folder
- Run with administrator privileges if needed

### API Startup Issues

```bash
# Check if all dependencies are installed
python api/startup.py

# Manual dependency check
pip install -r requirements.txt
```

### Performance Optimization

- Adjust `website_delay_seconds` and `rate_limit_delay_seconds` in config
- Use `include_screenshot: false` for faster processing
- Monitor token usage for cost optimization

## 📈 Monitoring & Logs

The API provides detailed logging and monitoring:

- Health check endpoint for uptime monitoring
- Token usage tracking for cost management
- Processing time metrics
- Error tracking and reporting

## 🆘 Support

- Check the [interactive API docs](http://127.0.0.1:8000/docs) for detailed endpoint information
- Use the health check endpoint to verify system status
- Review logs for debugging information
- Ensure all environment variables are properly set

## 📝 License

This project is licensed under the same terms as the main Business Insights project.
