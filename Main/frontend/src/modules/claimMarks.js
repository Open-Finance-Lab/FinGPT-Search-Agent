// Decorate Validate claim spans pre-wrapped by the backend.
//
// The backend post-processor wraps each reported claim value in
// <span data-claim-id="...">value</span>. This helper joins the
// Validate status back to the span by id and applies one of three
// status classes. Visual-only: per the spec (D3), no click handler,
// no custom tooltip, no focus ring.

const STATUS_CLASS = {
    VERIFIED: 'claim-mark-verified',
    FAILED: 'claim-mark-failed',
    NOT_APPLICABLE: 'claim-mark-na',
};

export function decorateClaimMarks(bubble, claims) {
    if (!bubble || !Array.isArray(claims)) return;
    for (const c of claims) {
        if (!c || !c.claim_id) continue;
        const cls = STATUS_CLASS[c.status];
        if (!cls) continue;  // SKIPPED or unknown status: no decoration
        const span = bubble.querySelector(
            '[data-claim-id="' + CSS.escape(c.claim_id) + '"]'
        );
        if (!span) {
            console.warn('[Validate] no span for claim_id', c.claim_id);
            continue;
        }
        span.classList.add(cls);
    }
}
