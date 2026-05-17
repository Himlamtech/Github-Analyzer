# Mermaid sources for report charts

Render these files to PNG and place the outputs in `docs/images/` with matching
names. Example with Mermaid CLI:

```bash
mmdc -i docs/mermaid/event_filter_flow.mmd -o docs/images/event_filter_flow.png -b white
mmdc -i docs/mermaid/dual_sink_pattern.mmd -o docs/images/dual_sink_pattern.png -b white
mmdc -i docs/mermaid/hybrid_search_pipeline.mmd -o docs/images/hybrid_search_pipeline.png -b white
mmdc -i docs/mermaid/end_to_end_flow.mmd -o docs/images/end_to_end_flow.png -b white
```

The report currently references these PNG files from `docs/images/`.
