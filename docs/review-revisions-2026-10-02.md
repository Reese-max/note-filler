# Review revisions and durable manual edits

Browser review forms now submit document content, document instance, claim,
evidence, and latest decision revisions. Missing or changed revisions return
HTTP 409 before any decision or file is written. Reload the result page to
review the current content. An identical new upload is a new document instance.

The review ledger writes schema v2 and still reads v1 unedited decisions.
Manual edits retain the generated claim hash, reviewed evidence hash, revised
text, and revised claim hash. Multiple edits keep the first generated base;
later accept/reject decisions preserve the edit in the decision history.

Replay applies to a copy of the generated document only when its original
fingerprint, generated claim and citation spans, evidence bundle, and revised
text hash all match. Changed generated text or sources remain stale. Markdown,
JSON, DOCX, CLI export and the web result share this replay rule. Original
paragraphs are unchanged. A failed ledger save publishes neither an edit nor
a decision.

Python 3.12 timestamps use timezone-aware UTC instead of deprecated utcnow,
with deprecation warnings still treated as errors.
