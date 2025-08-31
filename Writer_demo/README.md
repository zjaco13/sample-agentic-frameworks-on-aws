# AI Cover Letter Generator

A comprehensive AI-powered cover letter generation system built with Writer AI and AWS Bedrock Agent Core. This project provides both a command-line interface and a web-based Streamlit application for creating personalized, professional cover letters.

## 🚀 Features

- **AI-Powered Generation**: Uses Writer AI's Palmyra-X5 model for intelligent cover letter creation
- **Interactive Web Interface**: Streamlit-based UI for easy form filling and real-time generation
- **Command Line Interface**: Terminal-based interactive cover letter generator
- **AWS Bedrock Integration**: Deployed as a Bedrock Agent Core runtime for scalable cloud execution
- **Streaming Responses**: Real-time streaming of generated content with visual effects
- **Multiple Output Formats**: JSON data export and formatted text download
- **Tone Customization**: Professional, enthusiastic, or formal writing styles
- **Docker Support**: Containerized deployment for consistent environments

## 📁 Project Structure

```
.
├── writer_agent.py          # Main agent with interactive CLI
├── writer_agent_orig.py     # Original Writer AI implementation
├── streamlit_app.py         # Web interface application
├── requirements.txt         # Python dependencies
├── Dockerfile              # Container configuration
├── .bedrock_agentcore.yaml # AWS Bedrock Agent Core configuration
└── README.md               # This file
```

## 🛠️ Installation

### Prerequisites

- Python 3.9+
- Writer AI API key
- AWS credentials (for Bedrock deployment)
- Docker (optional, for containerized deployment)

### Local Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd writer-ai-cover-letter-generator
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv writer_demo
   source writer_demo/bin/activate  # On Windows: writer_demo\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables**
   ```bash
   export WRITER_API_KEY="your_writer_ai_api_key_here"
   ```

## 🎯 Usage

### Command Line Interface

Run the interactive CLI version:

```bash
python writer_agent_orig.py
```

Choose from:
- **Interactive Cover Letter Generator** - Prompts for your information
- **Demo with Sample Data** - Shows example generation

### Web Interface

Launch the Streamlit web application:

```bash
streamlit run streamlit_app.py
```

Then open your browser to `http://localhost:8501`

#### Web Interface Features:
- **📋 Form Fields**: Job title, company name, personal info, skills
- **🎨 Tone Selection**: Professional, enthusiastic, or formal
- **📊 JSON Export**: View and copy form data as JSON
- **🤖 AI Generation**: Stream cover letter generation in real-time
- **📥 Download**: Save generated cover letters as text files

### AWS Bedrock Deployment

The project is configured for AWS Bedrock Agent Core deployment:

```bash
# Deploy to AWS Bedrock
bedrock-agentcore deploy

# Invoke the deployed agent
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn "arn:aws:bedrock-agentcore:us-west-2:211395677819:runtime/writer_agent-CnQSKJ7d4G" \
  --qualifier "DEFAULT" \
  --payload '{"job_title": "Software Engineer", "company_name": "TechCorp", ...}'
```

## 📝 API Reference

### CoverLetterAgent Class

```python
from writer_agent import CoverLetterAgent

agent = CoverLetterAgent(api_key="your_api_key")

# Generate cover letter
cover_letter = agent.generate_cover_letter(
    job_title="Senior Software Engineer",
    company_name="TechCorp Inc.",
    applicant_name="John Doe",
    applicant_skills="Python, React, AWS, team leadership",
    job_description="Optional job posting details",
    company_info="Optional company background",
    tone="professional"  # or "enthusiastic", "formal"
)
```

### Required Parameters

- `job_title`: Position being applied for
- `company_name`: Target company name
- `applicant_name`: Full name of applicant
- `applicant_skills`: Key skills and experience

### Optional Parameters

- `job_description`: Job posting details for better matching
- `company_info`: Company background for personalization
- `tone`: Writing style (default: "professional")

## 🔧 Configuration

### Writer AI Setup

1. Get API key from [Writer.com](https://writer.com)
2. Set environment variable:
   ```bash
   export WRITER_API_KEY="your_api_key_here"
   ```

### AWS Configuration

The project uses AWS Bedrock Agent Core with the following configuration:

- **Region**: us-west-2
- **Agent ARN**: `arn:aws:bedrock-agentcore:us-west-2:211395677819:runtime/writer_agent-CnQSKJ7d4G`
- **Platform**: linux/arm64
- **Runtime**: Docker

## 🐳 Docker Deployment

Build and run the containerized version:

```bash
# Build the Docker image
docker build -t writer-agent .

# Run the container
docker run -e WRITER_API_KEY="your_api_key" -p 8501:8501 writer-agent
```

## 📊 Example Output

The generated cover letters include:

- **Professional formatting** with proper business letter structure
- **Personalized content** matching job requirements to applicant skills
- **Company-specific details** when provided
- **Strong opening and closing** statements
- **Tone-appropriate language** based on selection

### Sample JSON Input:
```json
{
  "job_title": "Senior Software Engineer",
  "company_name": "TechCorp Inc.",
  "applicant_name": "Alex Johnson",
  "applicant_skills": "5+ years Python development, React, AWS, team leadership",
  "job_description": "Looking for a senior engineer to lead backend team",
  "company_info": "Fast-growing fintech startup",
  "tone": "professional"
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Troubleshooting

### Common Issues

**Writer AI API Key Error**
```
❌ Writer AI API key not found
```
- Solution: Set the `WRITER_API_KEY` environment variable

**Streamlit Form Error**
```
st.download_button() can't be used in an st.form()
```
- Solution: This has been fixed in the current version using session state

**AWS Bedrock Connection Issues**
- Ensure AWS credentials are properly configured
- Verify the agent ARN is correct for your deployment

### Debug Mode

Enable debug output by setting:
```bash
export DEBUG=true
```

## 📞 Support

For issues and questions:
- Create an issue in the repository
- Check the troubleshooting section above
- Review the Writer AI documentation

---

**Built with ❤️ using Writer AI, Streamlit, and AWS Bedrock Agent Core**