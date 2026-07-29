import json
from loguru import logger
from agents.document_extraction_agent import run_extraction

def main():
    # Test with a sample PDF
    test_file = "sample_paper.pdf"  # Replace with actual path

    logger.info(f"Starting SciNexus Document AI Agent on: {test_file}")

    try:
        result = run_extraction(test_file)

        # Pretty print result
        output = result.model_dump()
        print(json.dumps(output, indent=2, default=str))

        # Save to JSON
        with open("extracted_output.json", "w") as f:
            json.dump(output, f, indent=2, default=str)

        logger.success(f"Extraction complete! Document ID: {result.document_id}")
        logger.info(f"Document Type: {result.document_type}")
        logger.info(f"Pages: {result.metadata.page_count}")
        logger.info(f"Sections: {len(result.sections)}")
        logger.info(f"Tables: {len(result.tables)}")
        logger.info(f"Figures: {len(result.figures)}")
        logger.info(f"Confidence: {result.confidence_score:.3f}")

    except Exception as e:
        logger.error(f"Failed: {e}")
        raise

if __name__ == "__main__":
    main()