import asyncio
import json
import logging
from typing import Optional, List
from datetime import datetime
from pathlib import Path
import sys

import asyncpg
from dotenv import load_dotenv

from livekit import agents, rtc
from livekit.agents import (
    JobContext,
    AutoSubscribe,
    WorkerOptions,
    llm,
    voice,
    function_tool,
    RoomIO,
    RoomInputOptions,
    RoomOutputOptions,
)
from livekit.plugins import openai, noise_cancellation

# Local imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.settings import settings
from config.database import db_manager
from app.services.customer_service import CustomerService
from app.services.queue_manager import QueueManager
from app.services.transcript_service import TranscriptService
from app.services.sentiment_analyzer import SentimentAnalyzer
from app.tools.account_tools import AccountTools
from app.tools.scheduling_tools import SchedulingTools
from app.tools.knowledge_base import KnowledgeBase
from app.agents import prompts

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================================
# OPENAI CUSTOMER SERVICE AGENT
# ============================================================================

class OpenAICustomerServiceAgent:
    """
    """

    def __init__(self):
        """Initialize agent with service connections"""
        # Database services
        self.db_pool: Optional[asyncpg.Pool] = None
        self.customer_service: Optional[CustomerService] = None
        self.queue_manager: Optional[QueueManager] = None
        self.transcript_service: Optional[TranscriptService] = None
        self.sentiment_analyzer: Optional[SentimentAnalyzer] = None
        
        # Function tools
        self.account_tools: Optional[AccountTools] = None
        self.scheduling_tools: Optional[SchedulingTools] = None
        self.knowledge_base: Optional[KnowledgeBase] = None
        
        # Call state
        self.session_id: Optional[int] = None
        self.customer_id: Optional[int] = None
        self.queue_id: Optional[int] = None
        self.phone_number: Optional[str] = None
        self.call_type: Optional[str] = None
        self.customer_name: Optional[str] = None
        self.transfer_requested = False
        self.is_first_time_customer = False
        
        logger.info("OpenAICustomerServiceAgent initialized")

    # ========================================================================
    # DATABASE INITIALIZATION
    # ========================================================================

    async def initialize_database(self):
        """Initialize database connection pool and all services"""
        try:
            await db_manager.connect()
            self.db_pool = db_manager.pool
            
            # Initialize services
            self.customer_service = CustomerService(self.db_pool)
            self.queue_manager = QueueManager(self.db_pool)
            self.transcript_service = TranscriptService(self.db_pool)
            self.sentiment_analyzer = SentimentAnalyzer(self.db_pool)
            
            # Initialize tools
            self.account_tools = AccountTools(self.db_pool)
            self.scheduling_tools = SchedulingTools(self.db_pool)
            self.knowledge_base = KnowledgeBase(self.db_pool)
            
            logger.info("Database and services initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
            raise

    # ========================================================================
    # CUSTOMER CONTEXT
    # ========================================================================

    async def get_customer_context(self, phone_number: str) -> str:
        """
        Build comprehensive customer context for the AI.
        
        Args:
            phone_number: Customer's phone number
            
        Returns:
            Formatted customer context string
        """
        try:
            logger.info(f"Fetching customer context for {phone_number}")
            
            customer = await self.customer_service.get_customer_info(phone_number)
            
            if not customer:
                self.is_first_time_customer = True
                logger.info(f"New customer: {phone_number}")
                return (
                    f"New customer calling from {phone_number}. "
                    f"This is their first interaction with our service."
                )
            
            # Returning customer
            self.customer_id = customer["customer_id"]
            self.customer_name = customer.get("name")
            self.is_first_time_customer = False
            
            total_calls = customer.get("total_calls", 0)
            logger.info(
                f"Returning customer: {self.customer_name} "
                f"(ID: {self.customer_id}, {total_calls} previous calls)"
            )
            
            # Get recent call history
            history = await self.customer_service.get_call_history(
                customer["customer_id"], 
                limit=3
            )
            
            # Build context
            context = f"""Customer Information:
- Name: {customer.get('name', 'Unknown')}
- Phone: {phone_number}
- Customer ID: {customer['customer_id']}
- Member since: {customer.get('created_at', 'Unknown')}
- Total previous calls: {total_calls}
- Last call: {customer.get('last_call_time', 'Never')}
"""
            
            if history:
                context += "\nRecent Call History:\n"
                for idx, call in enumerate(history, 1):
                    summary = call.get("summary", "No summary")
                    duration = call.get("duration_seconds", 0)
                    sentiment = call.get("sentiment", "neutral")
                    context += (
                        f"{idx}. {call['start_time']} "
                        f"({duration}s, {sentiment}): {summary}\n"
                    )
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting customer context: {e}", exc_info=True)
            return f"Customer calling from {phone_number} (context unavailable)"

    # ========================================================================
    # FUNCTION TOOLS (LiveKit 1.x Style)
    # ========================================================================

    def build_tools(self) -> List[llm.FunctionTool]:
        """
        Build list of function tools for the agent.
        
        Returns:
            List of FunctionTool objects
        """
        tools: List[llm.FunctionTool] = []
        
        # TEMPORARILY DISABLED - These tools cause KeyError: 'args' due to *args, **kwargs
        # TODO: Fix by creating proper wrapper functions with explicit parameters
        
        # # Account tools - wrap bound methods in lambdas
        # if self.account_tools:
        #     if hasattr(self.account_tools, "check_account_balance"):
        #         async def check_balance(*args, **kwargs):
        #             return await self.account_tools.check_account_balance(*args, **kwargs)
        #         
        #         tools.append(
        #             function_tool(
        #                 check_balance,
        #                 name="check_account_balance",
        #                 description="Retrieve the customer's current account balance.",
        #             )
        #         )
        #     
        #     if hasattr(self.account_tools, "get_recent_transactions"):
        #         async def get_transactions(*args, **kwargs):
        #             return await self.account_tools.get_recent_transactions(*args, **kwargs):
        #         
        #         tools.append(
        #             function_tool(
        #                 get_transactions,
        #                 name="get_recent_transactions",
        #                 description="Get the customer's recent transaction history.",
        #             )
        #         )
        #     
        #     if hasattr(self.account_tools, "update_contact_info"):
        #         async def update_contact(*args, **kwargs):
        #             return await self.account_tools.update_contact_info(*args, **kwargs)
        #         
        #         tools.append(
        #             function_tool(
        #                 update_contact,
        #                 name="update_contact_info",
        #                 description="Update customer contact information (phone, email, address).",
        #             )
        #         )
        # 
        # # Scheduling tools
        # if self.scheduling_tools:
        #     if hasattr(self.scheduling_tools, "schedule_callback"):
        #         async def schedule_cb(*args, **kwargs):
        #             return await self.scheduling_tools.schedule_callback(*args, **kwargs)
        #         
        #         tools.append(
        #             function_tool(
        #                 schedule_cb,
        #                 name="schedule_callback",
        #                 description="Schedule a callback for the customer at a specified time.",
        #             )
        #         )
        #     
        #     if hasattr(self.scheduling_tools, "check_availability"):
        #         async def check_avail(*args, **kwargs):
        #             return await self.scheduling_tools.check_availability(*args, **kwargs)
        #         
        #         tools.append(
        #             function_tool(
        #                 check_avail,
        #                 name="check_availability",
        #                 description="Check availability for scheduling appointments.",
        #             )
        #         )
        # 
        # # Knowledge base
        # if self.knowledge_base:
        #     if hasattr(self.knowledge_base, "search_knowledge_base"):
        #         async def search_kb(*args, **kwargs):
        #             return await self.knowledge_base.search_knowledge_base(*args, **kwargs)
        #         
        #         tools.append(
        #             function_tool(
        #                 search_kb,
        #                 name="search_knowledge_base",
        #                 description="Search the knowledge base for answers to common questions.",
        #             )
        #         )
        
        # Transfer to human
        async def transfer_to_human(reason: str) -> str:
            """Transfer call to a human agent"""
            self.transfer_requested = True
            logger.info(f"Transfer requested: {reason}")
            return prompts.get_transfer_message(reason)
        
        tools.append(
            function_tool(
                transfer_to_human,
                name="transfer_to_human",
                description=(
                    "Transfer the call to a human agent. Use when the customer requests "
                    "a human, is frustrated, or the issue requires human judgment."
                ),
            )
        )
        
        logger.info(f"Built {len(tools)} function tools")
        return tools

    # ========================================================================
    # EVENT HANDLERS
    # ========================================================================

    def setup_event_handlers(self, session: voice.AgentSession):
        """
        Setup event handlers for transcripts and sentiment analysis.
        
        Args:
            session: The AgentSession to attach handlers to
        """
        
        async def handle_user_speech(msg: llm.ChatMessage):
            """Handle user speech - save transcript and analyze sentiment"""
            try:
                text = getattr(msg, "content", None) or getattr(msg, "text", None)
                if not text:
                    return
                
                logger.info(f"User: {text}")
                
                # Save transcript
                if self.transcript_service and self.session_id:
                    await self.transcript_service.save_transcript(
                        self.session_id,
                        "customer",
                        text,
                        confidence=0.95,
                    )
                
                # Analyze sentiment
                if self.sentiment_analyzer and self.session_id:
                    sentiment = await self.sentiment_analyzer.analyze_conversation(
                        self.session_id,
                        window_size=3,
                    )
                    
                    if sentiment:
                        polarity = sentiment.get("polarity", 0)
                        label = sentiment.get("label", "neutral")
                        logger.info(f"Sentiment: {label} (polarity: {polarity:.2f})")
                        
                        if sentiment.get("recommend_transfer"):
                            logger.warning(f"Negative sentiment detected in session {self.session_id}")
                        
                        if sentiment.get("strong_negative"):
                            logger.error(f"STRONG negative sentiment detected in session {self.session_id}")
                            
            except Exception as e:
                logger.error(f"Error handling user speech: {e}", exc_info=True)
        
        @session.on("user_speech_committed")
        def on_user_speech(msg: llm.ChatMessage):
            """Synchronous wrapper for user speech handling"""
            asyncio.create_task(handle_user_speech(msg))
        
        async def handle_agent_speech(msg: llm.ChatMessage):
            """Handle agent speech - save transcript"""
            try:
                text = getattr(msg, "content", None) or getattr(msg, "text", None)
                if not text:
                    return
                
                logger.info(f"Agent: {text}")
                
                # Save transcript
                if self.transcript_service and self.session_id:
                    await self.transcript_service.save_transcript(
                        self.session_id,
                        "ai_agent",
                        text,
                        confidence=1.0,
                    )
                    
            except Exception as e:
                logger.error(f"Error handling agent speech: {e}", exc_info=True)
        
        @session.on("agent_speech_committed")
        def on_agent_speech(msg: llm.ChatMessage):
            """Synchronous wrapper for agent speech handling"""
            asyncio.create_task(handle_agent_speech(msg))
        
        async def handle_function_calls(calls):
            """Handle function calls - log tool usage"""
            try:
                for call in calls:
                    function_name = getattr(call, "function_name", "unknown")
                    logger.info(f"Function executed: {function_name}")
                    
                    # Save to transcript
                    if self.transcript_service and self.session_id:
                        await self.transcript_service.save_transcript(
                            self.session_id,
                            "system",
                            f"Function called: {function_name}",
                            confidence=1.0,
                        )
                    
                    # Handle transfer
                    if function_name == "transfer_to_human" and self.transfer_requested:
                        logger.info("Initiating transfer to human agent")
                        
            except Exception as e:
                logger.error(f"Error handling function calls: {e}", exc_info=True)
        
        @session.on("function_calls_finished")
        def on_function_calls(calls):
            """Synchronous wrapper for function calls handling"""
            asyncio.create_task(handle_function_calls(calls))
        
        logger.info("Event handlers configured")

    # ========================================================================
    # MAIN ENTRYPOINT
    # ========================================================================

    async def entrypoint(self, ctx: JobContext):
        """
        Main agent entrypoint - handles complete call flow.
        
        This is called by LiveKit for each incoming/outgoing call.
        
        Args:
            ctx: JobContext from LiveKit
        """
        try:
            # Initialize database (per-job to avoid connection issues)
            await self.initialize_database()
            
            # Connect to room
            await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
            logger.info(f"Connected to room: {ctx.room.name}")
            
            # Parse call metadata
            metadata = json.loads(ctx.job.metadata or "{}")
            self.phone_number = metadata.get("phone_number", "unknown")
            self.call_type = metadata.get("call_type", prompts.CallType.INBOUND)
            
            logger.info(
                f"Processing {self.call_type} call from {self.phone_number}"
            )
            
            # Get customer context
            customer_context = await self.get_customer_context(self.phone_number)
            
            # Ensure customer record exists
            if not self.customer_id and self.customer_service:
                logger.info(f"Creating customer record for {self.phone_number}")
                customer = await self.customer_service.get_or_create_customer(
                    self.phone_number,
                    name=f"Customer-{self.phone_number[-4:]}",
                )
                self.customer_id = customer["customer_id"]
                logger.info(f"Customer ID: {self.customer_id}")
            
            # Create call session
            if self.customer_service and self.customer_id:
                self.session_id = await self.customer_service.create_session(
                    self.customer_id,
                    ctx.room.name,
                )
                logger.info(f"Session ID: {self.session_id}")
            
            # Add to queue (for inbound calls)
            if self.call_type == prompts.CallType.INBOUND and self.queue_manager:
                self.queue_id = await self.queue_manager.add_to_queue(
                    self.customer_id,
                    self.phone_number,
                    ctx.room.name,
                    priority=1 if self.is_first_time_customer else 2,
                )
                logger.info(f"Queue ID: {self.queue_id}")
            
            # ================================================================
            # CREATE AGENT SESSION WITH KRISP NOISE CANCELLATION
            # ================================================================
            
            # Build system instructions
            system_instructions = prompts.get_system_instructions(
                customer_context,
                self.call_type,
                self.is_first_time_customer,
            )
            
            # Create OpenAI realtime model
            model = openai.realtime.RealtimeModel(
                model=settings.openai_model,
                voice=settings.openai_voice,
                temperature=settings.openai_temperature,
            )
            logger.info("OpenAI RealtimeModel created")
            
            # Build function tools
            tools = self.build_tools()
            
            # Create AgentSession
            session = voice.AgentSession(llm=model)
            
            # Create voice Agent with tools
            agent = voice.Agent(
                instructions=system_instructions,
                llm=model,
                tools=tools,
            )
            logger.info("Voice Agent created with tools")
            
            # Setup event handlers
            self.setup_event_handlers(session)
            
            # TEMPORARILY DISABLED - Greeting mechanism
            # TODO: Re-enable once basic agent is working
            # Generate greeting
            # greeting = prompts.get_greeting(
            #     self.call_type,
            #     self.is_first_time_customer,
            #     self.customer_name
            # )
            # 
            # # Setup greeting handler - send greeting when session starts
            # @session.on("session_started")
            # def on_session_started():
            #     async def send_greeting():
            #         # Wait for connection to stabilize
            #         await asyncio.sleep(1.0) 
            #         if greeting:
            #             logger.info(f"Sending greeting: {greeting}")
            #             await session.say(greeting, allow_interruptions=True)
            #     
            #     asyncio.create_task(send_greeting())
            
            # Start session and handle conversation
            await session.start(
                agent=agent,
                room=ctx.room,
                room_input_options=RoomInputOptions(),
            )
            logger.info("Agent session started and conversation completed")
            
            # ================================================================
            # CLEANUP
            # ================================================================
            
            try:
                # Update session end
                if self.session_id and self.customer_service:
                    await self.customer_service.update_session_end(
                        self.session_id,
                        json.dumps({
                            "transfer_requested": self.transfer_requested,
                            "completed_at": datetime.now().isoformat(),
                            "first_time_customer": self.is_first_time_customer,
                            "call_type": self.call_type,
                        }),
                    )
                
                # Mark queue as completed
                if self.queue_id and self.queue_manager:
                    await self.queue_manager.mark_completed(self.queue_id)
                
                logger.info(
                    f"Session {self.session_id} completed "
                    f"({'transferred' if self.transfer_requested else 'resolved by AI'})"
                )
                
            except Exception as cleanup_err:
                logger.error(
                    f"Error during cleanup: {cleanup_err}",
                    exc_info=True,
                )
        
        except Exception as e:
            logger.error(f"Error in agent entrypoint: {e}", exc_info=True)
            
            # Cleanup on error
            try:
                if self.queue_id and self.queue_manager:
                    await self.queue_manager.mark_abandoned(self.queue_id)
                
                if self.session_id and self.customer_service:
                    await self.customer_service.update_session_end(
                        self.session_id,
                        json.dumps({
                            "transfer_requested": self.transfer_requested,
                            "completed_at": datetime.now().isoformat(),
                            "first_time_customer": self.is_first_time_customer,
                            "call_type": self.call_type,
                            "error": str(e),
                        }),
                    )
            except Exception as inner:
                logger.error(
                    f"Error during error cleanup: {inner}",
                    exc_info=True,
                )


# ============================================================================
# MODULE-LEVEL ENTRYPOINT FOR LIVEKIT WORKER
# ============================================================================

agent_instance = OpenAICustomerServiceAgent()


async def entrypoint(ctx: JobContext):
    """Entry point for LiveKit worker"""
    await agent_instance.entrypoint(ctx)


if __name__ == "__main__":
    agents.cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="AgnoX-AI-Agent",
        )
    )
