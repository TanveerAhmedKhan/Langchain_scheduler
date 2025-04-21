"""
Agent module for Scout Agent PoC.
Uses LangChain to parse user instructions and manage the monitoring tasks.
"""

import os
import re
from typing import Dict, Any, Optional, Tuple
import logging
from datetime import datetime

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define the output schema for task parsing
class MonitoringTask(BaseModel):
    """Schema for a monitoring task."""
    url: str = Field(description="The URL to monitor")
    frequency_hours: float = Field(description="How often to check in hours")
    task_description: str = Field(description="Description of what to monitor for")
    
    @validator('url')
    def validate_url(cls, v):
        """Validate that the URL is properly formatted."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        return v
    
    @validator('frequency_hours')
    def validate_frequency(cls, v):
        """Validate that the frequency is reasonable."""
        if v <= 0:
            raise ValueError("Frequency must be positive")
        if v < 0.25:  # 15 minutes minimum
            raise ValueError("Frequency must be at least 0.25 hours (15 minutes)")
        return v

class ScoutAgent:
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        """Initialize the Scout Agent with the specified LLM."""
        # Initialize the language model
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not found in environment variables.")
            
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0,
            api_key=api_key
        )
        
        # Initialize the output parser
        self.parser = PydanticOutputParser(pydantic_object=MonitoringTask)
        
        # Load the instruction parsing prompt
        self.instruction_prompt = PromptTemplate(
            template=self._load_prompt_template("instruction_prompt.txt"),
            input_variables=["instruction"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )
        
        # Load the confirmation prompt
        self.confirmation_prompt = PromptTemplate(
            template=self._load_prompt_template("confirm_prompt.txt"),
            input_variables=["task_details"]
        )
    
    def _load_prompt_template(self, filename: str) -> str:
        """Load a prompt template from file or return a default if file not found."""
        prompt_path = os.path.join("prompts", filename)
        
        # Default prompts in case files don't exist
        defaults = {
            "instruction_prompt.txt": """
            You are a helpful assistant that parses monitoring instructions.
            
            Given the following instruction from a user, extract the URL to monitor,
            how frequently to check it (in hours), and what to watch for.
            
            Instruction: {instruction}
            
            {format_instructions}
            """,
            
            "confirm_prompt.txt": """
            I'll monitor the following for you:
            
            {task_details}
            
            Is this correct? (yes/no)
            """
        }
        
        try:
            with open(prompt_path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"Prompt file {prompt_path} not found. Using default.")
            return defaults.get(filename, "")
    
    def parse_instruction(self, instruction: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Parse a natural language instruction into structured task details.
        
        Args:
            instruction: The user's natural language instruction
            
        Returns:
            Tuple of (success, task_details)
        """
        try:
            # Format the prompt with the user's instruction
            formatted_prompt = self.instruction_prompt.format(instruction=instruction)
            
            # Get the response from the LLM
            response = self.llm.invoke(formatted_prompt)
            
            # Parse the response
            task = self.parser.parse(response.content)
            
            # Convert to dictionary and add frequency in seconds
            task_dict = task.dict()
            task_dict["frequency_seconds"] = int(task_dict["frequency_hours"] * 3600)
            
            return True, task_dict
        except Exception as e:
            logger.error(f"Error parsing instruction: {str(e)}")
            return False, {"error": str(e)}
    
    def generate_confirmation(self, task_details: Dict[str, Any]) -> str:
        """
        Generate a confirmation message for the parsed task.
        
        Args:
            task_details: The parsed task details
            
        Returns:
            A confirmation message to show to the user
        """
        # Format the task details for display
        frequency_str = self._format_frequency(task_details["frequency_hours"])
        
        task_summary = f"""
        URL: {task_details['url']}
        Check frequency: {frequency_str}
        What to monitor for: {task_details['task_description']}
        """
        
        # Generate the confirmation message
        return self.confirmation_prompt.format(task_details=task_summary)
    
    def _format_frequency(self, hours: float) -> str:
        """Format the frequency in a human-readable way."""
        if hours >= 24:
            days = hours / 24
            return f"every {days:.1f} days"
        elif hours >= 1:
            return f"every {hours:.1f} hours"
        else:
            minutes = hours * 60
            return f"every {minutes:.0f} minutes"
    
    def extract_url_from_text(self, text: str) -> Optional[str]:
        """Extract a URL from text using regex."""
        url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
        match = re.search(url_pattern, text)
        if match:
            url = match.group(0)
            # Ensure URL has a scheme
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            return url
        return None
