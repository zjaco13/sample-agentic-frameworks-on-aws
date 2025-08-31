from writerai import Writer
import json
from typing import Dict, Optional
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app=BedrockAgentCoreApp()

class CoverLetterAgent:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Writer AI client for cover letter generation."""
        self.client = Writer(api_key=api_key) if api_key else Writer()
        self.model = "palmyra-x5"
    
    def generate_cover_letter(self, 
                            job_title: str,
                            company_name: str,
                            applicant_name: str,
                            applicant_skills: str,
                            job_description: str = "",
                            company_info: str = "",
                            tone: str = "professional") -> str:
        """
        Generate a personalized cover letter using Writer AI.
        
        Args:
            job_title: The position being applied for
            company_name: Name of the company
            applicant_name: Name of the job applicant
            applicant_skills: Key skills and experience of the applicant
            job_description: Optional job posting details
            company_info: Optional information about the company
            tone: Tone of the letter (professional, enthusiastic, formal)
        
        Returns:
            Generated cover letter as a string
        """
        
        prompt = self._build_prompt(
            job_title, company_name, applicant_name, 
            applicant_skills, job_description, company_info, tone
        )
        
        try:
            response = self.client.chat.chat(
                messages=[{"content": prompt, "role": "user"}],
                model=self.model
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating cover letter: {str(e)}"
    
    def _build_prompt(self, job_title: str, company_name: str, 
                     applicant_name: str, applicant_skills: str,
                     job_description: str, company_info: str, tone: str) -> str:
        """Build the prompt for the Writer AI model."""
        
        prompt = f"""Write a compelling cover letter for a job application with the following details:

Job Title: {job_title}
Company: {company_name}
Applicant Name: {applicant_name}
Key Skills/Experience: {applicant_skills}
Tone: {tone}"""

        if job_description:
            prompt += f"\n\nJob Description:\n{job_description}"
        
        if company_info:
            prompt += f"\n\nCompany Information:\n{company_info}"
        
        prompt += f"""

Please write a professional cover letter that:
1. Opens with a strong, engaging introduction
2. Highlights relevant skills and experience that match the job requirements
3. Shows knowledge of and enthusiasm for the company
4. Demonstrates value the applicant would bring to the role
5. Closes with a confident call to action
6. Maintains a {tone} tone throughout
7. Is approximately 3-4 paragraphs long
8. Includes proper business letter formatting

The letter should be personalized, specific, and compelling while avoiding generic phrases."""
        
        return prompt

def get_user_input():
    """Collect cover letter information from user input."""
    print("🚀 Welcome to the Cover Letter Generator!")
    print("=" * 50)
    print("Please provide the following information:\n")
    
    # Required fields
    job_title = input("📋 Job Title: ").strip()
    company_name = input("🏢 Company Name: ").strip()
    applicant_name = input("👤 Your Full Name: ").strip()
    
    print("\n💼 Tell me about your relevant skills and experience:")
    print("(e.g., '5+ years Python development, React, AWS, team leadership')")
    applicant_skills = input("🛠️  Skills & Experience: ").strip()
    
    # Optional fields
    print("\n📄 Optional Information (press Enter to skip):")
    job_description = input("📝 Job Description/Requirements: ").strip()
    company_info = input("🏛️  Company Information: ").strip()
    
    # Tone selection
    print("\n🎨 Choose the tone for your cover letter:")
    print("1. Professional (default)")
    print("2. Enthusiastic")
    print("3. Formal")
    
    tone_choice = input("Select tone (1-3, or press Enter for professional): ").strip()
    tone_map = {"1": "professional", "2": "enthusiastic", "3": "formal"}
    tone = tone_map.get(tone_choice, "professional")
    
    return {
        "job_title": job_title,
        "company_name": company_name,
        "applicant_name": applicant_name,
        "applicant_skills": applicant_skills,
        "job_description": job_description,
        "company_info": company_info,
        "tone": tone
    }

@app.entrypoint
def interactive_cover_letter_generator(payload):
    """Interactive cover letter generator that prompts user for input."""
    # Get user input
    #user_data = get_user_input()
    user_data=payload
    print(str(user_data))
    # Validate required fields
    required_fields = ["job_title", "company_name", "applicant_name", "applicant_skills"]
    missing_fields = [field for field in required_fields if not user_data[field]]
        
    if missing_fields:
        print(f"\n❌ Error: Please provide the following required fields: {', '.join(missing_fields)}")
        return
        
    # Initialize agent and generate cover letter
    print(f"\n🤖 Generating your cover letter with {user_data['tone']} tone...")
    print("=" * 60)
        
    agent = CoverLetterAgent()
    cover_letter = agent.generate_cover_letter(**user_data)
        
    print(cover_letter)
    print("\n" + "=" * 60)
    print("✅ Cover letter generated successfully!")
    print("\n💡 Tip: Review and customize the letter before sending!")
        
    return {"result": cover_letter}

def demo_cover_letter_agent():
    """Demonstrate the cover letter agent with sample data."""
    agent = CoverLetterAgent()
    
    # Sample job application data
    sample_data = {
        "job_title": "Senior Software Engineer",
        "company_name": "TechCorp Inc.",
        "applicant_name": "Alex Johnson",
        "applicant_skills": "5+ years Python development, React, AWS, team leadership, agile methodologies",
        "job_description": "Looking for a senior engineer to lead our backend team, work with Python/Django, and mentor junior developers.",
        "company_info": "TechCorp is a fast-growing fintech startup focused on democratizing financial services.",
        "tone": "professional"
    }
    
    print("Generating sample cover letter...")
    print("=" * 50)
    
    cover_letter = agent.generate_cover_letter(**sample_data)
    print(cover_letter)
    
    return cover_letter

if __name__ == "__main__":
    app.run()
    #interactive_cover_letter_generator()
    