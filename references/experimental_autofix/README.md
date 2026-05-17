# Experimental Auto-Fix Reference

This folder stores exploratory auto-fix code for later review.

Do not import this into the production FastAPI server yet. The current MVP should remain focused on deterministic analysis, annotated DOCX comments, and clear student-facing guidance.

Before using this code, review at least:

- margin changes, because forcing one margin value can break one-page resumes
- tab stop fixes, because not every tab should become a right-aligned date tab
- bullet indent constants, because they need verification against approved resumes
- session filtering, because fixed or ignored issues must not reappear in comments
- any change that rewrites layout, because it may alter the visual resume unexpectedly
