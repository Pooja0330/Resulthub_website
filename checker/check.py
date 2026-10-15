    candidates = []
    for title, link, published in links:
        title = " ".join(title.split())
        link = link.split("#")[0].strip()
        if len(title) < 8 or not host_allowed(link, hosts):
            continue
        category = classify(title)
        if not category:
            continue
        # Avoid old items if an explicit date is present. Undated links are kept for review,
        # but are never treated as verified or published automatically.
        date_found = extract_title_date(title)
        if date_found:
            now = datetime.now(timezone.utc)
            if date_found < now - timedelta(days=MAX_AGE_DAYS) or date_found > now + timedelta(days=400):
                continue
        candidates.append({"title": title[:260], "url": link, "category": category, "source_name": name, "source_url": url, "published": str(published)[:100]})
    return candidates

def main():
    registry = load_json("checker/sources.json", {"sources": []})
    state = load_json("checker/state.json", {"seen": {}, "source_health": {}, "last_run": None})
    if not isinstance(registry, dict) or not isinstance(registry.get("sources"), list):
        sys.exit("ERROR: sources.json must contain a sources list")
    seen = state.setdefault("seen", {})
    health = state.setdefault("source_health", {})
    sources = [s for s in registry["sources"] if s.get("enabled", True)]
    now = datetime.now(timezone.utc).isoformat()
    candidates, failures, successful = [], 0, 0
    print(f"GoResultHub checker: {len(sources)} enabled sources; {WORKERS} workers")
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        jobs = {executor.submit(fetch_source, source): source for source in sources}
        for future in as_completed(jobs):
            source = jobs[future]
            source_id = source.get("id", source.get("name", "unknown"))
            try:
                items = future.result()
                successful += 1
                fresh = []
                for item in items:
                    key = hashlib.sha256(item["url"].encode("utf-8")).hexdigest()[:24]
                    if key in seen:
                        continue
                    seen[key] = {"first_seen": now, "source_id": source_id, "url": item["url"]}
                    item["id"] = key
                    fresh.append(item)
                candidates.extend(fresh)
                health[source_id] = {"status": "ok", "checked_at": now, "new_candidates": len(fresh)}
                print(f"OK {source.get('name', source_id)}: {len(fresh)} new candidates")
            except Exception as exc:
                failures += 1
                health[source_id] = {"status": "failed", "checked_at": now, "error": f"{type(exc).__name__}: {str(exc)[:250]}"}
                print(f"FAIL {source.get('name', source_id)}: {type(exc).__name__}: {str(exc)[:250]}")
    state.update({"last_run": now, "last_run_failures": failures, "last_run_successful_sources": successful, "last_run_new_candidates": len(candidates), "source_registry_count": len(sources)})
    save_json("checker/state.json", state)

    # Private review digest only. These are NOT labelled as verified.
    if candidates and ADMIN:
        lines = ["GoResultHub | PRIVATE REVIEW DIGEST", f"Checked: {now}", f"New candidate links: {len(candidates)}", "", "Review each announcement on the official page before publishing.", "No public posts were made by discovery.", ""]
        for item in candidates[:MAX_REVIEW_ITEMS]:
            lines.extend([f"• {item['source_name']} | {item['category']}", item["title"], item["url"], ""])
        if len(candidates) > MAX_REVIEW_ITEMS:
            lines.append(f"Additional candidates not shown: {len(candidates)-MAX_REVIEW_ITEMS}")
        print("Private digest delivered:", telegram_send(ADMIN, "\n".join(lines)))
    elif candidates:
        print("Candidates found but TG_ADMIN is missing; no digest sent")
    else:
        print("No new candidates passed the filters")

    # Explicitly approved items are read from checker/approved.json.
    # Approval means a human checked the live official notice; the code cannot prove that itself.
    approval_data = load_json("checker/approved.json", {"pending": []})
    pending = approval_data.get("pending", []) if isinstance(approval_data, dict) else []
    if not isinstance(pending, list):
        sys.exit("ERROR: checker/approved.json must contain a pending list")
    remaining, public_posts = [], 0
    for item in pending:
        if not isinstance(item, dict):
            continue
        if item.get("approved") is not True:
            remaining.append(item)
            continue
        title = str(item.get("title", "")).strip()
        url = str(item.get("url", "")).strip()
        source_name = str(item.get("source_name", "")).strip()
        category = str(item.get("category", "")).strip()
        source = next((s for s in sources if s.get("name") == source_name), None)
        hosts = source.get("allowed_hosts", []) if source else []
        if not title or not category or not source or not host_allowed(url, hosts):
            print("Rejected approved item: missing title/category or source host mismatch")
            remaining.append(item)
            continue
        if not CHANNEL:
            print("TG_CHANNEL missing; approved item kept pending")
            remaining.append(item)
            continue
        message = (f"📢 GoResultHub | Exam Update\n\nAuthority: {source_name}\nUpdate type: {category.replace('_', ' ').title()}\n\n{title}\n\nOfficial source:\n{url}\n\nPlease verify candidate-specific details on the official portal.")
        if telegram_send(CHANNEL, message):
            public_posts += 1
            print("Published manually approved item:", title)
        else:
            remaining.append(item)
    save_json("checker/approved.json", {"pending": remaining})
    print(f"SUMMARY: successful_sources={successful}; failed_sources={failures}; new_candidates={len(candidates)}; public_posts={public_posts}")
    if sources and successful == 0:
        sys.exit("ERROR: no source could be checked successfully")

if __name__ == "__main__":
    main()
