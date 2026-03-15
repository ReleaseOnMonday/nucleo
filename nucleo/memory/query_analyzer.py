"""
Query complexity analysis for intelligent routing.

Memory Impact: Minimal analysis overhead (~100KB)

Analyzes queries to determine:
- Complexity level (simple, moderate, complex)
- Estimated processing cost
- Required context size
- Optimal model selection
- Whether to use cached response vs fresh processing

This enables routing simple queries to fast-path code with minimal memory usage.

Usage:
    analyzer = QueryComplexityAnalyzer()
    
    complexity = analyzer.analyze("What is 2+2?")  # simple
    complexity = analyzer.analyze("Explain quantum entanglement")  # complex
    
    if complexity.level == "simple":
        use_fast_model()
    else:
        use_smart_model()
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List

logger = logging.getLogger(__name__)


class ComplexityLevel(Enum):
    """Query complexity levels."""

    SIMPLE = "simple"  # Factual, short, cache-friendly
    MODERATE = "moderate"  # Requires reasoning, medium context
    COMPLEX = "complex"  # Multi-step reasoning, large context


@dataclass
class ComplexityAnalysis:
    """Result of query complexity analysis."""

    level: ComplexityLevel
    score: float  # 0.0-1.0
    word_count: int
    unique_words: int
    complexity_indicators: List[str]
    estimated_processing_ms: int
    estimated_context_size_tokens: int
    cache_friendly: bool
    suggested_model: str  # "fast", "balanced", "smart"


class QueryComplexityAnalyzer:
    """
    Lightweight query complexity analyzer.
    
    Uses heuristics to categorize queries without ML overhead:
    - Word count and vocabulary richness
    - Keyword matching (explain, analyze, compare, etc.)
    - Query structure (questions, imperatives, etc.)
    - Special characters and technical terms
    
    Not a ML model - pure heuristic analysis (~1-2ms per query)
    
    Memory Impact: ~200KB for keyword dictionaries + analyzer state
    """

    # Keywords indicating simple queries
    SIMPLE_KEYWORDS = {
        "what is",
        "how much",
        "when",
        "where",
        "who",
        "which",
        "can you",
        "do you",
        "yes",
        "no",
        "hello",
        "hi",
        "thanks",
        "time",
        "date",
        "weather",
        "define",
        "meaning",
    }

    # Keywords indicating complex queries
    COMPLEX_KEYWORDS = {
        "explain",
        "analyze",
        "compare",
        "contrast",
        "evaluate",
        "assess",
        "argue",
        "discuss",
        "debate",
        "reason",
        "derive",
        "prove",
        "troubleshoot",
        "debug",
        "optimize",
        "refactor",
        "design",
        "architecture",
        "solution",
        "strategy",
        "approach",
        "methodology",
        "implement",
        "integrate",
    }

    # Technical terms indicating higher complexity
    TECHNICAL_TERMS = {
        "algorithm",
        "complexity",
        "performance",
        "optimization",
        "architecture",
        "design pattern",
        "api",
        "protocol",
        "framework",
        "library",
        "database",
        "query",
        "execution",
        "concurrency",
        "threading",
        "async",
        "memory",
        "allocation",
        "garbage collection",
        "quantum",
        "cryptography",
        "machine learning",
        "neural network",
        "regression",
        "classification",
    }

    # Common question starters (typically simpler)
    SIMPLE_STARTERS = {"what", "where", "when", "who", "which", "how much", "do"}

    # Complex question starters
    COMPLEX_STARTERS = {"explain", "analyze", "compare", "why", "how", "describe"}

    def __init__(self):
        """Initialize analyzer."""
        self._analysis_cache: Dict[str, ComplexityAnalysis] = {}

    def analyze(self, query: str) -> ComplexityAnalysis:
        """
        Analyze query complexity.
        
        Args:
            query: User query string
        
        Returns:
            ComplexityAnalysis with level and details
        
        Processing Time: ~1-5ms per query
        Memory Impact: None (uses pre-built dictionaries)
        """
        # Check cache first
        cache_key = query.lower().strip()
        if cache_key in self._analysis_cache:
            return self._analysis_cache[cache_key]

        query_lower = query.lower().strip()

        # Calculate basic metrics
        word_count = len(query.split())
        unique_words = len(set(query.lower().split()))
        
        # Analyze query characteristics
        indicators: List[str] = []
        simple_score = 0.0
        complex_score = 0.0

        # Check word count
        if word_count <= 5:
            simple_score += 0.3
            indicators.append("short")
        elif word_count > 20:
            complex_score += 0.3
            indicators.append("long")

        # Check for question markers
        if "?" in query:
            indicators.append("question")
            # Analyze question type
            for starter in self.SIMPLE_STARTERS:
                if query_lower.startswith(starter):
                    simple_score += 0.2
                    break

            for starter in self.COMPLEX_STARTERS:
                if query_lower.startswith(starter):
                    complex_score += 0.2
                    break

        # Check for simple keywords
        for keyword in self.SIMPLE_KEYWORDS:
            if keyword in query_lower:
                simple_score += 0.15
                indicators.append(f"simple_keyword:{keyword}")
                break

        # Check for complex keywords
        for keyword in self.COMPLEX_KEYWORDS:
            if keyword in query_lower:
                complex_score += 0.25
                indicators.append(f"complex_keyword:{keyword}")

        # Check for technical terms
        for term in self.TECHNICAL_TERMS:
            if term in query_lower:
                complex_score += 0.1
                indicators.append(f"technical:{term}")

        # Check for multiple sentences (higher complexity)
        sentence_count = len(re.split(r'[.!?]+', query.strip())) - 1
        if sentence_count > 2:
            complex_score += 0.2
            indicators.append(f"multiple_sentences:{sentence_count}")

        # Check vocabulary richness
        if word_count > 0:
            vocab_ratio = unique_words / word_count
            if vocab_ratio > 0.85:  # Very unique words
                complex_score += 0.1
                indicators.append("high_vocabulary")

        # Check for imperative mood (typically more complex)
        if query_lower.endswith(("!", "...", "...")):
            complex_score += 0.1
            indicators.append("emphatic")

        # Normalize scores
        total_score = simple_score + complex_score
        if total_score > 0:
            simple_score /= total_score
            complex_score /= total_score
        else:
            simple_score = 0.5
            complex_score = 0.5

        # Determine level
        if complex_score > 0.6 or complex_score > simple_score + 0.3:
            level = ComplexityLevel.COMPLEX
            score = complex_score
        elif simple_score > 0.6 or simple_score > complex_score + 0.3:
            level = ComplexityLevel.SIMPLE
            score = simple_score
        else:
            level = ComplexityLevel.MODERATE
            score = 0.5

        # Determine model suggestion
        if level == ComplexityLevel.SIMPLE:
            suggested_model = "fast"
            estimated_processing_ms = 100
            estimated_context_tokens = 100
            cache_friendly = True
        elif level == ComplexityLevel.MODERATE:
            suggested_model = "balanced"
            estimated_processing_ms = 500
            estimated_context_tokens = 500
            cache_friendly = False
        else:
            suggested_model = "smart"
            estimated_processing_ms = 2000
            estimated_context_tokens = 2000
            cache_friendly = False

        analysis = ComplexityAnalysis(
            level=level,
            score=score,
            word_count=word_count,
            unique_words=unique_words,
            complexity_indicators=indicators,
            estimated_processing_ms=estimated_processing_ms,
            estimated_context_size_tokens=estimated_context_tokens,
            cache_friendly=cache_friendly,
            suggested_model=suggested_model,
        )

        # Cache result
        self._analysis_cache[cache_key] = analysis

        return analysis

    def should_use_cache(self, query: str) -> bool:
        """Check if query result can be cached safely."""
        analysis = self.analyze(query)
        return analysis.cache_friendly

    def suggest_fast_path(self, query: str) -> bool:
        """Check if query can use fast processing path."""
        analysis = self.analyze(query)
        return analysis.level == ComplexityLevel.SIMPLE

    def estimate_memory_impact(self, analysis: ComplexityAnalysis) -> int:
        """
        Estimate memory impact of processing this query (MB).
        
        Args:
            analysis: Complexity analysis result
        
        Returns:
            Estimated memory needed in MB
        """
        # Base overhead
        base = 10

        # Context size adds memory
        context_memory = analysis.estimated_context_size_tokens / 1000

        # Processing overhead based on complexity
        if analysis.level == ComplexityLevel.SIMPLE:
            overhead = 5
        elif analysis.level == ComplexityLevel.MODERATE:
            overhead = 15
        else:
            overhead = 30

        return base + int(context_memory) + overhead

    def get_analysis_report(self, query: str) -> str:
        """Get human-readable analysis report."""
        analysis = self.analyze(query)

        report = (
            f"Query Complexity Analysis:\n"
            f"  Level: {analysis.level.value}\n"
            f"  Score: {analysis.score:.2f}\n"
            f"  Words: {analysis.word_count} (unique: {analysis.unique_words})\n"
            f"  Indicators: {', '.join(analysis.complexity_indicators[:5])}\n"
            f"  Suggested Model: {analysis.suggested_model}\n"
            f"  Estimated Time: {analysis.estimated_processing_ms}ms\n"
            f"  Estimated Memory: {self.estimate_memory_impact(analysis)}MB\n"
            f"  Cache Friendly: {analysis.cache_friendly}\n"
        )

        return report

    def clear_cache(self) -> None:
        """Clear analysis cache."""
        self._analysis_cache.clear()

    def __repr__(self) -> str:
        return f"<QueryComplexityAnalyzer: {len(self._analysis_cache)} cached>"


def get_query_analyzer() -> QueryComplexityAnalyzer:
    """Get or create global query analyzer instance."""
    if not hasattr(get_query_analyzer, "_instance"):
        get_query_analyzer._instance = QueryComplexityAnalyzer()
    return get_query_analyzer._instance


def estimate_complexity_analysis_overhead() -> Dict[str, str]:
    """Estimate overhead of query analysis."""
    return {
        "keyword_dictionaries": "~200KB",
        "analyzer_instance": "~100KB",
        "per_query_time": "~1-5ms",
        "cache_per_entry": "~1KB",
        "total_per_100_queries": "~1.2MB if all cached",
    }
