#!/usr/bin/env python3
"""Main evaluation runner for movie recommendation agent."""

import os
import logging
from typing import List, Optional, Dict, Any
from langsmith import Client, evaluate

from src.evaluation.wrapper import evaluation_wrapper
from src.evaluation.evaluators import (
    relevance_evaluator,
    completeness_evaluator,
    format_quality_evaluator,
    tool_usage_evaluator,
    response_time_evaluator,
    ground_truth_evaluator,
)
from src.evaluation.dataset import create_initial_dataset

logger = logging.getLogger(__name__)


def run_evaluation(
    dataset_name: str = "movie-recommendations-1",
    experiment_prefix: str = "movie-recommender",
    description: Optional[str] = None,
    max_concurrency: int = 4,
    evaluators: Optional[List] = None,
    create_dataset_if_missing: bool = True
) -> Dict[str, Any]:
    """
    Run evaluation on the movie recommendation agent.
    
    Args:
        dataset_name: Name of the LangSmith dataset to evaluate on
        experiment_prefix: Prefix for the experiment name in LangSmith
        description: Optional description for the experiment
        max_concurrency: Maximum number of concurrent evaluations
        evaluators: Optional list of custom evaluators (defaults to all evaluators)
        create_dataset_if_missing: If True, create dataset with default examples if it doesn't exist
        
    Returns:
        Dictionary with evaluation results and summary
    """
    try:
        client = Client()
        
        # Check if dataset exists
        try:
            datasets = list(client.list_datasets(dataset_name=dataset_name))
            if not datasets:
                if create_dataset_if_missing:
                    logger.info(f"Dataset '{dataset_name}' not found. Creating it...")
                    create_initial_dataset(dataset_name)
                else:
                    raise ValueError(f"Dataset '{dataset_name}' not found. Set create_dataset_if_missing=True to create it automatically.")
        except Exception as e:
            logger.warning(f"Error checking for dataset: {str(e)}")
            if create_dataset_if_missing:
                logger.info("Creating dataset...")
                create_initial_dataset(dataset_name)
        
        # Default evaluators if not provided
        if evaluators is None:
            evaluators = [
                relevance_evaluator,
                completeness_evaluator,
                format_quality_evaluator,
                tool_usage_evaluator,
                response_time_evaluator,
                ground_truth_evaluator,
            ]
        
        logger.info(f"Starting evaluation on dataset '{dataset_name}' with {len(evaluators)} evaluators")
        logger.info(f"Experiment prefix: '{experiment_prefix}'")
        logger.info(f"Max concurrency: {max_concurrency}")
        
        # Run evaluation
        results = client.evaluate(
            evaluation_wrapper,
            data=dataset_name,
            evaluators=evaluators,
            experiment_prefix=experiment_prefix,
            description=description or f"Evaluation of movie recommendation agent: {experiment_prefix}",
            max_concurrency=max_concurrency,
        )
        
        logger.info("Evaluation completed successfully")
        
        # Calculate summary statistics
        summary = _calculate_summary(results)
        
        return {
            "success": True,
            "results": results,
            "summary": summary,
            "experiment_name": f"{experiment_prefix}-{results.experiment_name.split('-')[-1]}" if hasattr(results, 'experiment_name') else experiment_prefix
        }
        
    except Exception as e:
        logger.error(f"Error running evaluation: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def _calculate_summary(results) -> Dict[str, Any]:
    """
    Calculate summary statistics from evaluation results.
    
    Args:
        results: Evaluation results from LangSmith
        
    Returns:
        Dictionary with summary statistics
    """
    try:
        # Extract scores from results
        # The results object structure may vary, so we'll try to extract what we can
        summary = {
            "total_examples": 0,
            "evaluator_scores": {}
        }
        
        # Try to access results data
        if hasattr(results, 'results'):
            runs = results.results
        elif hasattr(results, 'runs'):
            runs = results.runs
        else:
            # Fallback: try to iterate over results
            runs = list(results) if hasattr(results, '__iter__') else []
        
        summary["total_examples"] = len(runs) if runs else 0
        
        # Extract scores by evaluator
        # This is a simplified version - actual structure depends on LangSmith's response
        if runs:
            # Try to get feedback/scores from runs
            for run in runs:
                if hasattr(run, 'feedback_stats'):
                    for evaluator_name, stats in run.feedback_stats.items():
                        if evaluator_name not in summary["evaluator_scores"]:
                            summary["evaluator_scores"][evaluator_name] = {
                                "scores": [],
                                "average": 0.0
                            }
                        # Extract scores (this is simplified - actual structure may differ)
                        if hasattr(stats, 'score'):
                            summary["evaluator_scores"][evaluator_name]["scores"].append(stats.score)
        
        # Calculate averages
        for evaluator_name, data in summary["evaluator_scores"].items():
            if data["scores"]:
                data["average"] = sum(data["scores"]) / len(data["scores"])
        
        return summary
        
    except Exception as e:
        logger.warning(f"Error calculating summary: {str(e)}")
        return {
            "total_examples": 0,
            "evaluator_scores": {},
            "error": str(e)
        }


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run evaluation
    results = run_evaluation(
        dataset_name="movie-recommendations-1",
        experiment_prefix="claude-haiku-baseline",
        description="Baseline evaluation of movie recommendation agent",
        max_concurrency=4
    )
    
    if results["success"]:
        print("\n" + "="*50)
        print("Evaluation Summary")
        print("="*50)
        print(f"Total examples evaluated: {results['summary'].get('total_examples', 0)}")
        print(f"Experiment: {results.get('experiment_name', 'N/A')}")
        print("\nEvaluator Scores:")
        for evaluator, data in results['summary'].get('evaluator_scores', {}).items():
            avg_score = data.get('average', 0.0)
            print(f"  {evaluator}: {avg_score:.2f} (avg)")
        print("\n" + "="*50)
        print("View detailed results in LangSmith UI")
        print("="*50)
    else:
        print(f"Evaluation failed: {results.get('error', 'Unknown error')}")

