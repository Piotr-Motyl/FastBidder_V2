# FastBidder

FastBidder is an innovative application designed to automate the preparation of bids in the construction industry by semantically matching work descriptions. The project was created with the goal of learning Python and developing programming skills, and its primary purpose is to reduce the time required for manual comparison of descriptions in Excel files.

## Project Description

In the construction industry, preparing a bid is a seemingly simple yet time-consuming task that involves manually comparing work descriptions across different Excel files. FastBidder automates this process by comparing descriptions from the offer file (Working File, WF) with catalog prices from the reference file (Reference File, REF) using semantic analysis. Based on the similarity between descriptions, the application assigns appropriate unit prices. By automating the comparison of hundreds or even thousands of cells in excel file, FastBidder significantly saves time and reduces costs in bid preparation.

## Architecture and Modules

The project is built using the Django framework and consists of the following modules:
- **Orchestrator**: Coordinates the entire file comparison process, validates input data, and manages data flow between modules.
- **File Management**: Handles uploading, validating, and storing Excel files.
- **Excel Processing**: Extracts data from files and modifies the offer file.
- **Semantic Analysis**: Generates embeddings for descriptions and performs semantic similarity analysis.
- **Matching Engine**: Matches descriptions from the offer file to those in the reference file using semantic analysis results and assigns appropriate unit prices.
- **Processing Data**: Temporarily stores description data and matching results during processing sessions.

## Application Workflow

1. The user sends a request to the central API endpoint (Orchestrator) with specific parameters (file paths, row ranges, columns, matching threshold).
2. The File Management module validates the files and retrieves their locations.
3. Excel Processing extracts data from the files based on specified columns and ranges, processing descriptions from the Working File (WF) and descriptions with prices from the Reference File (REF).
4. Data is temporarily stored in the Processing Data module.
5. The Semantic Analysis module generates embeddings for descriptions, and then the Matching Engine determines the best matches.
6. Based on matching results, Excel Processing updates the offer file with unit prices.
7. Finally, Orchestrator returns the modified file to the user.

## Technologies and Tools

- **Python** and **Django** – core backend technologies.
- **openpyxl** or **pandas** – libraries for working with Excel files.
- NLP models such as **Sentence-Transformers** (e.g., all-MiniLM-L6-v2) or alternatively **FastEmbed** for generating embeddings.

## Development Status and Future Plans

The project is in an active development phase and serves as an educational experiment.  

**Planned Features:**
- Implementation of the `generate_embeddings` method in the Semantic Analysis module.
- Expansion of automated tests.
- Improved error handling and session identifier mechanisms.
- Completion of documentation and docstrings in both Polish and English.

## Contribution Guidelines

FastBidder is primarily an educational project, meaning many elements (e.g., tests, full documentation) will be systematically added and improved over time.  
- Suggestions for improvements or extensions are welcome.
- Docstrings are currently written in Polish but will be translated soon into English.

## Final Notes

FastBidder is an open educational project aimed at automating pricing processes while fostering programming skill development. The project will be systematically enhanced with new features and tests.  


---
