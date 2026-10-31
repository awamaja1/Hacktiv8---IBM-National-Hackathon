# Archived: TradeFlow Sentinel Mock LLM Mode

This directory contains the legacy Mock LLM implementation and references previously used during early development stages (MVP Phase 1).

## Architecture

- **Zero-Token Offline Synthesis**: Constructed executive narratives via deterministic template interpolation from the 6-layer audit findings JSON.
- **MD5 Hash Caching**: Repeated identical document sets returned in `< 1 ms` without external network roundtrips.
- **Status in Active Production**: Replaced in Phase 2 with **IBM watsonx.ai Enterprise Runtime (`ibm/granite-3-3-8b-instruct`)**.
