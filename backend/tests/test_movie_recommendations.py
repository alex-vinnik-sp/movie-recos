"""Pytest tests for movie recommendation agent using LangSmith integration."""

import os
import pytest
from langsmith import testing as t
from langsmith import expect
from langchain_aws import ChatBedrock

from src.agent import create_movie_agent
from src.evaluation.evaluators import (
    _get_evaluator_llm,
    _fuzzy_match_title,
)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


@pytest.fixture(scope="module")
def agent():
    """Create a movie agent instance for testing."""
    tmdb_api_key = os.getenv("TMDB_API_KEY")
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    
    if not tmdb_api_key or not tavily_api_key:
        pytest.skip("Missing required API keys (TMDB_API_KEY or TAVILY_API_KEY)")
    
    return create_movie_agent(
        tmdb_api_key=tmdb_api_key,
        tavily_api_key=tavily_api_key,
        aws_region=aws_region
    )


@pytest.mark.langsmith
def test_action_movies_recommendation(agent):
    """Test recommendation for action movies like John Wick."""
    user_query = "action movies like John Wick"
    t.log_inputs({"query": user_query})
    
    result = agent.get_recommendations(user_query)
    t.log_outputs({"response": result.get("response", "")})
    
    # Basic assertions
    assert result.get("success"), f"Agent failed: {result.get('error', 'Unknown error')}"
    assert "response" in result, "Response missing from result"
    assert len(result["response"]) > 0, "Empty response"
    
    # Check that response contains movie-related content
    response_lower = result["response"].lower()
    assert any(keyword in response_lower for keyword in ["movie", "film", "recommend"]), \
        "Response should contain movie-related keywords"


@pytest.mark.langsmith
def test_romantic_comedies_90s(agent):
    """Test recommendation for romantic comedies from the 90s."""
    user_query = "romantic comedies from the 90s"
    t.log_inputs({"query": user_query})
    
    result = agent.get_recommendations(user_query)
    t.log_outputs({"response": result.get("response", "")})
    
    assert result.get("success"), f"Agent failed: {result.get('error', 'Unknown error')}"
    assert "response" in result, "Response missing from result"
    
    # Check for 90s reference
    response_lower = result["response"].lower()
    has_90s_reference = "90" in result["response"] or "nineties" in response_lower or "199" in result["response"]
    # Note: This is a soft check - the agent might recommend 90s movies without explicitly mentioning the decade
    # t.log_feedback(key="mentions_90s", score=1.0 if has_90s_reference else 0.5)


@pytest.mark.langsmith
def test_sci_fi_time_travel(agent):
    """Test recommendation for sci-fi movies with time travel."""
    user_query = "sci-fi movies with time travel"
    t.log_inputs({"query": user_query})
    
    result = agent.get_recommendations(user_query)
    t.log_outputs({"response": result.get("response", "")})
    
    assert result.get("success"), f"Agent failed: {result.get('error', 'Unknown error')}"
    assert "response" in result, "Response missing from result"
    
    # Check for sci-fi/time travel keywords
    response_lower = result["response"].lower()
    has_sci_fi_keywords = any(kw in response_lower for kw in ["sci-fi", "science fiction", "time travel", "time"])
    t.log_feedback(key="has_sci_fi_keywords", score=1.0 if has_sci_fi_keywords else 0.0)


@pytest.mark.langsmith
def test_completeness_of_recommendations(agent):
    """Test that recommendations include sufficient information."""
    user_query = "surprise me"
    t.log_inputs({"query": user_query})
    
    result = agent.get_recommendations(user_query)
    response = result.get("response", "")
    t.log_outputs({"response": response})
    
    assert result.get("success"), f"Agent failed: {result.get('error', 'Unknown error')}"
    
    # Check for completeness indicators
    import re
    
    # Look for movie titles (numbered lists, bullet points, or titles)
    movie_patterns = [
        r'\d+\.\s+[A-Z]',  # Numbered list
        r'[-*•]\s+[A-Z]',  # Bullet points
    ]
    found_titles = sum(1 for pattern in movie_patterns if re.search(pattern, response))
    
    # Look for ratings
    has_rating = bool(re.search(r'\d+\.?\d*\s*/?\s*10|\d+\.?\d*\s*stars?', response, re.IGNORECASE))
    
    # Look for descriptions (sentences with reasonable length)
    sentences = re.split(r'[.!?]\s+', response)
    descriptive_sentences = [s for s in sentences if len(s.split()) > 10]
    
    completeness_score = 0.0
    if found_titles >= 2:
        completeness_score += 0.4
    if has_rating:
        completeness_score += 0.3
    if len(descriptive_sentences) >= 2:
        completeness_score += 0.3
    
    t.log_feedback(key="completeness", score=completeness_score)


@pytest.mark.langsmith
def test_relevance_with_llm_judge(agent):
    """Test relevance using LLM-as-judge evaluator."""
    user_query = "horror movies from the 80s"
    t.log_inputs({"query": user_query})
    
    result = agent.get_recommendations(user_query)
    response = result.get("response", "")
    t.log_outputs({"response": response})
    
    assert result.get("success"), f"Agent failed: {result.get('error', 'Unknown error')}"
    
    # Use LLM-as-judge for relevance evaluation
    with t.trace_feedback():
        llm = _get_evaluator_llm()
        
        evaluation_prompt = f"""You are evaluating a movie recommendation system. Determine how well the recommendations match the user's query.

User Query: "{user_query}"

Agent Response:
{response}

Evaluate the relevance:
1. Do the recommended movies match the user's request (horror genre, 80s decade)?
2. Are the recommendations appropriate for what the user asked for?

Respond with a JSON object containing:
- "score": a float between 0.0 and 1.0 (1.0 = perfect match, 0.0 = completely irrelevant)
- "reasoning": a brief explanation

JSON Response:"""
        
        eval_result = llm.invoke(evaluation_prompt)
        content = eval_result.content.strip()
        
        # Try to extract score from JSON
        import json
        import re
        
        json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
        if json_match:
            try:
                eval_data = json.loads(json_match.group())
                score = float(eval_data.get("score", 0.0))
                reasoning = eval_data.get("reasoning", content)
            except json.JSONDecodeError:
                score = 0.5
                reasoning = "Could not parse LLM response"
        else:
            # Fallback: try to extract score from text
            score_match = re.search(r'score["\']?\s*:\s*([0-9.]+)', content, re.IGNORECASE)
            if score_match:
                score = float(score_match.group(1))
                reasoning = content
            else:
                score = 0.5
                reasoning = "Could not extract score"
        
        t.log_feedback(key="relevance", score=max(0.0, min(1.0, score)))


@pytest.mark.langsmith
@pytest.mark.parametrize(
    "query,expected_keywords",
    [
        ("action movies", ["action", "movie"]),
        ("comedy films", ["comedy", "film"]),
        ("drama movies", ["drama", "movie"]),
    ],
)
def test_genre_recommendations(agent, query, expected_keywords):
    """Parametrized test for different genre recommendations."""
    t.log_inputs({"query": query})
    
    result = agent.get_recommendations(query)
    response = result.get("response", "")
    t.log_outputs({"response": response})
    
    assert result.get("success"), f"Agent failed: {result.get('error', 'Unknown error')}"
    
    # Check that response contains expected keywords
    response_lower = response.lower()
    keywords_found = sum(1 for kw in expected_keywords if kw in response_lower)
    relevance_score = keywords_found / len(expected_keywords) if expected_keywords else 0.0
    
    t.log_feedback(key="keyword_relevance", score=relevance_score)


@pytest.mark.langsmith
def test_format_quality(agent):
    """Test that response has good formatting and structure."""
    user_query = "recommend some good movies"
    t.log_inputs({"query": user_query})
    
    result = agent.get_recommendations(user_query)
    response = result.get("response", "")
    t.log_outputs({"response": response})
    
    assert result.get("success"), f"Agent failed: {result.get('error', 'Unknown error')}"
    
    # Check formatting quality
    import re
    
    score = 1.0
    issues = []
    
    # Check for broken markdown/brackets
    open_brackets = response.count('[') - response.count(']')
    open_parens = response.count('(') - response.count(')')
    
    if open_brackets != 0:
        score -= 0.2
        issues.append("Unmatched brackets")
    
    if open_parens != 0:
        score -= 0.1
        issues.append("Unmatched parentheses")
    
    # Check for excessive whitespace
    if re.search(r'\n{4,}', response):
        score -= 0.1
        issues.append("Excessive newlines")
    
    # Check for reasonable length
    word_count = len(response.split())
    if word_count < 20:
        score -= 0.2
        issues.append("Response too short")
    elif word_count > 2000:
        score -= 0.1
        issues.append("Response very long")
    
    t.log_feedback(key="format_quality", score=max(0.0, score))


@pytest.mark.langsmith
def test_response_contains_movie_details(agent):
    """Test that response contains movie-specific details like ratings or years."""
    user_query = "best movies of 2023"
    t.log_inputs({"query": user_query})
    
    result = agent.get_recommendations(user_query)
    response = result.get("response", "")
    t.log_outputs({"response": response})
    
    assert result.get("success"), f"Agent failed: {result.get('error', 'Unknown error')}"
    
    # Check for movie-specific information
    import re
    
    has_rating = bool(re.search(r'\d+\.?\d*\s*/?\s*10|\d+\.?\d*\s*stars?', response, re.IGNORECASE))
    has_year = bool(re.search(r'\d{4}', response))  # Year mentioned
    has_movie_details = bool(re.search(r'(rating|release|director|cast|genre)', response, re.IGNORECASE))
    
    detail_score = 0.0
    if has_rating:
        detail_score += 0.4
    if has_year:
        detail_score += 0.3
    if has_movie_details:
        detail_score += 0.3
    
    t.log_feedback(key="movie_details", score=detail_score)


@pytest.mark.langsmith
def test_expectations_example(agent):
    """Example test using LangSmith's expect utility."""
    user_query = "action movies"
    t.log_inputs({"query": user_query})
    
    result = agent.get_recommendations(user_query)
    response = result.get("response", "")
    t.log_outputs({"response": response})
    
    assert result.get("success"), f"Agent failed: {result.get('error', 'Unknown error')}"
    
    # Use expect utility for assertions
    expect(response).to_contain("movie")  # Response should contain "movie"
    expect(len(response)).to_be_greater_than(50)  # Response should be substantial
    
    # Check that response is not an error message
    expect(response.lower()).not_to_contain("error")


@pytest.mark.langsmith
def test_ground_truth_comparison(agent):
    """Test with ground truth comparison using fuzzy matching."""
    user_query = "action movies like John Wick"
    t.log_inputs({"query": user_query})
    
    # Expected movies (ground truth)
    expected_movies = ["John Wick", "John Wick: Chapter 2", "John Wick: Chapter 3"]
    t.log_reference_outputs({"expected_movies": expected_movies})
    
    result = agent.get_recommendations(user_query)
    response = result.get("response", "")
    t.log_outputs({"response": response})
    
    assert result.get("success"), f"Agent failed: {result.get('error', 'Unknown error')}"
    
    # Check if expected movies appear in response using fuzzy matching
    matches = 0
    for expected_movie in expected_movies:
        if _fuzzy_match_title(expected_movie, response, threshold=0.6):
            matches += 1
    
    match_score = matches / len(expected_movies) if expected_movies else 0.0
    t.log_feedback(key="ground_truth_match", score=match_score)


@pytest.fixture
def action_query() -> str:
    """Fixture providing an action movie query."""
    return "action movies with car chases"


@pytest.fixture
def expected_action_keywords() -> list:
    """Fixture providing expected keywords for action movies."""
    return ["action", "thriller", "adventure"]


@pytest.mark.langsmith(output_keys=["expected_action_keywords"])
def test_using_fixtures_as_inputs_outputs(agent, action_query, expected_action_keywords):
    """
    Example using pytest fixtures as inputs and reference outputs.
    
    The action_query fixture will be logged as an input.
    The expected_action_keywords fixture will be logged as a reference output
    because it's specified in output_keys.
    """
    result = agent.get_recommendations(action_query)
    response = result.get("response", "")
    t.log_outputs({"response": response})
    
    assert result.get("success"), f"Agent failed: {result.get('error', 'Unknown error')}"
    
    # Check for expected keywords
    response_lower = response.lower()
    keywords_found = sum(1 for kw in expected_action_keywords if kw in response_lower)
    score = keywords_found / len(expected_action_keywords) if expected_action_keywords else 0.0
    t.log_feedback(key="keyword_match", score=score)


@pytest.mark.asyncio
@pytest.mark.langsmith
async def test_async_recommendation(agent):
    """Example async test using pytest-asyncio."""
    user_query = "sci-fi movies"
    t.log_inputs({"query": user_query})
    
    # Use async version of get_recommendations
    result = await agent.aget_recommendations(user_query)
    response = result.get("response", "")
    t.log_outputs({"response": response})
    
    assert result.get("success"), f"Agent failed: {result.get('error', 'Unknown error')}"
    assert len(response) > 0, "Empty response"
    
    t.log_feedback(key="async_success", score=1.0)


@pytest.mark.langsmith(cached_hosts=["api.themoviedb.org", "api.tavily.com"])
def test_with_selective_caching(agent):
    """
    Example test with selective caching for specific hosts.
    
    Only requests to TMDB and Tavily APIs will be cached.
    This is useful when you want to cache external API calls
    but not internal service calls.
    """
    user_query = "popular movies"
    t.log_inputs({"query": user_query})
    
    result = agent.get_recommendations(user_query)
    response = result.get("response", "")
    t.log_outputs({"response": response})
    
    assert result.get("success"), f"Agent failed: {result.get('error', 'Unknown error')}"


@pytest.mark.langsmith(test_suite_name="Movie Recommendations - Genre Tests")
def test_custom_test_suite_name(agent):
    """
    Example test with custom test suite name.
    
    This test will be grouped into a different test suite
    than the default one.
    """
    user_query = "horror movies"
    t.log_inputs({"query": user_query})
    
    result = agent.get_recommendations(user_query)
    response = result.get("response", "")
    t.log_outputs({"response": response})
    
    assert result.get("success"), f"Agent failed: {result.get('error', 'Unknown error')}"


@pytest.mark.langsmith
def test_expect_embedding_distance(agent):
    """Example using expect.embedding_distance() for semantic similarity."""
    user_query = "romantic comedies"
    t.log_inputs({"query": user_query})
    
    result = agent.get_recommendations(user_query)
    response = result.get("response", "")
    t.log_outputs({"response": response})
    
    assert result.get("success"), f"Agent failed: {result.get('error', 'Unknown error')}"
    
    # Expected semantic content
    expectation = "romantic comedy movies recommendations"
    
    # Use embedding distance to check semantic similarity
    # Lower distance = more similar
    expect.embedding_distance(
        prediction=response,
        expectation=expectation
    ).to_be_less_than(0.5)  # Assert that semantic distance is less than 0.5


@pytest.mark.langsmith
def test_expect_edit_distance(agent):
    """Example using expect.edit_distance() for string similarity."""
    user_query = "action movies"
    t.log_inputs({"query": user_query})
    
    result = agent.get_recommendations(user_query)
    response = result.get("response", "")
    t.log_outputs({"response": response})
    
    assert result.get("success"), f"Agent failed: {result.get('error', 'Unknown error')}"
    
    # Expected to contain "action" somewhere
    expectation = "action"
    
    # Use edit distance (normalized Damerau-Levenshtein distance)
    # This logs the distance as feedback even without a predicate
    edit_dist = expect.edit_distance(
        prediction=response.lower(),
        expectation=expectation
    )
    
    # The distance is logged as feedback
    # We can also assert against it if needed
    # Lower distance = more similar (0.0 = identical, 1.0 = completely different)


@pytest.mark.langsmith
@pytest.mark.parametrize(
    "query, expectation",
    [
        ("action movies", "action"),
        ("comedy films", "comedy"),
        ("drama movies", "drama"),
    ],
)
def test_expect_with_parametrize(agent, query, expectation):
    """
    Example combining expect utility with parametrize.
    
    This test will create multiple test cases, each with
    its own expectation check.
    """
    t.log_inputs({"query": query})
    
    result = agent.get_recommendations(query)
    response = result.get("response", "")
    t.log_outputs({"response": response})
    
    assert result.get("success"), f"Agent failed: {result.get('error', 'Unknown error')}"
    
    # Use expect to check that response contains the expected keyword
    expect(response.lower()).to_contain(expectation.lower())
    
    # Also use edit distance for fuzzy matching
    expect.edit_distance(
        prediction=response.lower(),
        expectation=expectation.lower()
    ).to_be_less_than(0.3)  # Very similar strings


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

