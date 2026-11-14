# Lessons: tools_dftracer_utils

- [L-1ba2ff08] dftracer_stats --report categories/summary fails per file with 'No chunk statistics in index for <file>' on compacted traces; dftracer_index --rebuild-summaries reports 'Events processed: 0' -> The index build only creates bloom-filter existence indexes and never scans event content (upstream dftracer-utils bug; prebuilt binary, no local source). -> Use event_count for totals; count categories by gzip+json parsing every chunk; fix upstream. (2026-08-02)
- [L-4678e2b3] Need fast per-category / per-name counts on a large run -> On raw per-rank traces the stats path works. -> dftracer_stats -d <raw_dir> --index-dir <idx> --report categories|top-names (358 M events in ~70 s, 32 threads). (2026-09-30)
