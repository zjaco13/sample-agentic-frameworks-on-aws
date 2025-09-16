import json
from pr_handler import PullRequestHandler
from pr_agent import PRAgent
import logging
import json
import re


logger = logging.getLogger()
logger.setLevel(logging.INFO)

def extract_json(response_text: str):

    try:
        # Find JSON block between json and ````
        pattern = r'json\s*(\{.*?\})\s*'
        match = re.search(pattern, response_text, re.DOTALL)
        
        if match:
            json_str = match.group(1)
            return json.loads(json_str)
        else:
            return json.loads(response_text)
    except:
        return {
            'review_comments': 'Technical issues in reviewing the PR. Pl check logs for details.',
            'approve': False
        }

def lambda_handler(event, context):
    logger.info(f'input payload -->\n{event}')

    project = event['repository']['workspace']['slug']
    repository_name = event['repository']['name']
    pullrequest_id = event['pullrequest']['id']

    logger.info(f"Workspace: {project}")
    logger.info(f"Repository: {repository_name}")
    logger.info(f"PR ID: {pullrequest_id}")

    summary = event['pullrequest']['summary']['raw']
    title = event['pullrequest']['rendered']['title']['raw']

    pr_obj = PullRequestHandler(project_name=project, repo_name=repository_name, pull_request_id=pullrequest_id)
    response = pr_obj.find_diff()
    logger.info(f'Changed files: {response}')

    #TODO - Initiate agentic workflow
    pr_agent_obj = PRAgent()
    
    response = pr_agent_obj.analyse_pr(pr_title=title, pr_description=summary, pr_code_diff=response)
    logger.info(f'Agent response: {response}')

    json_data = extract_json(str(response))
    logger.info(f'extracted json: {json_data}')

    review_comments = json_data['review_comments']
    approve = json_data['approve']

    response = pr_obj.add_comment(review_comments)
    logger.info(f'Comment added with response - {response}')
    if (approve):
        response = pr_obj.merge(message = 'Merge approved')
        logger.info(f'Merge completed')

    return {
        'statusCode': 200,
        'body': event
    }
