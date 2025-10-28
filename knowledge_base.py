
"""
Knowledge Base Integration Module
Integrates with multiple websites to answer customer questions
"""

import os
import json
import requests
from typing import Dict, List, Optional
from datetime import datetime

class KnowledgeBase:
    """
    Manages knowledge from multiple website sources
    """
    
    def __init__(self):
        self.sources = {
            'house_of_sports': {
                'name': 'House of Sports',
                'url': 'https://houseofsports.com',  # Update with actual URL
                'description': 'Main sports facility with basketball courts, party packages, training programs',
                'keywords': ['basketball', 'sports', 'facility', 'courts', 'training']
            },
            'rise_as_one': {
                'name': 'Rise as One',
                'url': 'https://riseasone.com',  # Update with actual URL
                'description': 'Youth basketball program focused on skill development and teamwork',
                'keywords': ['youth', 'basketball', 'program', 'training', 'development', 'team']
            },
            'basketball_factory': {
                'name': 'Basketball Factory Inc',
                'url': 'https://basketballfactory.com',  # Update with actual URL
                'description': 'Elite basketball training and development programs',
                'keywords': ['elite', 'training', 'basketball', 'development', 'coaching']
            }
        }
        
        # Check if Abacus AI API key is available
        self.abacus_api_key = os.getenv('ABACUSAI_API_KEY')
        if not self.abacus_api_key:
            print("⚠ Warning: ABACUSAI_API_KEY not found. Knowledge base will use fallback mode.")
    
    def get_relevant_source(self, query: str) -> Optional[str]:
        """
        Determine which website/source is most relevant for the query
        """
        query_lower = query.lower()
        
        # Check for specific mentions
        if 'rise as one' in query_lower or 'rise' in query_lower:
            return 'rise_as_one'
        elif 'basketball factory' in query_lower or 'factory' in query_lower:
            return 'basketball_factory'
        elif 'house of sports' in query_lower:
            return 'house_of_sports'
        
        # Check keywords
        for source_id, source in self.sources.items():
            for keyword in source['keywords']:
                if keyword in query_lower:
                    # Return first match (can be made smarter with scoring)
                    return source_id
        
        # Default to house of sports for general queries
        return 'house_of_sports'
    
    def query_knowledge(self, user_question: str, context: Dict = None) -> Dict:
        """
        Query the knowledge base to answer customer questions
        Uses Abacus AI LLM with knowledge from all three websites
        """
        
        if context is None:
            context = {}
        
        # Determine relevant source
        relevant_source_id = self.get_relevant_source(user_question)
        relevant_source = self.sources.get(relevant_source_id, {})
        
        print(f"\n[KNOWLEDGE BASE] Query: '{user_question}'")
        print(f"[KNOWLEDGE BASE] Relevant source: {relevant_source.get('name', 'Unknown')}")
        
        # Build context-aware prompt
        prompt = self._build_knowledge_prompt(user_question, relevant_source, context)
        
        # Query Abacus AI LLM
        if self.abacus_api_key:
            response = self._query_abacus_llm(prompt)
        else:
            response = self._fallback_response(user_question, relevant_source)
        
        return {
            'answer': response,
            'source': relevant_source.get('name'),
            'source_url': relevant_source.get('url'),
            'confidence': 'high' if self.abacus_api_key else 'low'
        }
    
    def _build_knowledge_prompt(self, question: str, source: Dict, context: Dict) -> str:
        """
        Build a comprehensive prompt with knowledge base context
        """
        
        # Base knowledge about all three organizations
        knowledge_base_text = """
        You are a helpful assistant for three connected sports organizations:

        1. HOUSE OF SPORTS:
        - Premier sports facility with indoor basketball courts
        - Located at multiple locations across the region
        - Offers hourly court rentals, birthday party packages, leagues, and training
        - Pricing: $75-125/hour for basketball court rentals depending on time and day
        - Birthday party packages starting at $250
        - Open 7 days a week, 6 AM - 11 PM
        - Amenities: Professional courts, locker rooms, concessions, WiFi
        - Contact: (555) 123-4567
        
        2. RISE AS ONE:
        - Youth basketball development program
        - Focus on skill development, teamwork, and character building
        - Programs for ages 8-18
        - Seasonal training programs and camps
        - Experienced coaching staff
        - Values: Teamwork, Dedication, Excellence, Respect
        - Practices held at House of Sports facilities
        
        3. BASKETBALL FACTORY INC:
        - Elite basketball training and player development
        - Individual and group training sessions
        - College prep and recruiting assistance
        - Advanced skill development programs
        - Professional coaching staff with college and pro experience
        - Training sessions held at House of Sports facilities
        """
        
        # Add specific source context
        if source:
            knowledge_base_text += f"\n\nThe customer's question is most relevant to: {source.get('name')} - {source.get('description')}\n"
        
        # Add current conversation context
        context_text = ""
        if context.get('service_type'):
            context_text += f"\nCustomer is interested in: {context['service_type']}\n"
        if context.get('selected_option'):
            context_text += f"Customer selected: {context['selected_option']}\n"
        
        prompt = f"""{knowledge_base_text}
        
        {context_text}
        
        Customer Question: {question}
        
        Instructions:
        - Answer the question helpfully and accurately based on the knowledge above
        - If the question is about pricing, availability, or booking, provide relevant information
        - If you need to transfer to a specific organization, mention which one
        - Keep answers concise but informative (2-3 sentences)
        - Be friendly and professional
        
        Answer:"""
        
        return prompt
    
    def _query_abacus_llm(self, prompt: str) -> str:
        """
        Query Abacus AI LLM API
        """
        try:
            # Use OpenAI-compatible endpoint with Abacus AI key
            headers = {
                'Authorization': f'Bearer {self.abacus_api_key}',
                'Content-Type': 'application/json'
            }
            
            # Abacus AI endpoint (OpenAI-compatible)
            url = "https://api.abacus.ai/v1/chat/completions"
            
            payload = {
                "model": "gpt-4",  # or another model available through Abacus AI
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant for House of Sports, Rise as One, and Basketball Factory Inc."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 200
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                print(f"[KNOWLEDGE BASE] ✓ Got response from Abacus AI LLM")
                return answer.strip()
            else:
                print(f"[KNOWLEDGE BASE] ✗ LLM API error: {response.status_code}")
                return self._fallback_response(prompt, {})
                
        except Exception as e:
            print(f"[KNOWLEDGE BASE] ✗ Error querying LLM: {e}")
            return self._fallback_response(prompt, {})
    
    def _fallback_response(self, question: str, source: Dict) -> str:
        """
        Fallback response when LLM is not available
        """
        question_lower = question.lower()
        
        # Pricing questions
        if any(word in question_lower for word in ['price', 'cost', 'how much', 'rates']):
            return "Our basketball court rentals range from $75-125 per hour depending on the time and day. Birthday party packages start at $250. For detailed pricing, I can transfer you to our staff or you can visit houseofsports.com."
        
        # Availability questions
        elif any(word in question_lower for word in ['available', 'availability', 'open', 'hours']):
            return "We're open 7 days a week from 6 AM to 11 PM. Court availability varies, so I can check specific dates and times for you. What date and time were you interested in?"
        
        # Programs/training questions
        elif any(word in question_lower for word in ['program', 'training', 'coach', 'lessons']):
            source_name = source.get('name', 'our organizations')
            return f"{source_name} offers various programs and training options. We have programs for youth development, elite training, and skill building. Would you like me to transfer you to learn more about specific programs?"
        
        # Location questions
        elif any(word in question_lower for word in ['location', 'address', 'where']):
            return "We have multiple House of Sports locations across the region. To find the closest location to you, I can transfer you to our staff or you can visit houseofsports.com for a full list of locations."
        
        # General
        else:
            return "I can help you with information about our facilities, programs, pricing, and bookings. What would you like to know more about?"
    
    def get_all_sources_info(self) -> List[Dict]:
        """
        Get information about all knowledge sources
        """
        return [
            {
                'id': source_id,
                'name': source['name'],
                'url': source['url'],
                'description': source['description']
            }
            for source_id, source in self.sources.items()
        ]


# Global instance
knowledge_base = KnowledgeBase()
