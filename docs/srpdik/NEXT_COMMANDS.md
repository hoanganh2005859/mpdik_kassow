# SR-PPO-DLS — Next Commands

Run from repo root `D:\data\hoang_anh\mpdik_kassow` unless noted.

## To resume this session's context in a fresh Claude session

Read, in order: `docs/srpdik/HANDOFF.md`, `docs/srpdik/PHASE_STATUS.json`,
`docs/srpdik/DECISIONS.md`, `docs/srpdik/SRPDIK_SOURCE_MAP.md`,
`docs/srpdik/SRPDIK_REFERENCE_REQUIREMENTS.md` (only the section relevant to the next atomic
task), then `docs/srpdik/SRPDIK_IMPLEMENTATION_PLAN.md` for the phase table.

## Verify Phase 0 artifacts exist

```
ls docs/srpdik/references/
ls docs/srpdik/
```

## Re-run baseline tests (targeted first, then full)

```
pytest tests/test_dls_solver.py -q
pytest -q
```

## PROMPT 1 (exact next prompt to give Claude)

```
Đọc docs/srpdik/HANDOFF.md, docs/srpdik/PHASE_STATUS.json, docs/srpdik/DECISIONS.md,
docs/srpdik/SRPDIK_SOURCE_MAP.md trước khi làm bất cứ việc gì khác.

Thực hiện Phase A theo docs/srpdik/SRPDIK_IMPLEMENTATION_PLAN.md:
1. Tìm và đọc final_dls_summary.json (hoặc file tương đương) trong frozen public export root
   được nhắc tới trong docs/CHATGPT_DLS_CURRENT_STATE_BRIEF.md.
2. Đối chiếu chính xác con số standard Point-IK success frozen (95.08% trong PDF vs 0.951 trong
   brief) — ghi số chính xác và nguồn vào docs/srpdik/DECISIONS.md, đánh dấu quyết định #9 là
   resolved.
3. Tổng hợp bảng stagnation/iterations/success/margin/sigma_min theo difficulty/init class từ dữ
   liệu frozen đã có (không tạo thêm evaluation run mới, không đụng frozen_test generation).
4. Chỉ đọc, không sửa bất cứ file dataset v1/v2 nào.
5. Cập nhật docs/srpdik/HANDOFF.md, docs/srpdik/PHASE_STATUS.json,
   docs/srpdik/SRPDIK_IMPLEMENTATION_LOG.md sau khi xong Phase A.
6. Nếu token sắp hết giữa chừng, dừng theo đúng Token-Safe Execution Protocol trong CLAUDE.md
   context/phần E của prompt gốc: hoàn tất hoặc rollback atomic task đang làm, cập nhật handoff,
   dừng — không bắt đầu atomic task mới.
```
