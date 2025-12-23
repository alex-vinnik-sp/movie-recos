"""Evaluators for movie recommendation agent."""

import os
import re
import json
import time
import logging
from typing import Dict, Any, Optional
from difflib import SequenceMatcher

from langchain_aws import ChatBedrock
from langsmith import Client

logger = logging.getLogger(__name__)


def _get_evaluator_llm() -> ChatBedrock:
    """Get the LLM instance for evaluators (same as agent)."""
    model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    
    return ChatBedrock(
        model_id=model_id,
        region_name=aws_region,
        model_kwargs={"temperature": 0}  # Use temperature 0 for consistent evaluation
    )


def relevance_evaluator(
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
    reference_outputs: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    LLM-as-judge evaluator for relevance of movie recommendations.
    
    Uses Claude Haiku to judge if recommendations match the user's query intent.
    
    Args:
        inputs: Input dictionary containing the user query
        outputs: Output dictionary containing the agent's response
        reference_outputs: Optional reference outputs (not used for LLM-as-judge)
        
    Returns:
        Dictionary with 'score' (0-1) and 'reasoning' fields
    """
    try:
        query = inputs.get("query") or inputs.get("text") or inputs.get("user_prompt", "")
        response = outputs.get("output", "")
        
        if not query or not response:
            return {
                "score": 0.0,
                "reasoning": "Missing query or response"
            }
        
        llm = _get_evaluator_llm()
        
        evaluation_prompt = f"""You are evaluating a movie recommendation system. Your task is to determine how well the recommendations match the user's query.

User Query: "{query}"

Agent Response:
{response}

Evaluate the relevance of the recommendations:
1. Do the recommended movies match the user's request (genre, style, preferences)?
2. Are the recommendations appropriate for what the user asked for?
3. Does the response address the user's intent?

Respond with a JSON object containing:
- "score": a float between 0.0 and 1.0 (1.0 = perfect match, 0.0 = completely irrelevant)
- "reasoning": a brief explanation of your score

JSON Response:"""
        
        result = llm.invoke(evaluation_prompt)
        content = result.content.strip()
        
        # Try to extract JSON from the response
        json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
        if json_match:
            try:
                eval_result = json.loads(json_match.group())
                score = float(eval_result.get("score", 0.0))
                reasoning = eval_result.get("reasoning", content)
                return {
                    "score": max(0.0, min(1.0, score)),  # Clamp to [0, 1]
                    "reasoning": reasoning
                }
            except json.JSONDecodeError:
                pass
        
        # Fallback: try to extract score from text
        score_match = re.search(r'score["\']?\s*:\s*([0-9.]+)', content, re.IGNORECASE)
        if score_match:
            score = float(score_match.group(1))
            return {
                "score": max(0.0, min(1.0, score)),
                "reasoning": content
            }
        
        # If we can't parse, return a default score based on keyword matching
        query_lower = query.lower()
        response_lower = response.lower()
        
        # Simple heuristic: check if response contains relevant keywords
        relevant_keywords = ["movie", "film", "recommendation", "suggest"]
        has_keywords = any(kw in response_lower for kw in relevant_keywords)
        
        return {
            "score": 0.5 if has_keywords else 0.0,
            "reasoning": f"Could not parse LLM response. Fallback score based on keyword matching. Original response: {content[:200]}"
        }
        
    except Exception as e:
        logger.error(f"Error in relevance_evaluator: {str(e)}", exc_info=True)
        return {
            "score": 0.0,
            "reasoning": f"Error during evaluation: {str(e)}"
        }


def completeness_evaluator(
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
    reference_outputs: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluates if the response contains sufficient information.
    
    Checks for:
    - Movie titles
    - Ratings or scores
    - Brief descriptions or overviews
    - Minimum number of recommendations (at least 2-3)
    
    Args:
        inputs: Input dictionary
        outputs: Output dictionary with agent response
        reference_outputs: Optional reference outputs
        
    Returns:
        Dictionary with 'score' (0-1) and 'reasoning' fields
    """
    try:
        response = outputs.get("output", "")
        
        if not response:
            return {
                "score": 0.0,
                "reasoning": "Empty response"
            }
        
        # Check for movie titles (look for patterns like "Title (Year)" or numbered lists)
        movie_patterns = [
            r'\d+\.\s+[A-Z][^:]+',  # Numbered list items
            r'[-*•]\s+[A-Z][^:]+',  # Bullet points
            r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+\(\d{4}\))?',  # Title patterns
        ]
        
        found_titles = []
        for pattern in movie_patterns:
            matches = re.findall(pattern, response)
            found_titles.extend(matches)
        
        # Check for ratings (look for patterns like "8.5/10", "4.5 stars", "rating: 7.2")
        rating_patterns = [
            r'\d+\.?\d*\s*/?\s*10',
            r'\d+\.?\d*\s*stars?',
            r'rating[:\s]+\d+\.?\d*',
            r'\d+\.?\d*\s*\/\s*10',
        ]
        
        found_ratings = []
        for pattern in rating_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            found_ratings.extend(matches)
        
        # Check for descriptions (look for longer sentences, overview text)
        sentences = re.split(r'[.!?]\s+', response)
        descriptive_sentences = [s for s in sentences if len(s.split()) > 10]
        
        # Calculate score components
        has_titles = len(found_titles) >= 2  # At least 2 recommendations
        has_ratings = len(found_ratings) >= 1  # At least one rating mentioned
        has_descriptions = len(descriptive_sentences) >= 2  # At least 2 descriptive sentences
        
        score = 0.0
        reasoning_parts = []
        
        if has_titles:
            score += 0.4
            reasoning_parts.append(f"Found {len(found_titles)} potential movie titles")
        else:
            reasoning_parts.append(f"Only found {len(found_titles)} movie titles (need at least 2)")
        
        if has_ratings:
            score += 0.3
            reasoning_parts.append(f"Found {len(found_ratings)} ratings")
        else:
            reasoning_parts.append("No ratings found")
        
        if has_descriptions:
            score += 0.3
            reasoning_parts.append(f"Found {len(descriptive_sentences)} descriptive sentences")
        else:
            reasoning_parts.append("Insufficient descriptions")
        
        return {
            "score": min(1.0, score),
            "reasoning": "; ".join(reasoning_parts)
        }
        
    except Exception as e:
        logger.error(f"Error in completeness_evaluator: {str(e)}", exc_info=True)
        return {
            "score": 0.0,
            "reasoning": f"Error during evaluation: {str(e)}"
        }


def format_quality_evaluator(
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
    reference_outputs: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluates the format quality and readability of the response.
    
    Checks for:
    - Proper formatting (markdown, lists)
    - No broken text or formatting errors
    - Readable structure
    - Appropriate length
    
    Args:
        inputs: Input dictionary
        outputs: Output dictionary with agent response
        reference_outputs: Optional reference outputs
        
    Returns:
        Dictionary with 'score' (0-1) and 'reasoning' fields
    """
    try:
        response = outputs.get("output", "")
        
        if not response:
            return {
                "score": 0.0,
                "reasoning": "Empty response"
            }
        
        score = 1.0
        issues = []
        
        # Check for broken markdown (unclosed brackets, unmatched formatting)
        open_brackets = response.count('[') - response.count(']')
        open_parens = response.count('(') - response.count(')')
        open_braces = response.count('{') - response.count('}')
        
        if open_brackets != 0:
            score -= 0.2
            issues.append(f"Unmatched brackets (difference: {open_brackets})")
        
        if open_parens != 0:
            score -= 0.1
            issues.append(f"Unmatched parentheses (difference: {open_parens})")
        
        if open_braces != 0:
            score -= 0.1
            issues.append(f"Unmatched braces (difference: {open_braces})")
        
        # Check for excessive whitespace or formatting issues
        if re.search(r'\n{4,}', response):  # 4+ consecutive newlines
            score -= 0.1
            issues.append("Excessive newlines")
        
        if re.search(r' {3,}', response):  # 3+ consecutive spaces
            score -= 0.05
            issues.append("Excessive spaces")
        
        # Check for reasonable length (not too short, not too long)
        word_count = len(response.split())
        if word_count < 20:
            score -= 0.2
            issues.append(f"Response too short ({word_count} words)")
        elif word_count > 2000:
            score -= 0.1
            issues.append(f"Response very long ({word_count} words)")
        
        # Check for basic structure (has some organization)
        has_structure = bool(
            re.search(r'\n', response) or  # Has line breaks
            re.search(r'[0-9]+\.', response) or  # Has numbered list
            re.search(r'[-*•]', response)  # Has bullet points
        )
        
        if not has_structure and word_count > 50:
            score -= 0.15
            issues.append("Lacks clear structure/organization")
        
        return {
            "score": max(0.0, score),
            "reasoning": "; ".join(issues) if issues else "Good formatting and structure"
        }
        
    except Exception as e:
        logger.error(f"Error in format_quality_evaluator: {str(e)}", exc_info=True)
        return {
            "score": 0.0,
            "reasoning": f"Error during evaluation: {str(e)}"
        }


def tool_usage_evaluator(
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
    reference_outputs: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluates if appropriate tools were used.
    
    Note: This evaluator requires access to trace data. In LangSmith,
    trace information is available through the evaluation context.
    For now, we'll check if the response suggests tools were used.
    
    Args:
        inputs: Input dictionary
        outputs: Output dictionary with agent response
        reference_outputs: Optional reference outputs
        
    Returns:
        Dictionary with 'score' (0-1) and 'reasoning' fields
    """
    try:
        response = outputs.get("output", "")
        query = inputs.get("query") or inputs.get("text") or inputs.get("user_prompt", "")
        
        if not response:
            return {
                "score": 0.0,
                "reasoning": "Empty response"
            }
        
        score = 0.0
        reasoning_parts = []
        
        # Check if response contains movie-specific information (suggests search_movies was used)
        # Look for patterns that suggest TMDB data: ratings, release dates, movie IDs, etc.
        has_rating = bool(re.search(r'\d+\.?\d*\s*/?\s*10|\d+\.?\d*\s*stars?', response, re.IGNORECASE))
        has_release_date = bool(re.search(r'\d{4}', response))  # Year mentioned
        has_movie_details = bool(re.search(r'(rating|release|director|cast|genre)', response, re.IGNORECASE))
        
        if has_rating or has_release_date or has_movie_details:
            score += 0.5
            reasoning_parts.append("Response contains movie-specific data (suggests search_movies was used)")
        else:
            reasoning_parts.append("No clear evidence of movie-specific data")
        
        # Check if response seems informed (suggests tools were used rather than hallucination)
        # Generic responses without specific details suggest tools weren't used
        generic_phrases = [
            "here are some movies",
            "you might like",
            "some recommendations",
        ]
        
        is_generic = any(phrase in response.lower() for phrase in generic_phrases)
        has_specific_info = bool(re.search(r'\d+\.?\d*|\(|\)', response))  # Has numbers or structured info
        
        if has_specific_info and not is_generic:
            score += 0.5
            reasoning_parts.append("Response contains specific information (suggests tools were used)")
        elif is_generic and not has_specific_info:
            score -= 0.3
            reasoning_parts.append("Response seems generic without specific details")
        
        # Note: Full tool usage analysis would require trace data access
        # This is a heuristic-based approach
        reasoning_parts.append("(Note: Full tool usage requires trace data access)")
        
        return {
            "score": max(0.0, min(1.0, score)),
            "reasoning": "; ".join(reasoning_parts)
        }
        
    except Exception as e:
        logger.error(f"Error in tool_usage_evaluator: {str(e)}", exc_info=True)
        return {
            "score": 0.0,
            "reasoning": f"Error during evaluation: {str(e)}"
        }


def response_time_evaluator(
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
    reference_outputs: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluates response time/latency.
    
    Note: This evaluator would ideally measure actual response time.
    For LangSmith evaluations, timing information is typically available
    in the trace metadata. This is a placeholder that checks if timing
    info is available in outputs.
    
    Args:
        inputs: Input dictionary
        outputs: Output dictionary (may contain timing info)
        reference_outputs: Optional reference outputs
        
    Returns:
        Dictionary with 'score' (0-1) and 'reasoning' fields
    """
    try:
        # Check if timing information is in outputs
        # LangSmith may provide this in trace metadata
        timing_info = outputs.get("latency") or outputs.get("response_time") or outputs.get("duration")
        
        if timing_info:
            # Acceptable threshold: under 30 seconds
            threshold = 30.0
            if isinstance(timing_info, (int, float)):
                if timing_info <= threshold:
                    return {
                        "score": 1.0,
                        "reasoning": f"Response time {timing_info:.2f}s is within acceptable threshold ({threshold}s)"
                    }
                else:
                    # Score decreases as time increases
                    score = max(0.0, 1.0 - (timing_info - threshold) / threshold)
                    return {
                        "score": score,
                        "reasoning": f"Response time {timing_info:.2f}s exceeds threshold ({threshold}s)"
                    }
        
        # If no timing info available, return neutral score
        return {
            "score": 0.5,
            "reasoning": "Timing information not available in outputs (check trace metadata)"
        }
        
    except Exception as e:
        logger.error(f"Error in response_time_evaluator: {str(e)}", exc_info=True)
        return {
            "score": 0.0,
            "reasoning": f"Error during evaluation: {str(e)}"
        }


def _fuzzy_match_title(title1: str, title2: str, threshold: float = 0.8) -> bool:
    """Check if two movie titles are similar using fuzzy matching."""
    title1_clean = re.sub(r'[^\w\s]', '', title1.lower()).strip()
    title2_clean = re.sub(r'[^\w\s]', '', title2.lower()).strip()
    
    similarity = SequenceMatcher(None, title1_clean, title2_clean).ratio()
    return similarity >= threshold


def ground_truth_evaluator(
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
    reference_outputs: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Compares actual outputs to reference/ground truth outputs.
    
    Uses fuzzy matching for movie titles to handle variations.
    
    Args:
        inputs: Input dictionary
        outputs: Output dictionary with agent response
        reference_outputs: Reference outputs with expected movies
        
    Returns:
        Dictionary with 'score' (0-1) and 'reasoning' fields
    """
    try:
        if not reference_outputs:
            return {
                "score": 0.5,
                "reasoning": "No reference outputs provided for comparison"
            }
        
        response = outputs.get("output", "")
        expected_output = reference_outputs.get("output") or reference_outputs.get("expected", "")
        
        if not response or not expected_output:
            return {
                "score": 0.0,
                "reasoning": "Missing response or expected output"
            }
        
        # Extract movie titles from both responses
        # Look for patterns like "Title (Year)" or just titles
        def extract_titles(text: str) -> list:
            # Try to find titles in various formats
            titles = []
            
            # Pattern 1: "Title (Year)"
            pattern1 = r'([A-Z][^\(]+?)\s*\(\d{4}\)'
            matches = re.findall(pattern1, text)
            titles.extend([m.strip() for m in matches])
            
            # Pattern 2: Numbered or bulleted list items
            pattern2 = r'[0-9]+\.\s+([A-Z][^:\n]+?)(?:\s*\(|$|:)'
            matches = re.findall(pattern2, text)
            titles.extend([m.strip() for m in matches])
            
            # Pattern 3: Bullet points
            pattern3 = r'[-*•]\s+([A-Z][^:\n]+?)(?:\s*\(|$|:)'
            matches = re.findall(pattern3, text)
            titles.extend([m.strip() for m in matches])
            
            return titles
        
        expected_titles = extract_titles(expected_output)
        actual_titles = extract_titles(response)
        
        if not expected_titles:
            # If we can't extract expected titles, do a simple text similarity check
            similarity = SequenceMatcher(None, response.lower(), expected_output.lower()).ratio()
            return {
                "score": similarity,
                "reasoning": f"Could not extract movie titles. Text similarity: {similarity:.2f}"
            }
        
        # Count matches using fuzzy matching
        matches = 0
        matched_titles = []
        
        for expected_title in expected_titles:
            for actual_title in actual_titles:
                if _fuzzy_match_title(expected_title, actual_title):
                    matches += 1
                    matched_titles.append(expected_title)
                    break
        
        # Calculate score based on how many expected titles were found
        if expected_titles:
            score = matches / len(expected_titles)
            reasoning = f"Found {matches}/{len(expected_titles)} expected movies"
            if matched_titles:
                reasoning += f": {', '.join(matched_titles[:3])}"
        else:
            score = 0.0
            reasoning = "No expected titles found in reference output"
        
        return {
            "score": max(0.0, min(1.0, score)),
            "reasoning": reasoning
        }
        
    except Exception as e:
        logger.error(f"Error in ground_truth_evaluator: {str(e)}", exc_info=True)
        return {
            "score": 0.0,
            "reasoning": f"Error during evaluation: {str(e)}"
        }

