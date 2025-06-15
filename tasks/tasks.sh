#!/bin/bash

# Read tasks from all .md files with unchecked tasks with a date
tasks=$(find .. -type f -name "*.md" -exec grep -h "\[ \].*📅" {} \;)


# Get today's date and the date 5 days later in YYYY-MM-DD format
TODAY=$(date "+%Y-%m-%d")
FIVE_DAYS_LATER=$(date -d "$TODAY + 5 day" "+%Y-%m-%d")

# Function to print tasks based on date comparison
print_tasks() {
  local label=$1
  local compare=$2
  local date=$3

  echo "$label:"
  while IFS= read -r line; do
    task_date=$(echo "$line" | grep -oP '📅 \K\d{4}-\d{2}-\d{2}')  # Extract only the date

    # check if the task_date is empty
    if [ -z "$task_date" ]; then
      continue
    fi

    case "$compare" in
      "before")
        if [[ "$task_date" < "$date" ]]; then
          echo "$line"
        fi
        ;;
      "equal")
        if [[ "$task_date" == "$date" ]]; then
          echo "$line"
        fi
        ;;
      "between")
        if [[ "$task_date" > "$TODAY" && "$task_date" < "$FIVE_DAYS_LATER" ]]; then
          echo "$line"
        fi
       ;;
    esac
  done <<< "$tasks"
}

# Print tasks before today
print_tasks "Tasks Before Today" "before" "$TODAY"
echo

# Print tasks for today
print_tasks "Tasks For Today" "equal" "$TODAY"
echo

# Print tasks for the next 5 days
print_tasks "Tasks For the Next 5 Days" "between" "$FIVE_DAYS_LATER"
