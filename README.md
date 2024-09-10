# Code Churn Analysis Script

This Python script analyzes code churn in a Git repository. It calculates the contribution and churn for specified authors within a given date range or between specific commits.

[[Research] Code Churn: A Neglected Metric in Effort-Aware Just-in-Time Defect Prediction](https://ieeexplore.ieee.org/document/8169980)

[[Blog post] Introduction to code churn](https://www.pluralsight.com/blog/tutorials/code-churn)

## Features

- Analyze code churn by author
- Filter by date range or specific commits
- Include or exclude specific directories
- Calculate total contribution and churn

## Requirements

- Python 3.x
- Git

## Usage

```
python code_churn.py after="YYYY[-MM[-DD]]" before="YYYY[-MM[-DD]]" author="author_name" include_dir="path" [-exclude_dir="path"]
```

### Arguments

- `after`: Search after a certain date, in YYYY[-MM[-DD]] format
- `before`: Search before a certain date, in YYYY[-MM[-DD]] format
- `author`: An author (non-committer), leave blank to scope all authors
- `include_dir`: The Git repository root directory to include in the analysis
- `-exclude_dir`: (Optional) The Git repository subdirectory to exclude from the analysis

### Optional Arguments

- `-start_commit`: Search from a certain commit, in short SHA format
- `-end_commit`: Search to a certain commit, in short SHA format

## Example

```
python code_churn.py after="2023-01-01" before="2023-12-31" author="johndoe" include_dir="/path/to/repo" -exclude_dir="tests"
```

## Output

The script will display the following information:

- Author(s)
- Total contribution (lines added)
- Total churn (lines removed)

## How it works

1. Fetches commit hashes within the specified date range or between specified commits
2. Analyzes each commit to calculate contribution and churn
3. Processes file changes and updates the total contribution and churn
4. Displays the results

## Notes

- The script uses Git commands to fetch commit information, so it must be run in a Git repository or with a valid path to a Git repository.
- Make sure you have the necessary permissions to access the Git repository.

## Contributing

Feel free to submit issues or pull requests if you have suggestions for improvements or find any bugs.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
