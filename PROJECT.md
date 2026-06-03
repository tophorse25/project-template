# Project: Demand Intelligence Engine (Reddit)

> A deterministic, accumulating product-demand intelligence engine for e-commerce sellers.

## Description

This project gathers Reddit discussion around a product and turns it into a confidence-aware demand
report. Collection (Playwright browser + PRAW API) feeds a multi-agent pipeline backed by a SQLite
knowledge base that accumulates evidence across runs, dedupes it into canonical demand themes, scores
them honestly (thin data is never over-claimed), runs deterministic deep research, and renders
Markdown + static HTML. It closes the gap with — and surpasses — the mentor's `super_crawler`
reference on data, analysis, memory, and auditability (see `docs/ARCHITECTURE.md`).

## Stage

Phase 2: Demand Intelligence Engine (multi-agent, accumulating memory)

## Progress Snapshot

| Module | Status | Progress | Notes |
|--------|--------|----------|-------|
| Project Setup | Done | 100% | Repo, virtualenv, tracking files, and git workflow are in place |
| Browser Search Collector | In Progress | 70% | Playwright multi-query JSON configs; rich-field enrichment pending (Phase D) |
| Reddit API Collector | In Progress | 50% | PRAW collector saves posts and comments from target subreddits |
| Persistence / Memory (KB) | Done | 100% | SQLite knowledge base; evidence accumulates across runs via stable ids + score history |
| Analysis Core | Done | 95% | Word-boundary + negation-aware signals, geo distribution, confidence-aware scoring |
| Agent Pipeline | Done | 90% | Discovery, pool manager, deep research, change detection, report agent + runner |
| Reporting | Done | 90% | KB-based Markdown + self-contained static HTML with provenance |
| Collection Enrichment | Not Started | 0% | Rich search-card fields + deep-fetch of post body/comments (Phase D) |

**Status values**: Not Started -> In Progress -> Done | **Progress**: percentage or rough estimate

## Last Sync

2026-06-02
