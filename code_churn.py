import argparse
import datetime
import os
import subprocess


def main():
    args = parse_arguments()

    after_date = strip_prefix(args.after, "after=")
    before_date = strip_prefix(args.before, "before=")
    author_name = strip_prefix(args.author, "author=")
    include_dir = args.include_dir
    exclude_dir = args.exclude_dir

    start_commit_timestamp = (
        get_commit_timestamp(args.start_commit, include_dir)
        if args.start_commit
        else None
    )
    end_commit_timestamp = (
        get_commit_timestamp(args.end_commit, include_dir) if args.end_commit else None
    )

    if start_commit_timestamp and end_commit_timestamp:
        start_commit_timestamp, end_commit_timestamp = sorted(
            [start_commit_timestamp, end_commit_timestamp]
        )

    commit_hashes = fetch_commit_hashes(
        args,
        start_commit_timestamp,
        end_commit_timestamp,
        after_date,
        before_date,
        author_name,
        include_dir,
    )

    files_data, total_contribution, total_churn = analyze_commits(
        commit_hashes, include_dir, exclude_dir
    )

    display_results(
        author_name,
        args.end_commit or before_date,
        args.start_commit or after_date,
        total_contribution,
        total_churn,
        include_dir,
    )


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Code churn",
        usage='python [*/]code_churn.py after="YYYY[-MM[-DD]]" before="YYYY[-MM[-DD]]" author="flacle" include_dir="[*/]path" [-exclude_dir="[*/]path"]',
    )
    parser.add_argument(
        "after", type=str, help="Search after a certain date, in YYYY[-MM[-DD]] format"
    )
    parser.add_argument(
        "before",
        type=str,
        help="Search before a certain date, in YYYY[-MM[-DD]] format",
    )
    parser.add_argument(
        "-start_commit",
        type=str,
        help="Search from a certain commit, in short SHA format",
    )
    parser.add_argument(
        "-end_commit", type=str, help="Search to a certain commit, in short SHA format"
    )
    parser.add_argument(
        "author",
        type=str,
        help="An author (non-committer), leave blank to scope all authors",
    )
    parser.add_argument(
        "include_dir",
        type=validate_directory_path,
        default="",
        help="The Git repository root directory to include in the analysis",
    )
    parser.add_argument(
        "-exclude_dir",
        metavar="",
        type=str,
        default="",
        help="The Git repository subdirectory to exclude from the analysis",
    )
    return parser.parse_args()


def fetch_commit_hashes(
    args,
    start_commit_timestamp,
    end_commit_timestamp,
    after_date,
    before_date,
    author_name,
    include_dir,
):
    if args.start_commit and args.start_commit == args.end_commit:
        return [args.start_commit]
    else:
        return get_commit_hashes(
            end_commit_timestamp or before_date,
            start_commit_timestamp or after_date,
            author_name,
            include_dir,
        )


def analyze_commits(commit_hashes, include_dir, exclude_dir):
    files_data = {}
    total_contribution = 0
    total_churn = 0

    for commit_hash in commit_hashes:
        files_data, total_contribution, total_churn = analyze_commit(
            commit_hash,
            include_dir,
            files_data,
            total_contribution,
            total_churn,
            exclude_dir,
        )

    return files_data, total_contribution, total_churn


def display_results(
    author_name, end_date, start_date, total_contribution, total_churn, include_dir
):
    if len(author_name.strip()) == 0:
        authors = set(
            get_commit_hashes(end_date, start_date, author_name, include_dir, "%an")
        )
        authors_str = ", ".join(authors)
        author_info = f"authors: \t {authors_str}"
    else:
        author_info = f"author: \t {author_name}"

    result = (
        f"{author_info}\n"
        f"contribution: \t {total_contribution}\n"
        f"churn: \t\t {-total_churn}"
    )

    print(result)


def get_commit_timestamp(commit_hash, include_dir):
    if len(commit_hash) < 7:
        raise argparse.ArgumentTypeError(f"{commit_hash} is not a valid commit hash.")

    commit_hash = commit_hash[:7]

    command = f"git show {commit_hash}"
    results = execute_command(command, include_dir).splitlines()

    date_line = next(line for line in results if line.startswith("Date:"))
    date_raw = date_line[5:].strip()
    date_object = datetime.datetime.strptime(date_raw, "%a %b %d %H:%M:%S %Y %z")
    formatted_date = date_object.strftime("%Y-%m-%d %H:%M")

    return formatted_date


def analyze_commit(
    commit_hash, include_dir, files_data, total_contribution, total_churn, exclude_dir
):
    command = build_git_show_command(commit_hash, exclude_dir)
    results = execute_command(command, include_dir).splitlines()

    current_file = ""
    loc_changes = ""

    for result in results:
        current_file = update_file(result, current_file, files_data)
        loc_changes, total_contribution, total_churn = process_loc_changes(
            result,
            current_file,
            loc_changes,
            files_data,
            total_contribution,
            total_churn,
        )

    return files_data, total_contribution, total_churn


def build_git_show_command(commit_hash, exclude_dir):
    command = "git show --format= --unified=0 --no-prefix " + commit_hash
    if exclude_dir:
        command += f' -- . ":(exclude,icase){exclude_dir}"'
    return command


def update_file(result, current_file, files_data):
    new_file = extract_new_file(result, current_file)
    if new_file != current_file:
        if new_file not in files_data:
            files_data[new_file] = {}
        return new_file
    return current_file


def process_loc_changes(
    result, current_file, loc_changes, files_data, total_contribution, total_churn
):
    new_loc_changes = extract_loc_changes(result, loc_changes)
    if loc_changes != new_loc_changes:
        loc_changes = new_loc_changes
        loc_change_dict = parse_loc_changes(loc_changes)
        for loc, count in loc_change_dict.items():
            if loc in files_data[current_file]:
                files_data[current_file][loc] += count
                total_churn += abs(count)
            else:
                files_data[current_file][loc] = count
                total_contribution += abs(count)
    return loc_changes, total_contribution, total_churn


def parse_loc_changes(loc_changes):
    left_part, right_part = loc_changes.split(" ")
    left_main, left_sub = parse_loc_part(left_part)
    right_main, right_sub = parse_loc_part(right_part)

    if left_main == right_main:
        return {left_main: right_sub - left_sub}
    else:
        return {left_main: left_sub, right_main: right_sub}


def parse_loc_part(part):
    if "," in part:
        main, sub = map(int, part[1:].split(","))
    else:
        main, sub = int(part[1:]), 1
    return main, sub


def extract_loc_changes(result, loc_changes):
    if result.startswith("@@"):
        loc_change = result[result.find(" ") + 1 :]
        loc_change = loc_change[: loc_change.find(" @@")]
        return loc_change
    else:
        return loc_changes


def extract_new_file(result, current_file):
    if result.startswith("+++"):
        return result[result.rfind(" ") + 1 :]
    else:
        return current_file


def get_commit_hashes(end_date, start_date, author_name, include_dir, format="%h"):
    command = [
        "git",
        "log",
        f"--author={author_name}",
        f"--format={format}",
        "--no-abbrev",
        f"--before={end_date}",
        f"--after={start_date}",
        "--no-merges",
        "--reverse",
    ]
    return execute_command(" ".join(command), include_dir).splitlines()


def format_date(date_str):
    date_str = date_str.rstrip("-")

    if len(date_str) == 4:  # Handle year-only input (YYYY)
        return f"{date_str}-12-31"

    if len(date_str) == 7:  # Handle year-month input (YYYY-MM)
        dt = datetime.datetime.strptime(date_str, "%Y-%m")
        last_day = get_month_last_day(dt)
        return f"{date_str}-{last_day:02d}"

    if len(date_str) == 10:  # Handle full date input (YYYY-MM-DD)
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")

    raise argparse.ArgumentTypeError("Invalid date format")


def get_month_last_day(date):
    if date.month == 12:
        return 31
    next_month = date.replace(month=date.month + 1, day=1)
    last_day = next_month - datetime.timedelta(days=1)
    return last_day.day


def fetch_files_for_commit(commit_hash, include_dir):
    command = f'git show --numstat --pretty="" {commit_hash}'
    results = execute_command(command, include_dir).splitlines()
    files = [line.split("\t")[-1] for line in results]
    return files


def execute_command(command, include_dir):
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=include_dir,
        shell=True,
    )
    return process.communicate()[0].decode("utf-8")


def validate_directory_path(path):
    path = strip_prefix(path, "include_dir=")
    if not os.path.isdir(path):
        raise argparse.ArgumentTypeError(f"{path} is not a valid path.")
    return path


def strip_prefix(text, prefix):
    return text[len(prefix) :] if text.startswith(prefix) else text


if __name__ == "__main__":
    main()
