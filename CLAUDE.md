# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

English learning application with SQLite database containing grammar rules and dictionary entries. The project provides asynchronous database access using SQLAlchemy with filtering, searching, and random selection capabilities.

## Database Architecture

**Database file**: `english_learning.db` (SQLite)

**Tables**:
- `grammar` (1,222 records): English grammar rules with levels A1-C2, categories, examples
- `dictionary` (5,948 records): English words with parts of speech and CEFR levels

**Data source**: JSON files in `json_to_backup/`:
- `grammar.json`: Contains grammar rules with SuperCategory, SubCategory, Level, Guideword, Can-do statement, Example
- `dictionary.json`: Contains word, class (part of speech), level

## Development Setup

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Required packages**:
- `sqlalchemy>=2.0.0` - ORM with async support
- `aiosqlite>=0.19.0` - Async SQLite driver

## Key Components

### reader.py - Async Database Access Layer

Uses async SQLAlchemy with declarative models. All functions are asynchronous and return Python dicts.

**Models**:
- `Grammar`: Maps to grammar table (id, super_category, sub_category, level, lexical_range, guideword, can_do_statement, example)
- `Dictionary`: Maps to dictionary table (id, word, class_, level)

**Core functions**:

Grammar queries:
- `get_grammar_list()`: Filtered list with optional random ordering
  - Filters: level, super_category, sub_category, limit
- `search_grammar_text()`: Full-text search across guideword, can_do_statement, example, categories
- `get_grammar_by_id()`: Single record lookup

Dictionary queries:
- `get_dictionary_list()`: Filtered list with optional random ordering
  - Filters: level, word_class, starts_with, limit
- `search_dictionary_text()`: Search by word pattern
- `get_word_by_id()`: Single record lookup

All query functions support:
- `random_order=True` for shuffled results
- `limit` parameter for result count
- Return list of dicts for easy serialization

## Database Schema Details

### Grammar Table
- Levels: A1, A2, B1, B2, C1, C2 (CEFR levels)
- Categories organized hierarchically: SuperCategory → SubCategory
- Text fields for search: guideword, can_do_statement, example

### Dictionary Table
- Levels: a1, a2, b1, b2, c1, c2 (lowercase)
- word_class: noun, verb, adjective, adverb, preposition, etc.
- Indexed by word for efficient lookups

## Running Examples

The `reader.py` file includes a `main()` function demonstrating all core functionality:

```bash
python reader.py
```

This will execute example queries showing:
- Random grammar rules by level
- Text search in grammar
- Random words by level
- Pattern matching in dictionary

## Important Notes

- All database operations are async - use `await` and `asyncio.run()`
- Database connection uses `sqlite+aiosqlite://` URL scheme
- Dictionary model uses `class_` attribute mapped to `class` column (Python keyword conflict)
- Random ordering uses SQLite's `func.random()` - results differ each query
- Text search uses SQL LIKE with `%pattern%` for substring matching
