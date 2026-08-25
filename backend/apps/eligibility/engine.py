"""
apps/eligibility/engine.py — Deterministic Eligibility Evaluation Engine.

This engine evaluates citizen profile data against structured government scheme rules
stored in the database (SchemeEligibilityRule).

Rule Grouping:
- Rules with the same `rule_group` are combined using AND.
- Different `rule_group`s are combined using OR (alternative qualification tracks).

Verdicts:
- ELIGIBLE: User definitively meets all mandatory criteria in at least one rule group.
- NOT_ELIGIBLE: User definitively fails mandatory criteria across all qualification groups.
- POSSIBLY_ELIGIBLE: User meets core criteria, but non-mandatory criteria are unverified.
- INSUFFICIENT_INFORMATION: Mandatory profile attributes are missing, preventing certainty.

Evidence & Citations:
- Every result retains passed rules, failed rules, missing info, and official source links.
"""
from __future__ import annotations

import datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from apps.schemes.models import (
    GovernmentScheme,
    RuleDataType,
    RuleOperator,
    SchemeEligibilityRule,
    SchemeSource,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# 1. Enums and Data Containers
# ─────────────────────────────────────────────────────────────

class EligibilityVerdict(str, Enum):
    LIKELY_ELIGIBLE = "Likely Eligible"
    ELIGIBLE = "Likely Eligible"
    POSSIBLY_ELIGIBLE = "Possibly Eligible"
    INSUFFICIENT_INFORMATION = "Insufficient Information"
    NOT_ELIGIBLE = "Not Eligible"


class RuleEvaluationStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    MISSING_INFO = "MISSING_INFO"


class RuleCheckDetail:
    """Detailed evaluation result for an individual SchemeEligibilityRule."""

    def __init__(
        self,
        rule_id: Optional[str],
        rule_group: int,
        criterion_key: str,
        rule_description: str,
        operator: str,
        expected_value: Any,
        user_value: Any,
        status: RuleEvaluationStatus,
        is_mandatory: bool = True,
        is_disqualification: bool = False,
        reason: str = "",
    ):
        self.rule_id = str(rule_id) if rule_id else None
        self.rule_group = rule_group
        self.criterion_key = criterion_key
        self.rule_description = rule_description
        self.operator = operator
        self.expected_value = expected_value
        self.user_value = user_value
        self.status = status
        self.is_mandatory = is_mandatory
        self.is_disqualification = is_disqualification
        self.reason = reason

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_group": self.rule_group,
            "criterion_key": self.criterion_key,
            "rule_description": self.rule_description,
            "operator": self.operator,
            "expected_value": self.expected_value,
            "user_value": self.user_value,
            "status": self.status.value,
            "is_mandatory": self.is_mandatory,
            "is_disqualification": self.is_disqualification,
            "reason": self.reason,
        }


class EligibilityEvaluationResult:
    """Complete evaluation outcome for a scheme against a user profile."""

    def __init__(
        self,
        scheme_id: str,
        scheme_name: str,
        verdict: EligibilityVerdict,
        is_eligible: Optional[bool],
        confidence_score: float,
        rules_checked: List[RuleCheckDetail],
        passed_rules: List[RuleCheckDetail],
        failed_rules: List[RuleCheckDetail],
        missing_information: List[str],
        evidence_sources: List[Dict[str, Any]],
        summary_explanation: str,
        rule_groups_evaluated: Optional[Dict[int, Dict[str, Any]]] = None,
        short_title: str = "",
    ):
        self.scheme_id = scheme_id
        self.scheme_name = scheme_name
        self.short_title = short_title
        self.verdict = verdict
        self.is_eligible = is_eligible
        self.confidence_score = confidence_score
        self.rules_checked = rules_checked
        self.passed_rules = passed_rules
        self.failed_rules = failed_rules
        self.missing_information = missing_information
        self.evidence_sources = evidence_sources
        self.summary_explanation = summary_explanation
        self.rule_groups_evaluated = rule_groups_evaluated or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scheme_id": self.scheme_id,
            "scheme_name": self.scheme_name,
            "short_title": self.short_title,
            "verdict": self.verdict.value,
            "is_eligible": self.is_eligible,
            "confidence_score": round(self.confidence_score, 2),
            "rules_checked": [r.to_dict() for r in self.rules_checked],
            "passed_rules": [r.to_dict() for r in self.passed_rules],
            "failed_rules": [r.to_dict() for r in self.failed_rules],
            "missing_information": self.missing_information,
            "evidence_sources": self.evidence_sources,
            "summary_explanation": self.summary_explanation,
            "rule_groups_summary": self.rule_groups_evaluated,
        }


# ─────────────────────────────────────────────────────────────
# 2. Context Extraction & State Alias Map
# ─────────────────────────────────────────────────────────────

# Standard Indian State / UT code to common name mappings for flexible equality checks
STATE_ALIASES: Dict[str, Set[str]] = {
    "AP": {"andhra pradesh", "ap"},
    "AR": {"arunachal pradesh", "ar"},
    "AS": {"assam", "as"},
    "BR": {"bihar", "br"},
    "CG": {"chhattisgarh", "cg", "ct"},
    "GA": {"goa", "ga"},
    "GJ": {"gujarat", "gj"},
    "HR": {"haryana", "hr"},
    "HP": {"himachal pradesh", "hp"},
    "JH": {"jharkhand", "jh"},
    "KA": {"karnataka", "ka"},
    "KL": {"kerala", "kl"},
    "MP": {"madhya pradesh", "mp"},
    "MH": {"maharashtra", "mh"},
    "MN": {"manipur", "mn"},
    "ML": {"meghalaya", "ml"},
    "MZ": {"mizoram", "mz"},
    "NL": {"nagaland", "nl"},
    "OD": {"odisha", "orissa", "od", "or"},
    "PB": {"punjab", "pb"},
    "RJ": {"rajasthan", "rj"},
    "SK": {"sikkim", "sk"},
    "TN": {"tamil nadu", "tn"},
    "TS": {"telangana", "ts", "tg"},
    "TR": {"tripura", "tr"},
    "UP": {"uttar pradesh", "up"},
    "UK": {"uttarakhand", "uk", "ua"},
    "WB": {"west bengal", "wb"},
    "AN": {"andaman and nicobar", "andaman and nicobar islands", "an"},
    "CH": {"chandigarh", "ch"},
    "DH": {"dadra and nagar haveli and daman and diu", "daman and diu", "dh", "dd", "dn"},
    "DL": {"delhi", "nct of delhi", "dl"},
    "JK": {"jammu and kashmir", "jk"},
    "LA": {"ladakh", "la"},
    "LD": {"lakshadweep", "ld"},
    "PY": {"puducherry", "pondicherry", "py"},
}


class ContextResolver:
    """Extracts and normalizes attributes from user profile or dictionary context."""

    SYNONYMS: Dict[str, List[str]] = {
        "age": ["age", "user_age", "applicant_age"],
        "annual_income": ["annual_income", "annual_income_inr", "income", "household_income", "family_income"],
        "state": ["state", "state_code", "state_name", "residence_state", "domicile_state"],
        "district": ["district", "district_name", "residence_district"],
        "gender": ["gender", "sex"],
        "occupation": ["occupation", "occupation_category", "profession", "job"],
        "education_level": ["education_level", "education", "qualification", "highest_education"],
        "social_category": ["social_category", "caste_category", "category", "caste"],
        "is_bpl": ["is_bpl", "bpl", "below_poverty_line"],
        "is_student": ["is_student", "student"],
        "has_disability": ["has_disability", "disability", "is_disabled", "pwd"],
        "disability_percentage": ["disability_percentage", "pwd_percentage"],
        "land_holding_acres": ["land_holding_acres", "land_holding", "land_acres", "acres"],
        "is_marginal_farmer": ["is_marginal_farmer", "marginal_farmer"],
        "is_small_farmer": ["is_small_farmer", "small_farmer"],
        "is_ex_serviceman": ["is_ex_serviceman", "ex_serviceman"],
        "is_minority": ["is_minority", "minority"],
        "is_widow": ["is_widow", "widow"],
        "is_single_girl_child": ["is_single_girl_child", "single_girl_child"],
        "family_size": ["family_size", "household_size", "family_members_count"],
        "date_of_birth": ["date_of_birth", "dob", "birth_date"],
        "is_urban": ["is_urban", "urban", "area_type"],
    }

    @classmethod
    def get_value(cls, key: str, context: Dict[str, Any]) -> Any:
        """Find value in context matching key or its known synonyms/sub-dicts."""
        norm_key = key.strip().lower()

        # 1. Direct match
        if norm_key in context and context[norm_key] not in (None, ""):
            return context[norm_key]

        # 2. Synonym match
        synonyms = cls.SYNONYMS.get(norm_key, [norm_key])
        for syn in synonyms:
            if syn in context and context[syn] not in (None, ""):
                return context[syn]

        # 3. Check in nested 'additional_attributes' or 'attributes'
        for nested_dict_key in ["additional_attributes", "attributes", "profile_data"]:
            nested = context.get(nested_dict_key)
            if isinstance(nested, dict):
                if norm_key in nested and nested[norm_key] not in (None, ""):
                    return nested[norm_key]
                for syn in synonyms:
                    if syn in nested and nested[syn] not in (None, ""):
                        return nested[syn]

        # 4. Computed value: derive 'age' from 'date_of_birth' if age is missing
        if norm_key == "age" and ("date_of_birth" in context or "dob" in context):
            dob = context.get("date_of_birth") or context.get("dob")
            computed_age = cls._calculate_age(dob)
            if computed_age is not None:
                return computed_age

        return None

    @staticmethod
    def _calculate_age(dob_val: Any) -> Optional[int]:
        """Derives integer age from a date object or date string."""
        if not dob_val:
            return None
        target_date: Optional[datetime.date] = None
        if isinstance(dob_val, (datetime.date, datetime.datetime)):
            target_date = dob_val if isinstance(dob_val, datetime.date) else dob_val.date()
        elif isinstance(dob_val, str):
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
                try:
                    target_date = datetime.datetime.strptime(dob_val.strip(), fmt).date()
                    break
                except ValueError:
                    continue

        if target_date:
            today = datetime.date.today()
            return today.year - target_date.year - ((today.month, today.day) < (target_date.month, target_date.day))
        return None


# ─────────────────────────────────────────────────────────────
# 3. Value Parsing & Operator Evaluation
# ─────────────────────────────────────────────────────────────

class ValueParser:
    """Parses and normalizes raw values according to RuleDataType."""

    @classmethod
    def parse(cls, raw_val: Any, data_type: str) -> Any:
        if raw_val is None:
            return None

        dtype = str(data_type).upper()

        if dtype == RuleDataType.INTEGER:
            return cls._parse_int(raw_val)
        elif dtype == RuleDataType.DECIMAL:
            return cls._parse_decimal(raw_val)
        elif dtype == RuleDataType.BOOLEAN:
            return cls._parse_bool(raw_val)
        elif dtype == RuleDataType.DATE:
            return cls._parse_date(raw_val)
        elif dtype == RuleDataType.LIST:
            return cls._parse_list(raw_val)
        else:  # STRING or fallback
            return str(raw_val).strip()

    @staticmethod
    def _parse_int(val: Any) -> Optional[int]:
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            return int(val)
        cleaned = re.sub(r"[^\d\-+]", "", str(val).strip())
        try:
            return int(cleaned)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_decimal(val: Any) -> Optional[Decimal]:
        if isinstance(val, Decimal):
            return val
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            return Decimal(str(val))
        cleaned = re.sub(r"[^\d.\-+]", "", str(val).strip())
        try:
            return Decimal(cleaned)
        except (InvalidOperation, ValueError, TypeError):
            return None

    @staticmethod
    def _parse_bool(val: Any) -> Optional[bool]:
        if isinstance(val, bool):
            return val
        s = str(val).strip().lower()
        if s in ("true", "1", "yes", "y", "t", "eligible", "active"):
            return True
        if s in ("false", "0", "no", "n", "f", "ineligible", "inactive"):
            return False
        return None

    @staticmethod
    def _parse_date(val: Any) -> Optional[datetime.date]:
        if isinstance(val, datetime.date):
            return val
        if isinstance(val, datetime.datetime):
            return val.date()
        s = str(val).strip()
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        return None

    @staticmethod
    def _parse_list(val: Any) -> List[str]:
        if isinstance(val, list):
            return [str(x).strip() for x in val if x is not None]
        if isinstance(val, tuple):
            return [str(x).strip() for x in val if x is not None]
        s = str(val).strip()
        # Split by comma or semicolon
        items = re.split(r"[,;]+", s)
        return [i.strip() for i in items if i.strip()]


class RuleComparator:
    """Deterministic comparison logic across all RuleOperator types."""

    @classmethod
    def compare(
        cls,
        user_raw: Any,
        operator: str,
        target_raw: str,
        min_raw: Optional[str],
        max_raw: Optional[str],
        data_type: str,
    ) -> Tuple[bool, str]:
        """
        Compares user_raw with target using operator.
        Returns: (passed: bool, reason: str)
        """
        # EXISTS operator check
        if operator == RuleOperator.EXISTS:
            passed = user_raw not in (None, "", [], {})
            reason = "Field is present in profile" if passed else "Required field is missing"
            return passed, reason

        # Parse target values
        dtype = str(data_type).upper()
        target_val = ValueParser.parse(target_raw, dtype) if target_raw is not None else None
        min_val = ValueParser.parse(min_raw, dtype) if min_raw is not None else None
        max_val = ValueParser.parse(max_raw, dtype) if max_raw is not None else None
        user_val = ValueParser.parse(user_raw, dtype)

        if user_val is None and operator not in (RuleOperator.BOOLEAN_FALSE,):
            return False, f"Could not parse user value '{user_raw}' for type {dtype}"

        # ── EQUALS / NOT_EQUALS ──
        if operator == RuleOperator.EQUALS:
            passed = cls._check_equality(user_val, target_val, target_raw, dtype)
            reason = f"Value '{user_raw}' matched required '{target_raw}'" if passed else f"Value '{user_raw}' did not match '{target_raw}'"
            return passed, reason

        if operator == RuleOperator.NOT_EQUALS:
            passed = not cls._check_equality(user_val, target_val, target_raw, dtype)
            reason = f"Value '{user_raw}' correctly differed from '{target_raw}'" if passed else f"Value '{user_raw}' matched excluded value '{target_raw}'"
            return passed, reason

        # ── NUMERIC / DATE COMPARISONS ──
        if operator == RuleOperator.GREATER_THAN:
            if target_val is None:
                return False, "Target comparison value missing"
            passed = user_val > target_val
            return passed, f"{user_val} > {target_val} (Result: {passed})"

        if operator == RuleOperator.LESS_THAN:
            if target_val is None:
                return False, "Target comparison value missing"
            passed = user_val < target_val
            return passed, f"{user_val} < {target_val} (Result: {passed})"

        if operator == RuleOperator.GTE:
            if target_val is None:
                return False, "Target comparison value missing"
            passed = user_val >= target_val
            return passed, f"{user_val} >= {target_val} (Result: {passed})"

        if operator == RuleOperator.LTE:
            if target_val is None:
                return False, "Target comparison value missing"
            passed = user_val <= target_val
            return passed, f"{user_val} <= {target_val} (Result: {passed})"

        if operator == RuleOperator.BETWEEN:
            if min_val is None and max_val is None:
                return False, "BETWEEN bounds missing"
            lower_ok = True if min_val is None else user_val >= min_val
            upper_ok = True if max_val is None else user_val <= max_val
            passed = lower_ok and upper_ok
            return passed, f"{min_raw} <= {user_val} <= {max_raw} (Result: {passed})"

        # ── LIST MEMBERSHIP ──
        if operator == RuleOperator.IN_LIST:
            target_list = ValueParser.parse(target_raw, RuleDataType.LIST)
            passed = cls._check_in_list(user_val, target_list)
            return passed, f"Value '{user_raw}' in allowed options {target_list} (Result: {passed})"

        if operator == RuleOperator.NOT_IN_LIST:
            target_list = ValueParser.parse(target_raw, RuleDataType.LIST)
            passed = not cls._check_in_list(user_val, target_list)
            return passed, f"Value '{user_raw}' not in restricted list {target_list} (Result: {passed})"

        # ── CONTAINS ──
        if operator == RuleOperator.CONTAINS:
            s_user = str(user_raw).lower()
            s_target = str(target_raw).lower()
            passed = s_target in s_user
            return passed, f"'{target_raw}' contained in '{user_raw}' (Result: {passed})"

        # ── BOOLEAN CHECKS ──
        if operator == RuleOperator.BOOLEAN_TRUE:
            passed = (user_val is True)
            return passed, f"Expected True, got {user_val}"

        if operator == RuleOperator.BOOLEAN_FALSE:
            passed = (user_val is False)
            return passed, f"Expected False, got {user_val}"

        return False, f"Unsupported operator: {operator}"

    @classmethod
    def _check_equality(cls, user_val: Any, target_val: Any, target_raw: str, dtype: str) -> bool:
        if dtype == RuleDataType.STRING or isinstance(user_val, str):
            u_str = str(user_val).strip().lower()
            t_str = str(target_raw).strip().lower()
            if u_str == t_str:
                return True
            # State code / alias check
            for code, aliases in STATE_ALIASES.items():
                if (u_str == code.lower() or u_str in aliases) and (t_str == code.lower() or t_str in aliases):
                    return True
            return False
        return user_val == target_val

    @classmethod
    def _check_in_list(cls, user_val: Any, target_list: List[str]) -> bool:
        normalized_targets = [str(t).strip().lower() for t in target_list]
        user_items = user_val if isinstance(user_val, list) else [user_val]

        for item in user_items:
            u_str = str(item).strip().lower()
            if u_str in normalized_targets:
                return True

            # Check state aliases if applicable
            for target in normalized_targets:
                for code, aliases in STATE_ALIASES.items():
                    if (u_str == code.lower() or u_str in aliases) and (target == code.lower() or target in aliases):
                        return True

        return False


# ─────────────────────────────────────────────────────────────
# 4. Core Deterministic Eligibility Engine
# ─────────────────────────────────────────────────────────────

class EligibilityEngine:
    """
    Deterministic rule evaluation engine for Government Schemes.

    Guarantees:
    - Never uses an LLM to hallucinate or guess eligibility decisions.
    - Evaluates strictly against structured SchemeEligibilityRule records.
    - Supports multiple AND conditions within a rule_group.
    - Supports multiple OR conditions across rule_groups.
    - Never claims certainty ('Eligible' / 'Not Eligible') if mandatory information is missing.
    - Returns full transparent breakdown: rules checked, passed, failed, missing info, and evidence citations.
    """
    def __init__(self):
        self.context_resolver = ContextResolver()

    def evaluate_scheme(
        self,
        user_context: Union[Dict[str, Any], Any],
        scheme: GovernmentScheme,
    ) -> EligibilityEvaluationResult:
        """
        Evaluates a single GovernmentScheme against user profile context.
        """
        # Normalize context from UserProfile model or dict
        context_dict = self._normalize_user_context(user_context)

        # Retrieve all rules for this scheme
        rules = list(scheme.eligibility_rules.all().order_by("rule_group", "order"))

        # Gather official sources for citation grounding
        sources = self._extract_scheme_sources(scheme)

        # If scheme has no structured eligibility rules defined:
        if not rules:
            return EligibilityEvaluationResult(
                scheme_id=str(scheme.id),
                scheme_name=scheme.name,
                short_title=scheme.short_title,
                verdict=EligibilityVerdict.INSUFFICIENT_INFORMATION,
                is_eligible=None,
                confidence_score=0.30,
                rules_checked=[],
                passed_rules=[],
                failed_rules=[],
                missing_information=["No codified eligibility rules available in database for this scheme."],
                evidence_sources=sources,
                summary_explanation=f"The eligibility criteria for '{scheme.name}' have not yet been codified into structured rules. Please refer to official scheme guidelines.",
            )

        # Evaluate rules and group by rule_group
        rule_checks: List[RuleCheckDetail] = []
        groups: Dict[int, List[RuleCheckDetail]] = {}

        for rule in rules:
            check_detail = self._evaluate_single_rule(rule, context_dict)
            rule_checks.append(check_detail)
            groups.setdefault(rule.rule_group, []).append(check_detail)

        # Evaluate group outcomes (AND within group, OR across groups)
        verdict, is_eligible, confidence, group_summary, missing_info = self._aggregate_verdict(groups, rule_checks)

        passed_rules = [r for r in rule_checks if r.status == RuleEvaluationStatus.PASSED]
        failed_rules = [r for r in rule_checks if r.status == RuleEvaluationStatus.FAILED]

        summary_explanation = self._generate_summary_explanation(
            scheme_name=scheme.name,
            verdict=verdict,
            passed_count=len(passed_rules),
            failed_count=len(failed_rules),
            missing_info=missing_info,
            group_summary=group_summary,
        )

        return EligibilityEvaluationResult(
            scheme_id=str(scheme.id),
            scheme_name=scheme.name,
            short_title=scheme.short_title,
            verdict=verdict,
            is_eligible=is_eligible,
            confidence_score=confidence,
            rules_checked=rule_checks,
            passed_rules=passed_rules,
            failed_rules=failed_rules,
            missing_information=missing_info,
            evidence_sources=sources,
            summary_explanation=summary_explanation,
            rule_groups_evaluated=group_summary,
        )

    def evaluate_multiple_schemes(
        self,
        user_context: Union[Dict[str, Any], Any],
        schemes: List[GovernmentScheme],
    ) -> List[EligibilityEvaluationResult]:
        """
        Evaluates a list of schemes and returns results ranked by actual matching criteria and relevance.
        Ranking Tier: Likely Eligible (0) -> Possibly Eligible (1) -> Insufficient Information (2) -> Not Eligible (3).
        Within each tier, ranked by:
        - Higher number of matched criteria
        - Lower number of failed criteria
        - Fewer missing information gaps
        - State-specific relevance
        """
        results = [self.evaluate_scheme(user_context, scheme) for scheme in schemes]
        user_dict = self._normalize_user_context(user_context)
        user_state = str(user_dict.get("state", "")).upper()

        verdict_priority = {
            EligibilityVerdict.LIKELY_ELIGIBLE: 0,
            EligibilityVerdict.ELIGIBLE: 0,
            EligibilityVerdict.POSSIBLY_ELIGIBLE: 1,
            EligibilityVerdict.INSUFFICIENT_INFORMATION: 2,
            EligibilityVerdict.NOT_ELIGIBLE: 3,
        }

        def compute_ranking_tuple(r: EligibilityEvaluationResult):
            tier = verdict_priority.get(r.verdict, 3)
            passed_cnt = len(r.passed_rules)
            failed_cnt = len(r.failed_rules)
            missing_cnt = len(r.missing_information)
            # Check if scheme matches user's state code/name
            state_match = 1 if user_state and (user_state in (r.short_title or "").upper() or user_state in r.scheme_name.upper()) else 0

            return (
                tier,
                -passed_cnt,
                failed_cnt,
                missing_cnt,
                -state_match,
                r.scheme_name,
            )

        results.sort(key=compute_ranking_tuple)
        return results

    # ── Internal Evaluation Methods ───────────────────────────

    def _evaluate_single_rule(
        self,
        rule: SchemeEligibilityRule,
        context: Dict[str, Any],
    ) -> RuleCheckDetail:
        """Evaluates one SchemeEligibilityRule against the user context."""
        user_raw = self.context_resolver.get_value(rule.criterion_key, context)

        # Check if user value is missing
        if user_raw is None or user_raw == "":
            status = RuleEvaluationStatus.MISSING_INFO
            reason = f"Profile attribute '{rule.criterion_key}' not provided"
            return RuleCheckDetail(
                rule_id=str(rule.id),
                rule_group=rule.rule_group,
                criterion_key=rule.criterion_key,
                rule_description=rule.rule_description or f"{rule.criterion_key} {rule.operator} {rule.value}",
                operator=rule.operator,
                expected_value=rule.value or f"{rule.min_value} - {rule.max_value}",
                user_value=None,
                status=status,
                is_mandatory=rule.is_mandatory,
                is_disqualification=rule.disqualification_condition,
                reason=reason,
            )

        # Run comparison
        matched, compare_reason = RuleComparator.compare(
            user_raw=user_raw,
            operator=rule.operator,
            target_raw=rule.value,
            min_raw=rule.min_value,
            max_raw=rule.max_value,
            data_type=rule.data_type,
        )

        # Disqualification handling:
        # If this is a disqualification rule (e.g. "Income tax payer = True -> Disqualified"),
        # matching the condition means the user FAILS eligibility.
        if rule.disqualification_condition:
            if matched:
                status = RuleEvaluationStatus.FAILED
                reason = f"Disqualification triggered: {rule.rule_description or compare_reason}"
            else:
                status = RuleEvaluationStatus.PASSED
                reason = "Did not meet disqualification criteria (Passed)"
        else:
            if matched:
                status = RuleEvaluationStatus.PASSED
                reason = compare_reason
            else:
                status = RuleEvaluationStatus.FAILED
                reason = f"Did not meet requirement: {compare_reason}"

        return RuleCheckDetail(
            rule_id=str(rule.id),
            rule_group=rule.rule_group,
            criterion_key=rule.criterion_key,
            rule_description=rule.rule_description or f"{rule.criterion_key} {rule.operator} {rule.value}",
            operator=rule.operator,
            expected_value=rule.value or f"{rule.min_value} - {rule.max_value}",
            user_value=user_raw,
            status=status,
            is_mandatory=rule.is_mandatory,
            is_disqualification=rule.disqualification_condition,
            reason=reason,
        )

    def _aggregate_verdict(
        self,
        groups: Dict[int, List[RuleCheckDetail]],
        all_checks: List[RuleCheckDetail],
    ) -> Tuple[
        EligibilityVerdict,
        Optional[bool],
        float,
        Dict[int, Dict[str, Any]],
        List[str],
    ]:
        """
        Aggregates eligibility rule results.

        Logic:
        - AND within each qualification group.
        - OR across qualification groups.
        - Missing mandatory information means the result
          cannot be declared eligible or not eligible.
        """

        group_summaries: Dict[int, Dict[str, Any]] = {}
        all_missing_keys: Set[str] = set()

        any_group_fully_passed = False
        any_group_potentially_open = False
        all_groups_definitively_failed = True

        for group_id, checks in groups.items():
            mandatory_checks = [
                check for check in checks
                if check.is_mandatory
            ]

            mandatory_failed = [
                check for check in mandatory_checks
                if check.status == RuleEvaluationStatus.FAILED
            ]

            mandatory_missing = [
                check for check in mandatory_checks
                if check.status == RuleEvaluationStatus.MISSING_INFO
            ]

            mandatory_passed = [
                check for check in mandatory_checks
                if check.status == RuleEvaluationStatus.PASSED
            ]

            for check in mandatory_missing:
                all_missing_keys.add(check.criterion_key)

            # A group passes only when every mandatory rule passes.
            group_passed = (
                len(mandatory_passed) == len(mandatory_checks)
                and len(mandatory_failed) == 0
                and len(mandatory_missing) == 0
            )

            # A group definitively fails if at least one mandatory rule fails.
            group_failed = len(mandatory_failed) > 0

            # A group remains open if no mandatory rule failed but
            # at least one mandatory attribute is missing.
            group_missing = (
                not group_failed
                and len(mandatory_missing) > 0
            )

            if group_passed:
                any_group_fully_passed = True
                all_groups_definitively_failed = False
            elif group_missing:
                any_group_potentially_open = True
                all_groups_definitively_failed = False
            elif not group_failed:
                # Handles an empty/ambiguous group safely.
                all_groups_definitively_failed = False

            group_summaries[group_id] = {
                "group_id": group_id,
                "status": (
                    "PASSED"
                    if group_passed
                    else (
                        "FAILED"
                        if group_failed
                        else "INCOMPLETE"
                    )
                ),
                "total_rules": len(checks),
                "passed_count": sum(
                    1
                    for check in checks
                    if check.status == RuleEvaluationStatus.PASSED
                ),
                "failed_count": sum(
                    1
                    for check in checks
                    if check.status == RuleEvaluationStatus.FAILED
                ),
                "missing_count": sum(
                    1
                    for check in checks
                    if check.status == RuleEvaluationStatus.MISSING_INFO
                ),
            }

        missing_list = sorted(all_missing_keys)

        # Decision 1: at least one complete qualification group passed.
        if any_group_fully_passed:
            optional_missing = [
                check
                for check in all_checks
                if (
                    not check.is_mandatory
                    and check.status == RuleEvaluationStatus.MISSING_INFO
                )
            ]

            confidence = 0.98 if not optional_missing else 0.90

            return (
                EligibilityVerdict.ELIGIBLE,
                True,
                confidence,
                group_summaries,
                [],
            )

        # Decision 2: at least one group is still open because
        # mandatory information is missing.
        if any_group_potentially_open:
            return (
                EligibilityVerdict.INSUFFICIENT_INFORMATION,
                None,
                0.40,
                group_summaries,
                missing_list,
            )

                # Decision 3:
        # If ANY mandatory information is missing, NEVER return
        # NOT_ELIGIBLE. We cannot make a definitive eligibility
        # decision until the missing information is provided.
        if missing_list:
            return (
                EligibilityVerdict.INSUFFICIENT_INFORMATION,
                None,
                0.40,
                group_summaries,
                missing_list,
            )

        # Decision 4:
        # Every qualification group definitively failed and there
        # is no missing information.
        if all_groups_definitively_failed:
            return (
                EligibilityVerdict.NOT_ELIGIBLE,
                False,
                0.95,
                group_summaries,
                [],
            )

        # Decision 5: ambiguous / partial result.
        return (
            EligibilityVerdict.POSSIBLY_ELIGIBLE,
            None,
            0.65,
            group_summaries,
            [],
        )
        # Decision 4: ambiguous / partial result.
        return (
            EligibilityVerdict.POSSIBLY_ELIGIBLE,
            None,
            0.65,
            group_summaries,
            missing_list,
        )
    def _generate_summary_explanation(
        self,
        scheme_name: str,
        verdict: EligibilityVerdict,
        passed_count: int,
        failed_count: int,
        missing_info: List[str],
        group_summary: Dict[int, Dict[str, Any]],
    ) -> str:
        """Constructs a deterministic, evidence-grounded textual explanation."""
        num_tracks = len(group_summary)
        track_str = f" across {num_tracks} qualification track{'s' if num_tracks > 1 else ''}"

        if verdict in (EligibilityVerdict.ELIGIBLE, EligibilityVerdict.LIKELY_ELIGIBLE) or str(verdict) in ("Eligible", "Likely Eligible"):
            return f"You are Likely Eligible for '{scheme_name}'. You satisfy all mandatory criteria{track_str} ({passed_count} rules passed)."

        elif verdict == EligibilityVerdict.NOT_ELIGIBLE:
            return f"You are Not Eligible for '{scheme_name}'. You failed {failed_count} mandatory requirement(s){track_str}."

        elif verdict == EligibilityVerdict.INSUFFICIENT_INFORMATION:
            missing_fmt = ", ".join(f"'{k}'" for k in missing_info[:5])
            return f"Insufficient Information to determine eligibility for '{scheme_name}'. Missing required profile attributes: {missing_fmt}."

        else:
            return f"You are Possibly Eligible for '{scheme_name}'. Core requirements appear met ({passed_count} passed), but additional verification is required."

    def _normalize_user_context(self, user_context: Any) -> Dict[str, Any]:
        """Converts UserProfile instances or raw dicts into standard dict."""
        if hasattr(user_context, "to_eligibility_context") and callable(user_context.to_eligibility_context):
            return user_context.to_eligibility_context()
        if isinstance(user_context, dict):
            return user_context
        # Handle model object with getattr
        ctx = {}
        for attr in ["age", "gender", "state", "district", "occupation", "annual_income", "social_category", "is_bpl", "is_student", "has_disability", "land_holding_acres"]:
            if hasattr(user_context, attr):
                ctx[attr] = getattr(user_context, attr)
        return ctx

    def _extract_scheme_sources(self, scheme: GovernmentScheme) -> List[Dict[str, Any]]:
        """Extracts official source citation records for grounding."""
        sources: List[Dict[str, Any]] = []

        try:
            for s in scheme.sources.all():
                sources.append({
                    "title": s.title,
                    "url": s.url,
                    "source_type": s.source_type,
                    "document_reference": s.document_reference_number,
                    "is_verified": s.is_verified,
                })
        except Exception:
            pass

        if not sources:
            if scheme.official_source_url:
                sources.append({
                    "title": f"{scheme.short_title or scheme.name} Official Portal",
                    "url": scheme.official_source_url,
                    "source_type": "PORTAL_WEBPAGE",
                    "is_verified": True,
                })
            if scheme.official_application_url:
                sources.append({
                    "title": f"{scheme.short_title or scheme.name} Application Portal",
                    "url": scheme.official_application_url,
                    "source_type": "PORTAL_WEBPAGE",
                    "is_verified": True,
                })

        return sources