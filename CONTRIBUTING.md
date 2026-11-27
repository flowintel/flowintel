# Contributing to Flowintel

For development guidance, see [AGENTS.md](AGENTS.md). The [contributor documentation](doc/contributor.md) describes the database model.

## AI-assisted contributions

Every commit containing code, tests, documentation, or other content generated or materially revised with an AI tool must include a `Co-Authored-By` trailer naming the model actually used and its provider's attribution email.

Place the trailer at the end of the commit message, separated from the body by a blank line. For example:

```text
fix: preserve browser identity during chatbot requests

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

- Replace the example with the model and provider used for your contribution.
- Include a separate trailer for each contributing AI model.
- Preserve these trailers when squashing or rewriting commits.
- Mention significant AI assistance in the pull request description.
- Review, understand, and test the changes before submitting them. The human contributor remains responsible for the contribution and for answering review comments.
