# Handoff: neolunamiku, 2026-10-05

## Where things stand

- `main` is at v0.2.0 plus quick phrases, the Discord input switch, a startup option, and setup and CI hardening (PR #7). See `git log` and `CHANGELOG.md`.
- Draft [PR #9](https://github.com/neolunadev/neolunamiku/pull/9) (`wip/installer-progress-window`) replaces the console bootstrap with a progress window. Its one recorded failure (empty exit code at the venv step) came from a test harness run in a temp folder, so it may not be an installer bug. It needs a clean-machine test before merging.

## Next steps, in order

0. Rebrand the project to Ruby (see the pending note at the top of `CLAUDE.md`). The repo is now `neolunadev/ruby`.
1. Voice fidelity milestone: the spoken output adds or expands words ("I'm" is spoken "I am", "love you" is spoken "I love you"). Hypothesis, untested: Kokoro speaks the text it is given, so the change happens before Kokoro, in input transcription or a text rewrite step. Start with `superpowers:systematic-debugging` and trace the text from input to `engine/pipeline.py`.
2. Voice quality: RVC and Kokoro tuning.

## Gotchas

- Hard-won engine and audio gotchas live in `claude.md`; read them before touching `engine/`.
