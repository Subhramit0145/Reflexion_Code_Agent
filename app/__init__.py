"""
Reflexion Code Agent
====================
Autonomous Code Debugger & Test-Driven Fixer powered by Verbal
Reinforcement Learning without Weight Updates.

Architecture
------------
Actor  ->  generates candidate code solutions
Evaluator  ->  executes tests in a sandboxed subprocess, captures results
Self-Reflector  ->  analyses failures and writes verbal reflections
Orchestrator  ->  drives the iterative loop with episodic memory
"""

__version__ = "0.1.0"
