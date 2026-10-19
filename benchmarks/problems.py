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
            "Implement a function that checks if a string is a palindrome."
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
            "which has the largest sum and return its sum."
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
            "Given a string `s` containing just brackets, "
            "determine if the input string is valid."
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
            "Implement fizzbuzz(n) that returns a list of strings from 1 to n."
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
            "Given a nested list of integers, flatten it into a single list."
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
    TaskSpec(
        task_id="bench-007-string-compress",
        description=(
            "Implement a function compress(s: str) -> str that performs run-length compression. "
            "Consecutive duplicate characters should be replaced with the character and its frequency. "
            "If the compressed string would not be shorter than the original string, return the original string."
        ),
        function_signature="def compress(s: str) -> str:",
        test_code=(
            "assert compress('aabcccccaaa') == 'a2bc5a3', f'Got {compress(\"aabcccccaaa\")}'\n"
            "assert compress('abcd') == 'abcd', f'Got {compress(\"abcd\")}'\n"
            "assert compress('') == '', f'Got {compress(\"\")}'\n"
            "assert compress('a') == 'a', f'Got {compress(\"a\")}'\n"
            "assert compress('abbbbbbbbbb') == 'ab10', f'Got {compress(\"abbbbbbbbbb\")}'\n"
            "print('5 passed')\n"
        ),
    ),
    TaskSpec(
        task_id="bench-008-nested-json-path",
        description=(
            "Implement a function query_json(data: dict | list, path: str) that retrieves a nested value "
            "using a string path syntax with dot-notation and array indices (e.g., 'users[0].profile.email'). "
            "If an index or key does not exist, return None instead of raising an error. "
            "If a key contains special characters escaped with backticks like 'data.`special.key`', handle it properly."
        ),
        function_signature="def query_json(data: dict | list, path: str):",
        test_code=(
            "d = {'users': [{'profile': {'email': 'a@b.com'}}, {'profile': None}], 'data': {'special.key': 42}}\n"
            "assert query_json(d, 'users[0].profile.email') == 'a@b.com'\n"
            "assert query_json(d, 'users[1].profile') is None\n"
            "assert query_json(d, 'users[2].profile') is None\n"
            "assert query_json(d, 'users[0].profile.phone') is None\n"
            "assert query_json(d, 'data.`special.key`') == 42\n"
            "assert query_json(d, '') == d\n"
            "print('6 passed')\n"
        ),
    ),
    TaskSpec(
        task_id="bench-009-redundant-parens",
        description=(
            "Implement a function remove_redundant_parens(expr: str) -> str. "
            "Remove all unnecessary parentheses from a valid algebraic expression with '+', '-', '*', and single-character variables. "
            "Rules: "
            "1. Parentheses surrounding the entire expression when not needed by an outer operator should be removed: '((a + b))' -> 'a + b'. "
            "2. Parentheses around operands whose operator has higher or equal precedence in an associative context should be removed: '(a * b) + c' -> 'a * b + c'. "
            "3. Parentheses needed for precedence must be kept: '(a + b) * c' stays '(a + b) * c'. "
            "4. Parentheses after a subtraction must be kept if they contain '+' or '-': 'a - (b + c)' stays 'a - (b + c)'."
        ),
        function_signature="def remove_redundant_parens(expr: str) -> str:",
        test_code=(
            "assert remove_redundant_parens('((a + b))') == 'a + b'\n"
            "assert remove_redundant_parens('(a * b) + c') == 'a * b + c'\n"
            "assert remove_redundant_parens('(a + b) * c') == '(a + b) * c'\n"
            "assert remove_redundant_parens('a - (b + c)') == 'a - (b + c)', 'Subtraction scope must preserve parens'\n"
            "assert remove_redundant_parens('a + (b + c)') == 'a + b + c'\n"
            "print('5 passed')\n"
        ),
    ),
]
