import os
import asyncio
import boto3
import json
from datetime import datetime, timedelta
import time
from queue import Queue
import concurrent.futures
from typing import List, Dict
import aiohttp
from pyfiglet import figlet_format
from colorama import Fore, init
import textwrap

init(autoreset=True)

region = os.environ.get("AWS_REGION", "us-east-1")
app_name = os.environ.get("APP_NAME", "adt")
env_name = os.environ.get("ENV_NAME", "dev")

class LogStreamReader:
    def __init__(self):
        self.cloudwatch_logs = boto3.client('logs')
        self.log_groups = [
            f'/aws/lambda/{app_name}-{env_name}-PortfolioManagerAgent',
            f'/aws/lambda/{app_name}-{env_name}-MarketAnalysisAgent',
            f'/aws/lambda/{app_name}-{env_name}-RiskAssessmentAgent',
            f'/aws/lambda/{app_name}-{env_name}-TradeExecutionAgent'
        ]
        self.log_queue = Queue()
        self.running = True
        self.seen_events = set()
        self.retry_count = 0
        self.max_retries = 5
        self.empty_responses = 0
        self.max_empty_responses = 3

    def stop(self):
        self.running = False

    def set_log_groups(self, log_groups):
        self.log_groups = log_groups

    def get_log_events(self, log_group: str, start_time: int) -> List[Dict]:
        try:
            # Exponential backoff for retries
            if self.retry_count > 0:
                backoff_time = min(1.5 ** self.retry_count, 5)
                print(f"{Fore.YELLOW}Backing off for {backoff_time:.2f} seconds before retry...")
                time.sleep(backoff_time)

            print(f"{Fore.CYAN}Fetching logs from {log_group.split('/')[-1]}...")
            response = self.cloudwatch_logs.filter_log_events(
                logGroupName=log_group,
                startTime=start_time,
                interleaved=True
            )

            # Reset retry count on successful request
            self.retry_count = 0

            new_events = []
            for event in response.get('events', []):
                event_id = f"{event['timestamp']}-{event['message']}"
                if event_id not in self.seen_events:
                    self.seen_events.add(event_id)
                    new_events.append(event)

            return new_events

        except Exception as e:
            self.retry_count += 1
            if self.retry_count <= self.max_retries:
                print(f"{Fore.YELLOW}Retrying log fetch for {log_group.split('/')[-1]} (attempt {self.retry_count}/{self.max_retries})")
                return self.get_log_events(log_group, start_time)
            else:
                print(f"{Fore.RED}Error reading logs from {log_group}: {str(e)}")
                return []

    def stream_log_group(self, log_group: str, start_time: int):
        last_timestamp = start_time
        empty_responses = 0

        print(f"{Fore.CYAN}Starting log streaming for {log_group.split('/')[-1]}...")

        while self.running:
            try:
                events = self.get_log_events(log_group, last_timestamp)

                if events:
                    empty_responses = 0  # Reset counter when we get events
                    for event in events:
                        self.log_queue.put({
                            'timestamp': event['timestamp'],
                            'group': log_group,
                            'message': event['message'].strip()
                        })
                        last_timestamp = max(last_timestamp, event['timestamp'] + 1)
                    time.sleep(0.5)  # Normal polling interval
                else:
                    empty_responses += 1
                    # Adaptive polling: Increase sleep time if we're getting multiple empty responses
                    sleep_time = min(0.5 * (1.5 ** empty_responses), 5)
                    if empty_responses % self.max_empty_responses == 0:
                        print(f"{Fore.YELLOW}No new logs for {log_group.split('/')[-1]}, increasing polling interval...")
                    time.sleep(sleep_time)

            except Exception as e:
                print(f"{Fore.RED}Error in stream_log_group for {log_group}: {str(e)}")
                if not self.running:
                    break
                time.sleep(1)

    def print_logs(self):
        while self.running:
            try:
                if not self.log_queue.empty():
                    log = self.log_queue.get()
                    timestamp = datetime.fromtimestamp(log['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
                    group_name = log['group'].split('/')[-1]
                    print(f"{Fore.BLUE}[{timestamp}] [{group_name}]{Fore.WHITE} {log['message']}")
                time.sleep(0.1)
            except Exception as e:
                print(f"{Fore.RED}Error in print_logs: {str(e)}")
                if not self.running:
                    break
                time.sleep(1)

def print_banner():
    banner = figlet_format("A2A Advisory", font="slant")
    print(Fore.CYAN + banner)
    print(Fore.YELLOW + "=" * 60)
    print(Fore.GREEN + "A2A Protocol | Powered by AWS Bedrock")
    print(Fore.MAGENTA + "💬 Ask your portfolio questions in natural language")
    print(Fore.YELLOW + "=" * 60 + "\n")

def format_block(title: str, content: str, color=Fore.WHITE):
    print(f"\n{color}{title}")
    print(Fore.YELLOW + "-" * len(title))
    print(textwrap.fill(content.strip(), width=80))

def generate_cloudwatch_log_link(log_group: str, task_id: str, region: str = 'us-east-1', start_time: int = None) -> str:
    encoded_log_group = log_group.replace('/', '$252F')
    end_time = int(time.time() * 1000)
    if not start_time:
        start_time = end_time - (5 * 60 * 1000)  # 5 minutes before now

    base_url = f"https://{region}.console.aws.amazon.com/cloudwatch/home"
    query_params = (
        f"?region={region}#logsV2:log-groups/log-group/{encoded_log_group}"
        f"/log-events$3FstartTime$3D{start_time}$26endTime$3D{end_time}"
        f"$26filterPattern$3D{task_id}"
    )

    return base_url + query_params

def generate_dynamodb_link(table_name: str, region: str = 'us-east-1', task_id: str = None) -> str:
    base_url = f"https://{region}.console.aws.amazon.com/dynamodbv2/home"
    query_params = (
        f"?region={region}#item-explorer"
        f"?table={table_name}"
    )

    if task_id:
        query_params += f"&filter=task_id%3D%3D%22{task_id}%22"

    return base_url + query_params

async def format_response(resp: dict, phase: str = "analysis"):
    print("\n" + Fore.CYAN + "🧠 Portfolio Manager Response:")
    print(Fore.YELLOW + "-" * 60)

    if phase == "analysis":
        # For non-trade responses, the results are in output.agent_outputs
        if isinstance(resp, dict) and "output" in resp:
            output = resp["output"]
            summary = output.get("summary", "")
            agent_outputs = output.get("agent_outputs", {})
        else:
            # For trade-related responses, results are in analysis_results
            summary = resp.get("summary", "")
            agent_outputs = resp.get("analysis_results", {})

        if summary:
            format_block("📝 Analysis Summary", summary, Fore.GREEN)

        # Display analysis results from each agent
        for agent, result in agent_outputs.items():
            if result.get("status") == "completed":
                response = result.get("response", {})
                if agent == "MarketSummary":
                    print(f"\n{Fore.CYAN}📈 Market Analysis Results:")
                    print(Fore.YELLOW + "-" * 40)
                    format_block("Market Summary", response.get("summary", ""), Fore.CYAN)
                    format_block("Tags", ", ".join(response.get("tags", [])), Fore.CYAN)
                    format_block("Sentiment", response.get("sentiment", "unknown"), Fore.CYAN)

                elif agent == "RiskEvaluation":
                    print(f"\n{Fore.RED}⚠️ Risk Assessment Results:")
                    print(Fore.YELLOW + "-" * 40)
                    format_block("Risk Score", str(response.get("score", "N/A")), Fore.RED)
                    format_block("Rating", response.get("rating", "unknown"), Fore.RED)
                    format_block("Risk Factors", ", ".join(response.get("factors", [])), Fore.RED)
                    format_block("Explanation", response.get("explanation", ""), Fore.RED)

    elif phase == "trade":
        if resp.get("status") == "completed":
            trade_result = resp.get("output", {}).get("agent_outputs", {}).get("ExecuteTrade", {})
            if trade_result.get("status") == "completed":
                response = trade_result.get("response", {})
                print(f"\n{Fore.GREEN}✅ Trade Execution Results:")
                print(Fore.YELLOW + "-" * 40)
                format_block("Status", response.get("status", ""), Fore.GREEN)
                format_block("Confirmation ID", response.get("confirmationId", ""), Fore.GREEN)
            else:
                print(f"\n{Fore.RED}❌ Trade Execution Failed:")
                print(Fore.YELLOW + "-" * 40)
                format_block("Error", trade_result.get("error", "Unknown error"), Fore.RED)
        else:
            print(f"\n{Fore.YELLOW}ℹ️ Trade Cancelled by User")

async def validate_trade_info(trade_details: dict) -> dict:
    updated_details = trade_details.copy()

    print(f"\n{Fore.YELLOW}Based on the analysis results, we need to confirm one or more information with you before proceeding to trade execution.{Fore.RESET}")

    # Validate symbol
    if not updated_details.get('symbol') or updated_details.get('symbol') == 'TBD':
        while True:
            user_input = input(f"{Fore.YELLOW}Enter the stock symbol: {Fore.RESET}").strip()
            if user_input:
                updated_details['symbol'] = user_input.upper()
                break
            print(f"{Fore.RED}Symbol cannot be empty.{Fore.RESET}")

    # Validate quantity
    current_quantity = updated_details.get('quantity')
    if not current_quantity or (
        not isinstance(current_quantity, (int, float)) or
        current_quantity <= 0 or
        current_quantity == 'TBD'
    ):
        while True:
            user_input = input(f"{Fore.YELLOW}Enter the quantity to trade: {Fore.RESET}").strip()
            try:
                quantity = int(user_input)
                if quantity <= 0:
                    print(f"{Fore.RED}Quantity must be a positive number.{Fore.RESET}")
                    continue
                updated_details['quantity'] = quantity
                break
            except ValueError:
                print(f"{Fore.RED}Please enter a valid number.{Fore.RESET}")

    # Validate action
    current_action = updated_details.get('action', '').lower()
    if not current_action or current_action not in ['buy', 'sell'] or current_action == 'tbd':
        while True:
            user_input = input(f"{Fore.YELLOW}Enter the action (buy/sell): {Fore.RESET}").strip().lower()
            if user_input in ['buy', 'sell']:
                updated_details['action'] = user_input
                break
            print(f"{Fore.RED}Action must be either 'buy' or 'sell'.{Fore.RESET}")

    return updated_details

async def send_request(api_url: str, question: str, log_streamer: LogStreamReader):
    try:
        start_time = int((datetime.now() - timedelta(seconds=90)).timestamp() * 1000)
        print(f"{Fore.YELLOW}Initializing analysis phase...")

        task_id = f"cli-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        payload = {
            "task": {
                "id": task_id,
                "input": {"user_input": question},
                "created_at": datetime.now().isoformat(),
                "modified_at": datetime.now().isoformat()
            }
        }

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(log_streamer.log_groups) + 1) as executor:
            futures = [
                executor.submit(log_streamer.stream_log_group, log_group, start_time)
                for log_group in log_streamer.log_groups
            ]
            printer_future = executor.submit(log_streamer.print_logs)

            async with aiohttp.ClientSession() as session:
                # Phase 1: Analysis
                async with session.post(
                        api_url,
                        json=payload,
                        headers={"Content-Type": "application/json"}
                ) as response:
                    response_data = await response.json()

                    # If it's a direct response (non-trade)
                    if response.status == 200:
                        if isinstance(response_data.get("body"), str):
                            response_data = json.loads(response_data["body"])

                    # Stop analysis phase logging
                    print(f"{Fore.CYAN}Analysis phase completed.")
                    log_streamer.stop()
                    for future in futures + [printer_future]:
                        future.cancel()

                    # For non-trade responses, display results and return None
                    if response.status == 200:
                        await format_response(response_data, phase="analysis")
                        print(f"\n{Fore.CYAN}CloudWatch Logs::")
                        for log_group in log_streamer.log_groups:
                            log_link = generate_cloudwatch_log_link(log_group, task_id, start_time=start_time)
                            print(f"{Fore.CYAN}• {log_group}: {Fore.BLUE}{log_link}{Fore.RESET}")
                        return None

                    # For trade responses, continue with trade flow
                    await format_response(response_data, phase="analysis")
                    print(f"\n{Fore.CYAN}CloudWatch Logs::")
                    for log_group in log_streamer.log_groups:
                        log_link = generate_cloudwatch_log_link(log_group, task_id, start_time=start_time)
                        print(f"{Fore.CYAN}• {log_group}: {Fore.BLUE}{log_link}{Fore.RESET}")

                    if response.status == 202:  # Trade confirmation needed
                        trade_details = response_data.get("trade_details", {})

                        await asyncio.sleep(3)

                        if trade_details:
                            updated_trade_details = await validate_trade_info(trade_details)

                            print(f"\n{Fore.YELLOW}Proposed Trade Details:")
                            print(Fore.YELLOW + "-" * 40)
                            print(f"Action: {updated_trade_details.get('action')}")
                            print(f"Symbol: {updated_trade_details.get('symbol')}")
                            print(f"Quantity: {updated_trade_details.get('quantity')}")

                            print(f"\n{Fore.CYAN}CloudWatch Logs:")
                            for log_group in log_streamer.log_groups:
                                log_link = generate_cloudwatch_log_link(
                                    log_group,
                                    response_data["session_id"],
                                    start_time=start_time
                                )
                                print(f"{Fore.CYAN}• {log_group}: {Fore.BLUE}{log_link}{Fore.RESET}")

                            confirmation = input(f"\n{Fore.YELLOW}Would you like to proceed with this trade? (y/n): {Fore.RESET}").strip().lower()

                            if confirmation in ["yes", "y"]:
                                # Phase 2: Trade Execution with specific log groups
                                print(f"\n{Fore.YELLOW}Initiating trade execution...")
                                trade_log_groups = [
                                    f"/aws/lambda/{app_name}-{env_name}-PortfolioManagerAgent",
                                    f"/aws/lambda/{app_name}-{env_name}-TradeExecutionAgent"
                                ]

                                new_log_streamer = LogStreamReader()
                                new_log_streamer.set_log_groups(trade_log_groups)
                                new_start_time = int(datetime.now().timestamp() * 1000)

                                await asyncio.sleep(2)

                                new_start_time = int((datetime.now() - timedelta(seconds=5)).timestamp() * 1000)

                                with concurrent.futures.ThreadPoolExecutor(max_workers=len(trade_log_groups) + 1) as new_executor:
                                    new_futures = [
                                        new_executor.submit(new_log_streamer.stream_log_group, log_group, new_start_time)
                                        for log_group in trade_log_groups
                                    ]
                                    new_printer_future = new_executor.submit(new_log_streamer.print_logs)

                                    trade_payload = {
                                        "task": {
                                            "id": response_data["session_id"],
                                            "input": {
                                                "trade_confirmation_phase": True,
                                                "trade_details": updated_trade_details
                                            },
                                            "created_at": datetime.now().isoformat(),
                                            "modified_at": datetime.now().isoformat()
                                        }
                                    }

                                    async with session.post(
                                            api_url,
                                            json=trade_payload,
                                            headers={"Content-Type": "application/json"}
                                    ) as trade_response:
                                        print(f"{Fore.YELLOW}Trade execution request sent, waiting for completion...")
                                        trade_result = await trade_response.json()

                                        await asyncio.sleep(3)

                                        # Stop trade execution logging
                                        new_log_streamer.stop()
                                        for future in new_futures + [new_printer_future]:
                                            future.cancel()

                                        # Display trade results
                                        await format_response(trade_result, phase="trade")

                                        # CloudWatch Logs
                                        print(f"\n{Fore.CYAN}CloudWatch Logs:")
                                        for log_group in trade_log_groups:
                                            log_link = generate_cloudwatch_log_link(
                                                log_group,
                                                response_data["session_id"],
                                                start_time=new_start_time
                                            )
                                            print(f"{Fore.CYAN}• {log_group}: {Fore.BLUE}{log_link}{Fore.RESET}")

                                        # DynamoDB Tables
                                        print(f"\n{Fore.CYAN}DynamoDB Record:")
                                        region = os.environ.get("AWS_REGION", "us-east-1")
                                        db_link = generate_dynamodb_link(
                                            f"{app_name}-{env_name}-trade-execution",
                                            region=region,
                                            task_id=response_data["session_id"]
                                        )
                                        print(f"{Fore.CYAN}• Trade Execution: {Fore.BLUE}{db_link}{Fore.RESET}")

                                        print(f"\n{Fore.YELLOW}Note: Click the links above to view detailed logs and database records.{Fore.RESET}")

                                        return None
                            else:
                                print(f"\n{Fore.RED}Trade cancelled by user.")
                                return None
                    return None

    except Exception as e:
        print(f"{Fore.RED}Error in send_request: {str(e)}")
        if 'log_streamer' in locals():
            log_streamer.stop()
        return None

async def main():
    try:
        print_banner()
        api_id = input(Fore.CYAN + "Enter your Portfolio Manager API Gateway ID (e.g., abc123xyz): ").strip()
        if not api_id:
            print(Fore.RED + "❌ API ID is required.")
            return

        api_url = f"https://{api_id}.execute-api.{region}.amazonaws.com/{env_name}/tasks/send"

        while True:
            question = input(Fore.CYAN + f"\n💬 Enter your portfolio question (or 'exit' to quit): {Fore.RESET}").strip()
            if not question:
                print(Fore.RED + "❌ You must provide a question.")
                question = input(Fore.CYAN + f"\n💬 Enter your portfolio question (or 'exit' to quit): {Fore.RESET}").strip()
            if question.lower() == 'exit':
                print(Fore.YELLOW + "\nThank you for using A2A Advisory! Goodbye! 👋 ✨")
                print("\n" * 4)
                break

            print(Fore.YELLOW + "\nProcessing your request... Real-time logs will appear below:\n")

            log_streamer = LogStreamReader()

            response = await send_request(api_url, question, log_streamer)
            if response:
                if response.get("status") == "pending":
                    # Phase 1: Analysis results
                    await format_response(response, phase="analysis")

                    # Trade confirmation handled in send_request
                    # If user confirms, Phase 2 response will be formatted there
                    # If user declines, appropriate message is shown there

                else:
                    # Non-trade request or final trade result
                    task_output = response.get("task", {}).get("output", {})
                    if "ExecuteTrade" in task_output.get("agent_outputs", {}):
                        await format_response(response, phase="trade")
                    else:
                        await format_response(response, phase="analysis")

    except Exception as e:
        print(f"{Fore.RED}Error in main: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
