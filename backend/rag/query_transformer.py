"""
rag/query_transformer.py

Query Understanding, Intent Classification, and Context Transformation.

Supports 9 intent categories:

1. eligibility
2. discovery
3. benefits
4. documents
5. procedure
6. comparison
7. document_explanation
8. follow_up
9. general
"""

import logging
import re
from typing import Optional

from django.conf import settings


logger = logging.getLogger(__name__)


class QueryTransformer:
    """
    Query understanding and transformation engine.

    Responsibilities:
    1. Intent classification
    2. Government scheme acronym expansion
    3. Citizen profile context injection
    4. Multi-query generation
    5. HyDE generation
    """

    # ============================================================
    # INTENT SIGNALS
    # ============================================================

    INTENT_SIGNALS = {
        # --------------------------------------------------------
        # ELIGIBILITY
        # --------------------------------------------------------
        "eligibility": [
            "am i eligible",
            "am i eligible for",
            "do i qualify",
            "do i qualify for",
            "can i apply for",
            "can i receive",
            "can i get",
            "will i get",
            "check my eligibility",
            "my eligibility",
            "my eligibility for",
            "am i qualified",
            "do i meet the eligibility",
            "do i meet eligibility",
            "who is eligible",
            "who can apply",
            "eligibility criteria",
        ],

        # --------------------------------------------------------
        # DISCOVERY
        # --------------------------------------------------------
        "discovery": [
            "what schemes",
            "which schemes",
            "schemes for",
            "list of schemes",
            "find schemes",
            "suggest schemes",
            "schemes available",
            "programmes for",
            "programs for",
            "yojana for",
            "schemes in",
            "scholarships",
            "scholarship",
            "find education",
            "grants for",
            "assistance for",
            "welfare programs",
            "welfare schemes",
        ],

        # --------------------------------------------------------
        # BENEFITS
        # --------------------------------------------------------
        "benefits": [
            "what benefits",
            "what benefit",
            "benefits of",
            "benefit of",
            "how much money",
            "how much amount",
            "subsidy amount",
            "financial assistance",
            "financial support",
            "what will i get",
            "financial aid",
            "incentive",
            "coverage amount",
            "benefit",
            "benefits",
            "amount provided",
            "amount available",
            "financial benefit",
        ],

        # --------------------------------------------------------
        # DOCUMENTS
        # --------------------------------------------------------
        "documents": [
            "what documents",
            "documents required",
            "documents needed",
            "required documents",
            "papers needed",
            "certificates required",
            "id proof",
            "ration card required",
            "aadhaar",
            "aadhaar card",
            "pan card",
            "card needed",
            "certificate needed",
            "proof needed",
            "document needed",
            "documents",
        ],

        # --------------------------------------------------------
        # PROCEDURE
        # --------------------------------------------------------
        "procedure": [
            "how to apply",
            "how can i apply",
            "how do i apply",
            "application process",
            "where to apply",
            "steps to apply",
            "registration process",
            "apply online",
            "application portal",
            "how do i register",
            "how to register",
            "registration",
            "application procedure",
        ],

        # --------------------------------------------------------
        # COMPARISON
        # --------------------------------------------------------
        "comparison": [
            "compare",
            "difference between",
            "versus",
            "vs",
            "which is better",
            "difference in benefits",
            "how does it differ",
            "compare benefits",
        ],

        # --------------------------------------------------------
        # DOCUMENT EXPLANATION
        # --------------------------------------------------------
        "document_explanation": [
            "explain document",
            "what does this mean",
            "explain clause",
            "explain section",
            "clarify guideline",
            "interpret clause",
            "what does paragraph",
            "in the document",
            "document mean",
            "in the pdf",
            "section mean",
            "clause mean",
            "meaning of",
            "explain this section",
            "explain this paragraph",
        ],

        # --------------------------------------------------------
        # FOLLOW UP
        # --------------------------------------------------------
        "follow_up": [
            "what about",
            "and for my",
            "does that apply",
            "is there also",
            "what if",
            "how about",
            "in that case",
            "can they also",
        ],
    }

    # ============================================================
    # GOVERNMENT ACRONYMS
    # ============================================================

    GOVERNMENT_ACRONYMS = {
        "pm-kisan": "PM-KISAN Pradhan Mantri Kisan Samman Nidhi",
        "pmkisan": "PM-KISAN Pradhan Mantri Kisan Samman Nidhi",

        "pmay": "PMAY Pradhan Mantri Awas Yojana",
        "pmay-u": "PMAY-U Pradhan Mantri Awas Yojana Urban",
        "pmayu": "PMAY-U Pradhan Mantri Awas Yojana Urban",

        "pmay-g": "PMAY-G Pradhan Mantri Awas Yojana Gramin",
        "pmayg": "PMAY-G Pradhan Mantri Awas Yojana Gramin",

        "pmuy": "PMUY Pradhan Mantri Ujjwala Yojana LPG",
        "ujjwala": "PMUY Pradhan Mantri Ujjwala Yojana",

        "apy": "APY Atal Pension Yojana",

        "pmjay": (
            "PM-JAY Ayushman Bharat "
            "Pradhan Mantri Jan Arogya Yojana"
        ),

        "pm-jay": (
            "PM-JAY Ayushman Bharat "
            "Pradhan Mantri Jan Arogya Yojana"
        ),

        "ayushman": (
            "PM-JAY Ayushman Bharat "
            "Pradhan Mantri Jan Arogya Yojana"
        ),

        "pmfby": (
            "PMFBY Pradhan Mantri Fasal Bima Yojana "
            "Crop Insurance"
        ),

        "pms-sc": (
            "PMS-SC Post Matric Scholarship for SC "
            "Scheduled Caste Students"
        ),

        "bscc": (
            "BSCC Bihar Student Credit Card Scheme "
            "Education Loan"
        ),

        "ssy": "SSY Sukanya Samriddhi Yojana Account",
        "sukanya": "SSY Sukanya Samriddhi Yojana Account",

        "ignoaps": (
            "IGNOAPS Indira Gandhi National Old Age "
            "Pension Scheme"
        ),

        "nsap": (
            "NSAP National Social Assistance Programme "
            "IGNOAPS"
        ),

        "mjpjay": (
            "MJPJAY Mahatma Jyotirao Phule "
            "Jan Arogya Yojana Maharashtra"
        ),

        "mkuy": (
            "MKUY Mukhyamantri Kanya Utthan Yojana Bihar"
        ),

        "svanidhi": (
            "PM SVANidhi Street Vendor Micro Credit"
        ),

        "pm-svanidhi": (
            "PM SVANidhi Street Vendor Micro Credit"
        ),
    }

    # ============================================================
    # ACRONYM EXPANSION
    # ============================================================

    def expand_acronyms(self, query: str) -> str:
        """
        Expand government scheme acronyms while preserving
        the original user query.
        """

        if not query:
            return query

        expansions = []

        tokens = re.findall(r"[\w\-]+", query)

        for token in tokens:
            token_lower = token.lower()

            if token_lower in self.GOVERNMENT_ACRONYMS:
                expansion = self.GOVERNMENT_ACRONYMS[token_lower]

                if expansion.lower() not in query.lower():
                    expansions.append(expansion)

        if expansions:
            return f"{query} {' '.join(expansions)}"

        return query

    # ============================================================
    # INTENT CLASSIFICATION
    # ============================================================

    def classify(self, query: str) -> str:
        """
        Classify the user query.

        Important rules:

        "What benefit does PM-KISAN provide to eligible farmers?"
            -> benefits

        "How can I apply for PM-KISAN?"
            -> procedure

        "Can I apply for PM-KISAN?"
            -> eligibility

        "Am I eligible for PM-KISAN?"
            -> eligibility

        "What documents are required for PM-KISAN?"
            -> documents
        """

        if not query:
            return "general"

        query_lower = query.lower().strip()

        # Normalize multiple spaces
        query_lower = re.sub(
            r"\s+",
            " ",
            query_lower,
        )

        # ========================================================
        # 1. PROCEDURE
        # ========================================================
        #
        # MUST come before eligibility.
        #
        # Why?
        #
        # "How can I apply for PM-KISAN?"
        #
        # contains "can I apply for", but it is clearly asking
        # HOW to apply, not whether the user qualifies.
        # ========================================================

        procedure_phrases = [
            "how can i apply",
            "how do i apply",
            "how to apply",
            "application process",
            "application procedure",
            "steps to apply",
            "where to apply",
            "apply online",
            "registration process",
            "how do i register",
            "how to register",
        ]

        for phrase in procedure_phrases:
            if phrase in query_lower:
                return "procedure"

        # ========================================================
        # 2. PERSONAL ELIGIBILITY
        # ========================================================
        #
        # These phrases indicate that the USER is asking about
        # their own eligibility/applicability.
        # ========================================================

        eligibility_phrases = [
            "am i eligible",
            "am i eligible for",
            "do i qualify",
            "do i qualify for",
            "can i apply for",
            "can i receive",
            "can i get",
            "will i get",
            "check my eligibility",
            "my eligibility",
            "my eligibility for",
            "am i qualified",
            "do i meet the eligibility",
            "do i meet eligibility",
        ]

        for phrase in eligibility_phrases:
            if phrase in query_lower:
                return "eligibility"

        # ========================================================
        # 3. BENEFITS
        # ========================================================
        #
        # Check benefit questions before generic matching.
        #
        # "eligible farmers" must NOT make this an eligibility
        # query.
        # ========================================================

        benefit_phrases = [
            "what benefit",
            "what benefits",
            "benefits of",
            "benefit of",
            "how much money",
            "how much amount",
            "subsidy amount",
            "financial assistance",
            "financial support",
            "what will i get",
            "financial aid",
            "coverage amount",
            "amount provided",
            "amount available",
            "financial benefit",
        ]

        for phrase in benefit_phrases:
            if phrase in query_lower:
                return "benefits"

        # ========================================================
        # 4. DOCUMENTS
        # ========================================================

        document_phrases = [
            "what documents",
            "documents required",
            "documents needed",
            "required documents",
            "papers needed",
            "certificates required",
            "id proof",
            "ration card required",
            "aadhaar card",
            "pan card",
            "card needed",
            "certificate needed",
            "proof needed",
            "document needed",
        ]

        for phrase in document_phrases:
            if phrase in query_lower:
                return "documents"

        # ========================================================
        # 5. COMPARISON
        # ========================================================

        comparison_phrases = [
            "compare",
            "difference between",
            "versus",
            "vs",
            "which is better",
            "difference in benefits",
            "how does it differ",
            "compare benefits",
        ]

        for phrase in comparison_phrases:
            if phrase in query_lower:
                return "comparison"

        # ========================================================
        # 6. DOCUMENT EXPLANATION
        # ========================================================

        explanation_phrases = [
            "explain document",
            "what does this mean",
            "explain clause",
            "explain section",
            "clarify guideline",
            "interpret clause",
            "what does paragraph",
            "in the document",
            "document mean",
            "in the pdf",
            "section mean",
            "clause mean",
            "meaning of",
            "explain this section",
            "explain this paragraph",
        ]

        for phrase in explanation_phrases:
            if phrase in query_lower:
                return "document_explanation"

        # ========================================================
        # 7. DISCOVERY
        # ========================================================

        discovery_phrases = [
            "what schemes",
            "which schemes",
            "schemes for",
            "list of schemes",
            "find schemes",
            "suggest schemes",
            "schemes available",
            "programmes for",
            "programs for",
            "yojana for",
            "schemes in",
            "scholarships",
            "scholarship",
            "find education",
            "grants for",
            "welfare programs",
            "welfare schemes",
        ]

        for phrase in discovery_phrases:
            if phrase in query_lower:
                return "discovery"

        # ========================================================
        # 8. FOLLOW-UP
        # ========================================================

        follow_up_phrases = [
            "what about",
            "and for my",
            "does that apply",
            "is there also",
            "what if",
            "how about",
            "in that case",
            "can they also",
        ]

        for phrase in follow_up_phrases:
            if phrase in query_lower:
                return "follow_up"

        # ========================================================
        # 9. GENERIC INTENT SIGNALS
        # ========================================================

        for intent, signals in self.INTENT_SIGNALS.items():

            # Eligibility was already handled explicitly.
            if intent == "eligibility":
                continue

            for signal in signals:

                # Word-boundary matching
                if re.search(
                    r"\b" + re.escape(signal) + r"\b",
                    query_lower,
                ):
                    return intent

                # Fallback substring matching
                if signal in query_lower:
                    return intent

        # ========================================================
        # DEFAULT
        # ========================================================

        return "general"

    # ============================================================
    # QUERY TRANSFORMATION
    # ============================================================

    def transform(
        self,
        query: str,
        query_type: str,
        user_context: Optional[dict] = None,
    ) -> dict:
        """
        Transform and expand the query based on:
        - intent
        - government scheme acronyms
        - citizen profile
        - HyDE
        """

        expanded_query = self.expand_acronyms(query)

        result = {
            "primary_query": expanded_query,
            "expanded_queries": [
                expanded_query,
                query,
            ],
            "hyde_text": None,
            "query_type": query_type,
        }

        # ========================================================
        # CITIZEN PROFILE CONTEXT
        # ========================================================

        if user_context and query_type in [
            "eligibility",
            "discovery",
            "benefits",
        ]:

            contextual_query = self._inject_context(
                expanded_query,
                user_context,
            )

            result["primary_query"] = contextual_query

            result["expanded_queries"] = [
                contextual_query,
                expanded_query,
                query,
            ]

        # ========================================================
        # HYDE
        # ========================================================

        if query_type in [
            "eligibility",
            "information",
            "procedure",
            "benefits",
            "documents",
        ]:

            try:
                result["hyde_text"] = self._generate_hyde(
                    query,
                    query_type,
                    user_context,
                )

            except Exception as exc:
                logger.debug(
                    "HyDE generation skipped: %s",
                    exc,
                )

        return result

    # ============================================================
    # CITIZEN CONTEXT
    # ============================================================

    def _inject_context(
        self,
        query: str,
        user_context: dict,
    ) -> str:
        """
        Enrich query with citizen demographic information.
        """

        parts = []

        if user_context.get("state"):
            parts.append(
                f"state: {user_context['state']}"
            )

        if user_context.get("occupation"):
            parts.append(
                f"occupation: {user_context['occupation']}"
            )

        if user_context.get("social_category"):
            parts.append(
                f"category: {user_context['social_category']}"
            )

        if user_context.get("age"):
            parts.append(
                f"age: {user_context['age']}"
            )

        if (
            user_context.get("annual_income_inr")
            or user_context.get("annual_income")
        ):

            income = (
                user_context.get("annual_income_inr")
                or user_context.get("annual_income")
            )

            parts.append(
                f"income: ₹{income}"
            )

        if user_context.get("is_bpl"):
            parts.append("BPL cardholder")

        if user_context.get("is_student"):
            parts.append("Student")

        if user_context.get("has_disability"):
            parts.append(
                "Person with Disability"
            )

        if parts:
            return (
                f"{query} "
                f"[Citizen Context: {', '.join(parts)}]"
            )

        return query

    # ============================================================
    # HYDE GENERATION
    # ============================================================

    def _generate_hyde(
        self,
        query: str,
        query_type: str,
        user_context: Optional[dict] = None,
    ) -> Optional[str]:
        """
        Generate a hypothetical official-government-style
        excerpt for semantic retrieval.

        Returns None when Google API is not configured.
        """

        api_key = getattr(
            settings,
            "GOOGLE_API_KEY",
            "",
        )

        if (
            not api_key
            or api_key == "mock-google-api-key"
        ):
            return None

        try:

            import google.generativeai as genai

            genai.configure(
                api_key=api_key
            )

            fast_model = getattr(
                settings,
                "LLM_FAST_MODEL",
                "gemini-2.0-flash-exp",
            )

            model = genai.GenerativeModel(
                fast_model
            )

            prompt = (
                "Write a short, factual 2-sentence excerpt "
                "from an official Indian government scheme "
                "notification answering this question: "
                f"{query}"
            )

            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=150,
                    temperature=0.2,
                ),
            )

            if not response or not response.text:
                return None

            return response.text.strip()

        except Exception as exc:

            logger.debug(
                "HyDE call failed: %s",
                exc,
            )

            return None