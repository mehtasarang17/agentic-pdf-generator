"""Writer Agent - Generates LLM-based descriptions and content."""

import json
import logging
import re
from typing import Dict, Any, List, Optional

from app.agents.base import BaseAgent
from app.agents.state import AgentState
from app.config import config

logger = logging.getLogger(__name__)


class WriterAgent(BaseAgent):
    """Agent for generating text content using LLM."""

    def __init__(self):
        super().__init__("Writer")
        self._token_encoder = None

    def process(self, state: AgentState) -> AgentState:
        """Generate descriptions for descriptive sections.

        Args:
            state: Current agent state with section_plans

        Returns:
            Updated state with generated_descriptions
        """
        if state.get('error'):
            return state

        section_plans = state.get('section_plans', [])
        generated_descriptions = {}
        generated_bullets = {}
        generated_findings = {}
        section_summaries = {}
        section_parts = {}
        table_value_summaries = {}

        for plan in section_plans:
            section_name = plan['name']
            section_type = plan['type']
            content = plan['content']

            structured = self._generate_structured_content(
                section_name,
                content,
                section_type
            )
            generated_descriptions[section_name] = structured['description']
            generated_bullets[section_name] = structured['bullets']
            generated_findings[section_name] = structured['findings']
            section_summaries[section_name] = structured['summary']
            parts = structured.get('parts')
            if parts:
                section_parts[section_name] = parts
            if section_type == 'analytics' and isinstance(content, dict):
                summaries = self._summarize_table_values(section_name, content)
                if summaries:
                    table_value_summaries[section_name] = summaries

            self.logger.debug(f"Generated content for section: {section_name}")

        state['generated_descriptions'] = generated_descriptions
        state['generated_bullets'] = generated_bullets
        state['generated_findings'] = generated_findings
        state['section_summaries'] = section_summaries
        if section_parts:
            state['section_parts'] = section_parts
        if table_value_summaries:
            state['table_value_summaries'] = table_value_summaries

        self.logger.info(f"Generated descriptions for {len(generated_descriptions)} sections")

        return state

    def _generate_structured_content(
        self,
        section_name: str,
        content: Dict[str, Any],
        section_type: str
    ) -> Dict[str, Any]:
        """Generate structured narrative content for a section."""
        content_str = json.dumps(content, indent=2, ensure_ascii=True)
        system_prompt = self._structured_system_prompt()
        base_spec = self._response_spec(detailed=False)
        prompt = self._structured_prompt(
            section_name,
            content_str,
            section_type,
            base_spec
        )

        if self._estimate_prompt_tokens(prompt, system_prompt) <= config.LLM_INPUT_TOKEN_BUDGET:
            return self._invoke_structured_response(
                prompt,
                system_prompt,
                section_name,
                max_tokens=base_spec["max_tokens"]
            )

        self.logger.info(
            "Section '%s' exceeds token budget (%s); chunking input.",
            section_name,
            config.LLM_INPUT_TOKEN_BUDGET
        )

        chunks = self._chunk_content(
            section_name,
            section_type,
            content,
            config.LLM_CHUNK_TOKEN_BUDGET
        )
        self.logger.info(
            "Section '%s' split into %s chunk(s) for LLM generation.",
            section_name,
            len(chunks)
        )

        if not chunks:
            return {
                "description": f"This section covers {section_name}.",
                "bullets": [],
                "findings": [],
                "summary": f"Summary of {section_name}."
            }

        detail_spec = self._response_spec(detailed=True)
        if len(chunks) > config.LLM_MAX_CHUNK_CALLS:
            self.logger.info(
                "Chunk count %s exceeds limit %s; using digest summaries.",
                len(chunks),
                config.LLM_MAX_CHUNK_CALLS
            )
            digests = [self._build_chunk_digest(chunk) for chunk in chunks]
            digest_batches = self._batch_chunk_digests(
                section_name,
                section_type,
                digests,
                system_prompt,
                detail_spec
            )
            self.logger.info(
                "Digest summaries packed into %s batch(es).",
                len(digest_batches)
            )
            chunk_outputs = []
            for idx, batch in enumerate(digest_batches, start=1):
                digest_prompt = self._digest_prompt(
                    section_name,
                    section_type,
                    batch,
                    detail_spec
                )
                self.logger.debug(
                    "Processing digest batch %s/%s for section '%s'.",
                    idx,
                    len(digest_batches),
                    section_name
                )
                chunk_outputs.append(
                    self._invoke_structured_response(
                        digest_prompt,
                        system_prompt,
                        section_name,
                        max_tokens=detail_spec["max_tokens"]
                    )
                )
        else:
            chunk_outputs = []
            for idx, chunk in enumerate(chunks, start=1):
                chunk_str = json.dumps(chunk, indent=2, ensure_ascii=True)
                chunk_prompt = self._structured_prompt(
                    section_name,
                    chunk_str,
                    section_type,
                    detail_spec
                )
                self.logger.debug(
                    "Processing chunk %s/%s for section '%s'.",
                    idx,
                    len(chunks),
                    section_name
                )
                chunk_outputs.append(
                    self._invoke_structured_response(
                        chunk_prompt,
                        system_prompt,
                        section_name,
                        max_tokens=detail_spec["max_tokens"]
                    )
                )

        merged = self._merge_structured_outputs(
            section_name,
            section_type,
            chunk_outputs,
            system_prompt
        )
        if len(chunk_outputs) > 1:
            merged['parts'] = chunk_outputs
        return merged

    def _structured_system_prompt(self) -> str:
        return (
            "You are a professional technical writer. "
            "Respond only with valid JSON."
        )

    def _table_value_system_prompt(self) -> str:
        return (
            "You are a data summarizer. "
            "Return ONLY valid JSON that maps each key to a concise, "
            "readable summary string. Do not include JSON, braces, brackets, "
            "or key:value lists in the summaries."
        )

    def _response_spec(self, detailed: bool) -> Dict[str, Any]:
        if detailed:
            return {
                "paragraphs": config.LLM_STRUCTURED_DETAIL_PARAGRAPHS,
                "bullets": config.LLM_STRUCTURED_DETAIL_BULLETS,
                "findings": config.LLM_STRUCTURED_DETAIL_FINDINGS,
                "max_tokens": config.LLM_STRUCTURED_MAX_TOKENS_DETAIL
            }
        return {
            "paragraphs": config.LLM_STRUCTURED_BASE_PARAGRAPHS,
            "bullets": config.LLM_STRUCTURED_BASE_BULLETS,
            "findings": config.LLM_STRUCTURED_BASE_FINDINGS,
            "max_tokens": config.LLM_STRUCTURED_MAX_TOKENS
        }

    def _structured_prompt(
        self,
        section_name: str,
        content_str: str,
        section_type: str,
        response_spec: Dict[str, Any]
    ) -> str:
        paragraphs = response_spec["paragraphs"]
        bullets = response_spec["bullets"]
        findings = response_spec["findings"]
        if section_type == 'analytics':
            return f"""Create narrative content for a report section based on the data below.
Return ONLY valid JSON with these keys:
- description: {paragraphs} paragraphs in plain text (no markdown)
- bullets: array of {bullets} concise bullet points (strings, no bullet symbols)
- findings: array of {findings} key findings or risks (strings)
- summary: single sentence

Section Name: {section_name}
Data:
{content_str}

Guidelines:
- Explain trends, outliers, and notable values
- Use precise numbers where helpful
- Do not echo raw JSON paths
- Keep language professional and clear"""

        return f"""Create narrative content for a report section based on the content below.
Return ONLY valid JSON with these keys:
- description: {paragraphs} paragraphs in plain text (no markdown)
- bullets: array of {bullets} concise bullet points (strings, no bullet symbols)
- findings: array of {findings} key findings or implications (strings)
- summary: single sentence

Section Name: {section_name}
Content:
{content_str}

Guidelines:
- Explain the meaning of the data in business language
- Highlight key entities, items, or risks
- Avoid listing every field; focus on what matters
- Do not echo raw JSON paths"""

    def _invoke_structured_response(
        self,
        prompt: str,
        system_prompt: str,
        section_name: str,
        max_tokens: int = config.LLM_STRUCTURED_MAX_TOKENS
    ) -> Dict[str, Any]:
        try:
            response = self.invoke_llm(
                prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=0.4
            )
        except Exception as e:
            self.logger.error(f"Failed to generate structured content: {e}")
            return {
                "description": f"This section covers {section_name}.",
                "bullets": [],
                "findings": [],
                "summary": f"Summary of {section_name}."
            }

        parsed = self._parse_json_response(response)
        if not parsed:
            description = response.strip() or f"This section covers {section_name}."
            return {
                "description": description,
                "bullets": [],
                "findings": [],
                "summary": self._summary_from_text(description, section_name)
            }

        description = str(parsed.get("description", "")).strip()
        if not description:
            description = f"This section covers {section_name}."

        bullets = self._normalize_list(parsed.get("bullets"))
        findings = self._normalize_list(parsed.get("findings"))
        summary = str(parsed.get("summary", "")).strip()
        if not summary:
            summary = self._summary_from_text(description, section_name)

        return {
            "description": description,
            "bullets": bullets,
            "findings": findings,
            "summary": summary
        }

    def _summarize_table_values(
        self,
        section_name: str,
        content: Dict[str, Any]
    ) -> Dict[str, str]:
        if not content:
            return {}

        system_prompt = self._table_value_system_prompt()
        batches = self._batch_table_values(
            section_name,
            content,
            system_prompt
        )
        summaries: Dict[str, str] = {}
        rewrite_count = 0
        call_count = 0
        for batch in batches:
            if call_count >= config.LLM_TABLE_VALUE_MAX_CALLS:
                self.logger.warning(
                    "Table value summarization call limit reached for %s; using fallbacks.",
                    section_name
                )
                for key, value in batch.items():
                    summaries[key] = self._fallback_table_value(value)
                continue
            prompt = self._table_value_prompt(section_name, batch)
            try:
                call_count += 1
                response = self.invoke_llm(
                    prompt,
                    system_prompt=system_prompt,
                    max_tokens=config.LLM_TABLE_VALUE_MAX_TOKENS,
                    temperature=0.3
                )
            except Exception as exc:
                self.logger.error(
                    "Failed to summarize table values for %s: %s",
                    section_name,
                    exc
                )
                for key, value in batch.items():
                    summaries[key] = self._fallback_table_value(value)
                continue

            parsed = self._parse_json_response(response)
            if not isinstance(parsed, dict):
                for key, value in batch.items():
                    summaries[key] = self._fallback_table_value(value)
                continue

            for key, value in batch.items():
                summary = parsed.get(key)
                if isinstance(summary, str) and summary.strip():
                    cleaned = summary.strip()
                    if (
                        self._summary_needs_rewrite(cleaned)
                        and rewrite_count < config.LLM_TABLE_VALUE_REWRITE_MAX
                    ):
                        rewritten = self._rewrite_table_value(
                            section_name,
                            key,
                            value
                        )
                        if rewritten:
                            summaries[key] = rewritten
                            rewrite_count += 1
                        else:
                            summaries[key] = self._fallback_table_value(value)
                    else:
                        summaries[key] = cleaned
                else:
                    summaries[key] = self._fallback_table_value(value)

        return summaries

    def _table_value_prompt(self, section_name: str, data: Dict[str, Any]) -> str:
        content_str = json.dumps(data, indent=2, ensure_ascii=True)
        return f"""Rewrite the values below into concise, readable summaries.
Return ONLY valid JSON mapping the same keys to summary strings.
Each summary should be one sentence or a short phrase with key numbers.
Do not include extra text, code fences, or explanations.

Section: {section_name}
Data:
{content_str}
"""

    def _batch_table_values(
        self,
        section_name: str,
        content: Dict[str, Any],
        system_prompt: str
    ) -> List[Dict[str, Any]]:
        batches: List[Dict[str, Any]] = []
        current: Dict[str, Any] = {}
        for key, value in content.items():
            candidate = {**current, key: value}
            prompt = self._table_value_prompt(section_name, candidate)
            if self._estimate_prompt_tokens(prompt, system_prompt) <= config.LLM_TABLE_VALUE_TOKEN_BUDGET:
                current = candidate
            else:
                if current:
                    batches.append(current)
                current = {key: value}
        if current:
            batches.append(current)
        return batches

    def _fallback_table_value(self, value: Any) -> str:
        if isinstance(value, dict):
            return self._summarize_dict_value(value)
        if isinstance(value, list):
            if not value:
                return "No items"
            sample = value[:3]
            return f"{len(value)} items; sample: {', '.join(self._format_scalar(item) for item in sample)}"
        return str(value)

    def _rewrite_table_value(
        self,
        section_name: str,
        key: str,
        value: Any
    ) -> Optional[str]:
        system_prompt = (
            "You rewrite metric values into clear, readable summaries. "
            "Do NOT output JSON or key:value lists. Use plain sentences."
        )
        payload = json.dumps(value, indent=2, ensure_ascii=True)
        prompt = f"""Rewrite the metric value into a clear summary.
Metric: {key}
Value:
{payload}

Constraints:
- No JSON, braces, brackets, or key:value lists
- Keep key numbers and counts
- One or two sentences max
"""
        if self._estimate_prompt_tokens(prompt, system_prompt) > config.LLM_TABLE_VALUE_TOKEN_BUDGET:
            return None
        try:
            response = self.invoke_llm(
                prompt,
                system_prompt=system_prompt,
                max_tokens=config.LLM_TABLE_VALUE_REWRITE_MAX_TOKENS,
                temperature=0.3
            )
        except Exception as exc:
            self.logger.error(
                "Failed to rewrite table value for %s: %s",
                key,
                exc
            )
            return None
        cleaned = response.strip().strip('"')
        if not cleaned or self._summary_needs_rewrite(cleaned):
            return None
        return cleaned

    def _summary_needs_rewrite(self, summary: str) -> bool:
        if not summary:
            return True
        return any(token in summary for token in ("{", "}", "[", "]"))

    def _summarize_dict_value(self, value: Dict[str, Any]) -> str:
        parts = []
        for idx, (key, val) in enumerate(value.items()):
            if idx >= 6:
                break
            parts.append(f"{self._format_key(key)} {self._format_scalar(val)}")
        return "; ".join(parts)

    def _format_key(self, key: Any) -> str:
        text = str(key).replace("_", " ").strip()
        return text.title() if text else str(key)

    def _format_scalar(self, value: Any) -> str:
        if isinstance(value, dict):
            return "multiple fields"
        if isinstance(value, list):
            return f"{len(value)} items"
        return str(value)

    def _estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        try:
            if self._token_encoder is None:
                import tiktoken

                self._token_encoder = tiktoken.get_encoding("cl100k_base")
            return len(self._token_encoder.encode(text))
        except Exception:
            chars_per_token = max(config.LLM_TOKEN_ESTIMATE_CHARS_PER_TOKEN, 1.0)
            return int(len(text) / chars_per_token) + 1

    def _estimate_prompt_tokens(self, prompt: str, system_prompt: str) -> int:
        return self._estimate_tokens(prompt) + self._estimate_tokens(system_prompt or "")

    def _fits_budget(
        self,
        section_name: str,
        section_type: str,
        content: Dict[str, Any],
        budget: int
    ) -> bool:
        content_str = json.dumps(content, indent=2, ensure_ascii=True)
        prompt = self._structured_prompt(
            section_name,
            content_str,
            section_type,
            self._response_spec(detailed=False)
        )
        tokens = self._estimate_prompt_tokens(prompt, self._structured_system_prompt())
        return tokens <= budget

    def _truncate_text(self, text: str, max_chars: int) -> str:
        if not text or len(text) <= max_chars:
            return text
        return text[:max_chars].rstrip() + "... [truncated]"

    def _split_list_item(
        self,
        section_name: str,
        section_type: str,
        key: str,
        value: List[Any],
        budget: int
    ) -> List[Dict[str, Any]]:
        chunks = []
        current = []
        for item in value:
            candidate = current + [item]
            if self._fits_budget(section_name, section_type, {key: candidate}, budget):
                current = candidate
                continue

            if current:
                chunks.append({key: current})
                current = []

            if self._fits_budget(section_name, section_type, {key: [item]}, budget):
                current = [item]
            else:
                if isinstance(item, str):
                    chunks.extend(
                        {key: [segment]}
                        for segment in self._split_text(item, config.LLM_MAX_FIELD_CHARS)
                    )
                else:
                    truncated_item = self._truncate_text(
                        json.dumps(item, ensure_ascii=True),
                        config.LLM_MAX_FIELD_CHARS
                    )
                    chunks.append({key: [truncated_item]})

        if current:
            chunks.append({key: current})
        return chunks or [{key: []}]

    def _shrink_list_to_fit(
        self,
        section_name: str,
        section_type: str,
        key: str,
        value: List[Any],
        budget: int
    ) -> List[Any]:
        if not value:
            return []
        if self._fits_budget(section_name, section_type, {key: value}, budget):
            return value
        end = len(value)
        while end > 1:
            candidate = value[:end]
            if self._fits_budget(section_name, section_type, {key: candidate}, budget):
                return candidate
            end = max(1, end // 2)
        truncated_item = self._truncate_text(
            json.dumps(value[0], ensure_ascii=True),
            config.LLM_MAX_FIELD_CHARS
        )
        return [truncated_item]

    def _shrink_dict_to_fit(
        self,
        section_name: str,
        section_type: str,
        key: str,
        value: Dict[str, Any],
        budget: int
    ) -> Dict[str, Any]:
        if not value:
            return {}
        if self._fits_budget(section_name, section_type, {key: value}, budget):
            return value
        keys = list(value.keys())
        end = len(keys)
        while end > 1:
            candidate = {k: value[k] for k in keys[:end]}
            if self._fits_budget(section_name, section_type, {key: candidate}, budget):
                return candidate
            end = max(1, end // 2)
        first_key = keys[0]
        truncated_value = self._truncate_text(
            json.dumps(value[first_key], ensure_ascii=True),
            config.LLM_MAX_FIELD_CHARS
        )
        return {first_key: truncated_value}

    def _shrink_payload_to_fit(
        self,
        section_name: str,
        section_type: str,
        payload: Dict[str, Any],
        budget: int
    ) -> Dict[str, Any]:
        if len(payload) != 1:
            truncated = self._truncate_text(
                json.dumps(payload, ensure_ascii=True),
                config.LLM_MAX_FIELD_CHARS
            )
            return {"_truncated": truncated}
        key = next(iter(payload))
        value = payload[key]
        if isinstance(value, str):
            return {key: self._truncate_text(value, config.LLM_MAX_FIELD_CHARS)}
        if isinstance(value, list):
            return {
                key: self._shrink_list_to_fit(
                    section_name,
                    section_type,
                    key,
                    value,
                    budget
                )
            }
        if isinstance(value, dict):
            return {
                key: self._shrink_dict_to_fit(
                    section_name,
                    section_type,
                    key,
                    value,
                    budget
                )
            }
        return payload

    def _expand_item(
        self,
        section_name: str,
        section_type: str,
        key: str,
        value: Any,
        budget: int
    ) -> List[Dict[str, Any]]:
        if self._fits_budget(section_name, section_type, {key: value}, budget):
            return [{key: value}]
        if isinstance(value, list):
            return self._split_list_item(
                section_name,
                section_type,
                key,
                value,
                budget
            )
        if isinstance(value, dict):
            subchunks = self._chunk_mapping_payloads(
                section_name,
                section_type,
                value,
                budget
            )
            if not subchunks:
                return [{key: {}}]
            return [{key: subchunk} for subchunk in subchunks]
        if isinstance(value, str):
            return [
                {key: segment}
                for segment in self._split_text(value, config.LLM_MAX_FIELD_CHARS)
            ]
        return [{key: value}]

    def _pack_payloads(
        self,
        section_name: str,
        section_type: str,
        payloads: List[Dict[str, Any]],
        budget: int
    ) -> List[Dict[str, Any]]:
        chunks = []
        current: Dict[str, Any] = {}
        for payload in payloads:
            if any(key in current for key in payload):
                if current:
                    chunks.append(current)
                    current = {}
            candidate = {**current, **payload}
            if self._fits_budget(section_name, section_type, candidate, budget):
                current = candidate
                continue
            if current:
                chunks.append(current)
            if not self._fits_budget(section_name, section_type, payload, budget):
                payload = self._shrink_payload_to_fit(
                    section_name,
                    section_type,
                    payload,
                    budget
                )
            chunks.append(payload)
            current = {}
        if current:
            chunks.append(current)
        return chunks

    def _chunk_mapping_payloads(
        self,
        section_name: str,
        section_type: str,
        mapping: Dict[str, Any],
        budget: int
    ) -> List[Dict[str, Any]]:
        payloads: List[Dict[str, Any]] = []
        for key, value in mapping.items():
            payloads.extend(
                self._expand_item(
                    section_name,
                    section_type,
                    key,
                    value,
                    budget
                )
            )
        return self._pack_payloads(
            section_name,
            section_type,
            payloads,
            budget
        )

    def _chunk_content(
        self,
        section_name: str,
        section_type: str,
        content: Dict[str, Any],
        budget: int
    ) -> List[Dict[str, Any]]:
        if not isinstance(content, dict):
            content = {"value": content}
        return self._chunk_mapping_payloads(
            section_name,
            section_type,
            content,
            budget
        )

    def _split_text(self, text: str, max_chars: int) -> List[str]:
        if not text:
            return [""]
        chunks = []
        start = 0
        length = len(text)
        while start < length:
            chunks.append(text[start:start + max_chars])
            start += max_chars
        return chunks

    def _digest_structured_output(self, output: Dict[str, Any]) -> Dict[str, Any]:
        summary = self._truncate_text(
            str(output.get("summary", "")).strip(),
            500
        )
        bullets = [
            self._truncate_text(str(item).strip(), 300)
            for item in output.get("bullets", []) or []
        ][:7]
        findings = [
            self._truncate_text(str(item).strip(), 300)
            for item in output.get("findings", []) or []
        ][:5]
        return {
            "summary": summary,
            "bullets": bullets,
            "findings": findings
        }

    def _merge_prompt(
        self,
        section_name: str,
        section_type: str,
        digests: List[Dict[str, Any]]
    ) -> str:
        content_str = json.dumps(digests, indent=2, ensure_ascii=True)
        base_spec = self._response_spec(detailed=False)
        paragraphs = base_spec["paragraphs"]
        bullets = base_spec["bullets"]
        findings = base_spec["findings"]
        return f"""Combine the following chunk summaries into a single cohesive section.
Return ONLY valid JSON with these keys:
- description: {paragraphs} paragraphs in plain text (no markdown)
- bullets: array of {bullets} concise bullet points (strings, no bullet symbols)
- findings: array of {findings} key findings or risks (strings)
- summary: single sentence

Section Name: {section_name}
Chunk Summaries:
{content_str}

Guidelines:
- De-duplicate overlapping points
- Keep language professional and clear
- Do not invent data beyond the provided summaries"""

    def _digest_prompt(
        self,
        section_name: str,
        section_type: str,
        digests: List[Dict[str, Any]],
        response_spec: Dict[str, Any]
    ) -> str:
        content_str = json.dumps(digests, indent=2, ensure_ascii=True)
        paragraphs = response_spec["paragraphs"]
        bullets = response_spec["bullets"]
        findings = response_spec["findings"]
        return f"""Create narrative content for a report section based on the chunk digests below.
Return ONLY valid JSON with these keys:
- description: {paragraphs} paragraphs in plain text (no markdown)
- bullets: array of {bullets} concise bullet points (strings, no bullet symbols)
- findings: array of {findings} key findings or risks (strings)
- summary: single sentence

Section Name: {section_name}
Chunk Digests:
{content_str}

Guidelines:
- Use the digest counts and samples to describe the data
- Highlight patterns or notable values where possible
- Do not invent data beyond the provided digests"""

    def _batch_chunk_digests(
        self,
        section_name: str,
        section_type: str,
        digests: List[Dict[str, Any]],
        system_prompt: str,
        response_spec: Dict[str, Any]
    ) -> List[List[Dict[str, Any]]]:
        batches: List[List[Dict[str, Any]]] = []
        current: List[Dict[str, Any]] = []
        for digest in digests:
            candidate = current + [digest]
            prompt = self._digest_prompt(
                section_name,
                section_type,
                candidate,
                response_spec
            )
            if self._estimate_prompt_tokens(prompt, system_prompt) <= config.LLM_DIGEST_TOKEN_BUDGET:
                current = candidate
            else:
                if current:
                    batches.append(current)
                current = [digest]
        if current:
            batches.append(current)
        return batches

    def _build_chunk_digest(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        digest = {}
        for key, value in chunk.items():
            digest[key] = self._summarize_value(value, max_depth=2)
        return digest

    def _summarize_value(self, value: Any, max_depth: int) -> Any:
        if max_depth <= 0:
            return self._truncate_text(
                json.dumps(value, ensure_ascii=True),
                300
            )
        if isinstance(value, dict):
            keys = list(value.keys())
            sample_keys = keys[:5]
            sample = {
                key: self._summarize_value(value[key], max_depth - 1)
                for key in sample_keys
            }
            return {
                "type": "dict",
                "key_count": len(keys),
                "sample_keys": sample_keys,
                "sample": sample
            }
        if isinstance(value, list):
            sample_items = value[:3]
            return {
                "type": "list",
                "length": len(value),
                "sample": [
                    self._summarize_value(item, max_depth - 1)
                    for item in sample_items
                ]
            }
        if isinstance(value, str):
            return self._truncate_text(value, 300)
        return value

    def _ensure_merge_fit(
        self,
        section_name: str,
        section_type: str,
        digest: Dict[str, Any],
        system_prompt: str
    ) -> Dict[str, Any]:
        prompt = self._merge_prompt(section_name, section_type, [digest])
        if self._estimate_prompt_tokens(prompt, system_prompt) <= config.LLM_MERGE_TOKEN_BUDGET:
            return digest
        summary = self._truncate_text(str(digest.get("summary", "")).strip(), 400)
        return {"summary": summary}

    def _batch_digests(
        self,
        section_name: str,
        section_type: str,
        digests: List[Dict[str, Any]],
        system_prompt: str
    ) -> List[List[Dict[str, Any]]]:
        batches: List[List[Dict[str, Any]]] = []
        current: List[Dict[str, Any]] = []
        for digest in digests:
            digest = self._ensure_merge_fit(
                section_name,
                section_type,
                digest,
                system_prompt
            )
            candidate = current + [digest]
            prompt = self._merge_prompt(section_name, section_type, candidate)
            if self._estimate_prompt_tokens(prompt, system_prompt) <= config.LLM_MERGE_TOKEN_BUDGET:
                current = candidate
            else:
                if current:
                    batches.append(current)
                current = [digest]
        if current:
            batches.append(current)
        return batches

    def _merge_structured_outputs(
        self,
        section_name: str,
        section_type: str,
        outputs: List[Dict[str, Any]],
        system_prompt: str
    ) -> Dict[str, Any]:
        if not outputs:
            return {
                "description": f"This section covers {section_name}.",
                "bullets": [],
                "findings": [],
                "summary": f"Summary of {section_name}."
            }
        if len(outputs) == 1:
            return outputs[0]

        digests = [self._digest_structured_output(output) for output in outputs]
        merged_outputs = outputs
        while len(merged_outputs) > 1:
            batches = self._batch_digests(
                section_name,
                section_type,
                digests,
                system_prompt
            )
            merged_outputs = []
            for batch in batches:
                prompt = self._merge_prompt(section_name, section_type, batch)
                merged_outputs.append(
                    self._invoke_structured_response(
                        prompt,
                        system_prompt,
                        section_name
                    )
                )
            digests = [
                self._digest_structured_output(output)
                for output in merged_outputs
            ]

        return merged_outputs[0]

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse a JSON object from an LLM response."""
        if not response:
            return {}
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`").strip()
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            cleaned = cleaned[start:end + 1]

        try:
            parsed = json.loads(cleaned)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            repaired = self._repair_json_string(cleaned)
            try:
                parsed = json.loads(repaired)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}

    def _repair_json_string(self, text: str) -> str:
        """Attempt to repair JSON with unescaped newlines inside strings."""
        output = []
        in_string = False
        escape = False

        for ch in text:
            if in_string:
                if escape:
                    output.append(ch)
                    escape = False
                    continue
                if ch == "\\":
                    output.append(ch)
                    escape = True
                    continue
                if ch == '"':
                    in_string = False
                    output.append(ch)
                    continue
                if ch == "\n":
                    output.append("\\n")
                    continue
                if ch == "\r":
                    continue
                if ch == "\t":
                    output.append("\\t")
                    continue
            else:
                if ch == '"':
                    in_string = True
            output.append(ch)

        return "".join(output)

    def _normalize_list(self, value: Any) -> List[str]:
        """Normalize LLM list outputs into a list of strings."""
        if not value:
            return []
        if isinstance(value, list):
            cleaned = [str(item).strip() for item in value if str(item).strip()]
            return cleaned
        if isinstance(value, str):
            lines = []
            for line in value.splitlines():
                cleaned = re.sub(r"^[^A-Za-z0-9]+", "", line).strip()
                if cleaned:
                    lines.append(cleaned)
            return lines
        return [str(value).strip()]

    def _summary_from_text(self, text: str, fallback_name: str) -> str:
        """Create a one-sentence summary from a description."""
        if not text:
            return f"Summary of {fallback_name}."
        for separator in [". ", ".\n"]:
            if separator in text:
                return text.split(separator)[0].strip() + "."
        return (text.strip().splitlines()[0] or f"Summary of {fallback_name}.").strip()

    def _generate_description(
        self,
        section_name: str,
        content: Dict[str, Any],
        section_type: str
    ) -> str:
        """Generate a description for a section.

        Args:
            section_name: Name of the section
            content: Section content
            section_type: Type of section ('analytics' or 'descriptive')

        Returns:
            Generated description text
        """
        content_str = json.dumps(content, indent=2)

        if section_type == 'analytics':
            prompt = f"""Write a professional analysis description for the following data section of a business report.

Section Name: {section_name}
Data:
{content_str}

Requirements:
- Write 2-3 paragraphs analyzing the data
- Highlight key trends, patterns, or notable values
- Use professional business language
- Include specific numbers and percentages where relevant
- Do not use markdown formatting

Write the analysis now:"""
        else:
            prompt = f"""Write a professional description for the following section of a business report.

Section Name: {section_name}
Content:
{content_str}

Requirements:
- Write 2-3 paragraphs elaborating on this content
- Maintain professional business language
- Expand on key points with additional context
- Make the content informative and engaging
- Do not use markdown formatting

Write the description now:"""

        try:
            description = self.invoke_llm(
                prompt,
                system_prompt="You are a professional technical writer creating content for business reports. Write clear, informative, and professional content.",
                max_tokens=1500,
                temperature=0.7
            )

            return description.strip()
        except Exception as e:
            self.logger.error(f"Failed to generate description: {e}")
            return f"This section covers {section_name}."

    def _generate_summary(self, section_name: str, content: Dict[str, Any]) -> str:
        """Generate a brief summary for a section.

        Args:
            section_name: Name of the section
            content: Section content

        Returns:
            Brief summary text
        """
        content_str = json.dumps(content, indent=2)

        prompt = f"""Write a one-sentence summary for the following section:

Section Name: {section_name}
Content:
{content_str}

Return ONLY the summary sentence, nothing else."""

        try:
            summary = self.invoke_llm(
                prompt,
                system_prompt="You are a concise technical writer.",
                max_tokens=100,
                temperature=0.5
            )
            return summary.strip()
        except Exception as e:
            self.logger.error(f"Failed to generate summary: {e}")
            return f"Summary of {section_name}."

    def _generate_introduction(self, title: str, sections: List[str]) -> str:
        """Generate an introduction for the document.

        Args:
            title: Document title
            sections: List of section names

        Returns:
            Introduction text
        """
        sections_str = ", ".join(sections)

        prompt = f"""Write a professional introduction paragraph for a business report with the following details:

Title: {title}
Sections covered: {sections_str}

Requirements:
- One paragraph, 3-4 sentences
- Professional tone
- Briefly introduce what the report covers
- Do not use markdown formatting

Write the introduction:"""

        try:
            intro = self.invoke_llm(
                prompt,
                system_prompt="You are a professional technical writer.",
                max_tokens=200,
                temperature=0.7
            )
            return intro.strip()
        except Exception as e:
            self.logger.error(f"Failed to generate introduction: {e}")
            return f"This report provides a comprehensive analysis of {sections_str}."


# Singleton instance
writer_agent = WriterAgent()
