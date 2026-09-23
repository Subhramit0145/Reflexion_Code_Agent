"""
Curated benchmark problem set.

Each problem is a TaskSpec with a description, function signature, and
comprehensive test suite.  The problems are designed to have subtle
edge cases that a naive first attempt is likely to miss -- making them
ideal for demonstrating the value of the Reflexion self-correction loop.

Problem selection rationale
---------------------------
- Two Sum: requires returning sorted indices, tricky with duplicate values
- Is Palindrome: alphanumeric-only filtering + case-insensitivity
- Max Subarray (Kadane): all-negative arrays are a classic pitfall
- Valid Parentheses: nested bracket matching with stack logic
- FizzBuzz: 1-indexed list, multiples-of-both must come before individual checks
- Flatten Nested List: arbitrary depth recursion, must handle mixed int/list
"""

from app.core.schemas import TaskSpec


BENCHMARK_PROBLEMS: list[TaskSpec] = [
    TaskSpec(
        task_id="bench-001-two-sum",
        description=(
            "Given a list of integers `nums` and an integer `target`, return "
            "the indices of the two numbers that add up to `target`. "
            "You may assume each input has exactly one solution. "
            "You may not use the same element twice. "
            "Return the indices in ascending order as a list."
        ),
        function_signature="def two_sum(nums: list[int], target: int) -> list[int]:",
        test_code=(
            "assert two_sum([2, 7, 11, 15], 9) == [0, 1]\n"
            "assert two_sum([3, 2, 4], 6) == [1, 2]\n"
            "assert two_sum([3, 3], 6) == [0, 1]\n"
            "assert two_sum([1, 5, 3, 7], 8) == [1, 2]\n"
            "print(\"4 passed\")\n"
        ),
    ),
    TaskSpec(
        task_id="bench-002-is-palindrome",
        description=(
            "Implement a function that checks if a string is a palindrome, "
            "considering only alphanumeric characters and ignoring case. "
            "An empty string is a valid palindrome."
        ),
        function_signature="def is_palindrome(s: str) -> bool:",
        test_code=(
            "assert is_palindrome(\"A man, a plan, a canal: Panama\") == True\n"
            "assert is_palindrome(\"race a car\") == False\n"
            "assert is_palindrome(\"\") == True\n"
            "assert is_palindrome(\" \") == True\n"
            "assert is_palindrome(\"0P\") == False\n"
            "print(\"5 passed\")\n"
        ),
    ),
    TaskSpec(
        task_id="bench-003-max-subarray",
        description=(
            "Given an integer array `nums`, find the contiguous subarray "
            "(containing at least one number) which has the largest sum "
            "and return its sum. Use Kadane's algorithm."
        ),
        function_signature="def max_subarray(nums: list[int]) -> int:",
        test_code=(
            "assert max_subarray([-2,1,-3,4,-1,2,1,-5,4]) == 6\n"
            "assert max_subarray([1]) == 1\n"
            "assert max_subarray([5,4,-1,7,8]) == 23\n"
            "assert max_subarray([-1]) == -1\n"
            "assert max_subarray([-2, -1]) == -1\n"
            "print(\"5 passed\")\n"
        ),
    ),
    TaskSpec(
        task_id="bench-004-valid-parentheses",
        description=(
            "Given a string `s` containing just the characters '(', ')', "
            "'{', '}', '[' and ']', determine if the input string is valid. "
            "A string is valid if: open brackets are closed by the same type "
            "and in the correct order. An empty string is valid."
        ),
        function_signature="def is_valid(s: str) -> bool:",
        test_code=(
            "assert is_valid(\"()\") == True\n"
            "assert is_valid(\"()[]{}\") == True\n"
            "assert is_valid(\"(]\") == False\n"
            "assert is_valid(\"([)]\") == False\n"
            "assert is_valid(\"{[]}\") == True\n"
            "assert is_valid(\"\") == True\n"
            "assert is_valid(\"(\") == False\n"
            "print(\"7 passed\")\n"
        ),
    ),
    TaskSpec(
        task_id="bench-005-fizzbuzz",
        description=(
            "Implement fizzbuzz(n) that returns a list of strings from 1 to n. "
            "For multiples of 3, use 'Fizz'. For multiples of 5, use 'Buzz'. "
            "For multiples of both 3 and 5, use 'FizzBuzz'. Otherwise use the "
            "number as a string."
        ),
        function_signature="def fizzbuzz(n: int) -> list[str]:",
        test_code=(
            "result = fizzbuzz(15)\n"
            "assert result[0] == \"1\", f\"Index 0: expected '1', got '{result[0]}'\"\n"
            "assert result[2] == \"Fizz\", f\"Index 2: expected 'Fizz', got '{result[2]}'\"\n"
            "assert result[4] == \"Buzz\", f\"Index 4: expected 'Buzz', got '{result[4]}'\"\n"
            "assert result[14] == \"FizzBuzz\", f\"Index 14: expected 'FizzBuzz', got '{result[14]}'\"\n"
            "assert len(result) == 15\n"
            "assert result[8] == \"Fizz\"\n"
            "assert result[9] == \"Buzz\"\n"
            "print(\"7 passed\")\n"
        ),
    ),
    TaskSpec(
        task_id="bench-006-flatten-nested",
        description=(
            "Given a nested list of integers, flatten it into a single list. "
            "For example, [[1,2],[3,[4,5]],6] should return [1,2,3,4,5,6]. "
            "Handle arbitrary nesting depth. Input may contain integers and "
            "lists (no other types)."
        ),
        function_signature="def flatten(lst) -> list[int]:",
        test_code=(
            "assert flatten([1, 2, 3]) == [1, 2, 3]\n"
            "assert flatten([[1, 2], [3, [4, 5]], 6]) == [1, 2, 3, 4, 5, 6]\n"
            "assert flatten([]) == []\n"
            "assert flatten([[[1]], [[2]], [[3]]]) == [1, 2, 3]\n"
            "assert flatten([1, [2, [3, [4, [5]]]]]) == [1, 2, 3, 4, 5]\n"
            "print(\"5 passed\")\n"
        ),
    ),
]
