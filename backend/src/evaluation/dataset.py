"""Dataset management for movie recommendation evaluations."""

import os
import logging
from typing import List, Dict, Any, Optional
from langsmith import Client

logger = logging.getLogger(__name__)


def create_dataset(
    dataset_name: str = "movie-recommendations-1",
    description: Optional[str] = None
) -> str:
    """
    Create a new dataset in LangSmith.
    
    Args:
        dataset_name: Name of the dataset to create
        description: Optional description for the dataset
        
    Returns:
        Dataset ID
    """
    try:
        client = Client()
        
        # Check if dataset already exists
        try:
            existing_datasets = list(client.list_datasets(dataset_name=dataset_name))
            if existing_datasets:
                dataset_id = existing_datasets[0].id
                logger.info(f"Dataset '{dataset_name}' already exists with ID: {dataset_id}")
                return dataset_id
        except Exception:
            # If list_datasets fails, try to create anyway
            pass
        
        # Create new dataset
        dataset = client.create_dataset(
            dataset_name=dataset_name,
            description=description or f"Movie recommendation evaluation dataset: {dataset_name}"
        )
        
        logger.info(f"Created dataset '{dataset_name}' with ID: {dataset.id}")
        return dataset.id
        
    except Exception as e:
        logger.error(f"Error creating dataset: {str(e)}", exc_info=True)
        raise


def add_examples(
    dataset_name: str,
    examples: List[Dict[str, Any]]
) -> None:
    """
    Add examples to a dataset.
    
    Args:
        dataset_name: Name of the dataset
        examples: List of example dictionaries with 'inputs' and optionally 'outputs' keys
                  Example format:
                  {
                      "inputs": {"query": "action movies like John Wick"},
                      "outputs": {"expected": "John Wick, John Wick: Chapter 2, ..."}  # Optional
                  }
    """
    try:
        client = Client()
        
        # Get dataset ID
        datasets = list(client.list_datasets(dataset_name=dataset_name))
        if not datasets:
            raise ValueError(f"Dataset '{dataset_name}' not found. Create it first using create_dataset()")
        
        dataset_id = datasets[0].id
        
        # Add examples
        client.create_examples(
            dataset_id=dataset_id,
            inputs=[ex["inputs"] for ex in examples],
            outputs=[ex.get("outputs") for ex in examples] if any(ex.get("outputs") for ex in examples) else None
        )
        
        logger.info(f"Added {len(examples)} examples to dataset '{dataset_name}'")
        
    except Exception as e:
        logger.error(f"Error adding examples: {str(e)}", exc_info=True)
        raise


def add_examples_from_file(
    dataset_name: str,
    file_path: str,
    has_ground_truth: bool = False
) -> None:
    """
    Add examples from a text file (one query per line).
    
    Args:
        dataset_name: Name of the dataset
        file_path: Path to the text file with queries
        has_ground_truth: If True, expects file to have tab-separated query and expected output
    """
    try:
        examples = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if has_ground_truth:
                    # Expect format: query\t expected_output
                    parts = line.split('\t', 1)
                    if len(parts) == 2:
                        query, expected = parts
                        examples.append({
                            "inputs": {"query": query.strip()},
                            "outputs": {"expected": expected.strip()}
                        })
                    else:
                        logger.warning(f"Skipping malformed line: {line}")
                else:
                    # Just a query per line
                    examples.append({
                        "inputs": {"query": line}
                    })
        
        if examples:
            add_examples(dataset_name, examples)
            logger.info(f"Added {len(examples)} examples from {file_path}")
        else:
            logger.warning(f"No valid examples found in {file_path}")
            
    except Exception as e:
        logger.error(f"Error adding examples from file: {str(e)}", exc_info=True)
        raise


def create_initial_dataset(
    dataset_name: str = "movie-recommendations-1",
    test_queries_file: Optional[str] = None
) -> str:
    """
    Create the initial dataset with examples from test_queries.txt.
    
    Args:
        dataset_name: Name of the dataset to create
        test_queries_file: Path to test queries file (defaults to test_queries.txt in project root)
        
    Returns:
        Dataset ID
    """
    # Create dataset
    dataset_id = create_dataset(dataset_name)
    
    # Add examples from file if provided
    if test_queries_file is None:
        # Default to test_queries.txt in project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        test_queries_file = os.path.join(project_root, "test_queries.txt")
    
    if os.path.exists(test_queries_file):
        add_examples_from_file(dataset_name, test_queries_file, has_ground_truth=False)
    else:
        logger.warning(f"Test queries file not found: {test_queries_file}")
        # Add some default examples
        default_examples = [
            {
                "inputs": {"query": "action movies like John Wick"}
            },
            {
                "inputs": {"query": "romantic comedies from the 90s"}
            },
            {
                "inputs": {"query": "sci-fi movies with time travel"}
            }
        ]
        add_examples(dataset_name, default_examples)
        logger.info("Added default examples to dataset")
    
    return dataset_id

