import streamlit as st
import json
import boto3


client = boto3.client('bedrock-agentcore')

def extract_and_format_result(data):
    """Extract and format the result field from the JSON list"""
    try:
        # Join all strings in the list to form complete JSON
        full_json_string = ''.join(data)
        
        # Parse the JSON
        json_data = json.loads(full_json_string)
        
        # Extract the result
        result = json_data.get('result', 'No result found')
        
        # Format the result by converting escaped newlines to actual newlines
        #formatted_result = result.replace('\\n', '\n')
        formatted_result=result
        
        return formatted_result
    
    except Exception as e:
        return f"Error extracting result: {str(e)}"



def main():
    st.title("📝 Cover Letter Information Collector")
    st.markdown("Fill out the form below to generate cover letter data in JSON format")
    
    # Create form
    with st.form("cover_letter_form"):
        st.subheader("📋 Job Information")
        job_title = st.text_input("Job Title", placeholder="e.g., Senior Software Engineer")
        company_name = st.text_input("Company Name", placeholder="e.g., TechCorp Inc.")
        
        st.subheader("👤 Personal Information")
        applicant_name = st.text_input("Your Full Name", placeholder="e.g., John Doe")
        applicant_skills = st.text_area("Skills & Experience", 
                                       placeholder="e.g., 5+ years Python development, React, AWS, team leadership",
                                       height=100)
        
        st.subheader("📄 Additional Details (Optional)")
        job_description = st.text_area("Job Description/Requirements", 
                                     placeholder="Paste the job posting details here...",
                                     height=100)
        company_info = st.text_area("Company Information", 
                                  placeholder="What do you know about this company?",
                                  height=100)
        
        st.subheader("🎨 Tone Selection")
        tone = st.selectbox("Choose the tone for your cover letter:",
                           ["professional", "enthusiastic", "formal"])
        
        # Submit button
        submitted = st.form_submit_button("Generate Cover Letter", type="primary")
        
        if submitted:
            # Create the data dictionary
            data = {
                "job_title": job_title,
                "company_name": company_name,
                "applicant_name": applicant_name,
                "applicant_skills": applicant_skills,
                "job_description": job_description,
                "company_info": company_info,
                "tone": tone
            }
            
            # Display the JSON
            #st.subheader("📊 Generated JSON Data")
            #st.json(data)
            
            # Also display as formatted text for easy copying
            st.subheader("📋 Input to Agent")
            json_string = json.dumps(data, indent=2)
            st.code(json_string, language="json")
            
            # Validation check
            required_fields = ["job_title", "company_name", "applicant_name", "applicant_skills"]
            missing_fields = [field for field in required_fields if not data[field].strip()]
            
            response = client.invoke_agent_runtime(
                agentRuntimeArn='arn:aws:bedrock-agentcore:us-west-2:211395677819:runtime/writer_agent-CnQSKJ7d4G',
                qualifier='DEFAULT',
                payload=json_string
            )
            print("Got here")
            # Process and print the response
            if "text/event-stream" in response.get("contentType", ""):
  
                # Handle streaming response
                content = []
                for line in response["response"].iter_lines(chunk_size=10):
                    if line:
                        line = line.decode("utf-8")
                        if line.startswith("data: "):
                            line = line[6:]
                            print(line)
                            content.append(line)
                print("\nComplete response:", "\n".join(content))

            elif response.get("contentType") == "application/json":
                # Handle standard JSON response
                content = []
                for chunk in response.get("response", []):
                    content.append(chunk.decode('utf-8'))
                print("APP/JSON")
                print(json.loads(''.join(content)))
  
            else:
                # Print raw response for other content types
                print("RAW")
                print(response)

            #print("my output")
            #print(content)
            formatted_cover_letter = extract_and_format_result(content)
            #print(formatted_cover_letter)
            st.subheader("***Cover Letter***")
            st.write(formatted_cover_letter)
            if missing_fields:
                st.warning(f"⚠️ Missing required fields: {', '.join(missing_fields)}")
            else:
                st.success("✅ All required fields completed!")

if __name__ == "__main__":
    main()