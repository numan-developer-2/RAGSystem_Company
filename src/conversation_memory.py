"""
Conversation Memory: Maintains context across multiple turns
for natural, contextual conversations
"""
from typing import List, Dict, Optional
from datetime import datetime
import json


class ConversationMemory:
    """
    Manages conversation history and context
    Enables multi-turn conversations with context awareness
    """
    
    def __init__(self, max_history: int = 10, max_tokens: int = 2000):
        """
        Initialize conversation memory
        
        Args:
            max_history: Maximum number of turns to remember
            max_tokens: Approximate max tokens to keep in context
        """
        self.max_history = max_history
        self.max_tokens = max_tokens
        self.conversations: Dict[str, List[Dict]] = {}
        
    def add_turn(self, session_id: str, question: str, answer: str, 
                 sources: List[Dict] = None):
        """
        Add a conversation turn
        
        Args:
            session_id: Unique session identifier
            question: User's question
            answer: Assistant's answer
            sources: Retrieved sources for this turn
        """
        if session_id not in self.conversations:
            self.conversations[session_id] = []
        
        turn = {
            'timestamp': datetime.now().isoformat(),
            'question': question,
            'answer': answer,
            'sources': sources or [],
            'turn_number': len(self.conversations[session_id]) + 1
        }
        
        self.conversations[session_id].append(turn)
        
        # Trim if exceeds max_history
        if len(self.conversations[session_id]) > self.max_history:
            self.conversations[session_id] = self.conversations[session_id][-self.max_history:]
    
    def get_context(self, session_id: str, include_last_n: int = 3) -> str:
        """
        Get conversation context for prompt
        
        Args:
            session_id: Session identifier
            include_last_n: Number of recent turns to include
        
        Returns:
            Formatted conversation history
        """
        if session_id not in self.conversations:
            return ""
        
        history = self.conversations[session_id][-include_last_n:]
        
        if not history:
            return ""
        
        context_parts = ["Previous conversation:"]
        for turn in history:
            context_parts.append(f"User: {turn['question']}")
            context_parts.append(f"Assistant: {turn['answer'][:200]}...")  # Truncate long answers
        
        return "\n".join(context_parts)
    
    def get_conversation_summary(self, session_id: str) -> Dict:
        """
        Get summary of conversation
        
        Returns:
            Summary with stats and key info
        """
        if session_id not in self.conversations:
            return {
                'total_turns': 0,
                'topics': [],
                'duration': None
            }
        
        history = self.conversations[session_id]
        
        if not history:
            return {'total_turns': 0, 'topics': [], 'duration': None}
        
        # Calculate duration
        start_time = datetime.fromisoformat(history[0]['timestamp'])
        end_time = datetime.fromisoformat(history[-1]['timestamp'])
        duration = (end_time - start_time).total_seconds()
        
        # Extract topics (simple keyword extraction)
        all_questions = " ".join([turn['question'] for turn in history])
        
        return {
            'total_turns': len(history),
            'start_time': history[0]['timestamp'],
            'last_activity': history[-1]['timestamp'],
            'duration_seconds': duration,
            'questions': [turn['question'] for turn in history]
        }
    
    def clear_session(self, session_id: str):
        """Clear conversation history for a session"""
        if session_id in self.conversations:
            del self.conversations[session_id]
    
    def export_conversation(self, session_id: str, format: str = 'json') -> str:
        """
        Export conversation in various formats
        
        Args:
            session_id: Session to export
            format: 'json', 'markdown', or 'text'
        
        Returns:
            Formatted conversation
        """
        if session_id not in self.conversations:
            return ""
        
        history = self.conversations[session_id]
        
        if format == 'json':
            return json.dumps(history, indent=2)
        
        elif format == 'markdown':
            lines = [f"# Conversation Export - {datetime.now().strftime('%Y-%m-%d %H:%M')}"]
            lines.append(f"\nTotal Turns: {len(history)}\n")
            
            for i, turn in enumerate(history, 1):
                lines.append(f"## Turn {i}")
                lines.append(f"**Time:** {turn['timestamp']}")
                lines.append(f"\n**Question:** {turn['question']}")
                lines.append(f"\n**Answer:** {turn['answer']}")
                if turn['sources']:
                    lines.append(f"\n**Sources:** {len(turn['sources'])} documents")
                lines.append("\n---\n")
            
            return "\n".join(lines)
        
        else:  # text format
            lines = [f"Conversation Export - {datetime.now().strftime('%Y-%m-%d %H:%M')}"]
            lines.append(f"Total Turns: {len(history)}\n")
            
            for i, turn in enumerate(history, 1):
                lines.append(f"[Turn {i}] {turn['timestamp']}")
                lines.append(f"Q: {turn['question']}")
                lines.append(f"A: {turn['answer']}\n")
            
            return "\n".join(lines)
    
    def get_contextual_query(self, session_id: str, current_question: str) -> str:
        """
        Enhance current question with conversation context
        Useful for follow-up questions like "tell me more" or "what about X?"
        
        Args:
            session_id: Session identifier
            current_question: Current user question
        
        Returns:
            Enhanced question with context
        """
        if session_id not in self.conversations or not self.conversations[session_id]:
            return current_question
        
        last_turn = self.conversations[session_id][-1]
        
        # Check if current question is a follow-up
        follow_up_indicators = ['more', 'also', 'what about', 'how about', 'tell me', 'explain']
        is_follow_up = any(indicator in current_question.lower() for indicator in follow_up_indicators)
        
        if is_follow_up:
            # Add context from last question
            enhanced = f"Previous question was: '{last_turn['question']}'. Now the user asks: '{current_question}'"
            return enhanced
        
        return current_question
