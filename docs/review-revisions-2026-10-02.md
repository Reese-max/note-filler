# Review revisions and durable manual edits

Browser review forms now submit document content, document instance, claim,
evidence, and latest decision revisions. Missing or changed revisions return
HTTP 409 before any decision or file is written. Reload the result page to
review the current content. An identical new upload is a new document instance.

Web result, review and export URLs include the opaque result capability. Bare,
unknown and expired capabilities return 404. Private review ledgers are scoped
to the browser's random HTTP-only owner cookie and the original document;
another browser uploading identical content starts with its own review state.
The same browser can replay its durable edits after regeneration. Results
retain their generated base and replay the latest ledger on display/export,
so an already edited tab also receives a later revision from another tab.
Stale tab forms cannot overwrite a newer saved decision. Result pages prevent
caching and referrer disclosure. CLI ledger replay remains document-bound.

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

Python 3.12 computes timestamps from UTC instead of deprecated utcnow while
preserving the latest main branch's serialized format. Deprecation warnings
remain errors.
