# Project Overview

This project is a Python script that interacts with the Yandex Disk API to automatically publish `.mov` files and retrieve their public links.

## Key Components

*   **`main.py`**: The main script that orchestrates the process of fetching file lists, publishing files, and generating the output file.
*   **`Get_links_YD/config.py`**: Configuration file containing the Yandex Disk API OAuth token, the target folder path, and the output file name.
*   **`links.txt`**: The output file where the script saves the public links of the processed files.
*   **`docker-compose.yml`**: A minimal Docker Compose file, currently only defining a default network.

## How it Works

The `main.py` script performs the following actions:

1.  **Reads Configuration**: It imports the `OAUTH_TOKEN`, `FOLDER_PATH`, and `OUTPUT_FILE` from the `Get_links_YD/config.py` file.
2.  **Lists Folder Items**: It sends a request to the Yandex Disk API to list the items in the specified `FOLDER_PATH`.
3.  **Publishes Files**: It identifies any `.mov` files that are not yet published and sends requests to the API to publish them.
4.  **Retrieves Public Links**: It fetches the public links for all `.mov` files in the folder.
5.  **Generates Output**: It creates a formatted text file (`links.txt`) containing the names of the files (without the extension) and their corresponding public URLs.

# Building and Running

## Prerequisites

*   Python 3.8 or higher.
*   A Yandex Disk account.
*   An OAuth token for the Yandex Disk API with appropriate permissions.

## Installation and Execution

1.  **Install Dependencies**: The required Python packages are listed in `Get_links_YD/requirements.txt`. You can install them using pip:

    ```bash
    pip install -r Get_links_YD/requirements.txt
    ```

2.  **Configure the Project**: Before running the script, you need to provide your Yandex Disk API credentials and the target folder path in the `Get_links_YD/config.py` file.

    ```python
    # Get_links_YD/config.py

    OAUTH_TOKEN = "YOUR_YANDEX_DISK_OAUTH_TOKEN"
    FOLDER_PATH = "/path/to/your/folder_on_yandex_disk"
    OUTPUT_FILE = "links.txt"
    ```

3.  **Run the Script**: Execute the main script from the project's root directory:

    ```bash
    python main.py
    ```

    The script will then connect to the Yandex Disk API, process the files, and save the results in the `links.txt` file.

# Development Conventions

*   **Configuration**: All sensitive information and environment-specific settings (like API tokens and folder paths) are stored in the `Get_links_YD/config.py` file. This file is included in the `.gitignore` file to prevent accidental commits of sensitive data.
*   **Modularity**: The core logic is contained within the `main.py` script, which is organized into several functions for clarity and maintainability.
*   **Error Handling**: The script includes basic error handling for API requests, printing error messages to standard error if an API call fails.
