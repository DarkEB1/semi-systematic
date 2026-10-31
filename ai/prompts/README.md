# Prompts

One paste-ready prompt per skill, for assistants that cannot load `.claude/skills/<name>/SKILL.md`
as a slash command the way Claude Code does. Each prompt says where the assistant is, the rules it
may not break, which files to read, the inputs to fill in, and what done looks like. The recipe
itself is never duplicated here: the prompt sends the assistant to the `SKILL.md`, which stays
the single source of truth and is checked by the repo-structure skill.

| prompt | skill | fill in |
|---|---|---|
| [new-experiment.md](new-experiment.md) | new-experiment | slug, hypothesis, datasets with snapshots |
| [pull-data.md](pull-data.md) | pull-data | source id, dataset name, cadence, vendor URL and licence |
| [refresh-data.md](refresh-data.md) | refresh-data | nothing, or the data-health issue to close |
| [promote-dataset.md](promote-dataset.md) | promote-dataset | dataset name, scratch key, snapshot date |
| [meeting-notes.md](meeting-notes.md) | meeting-notes | date, title, attendees, recording link, then the transcript |
| [build-index.md](build-index.md) | build-index | the question |
| [repo-structure.md](repo-structure.md) | repo-structure | the thing to place, or the convention to change |

Usage: copy the file's content into the assistant's chat, replace every `<...>`, and let it work
inside the devcontainer. With Claude Code just type `/<skill>` and the inputs in words
([knowledge/context/working-with-agents.md](../../knowledge/context/working-with-agents.md)).

Every prompt begins with the same preamble, [`_preamble.md`](_preamble.md), kept in one place so a
rule change is one edit.
